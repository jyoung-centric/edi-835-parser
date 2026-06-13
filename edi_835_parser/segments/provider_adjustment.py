from typing import Any, Dict, List, Optional, Tuple

from edi_835_parser.segments.utilities import get_element, split_segment


class ProviderAdjustmentDetail:
	def __init__(
			self,
			reason_code: str,
			reference_id: str,
			amount: str,
			adjustment_identifier: str,
	):
		self.reason_code = reason_code
		self.reference_id = reference_id
		self.amount = amount
		self.adjustment_identifier = adjustment_identifier

	def to_dict(self) -> Dict[str, Any]:
		return {
			"provider_adjustment_reason_code": str(self.reason_code),
			"provider_adjustment_identifier": str(self.reference_id),
			"provider_adjustment_amount": str(self.amount),
			"provider_adjustment_identifier_raw": str(self.adjustment_identifier),
		}


class ProviderAdjustment:
	identification = 'PLB'

	def __init__(self, segment: str):
		self.segment = segment
		segment = split_segment(segment)

		self.identifier = get_element(segment, 0)
		self.reference_identification = get_element(segment, 1, default="")
		self.fiscal_period_date = get_element(segment, 2, default="")
		self.adjustments = self._parse_adjustments(segment)

	def _parse_adjustments(self, segment: List[str]) -> List[ProviderAdjustmentDetail]:
		adjustments = []
		index = 3
		while index < len(segment):
			adjustment_identifier = get_element(segment, index, default="")
			amount = get_element(segment, index + 1, default="")

			if adjustment_identifier or amount:
				reason_code, reference_id = self._split_adjustment_identifier(adjustment_identifier)
				adjustments.append(
					ProviderAdjustmentDetail(
						reason_code=reason_code,
						reference_id=reference_id,
						amount=amount,
						adjustment_identifier=adjustment_identifier,
					)
				)

			index += 2

		return adjustments

	@staticmethod
	def _split_adjustment_identifier(value: Optional[str]) -> Tuple[str, str]:
		if not value:
			return "", ""

		for delimiter in (':', '>', '^', '\x1f', '\x1a'):
			if delimiter in value:
				reason_code, reference_id = value.split(delimiter, 1)
				return reason_code, reference_id

		return value, ""

	def to_adjustment_dicts(self) -> List[Dict[str, Any]]:
		adjustment_dicts = []
		for adjustment in self.adjustments:
			adjustment_dict = {
				"reference_identification": str(self.reference_identification),
				"fiscal_period_date": str(self.fiscal_period_date),
			}
			adjustment_dict.update(adjustment.to_dict())
			adjustment_dicts.append(adjustment_dict)

		return adjustment_dicts

	def __repr__(self):
		return '\n'.join(str(item) for item in self.__dict__.items())
