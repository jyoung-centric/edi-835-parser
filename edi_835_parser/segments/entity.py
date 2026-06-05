from edi_835_parser.elements.identifier import Identifier
from edi_835_parser.elements.entity_code import EntityCode
from edi_835_parser.elements.entity_type import EntityType
from edi_835_parser.elements.identification_code_qualifier import IdentificationCodeQualifier
from edi_835_parser.segments.utilities import split_segment, get_element


class Entity:
	identification = 'NM1'

	identifier = Identifier()
	entity = EntityCode()
	type = EntityType()
	identification_code_qualifier = IdentificationCodeQualifier()

	def __init__(self, segment: str):
		self.segment = segment
		segment = split_segment(segment)

		self.identifier = get_element(segment, 0)
		self.entity = get_element(segment, 1)
		self.type = get_element(segment, 2)
		self.last_name = get_element(segment, 3)
		self.first_name = get_element(segment, 4)
		self.middle_name = get_element(segment, 5)
		self.name_prefix = get_element(segment, 6)
		self.name_suffix = get_element(segment, 7)
		self.identification_code_qualifier = get_element(segment, 8)
		self.identification_code = get_element(segment, 9)

	def __repr__(self):
		return '\n'.join(str(item) for item in self.__dict__.items())

	@property
	def name(self) -> str:
		name_parts = [self.first_name, self.middle_name, self.last_name]
		full_name = ' '.join(part for part in name_parts if part)
		return full_name.title()


if __name__ == '__main__':
	pass
