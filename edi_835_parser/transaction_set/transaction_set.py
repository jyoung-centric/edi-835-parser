from typing import List, Iterator, Optional, Dict, Any
from collections import namedtuple
import json

import pandas as pd

from edi_835_parser.loops.claim import Claim as ClaimLoop
from edi_835_parser.loops.service import Service as ServiceLoop
from edi_835_parser.loops.organization import Organization as OrganizationLoop
from edi_835_parser.segments.utilities import find_identifier, split_segment
from edi_835_parser.segments.interchange import Interchange as InterchangeSegment
from edi_835_parser.segments.financial_information import FinancialInformation as FinancialInformationSegment
from edi_835_parser.segments.trace import Trace as TraceSegment

BuildAttributeResponse = namedtuple('BuildAttributeResponse', 'key value segment segments')


class TransactionSet:

	def __init__(
			self,
			interchange: InterchangeSegment,
			financial_information: FinancialInformationSegment,
			trace: TraceSegment,
			claims: List[ClaimLoop],
			organizations: List[OrganizationLoop],
			file_path: str,
	):
		self.interchange = interchange
		self.financial_information = financial_information
		self.trace = trace
		self.claims = claims
		self.organizations = organizations
		self.file_path = file_path

	def __repr__(self):
		return '\n'.join(str(item) for item in self.__dict__.items())

	@property
	def payer(self) -> OrganizationLoop:
		payer = [o for o in self.organizations if o.organization.type == 'payer']
		assert len(payer) == 1
		return payer[0]

	@property
	def payee(self) -> OrganizationLoop:
		payee = [o for o in self.organizations if o.organization.type == 'payee']
		assert len(payee) == 1
		return payee[0]

	def to_dataframe(self) -> pd.DataFrame:
		"""flatten the remittance advice by service to a pandas DataFrame"""
		data = []
		for claim in self.claims:
			for service in claim.services:

				datum = TransactionSet.serialize_service(
					self.financial_information,
					self.payer,
					claim,
					service
				)

				for index, adjustment in enumerate(service.adjustments):
					datum[f'adj_{index}_group'] = adjustment.group_code.code
					datum[f'adj_{index}_code'] = adjustment.reason_code.code
					datum[f'adj_{index}_amount'] = adjustment.amount

				for index, reference in enumerate(service.references):
					datum[f'ref_{index}_qual'] = reference.qualifier.code
					datum[f'ref_{index}_value'] = reference.value

				for index, remark in enumerate(service.remarks):
					datum[f'rem_{index}_qual'] = remark.qualifier.code
					datum[f'rem_{index}_code'] = remark.code.code

				data.append(datum)

		return pd.DataFrame(data)

	@staticmethod
	def serialize_service(
			financial_information: FinancialInformationSegment,
			payer: OrganizationLoop,
			claim: ClaimLoop,
			service: ServiceLoop,
	) -> dict:
		# if the service doesn't have a start date assume the service and claim dates match
		start_date = None
		if service.service_period_start:
			start_date = service.service_period_start.date
		elif claim.claim_statement_period_start:
			start_date = claim.claim_statement_period_start.date

		# if the service doesn't have an end date assume the service and claim dates match
		end_date = None
		if service.service_period_end:
			end_date = service.service_period_end.date
		elif claim.claim_statement_period_end:
			end_date = claim.claim_statement_period_end.date

		datum = {
			'marker': claim.claim.marker,
			'patient': claim.patient.name,
			'code': service.service.code,
			'modifier': service.service.modifier,
			'qualifier': service.service.qualifier,
			'allowed_units': service.service.allowed_units,
			'billed_units': service.service.billed_units,
			'transaction_date': financial_information.transaction_date,
			'icn': claim.claim.icn,
			'charge_amount': service.service.charge_amount,
			'allowed_amount': service.allowed_amount,
			'paid_amount': service.service.paid_amount,
			'payer': payer.organization.name,
			'start_date': start_date,
			'end_date': end_date,
			'rendering_provider': claim.rendering_provider.name if claim.rendering_provider else None,
			'payer_classification': str(claim.claim.status.payer_classification),
			'was_forwarded': claim.claim.status.was_forwarded
		}

		return datum

	def to_json(self) -> Dict[str, Any]:
		"""Convert the EDI 835 transaction set to JSON format matching the provided schema"""
		# Parse the raw file to extract all segments
		with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
			file_content = f.read()
		
		# Check if file needs preprocessing by looking for special characters
		needs_preprocessing = any(char in file_content for char in ['\x1d', '\x1e', '\x1f'])
		
		if needs_preprocessing:
			# Apply preprocessing 
			from edi_835_parser import preprocess_edi_content
			file_content = preprocess_edi_content(file_content)
			# Also try ':' as segment terminator for preprocessed content
			segments = file_content.split(':')
		else:
			segments = file_content.split('~')
		
		segments = [segment.strip() for segment in segments if segment.strip()]
		
		# Initialize JSON structure
		json_data = {
			"interchange": {
				"ISA": None,
				"GS": None,
				"transactions": [],
				"GE": None,
				"IEA": None
			}
		}
		
		current_transaction = None
		current_n1_loop = None
		current_clp_loop = None
		current_svc_loop = None
		
		for segment in segments:
			if not segment:
				continue
				
			parts = split_segment(segment)
			identifier = parts[0] if parts else ""
			
			if identifier == "ISA":
				json_data["interchange"]["ISA"] = self._convert_isa_segment(segment)
			elif identifier == "GS":
				json_data["interchange"]["GS"] = self._convert_gs_segment(segment)
			elif identifier == "ST":
				current_transaction = {
					"ST": self._convert_st_segment(segment),
					"BPR": None,
					"TRN": None,
					"DTM": [],
					"N1_loop": [],
					"CLP_loop": [],
					"PLB": [],
					"SE": None
				}
				json_data["interchange"]["transactions"].append(current_transaction)
			elif identifier == "BPR" and current_transaction:
				current_transaction["BPR"] = self._convert_bpr_segment(segment)
			elif identifier == "TRN" and current_transaction:
				current_transaction["TRN"] = self._convert_trn_segment(segment)
			elif identifier == "DTM" and current_transaction:
				dtm_data = self._convert_dtm_segment(segment)
				if current_svc_loop:
					if "DTM" not in current_svc_loop:
						current_svc_loop["DTM"] = []
					current_svc_loop["DTM"].append(dtm_data)
				else:
					current_transaction["DTM"].append(dtm_data)
			elif identifier == "N1" and current_transaction:
				current_n1_loop = {
					"N1": self._convert_n1_segment(segment),
					"N3": None,
					"N4": None,
					"PER": None
				}
				current_transaction["N1_loop"].append(current_n1_loop)
			elif identifier == "N3" and current_n1_loop:
				current_n1_loop["N3"] = self._convert_n3_segment(segment)
			elif identifier == "N4" and current_n1_loop:
				current_n1_loop["N4"] = self._convert_n4_segment(segment)
			elif identifier == "PER" and current_n1_loop:
				current_n1_loop["PER"] = self._convert_per_segment(segment)
			elif identifier == "REF" and current_transaction:
				ref_data = self._convert_ref_segment(segment)
				if current_svc_loop:
					if "REF" not in current_svc_loop:
						current_svc_loop["REF"] = []
					current_svc_loop["REF"].append(ref_data)
				elif current_clp_loop:
					if "REF" not in current_clp_loop:
						current_clp_loop["REF"] = []
					current_clp_loop["REF"].append(ref_data)
			elif identifier == "LX" and current_transaction:
				# LX starts a new claim grouping - this is handled within CLP loop
				pass
			elif identifier == "CLP" and current_transaction:
				current_clp_loop = {
					"CLP": self._convert_clp_segment(segment),
					"CAS": [],
					"NM1": [],
					"DTM": [],
					"AMT": [],
					"REF": [],
					"SVC_loop": []
				}
				current_transaction["CLP_loop"].append(current_clp_loop)
				current_svc_loop = None
			elif identifier == "CAS" and current_clp_loop:
				if current_svc_loop:
					if "CAS" not in current_svc_loop:
						current_svc_loop["CAS"] = []
					current_svc_loop["CAS"].append(self._convert_cas_segment(segment))
				else:
					current_clp_loop["CAS"].append(self._convert_cas_segment(segment))
			elif identifier == "NM1" and current_clp_loop:
				current_clp_loop["NM1"].append(self._convert_nm1_segment(segment))
			elif identifier == "AMT" and current_clp_loop:
				if current_svc_loop:
					if "AMT" not in current_svc_loop:
						current_svc_loop["AMT"] = []
					current_svc_loop["AMT"].append(self._convert_amt_segment(segment))
				else:
					current_clp_loop["AMT"].append(self._convert_amt_segment(segment))
			elif identifier == "SVC" and current_clp_loop:
				current_svc_loop = {
					"SVC": self._convert_svc_segment(segment)
				}
				current_clp_loop["SVC_loop"].append(current_svc_loop)
			elif identifier == "PLB" and current_transaction:
				current_transaction["PLB"].append(self._convert_plb_segment(segment))
			elif identifier == "SE" and current_transaction:
				current_transaction["SE"] = self._convert_se_segment(segment)
				current_transaction = None
				current_n1_loop = None
				current_clp_loop = None
				current_svc_loop = None
			elif identifier == "GE":
				json_data["interchange"]["GE"] = self._convert_ge_segment(segment)
			elif identifier == "IEA":
				json_data["interchange"]["IEA"] = self._convert_iea_segment(segment)
		
		return json_data

	def _convert_isa_segment(self, segment: str) -> Dict[str, str]:
		"""Convert ISA segment to JSON format"""
		parts = split_segment(segment)
		return {
			"authorization_information_qualifier": parts[1] if len(parts) > 1 else "",
			"authorization_information": parts[2] if len(parts) > 2 else "",
			"security_information_qualifier": parts[3] if len(parts) > 3 else "",
			"security_information": parts[4] if len(parts) > 4 else "",
			"interchange_sender_id_qualifier": parts[5] if len(parts) > 5 else "",
			"interchange_sender_id": parts[6] if len(parts) > 6 else "",
			"interchange_receiver_id_qualifier": parts[7] if len(parts) > 7 else "",
			"interchange_receiver_id": parts[8] if len(parts) > 8 else "",
			"interchange_date": parts[9] if len(parts) > 9 else "",
			"interchange_time": parts[10] if len(parts) > 10 else "",
			"interchange_control_standards_identifier": parts[11] if len(parts) > 11 else "",
			"interchange_control_version_number": parts[12] if len(parts) > 12 else "",
			"interchange_control_number": parts[13] if len(parts) > 13 else "",
			"acknowledgement_requested": parts[14] if len(parts) > 14 else "",
			"usage_indicator": parts[15] if len(parts) > 15 else "",
			"component_element_separator": parts[16] if len(parts) > 16 else ""
		}

	def _convert_gs_segment(self, segment: str) -> Dict[str, str]:
		"""Convert GS segment to JSON format"""
		parts = split_segment(segment)
		return {
			"functional_identifier_code": parts[1] if len(parts) > 1 else "",
			"application_sender_code": parts[2] if len(parts) > 2 else "",
			"application_receiver_id": parts[3] if len(parts) > 3 else "",
			"date": parts[4] if len(parts) > 4 else "",
			"time": parts[5] if len(parts) > 5 else "",
			"group_control_number": parts[6] if len(parts) > 6 else "",
			"responsible_agency_code": parts[7] if len(parts) > 7 else "",
			"version_release_industry_identifier": parts[8] if len(parts) > 8 else ""
		}

	def _convert_st_segment(self, segment: str) -> Dict[str, str]:
		"""Convert ST segment to JSON format"""
		parts = split_segment(segment)
		return {
			"transaction_set_identifier_code": parts[1] if len(parts) > 1 else "",
			"transaction_set_control_number": parts[2] if len(parts) > 2 else ""
		}

	def _convert_bpr_segment(self, segment: str) -> Dict[str, str]:
		"""Convert BPR segment to JSON format"""
		parts = split_segment(segment)
		return {
			"transaction_handling_code": parts[1] if len(parts) > 1 else "",
			"monetary_amount": parts[2] if len(parts) > 2 else "",
			"credit_debit_flag": parts[3] if len(parts) > 3 else "",
			"payment_method_code": parts[4] if len(parts) > 4 else "",
			"payment_format_code": parts[5] if len(parts) > 5 else "",
			"dfi_id_number_qualifier": parts[6] if len(parts) > 6 else "",
			"dfi_identification_number": parts[7] if len(parts) > 7 else "",
			"account_number_qualifier": parts[8] if len(parts) > 8 else "",
			"sender_bank_account_number": parts[9] if len(parts) > 9 else "",
			"originating_company_identifier": parts[10] if len(parts) > 10 else "",
			"originating_company_supplemental_code": parts[11] if len(parts) > 11 else "",
			"dfi_identification_number_qualifier": parts[12] if len(parts) > 12 else "",
			"receiver_or_provider_bank_id_number": parts[13] if len(parts) > 13 else "",
			"account_number_qualifier_2": parts[14] if len(parts) > 14 else "",
			"receiver_or_provider_account_number": parts[15] if len(parts) > 15 else "",
			"check_issue_or_eft_effective_date": parts[16] if len(parts) > 16 else ""
		}

	def _convert_trn_segment(self, segment: str) -> Dict[str, str]:
		"""Convert TRN segment to JSON format"""
		parts = split_segment(segment)
		return {
			"trace_type_code": parts[1] if len(parts) > 1 else "",
			"reference_identification": parts[2] if len(parts) > 2 else "",
			"originating_company_identifier": parts[3] if len(parts) > 3 else "",
			"originating_company_supplemental_code": parts[4] if len(parts) > 4 else ""
		}

	def _convert_dtm_segment(self, segment: str) -> Dict[str, str]:
		"""Convert DTM segment to JSON format"""
		parts = split_segment(segment)
		return {
			"date_time_qualifier": parts[1] if len(parts) > 1 else "",
			"date": parts[2] if len(parts) > 2 else "",
			"time": parts[3] if len(parts) > 3 else "",
			"time_code": parts[4] if len(parts) > 4 else "",
			"date_time_period_format": parts[5] if len(parts) > 5 else "",
			"date_time_period": parts[6] if len(parts) > 6 else ""
		}

	def _convert_n1_segment(self, segment: str) -> Dict[str, str]:
		"""Convert N1 segment to JSON format"""
		parts = split_segment(segment)
		return {
			"entity_identifier_code": parts[1] if len(parts) > 1 else "",
			"name": parts[2] if len(parts) > 2 else "",
			"identification_code_qualifier": parts[3] if len(parts) > 3 else "",
			"identification_code": parts[4] if len(parts) > 4 else ""
		}

	def _convert_n3_segment(self, segment: str) -> Dict[str, str]:
		"""Convert N3 segment to JSON format"""
		parts = split_segment(segment)
		return {
			"address_line_1": parts[1] if len(parts) > 1 else "",
			"address_line_2": parts[2] if len(parts) > 2 else ""
		}

	def _convert_n4_segment(self, segment: str) -> Dict[str, str]:
		"""Convert N4 segment to JSON format"""
		parts = split_segment(segment)
		return {
			"city_name": parts[1] if len(parts) > 1 else "",
			"state_code": parts[2] if len(parts) > 2 else "",
			"postal_code": parts[3] if len(parts) > 3 else "",
			"country_code": parts[4] if len(parts) > 4 else "",
			"location_qualifier": parts[5] if len(parts) > 5 else "",
			"location_identifier": parts[6] if len(parts) > 6 else ""
		}

	def _convert_per_segment(self, segment: str) -> Dict[str, str]:
		"""Convert PER segment to JSON format"""
		parts = split_segment(segment)
		return {
			"contact_function_code": parts[1] if len(parts) > 1 else "",
			"contact_name": parts[2] if len(parts) > 2 else "",
			"communication_number_qualifier_1": parts[3] if len(parts) > 3 else "",
			"communication_number_1": parts[4] if len(parts) > 4 else "",
			"communication_number_qualifier_2": parts[5] if len(parts) > 5 else "",
			"communication_number_2": parts[6] if len(parts) > 6 else "",
			"communication_number_qualifier_3": parts[7] if len(parts) > 7 else "",
			"communication_number_3": parts[8] if len(parts) > 8 else "",
			"contact_inquiry_reference": parts[9] if len(parts) > 9 else ""
		}

	def _convert_ref_segment(self, segment: str) -> Dict[str, str]:
		"""Convert REF segment to JSON format"""
		parts = split_segment(segment)
		return {
			"reference_identification_qualifier": parts[1] if len(parts) > 1 else "",
			"reference_identification": parts[2] if len(parts) > 2 else "",
			"description": parts[3] if len(parts) > 3 else "",
			"reference_identifier": parts[4] if len(parts) > 4 else ""
		}

	def _convert_clp_segment(self, segment: str) -> Dict[str, str]:
		"""Convert CLP segment to JSON format"""
		parts = split_segment(segment)
		return {
			"patient_control_number": parts[1] if len(parts) > 1 else "",
			"claim_status_code": parts[2] if len(parts) > 2 else "",
			"total_claim_charge_amount": parts[3] if len(parts) > 3 else "",
			"total_claim_payment_amount": parts[4] if len(parts) > 4 else "",
			"patient_responsibility_amount": parts[5] if len(parts) > 5 else "",
			"claim_filing_indicator_code": parts[6] if len(parts) > 6 else "",
			"payer_claim_control_number": parts[7] if len(parts) > 7 else "",
			"facility_type_code": parts[8] if len(parts) > 8 else "",
			"claim_frequency_code": parts[9] if len(parts) > 9 else "",
			"patient_status_code": parts[10] if len(parts) > 10 else "",
			"diagnosis_related_group_code": parts[11] if len(parts) > 11 else "",
			"drg_weight": parts[12] if len(parts) > 12 else "",
			"discharge_fraction": parts[13] if len(parts) > 13 else ""
		}

	def _convert_cas_segment(self, segment: str) -> Dict[str, str]:
		"""Convert CAS segment to JSON format"""
		parts = split_segment(segment)
		return {
			"claim_adjustment_group_code": parts[1] if len(parts) > 1 else "",
			"adjustment_reason_code": parts[2] if len(parts) > 2 else "",
			"adjustment_amount": parts[3] if len(parts) > 3 else "",
			"adjustment_quantity": parts[4] if len(parts) > 4 else "",
			"adjustment_reason_code_2": parts[5] if len(parts) > 5 else "",
			"adjustment_amount_2": parts[6] if len(parts) > 6 else "",
			"adjustment_quantity_2": parts[7] if len(parts) > 7 else "",
			"adjustment_reason_code_3": parts[8] if len(parts) > 8 else "",
			"adjustment_amount_3": parts[9] if len(parts) > 9 else "",
			"adjustment_quantity_3": parts[10] if len(parts) > 10 else "",
			"adjustment_reason_code_4": parts[11] if len(parts) > 11 else "",
			"adjustment_amount_4": parts[12] if len(parts) > 12 else "",
			"adjustment_quantity_4": parts[13] if len(parts) > 13 else "",
			"adjustment_reason_code_5": parts[14] if len(parts) > 14 else "",
			"adjustment_amount_5": parts[15] if len(parts) > 15 else "",
			"adjustment_quantity_5": parts[16] if len(parts) > 16 else "",
			"adjustment_reason_code_6": parts[17] if len(parts) > 17 else "",
			"adjustment_amount_6": parts[18] if len(parts) > 18 else "",
			"adjustment_quantity_6": parts[19] if len(parts) > 19 else ""
		}

	def _convert_nm1_segment(self, segment: str) -> Dict[str, str]:
		"""Convert NM1 segment to JSON format"""
		parts = split_segment(segment)
		return {
			"entity_identifier_code": parts[1] if len(parts) > 1 else "",
			"entity_type_qualifier": parts[2] if len(parts) > 2 else "",
			"last_name": parts[3] if len(parts) > 3 else "",
			"first_name": parts[4] if len(parts) > 4 else "",
			"middle_name": parts[5] if len(parts) > 5 else "",
			"name_prefix": parts[6] if len(parts) > 6 else "",
			"name_suffix": parts[7] if len(parts) > 7 else "",
			"identification_code_qualifier": parts[8] if len(parts) > 8 else "",
			"identification_code": parts[9] if len(parts) > 9 else "",
			"entity_relationship_code": parts[10] if len(parts) > 10 else "",
			"entity_identifier_code_2": parts[11] if len(parts) > 11 else "",
			"identification_code_qualifier_2": parts[12] if len(parts) > 12 else ""
		}

	def _convert_amt_segment(self, segment: str) -> Dict[str, str]:
		"""Convert AMT segment to JSON format"""
		parts = split_segment(segment)
		return {
			"amount_qualifier_code": parts[1] if len(parts) > 1 else "",
			"monetary_amount": parts[2] if len(parts) > 2 else "",
			"credit_debit_flag_code": parts[3] if len(parts) > 3 else ""
		}

	def _convert_svc_segment(self, segment: str) -> Dict[str, str]:
		"""Convert SVC segment to JSON format"""
		parts = split_segment(segment)
		return {
			"service_type_code": parts[1] if len(parts) > 1 else "",
			"charge_amount": parts[2] if len(parts) > 2 else "",
			"payment_amount": parts[3] if len(parts) > 3 else "",
			"revenue_code": parts[4] if len(parts) > 4 else "",
			"units_of_service_paid": parts[5] if len(parts) > 5 else "",
			"original_units_of_service": parts[6] if len(parts) > 6 else "",
			"adjudicated_date": parts[7] if len(parts) > 7 else ""
		}

	def _convert_plb_segment(self, segment: str) -> Dict[str, str]:
		"""Convert PLB segment to JSON format"""
		parts = split_segment(segment)
		return {
			"provider_identifier": parts[1] if len(parts) > 1 else "",
			"fiscal_period_date": parts[2] if len(parts) > 2 else "",
			"provider_adjustment_identifier": parts[3] if len(parts) > 3 else "",
			"provider_adjustment_amount": parts[4] if len(parts) > 4 else "",
			"provider_adjustment_identifier_2": parts[5] if len(parts) > 5 else "",
			"provider_adjustment_amount_2": parts[6] if len(parts) > 6 else ""
		}

	def _convert_se_segment(self, segment: str) -> Dict[str, str]:
		"""Convert SE segment to JSON format"""
		parts = split_segment(segment)
		return {
			"number_of_included_segments": parts[1] if len(parts) > 1 else "",
			"transaction_set_control_number": parts[2] if len(parts) > 2 else ""
		}

	def _convert_ge_segment(self, segment: str) -> Dict[str, str]:
		"""Convert GE segment to JSON format"""
		parts = split_segment(segment)
		return {
			"number_of_transaction_sets_included": parts[1] if len(parts) > 1 else "",
			"group_control_number": parts[2] if len(parts) > 2 else ""
		}

	def _convert_iea_segment(self, segment: str) -> Dict[str, str]:
		"""Convert IEA segment to JSON format"""
		parts = split_segment(segment)
		return {
			"number_of_included_functional_groups": parts[1] if len(parts) > 1 else "",
			"interchange_control_number": parts[2] if len(parts) > 2 else ""
		}

	@classmethod
	def build(cls, file_path: str) -> 'TransactionSet':
		interchange = None
		financial_information = None
		trace = None
		claims = []
		organizations = []

		with open(file_path) as f:
			file = f.read()

		segments = file.split('~')
		segments = [segment.strip() for segment in segments]

		segments = iter(segments)
		segment = None

		while True:
			response = cls.build_attribute(segment, segments)
			segment = response.segment
			segments = response.segments

			# no more segments to parse
			if response.segments is None:
				break

			if response.key == 'interchange':
				interchange = response.value

			if response.key == 'financial information':
				financial_information = response.value

			if response.key == 'trace':
				trace = response.value

			if response.key == 'organization':
				organizations.append(response.value)

			if response.key == 'claim':
				claims.append(response.value)

		return TransactionSet(interchange, financial_information, trace, claims, organizations, file_path)

	@classmethod
	def build_attribute(cls, segment: Optional[str], segments: Iterator[str]) -> BuildAttributeResponse:
		if segment is None:
			try:
				segment = segments.__next__()
			except StopIteration:
				return BuildAttributeResponse(None, None, None, None)

		identifier = find_identifier(segment)

		if identifier == InterchangeSegment.identification:
			interchange = InterchangeSegment(segment)
			return BuildAttributeResponse('interchange', interchange, None, segments)

		if identifier == FinancialInformationSegment.identification:
			financial_information = FinancialInformationSegment(segment)
			return BuildAttributeResponse('financial information', financial_information, None, segments)

		if identifier == TraceSegment.identification:
			trace = TraceSegment(segment)
			return BuildAttributeResponse('trace', trace, None, segments)

		if identifier == OrganizationLoop.initiating_identifier:
			organization, segments, segment = OrganizationLoop.build(segment, segments)
			return BuildAttributeResponse('organization', organization, segment, segments)

		elif identifier == ClaimLoop.initiating_identifier:
			claim, segments, segment = ClaimLoop.build(segment, segments)
			return BuildAttributeResponse('claim', claim, segment, segments)

		else:
			return BuildAttributeResponse(None, None, None, segments)


if __name__ == '__main__':
	pass