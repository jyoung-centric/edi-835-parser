from typing import Dict, Any, List
from abc import ABC, abstractmethod

class JsonMixin(ABC):
    """Base mixin for JSON conversion"""
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation"""
        pass

class ClaimLoopJsonMixin(JsonMixin):
    """JSON conversion mixin for ClaimLoop"""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "CLP": {
                "patient_control_number": str(self.claim.marker),
                "claim_status_code": str(self.claim.status),
                "total_claim_charge_amount": str(self.claim.charge_amount),
                "total_claim_payment_amount": str(self.claim.paid_amount),
                "patient_responsibility_amount": "",
                "claim_filing_indicator_code": str(self.claim.claim_type),
                "payer_claim_control_number": str(self.claim.icn),
                "facility_type_code": "",
                "claim_frequency_code": "",
                "patient_status_code": "",
                "diagnosis_related_group_code": "",
                "drg_weight": "",
                "discharge_fraction": ""
            },
            "CAS": self._get_claim_cas_data(),
            "NM1": self._get_nm1_data(),
            "DTM": self._get_claim_dtm_data(),
            "AMT": [],
            "REF": [],
            "SVC_loop": [svc.to_dict() for svc in self.services if hasattr(svc, 'to_dict')]
        }
    
    def _get_nm1_data(self) -> List[Dict[str, Any]]:
        """Extract NM1 (Name) data for the claim"""
        nm1_data = []
        if self.patient:
            nm1_data.append({
                "entity_identifier_code": str(self.patient.entity),
                "entity_type_qualifier": str(self.patient.type),
                "last_name": self.patient.last_name or "",
                "first_name": self.patient.first_name or "",
                "middle_name": "",
                "name_prefix": "",
                "name_suffix": "",
                "identification_code_qualifier": str(self.patient.identification_code_qualifier) if self.patient.identification_code_qualifier else "",
                "identification_code": str(self.patient.identification_code) if self.patient.identification_code else "",
                "entity_relationship_code": "",
                "entity_identifier_code_2": "",
                "identification_code_qualifier_2": ""
            })
        return nm1_data
    
    def _get_claim_dtm_data(self) -> List[Dict[str, Any]]:
        """Extract DTM (Date) data for the claim"""
        dtm_data = []
        if self.dates:
            for date_obj in self.dates:
                dtm_data.append({
                    "date_time_qualifier": str(date_obj.qualifier),
                    "date": date_obj.date.strftime('%Y%m%d') if hasattr(date_obj.date, 'strftime') else str(date_obj.date),
                    "time": "",
                    "time_code": "",
                    "date_time_period_format": "",
                    "date_time_period": ""
                })
        return dtm_data

    def _get_claim_amt_data(self) -> List[Dict[str, Any]]:
        """Extract AMT (Amount) data for the claim"""
        amt_data = []
        if self.amounts:
            for amount in self.amounts:
                amt_data.append({
                    "amount_qualifier_code": str(amount.qualifier.code),
                    "monetary_amount": str(amount.amount),
                    "credit_debit_flag_code": amount.credit_debit_flag_code
                })
        return amt_data

    def _get_claim_cas_data(self) -> List[Dict[str, Any]]:
        """Extract CAS (Claim Adjustment) data for the claim"""
        cas_data = []
        if hasattr(self, 'adjustments') and self.adjustments:
            for adjustment in self.adjustments:
                # Extract group code - handle both Code objects and strings
                group_code = adjustment.group_code
                if hasattr(group_code, 'code'):
                    group_code = group_code.code

                cas_entry = {
                    "claim_adjustment_group_code": str(group_code),
                    "adjustments": []
                }
                # Add all adjustment groups
                if hasattr(adjustment, 'adjustment_groups'):
                    for adj_group in adjustment.adjustment_groups:
                        cas_entry["adjustments"].append(adj_group.to_dict())
                cas_data.append(cas_entry)
        return cas_data

class ServiceLoopJsonMixin(JsonMixin):
    """JSON conversion mixin for ServiceLoop"""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "SVC": {
                "service_type_code": str(self.service.code),
                "charge_amount": str(self.service.charge_amount),
                "payment_amount": str(self.service.paid_amount),
                "revenue_code": "",
                "units_of_service_paid": str(self.service.allowed_units),
                "original_units_of_service": str(self.service.billed_units),
                "adjudicated_date": ""
            },
            "DTM": self._get_service_dtm_data(),
            "CAS": self._get_service_cas_data(),
            "REF": [],
            "AMT": self._get_service_amt_data()
        }
    
    def _get_service_dtm_data(self) -> List[Dict[str, Any]]:
        """Extract DTM (Date) data for the service"""
        dtm_data = []
        if self.dates:
            for date_obj in self.dates:
                dtm_data.append({
                    "date_time_qualifier": str(date_obj.qualifier),
                    "date": date_obj.date.strftime('%Y%m%d') if hasattr(date_obj.date, 'strftime') else str(date_obj.date),
                    "time": "",
                    "time_code": "",
                    "date_time_period_format": "",
                    "date_time_period": ""
                })
        return dtm_data
    
    def _get_service_amt_data(self) -> List[Dict[str, Any]]:
        """Extract AMT (Amount) data for the service"""
        amt_data = []
        if self.allowed_amount:
            amt_data.append({
                "amount_qualifier_code": "B6",
                "monetary_amount": str(self.allowed_amount),
                "credit_debit_flag_code": ""
            })
        return amt_data

    def _get_service_cas_data(self) -> List[Dict[str, Any]]:
        """Extract CAS (Claim Adjustment) data for the service"""
        cas_data = []
        if hasattr(self, 'adjustments') and self.adjustments:
            for adjustment in self.adjustments:
                # Extract group code - handle both Code objects and strings
                group_code = adjustment.group_code
                if hasattr(group_code, 'code'):
                    group_code = group_code.code

                cas_entry = {
                    "claim_adjustment_group_code": str(group_code),
                    "adjustments": []
                }
                # Add all adjustment groups
                if hasattr(adjustment, 'adjustment_groups'):
                    for adj_group in adjustment.adjustment_groups:
                        cas_entry["adjustments"].append(adj_group.to_dict())
                cas_data.append(cas_entry)
        return cas_data

class OrganizationLoopJsonMixin(JsonMixin):
    """JSON conversion mixin for OrganizationLoop"""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "N1": {
                "entity_identifier_code": self._get_entity_identifier(),
                "name": self.organization.name,
                "identification_code_qualifier": "",
                "identification_code": str(self.organization.identification_code) if self.organization.identification_code else ""
            },
            "N3": {
                "address_line_1": self.address.address if self.address else "",
                "address_line_2": ""
            },
            "N4": {
                "city_name": self.location.city if self.location else "",
                "state_code": self.location.state if self.location else "",
                "postal_code": self.location.zip_code if self.location else "",
                "country_code": "",
                "location_qualifier": "",
                "location_identifier": ""
            },
            "PER": None
        }
    
    def _get_entity_identifier(self) -> str:
        """Map organization type to entity identifier code"""
        org_type = self.organization.type.lower()
        if org_type == 'payer':
            return "PR"
        elif org_type == 'payee':
            return "PE"
        return self.organization.entity_identifier_code

class FinancialInformationJsonMixin(JsonMixin):
    """JSON conversion mixin for FinancialInformationSegment"""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_handling_code": str(self.identifier),
            "monetary_amount": str(self.amount_paid),
            "credit_debit_flag": "C",
            "payment_method_code": str(self.payment_method),
            "payment_format_code": "",
            "dfi_id_number_qualifier": "",
            "dfi_identification_number": str(self.routing_number),
            "account_number_qualifier": "",
            "sender_bank_account_number": "",
            "originating_company_identifier": "",
            "originating_company_supplemental_code": "",
            "dfi_identification_number_qualifier": "",
            "receiver_or_provider_bank_id_number": "",
            "account_number_qualifier_2": "",
            "receiver_or_provider_account_number": "",
            "check_issue_or_eft_effective_date": self.transaction_date.strftime('%Y%m%d') if self.transaction_date else ""
        }

class TraceJsonMixin(JsonMixin):
    """JSON conversion mixin for TraceSegment"""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_type_code": str(self.trace_type),
            "reference_identification": str(self.trace_number),
            "originating_company_identifier": str(self.entity_identifier) if self.entity_identifier else "",
            "originating_company_supplemental_code": ""
        }