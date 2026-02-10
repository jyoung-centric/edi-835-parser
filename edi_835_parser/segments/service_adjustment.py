from typing import List, Dict, Any
from edi_835_parser.elements.identifier import Identifier
from edi_835_parser.elements.dollars import Dollars
from edi_835_parser.elements.adjustment_group_code import AdjustmentGroupCode
from edi_835_parser.elements.adjustment_reason_code import AdjustmentReasonCode
from edi_835_parser.segments.utilities import split_segment


class AdjustmentGroup:
	"""Represents a single adjustment group within a CAS segment"""
	def __init__(self, reason_code: str, amount: str, quantity: str = None):
		self.reason_code = reason_code
		self.amount = amount
		self.quantity = quantity if quantity else ""

	def to_dict(self) -> Dict[str, Any]:
		"""Convert adjustment group to dictionary"""
		return {
			"claim_adjustment_reason_code": str(self.reason_code),
			"monetary_amount": str(self.amount),
			"quantity": str(self.quantity)
		}

	def __repr__(self):
		return f"AdjustmentGroup(reason_code={self.reason_code}, amount={self.amount}, quantity={self.quantity})"


class ServiceAdjustment:
	identification = 'CAS'

	identifier = Identifier()
	group_code = AdjustmentGroupCode()
	adjustment_groups = List[AdjustmentGroup]

	def __init__(self, segment: str):
		self.segment = segment
		segment = split_segment(segment)

		self.identifier = segment[0]
		self.group_code = segment[1]

		# Parse multiple adjustment groups (reason_code, amount, quantity triplets)
		# Pattern: CAS*group_code*reason_code_1*amount_1*quantity_1*reason_code_2*amount_2*quantity_2*...
		self.adjustment_groups = []
		i = 2
		while i < len(segment):
			if i + 2 < len(segment):
				# Full triplet: reason_code, amount, quantity
				reason_code = segment[i]
				amount = segment[i + 1]
				quantity = segment[i + 2] if i + 2 < len(segment) else ""
				self.adjustment_groups.append(AdjustmentGroup(reason_code, amount, quantity))
				i += 3
			elif i + 1 < len(segment):
				# Partial: reason_code, amount only
				reason_code = segment[i]
				amount = segment[i + 1]
				self.adjustment_groups.append(AdjustmentGroup(reason_code, amount))
				i += 2
			else:
				break

		# Maintain backward compatibility - expose first adjustment group as properties
		if self.adjustment_groups:
			self.reason_code = self.adjustment_groups[0].reason_code
			self.amount = self.adjustment_groups[0].amount
			self.quantity = self.adjustment_groups[0].quantity
		else:
			self.reason_code = None
			self.amount = None
			self.quantity = None

	def __repr__(self):
		return '\n'.join(str(item) for item in self.__dict__.items())


if __name__ == '__main__':
	pass
