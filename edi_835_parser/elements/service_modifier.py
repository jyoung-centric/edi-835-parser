from typing import List, Optional

from edi_835_parser.elements import Element
from edi_835_parser.elements.utilities import split_element


def parse_service_modifiers(value: str) -> List[str]:
	"""Return the populated SVC01 procedure modifiers (positions 3-6)."""
	components = split_element(value)
	return [modifier for modifier in components[2:6] if modifier]


class ServiceModifier(Element):
	"""Parse the first modifier while preserving the legacy scalar API."""

	def parser(self, value: str) -> Optional[str]:
		modifiers = parse_service_modifiers(value)
		return modifiers[0] if modifiers else None


class ServiceModifiers(Element):
	"""Parse all procedure modifiers from the SVC01 composite."""

	def parser(self, value: str) -> List[str]:
		return parse_service_modifiers(value)
