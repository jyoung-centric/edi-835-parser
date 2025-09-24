from edi_835_parser.elements.identifier import Identifier
from edi_835_parser.elements.contact_function_code import ContactFunctionCode
from edi_835_parser.elements.communication_qualifier import CommunicationQualifier
from edi_835_parser.segments.utilities import split_segment, get_element


class Contact:
	identification = 'PER'

	identifier = Identifier()
	contact_function_code = ContactFunctionCode()
	communication_number_qualifier = CommunicationQualifier()
	communication_number_qualifier_2 = CommunicationQualifier()

	def __init__(self, segment: str):
		self.segment = segment
		segment = split_segment(segment)

		self.identifier = segment[0]
		self.contact_function_code = segment[1]
		self.name = get_element(segment, 2) if get_element(segment, 2) != '' else None
		self.communication_number_qualifier = get_element(segment, 3)
		self.communication_number = get_element(segment, 4)
		self.communication_number_qualifier_2 = get_element(segment, 5)
		self.communication_number_2 = get_element(segment, 6)

	def __repr__(self) -> str:
		return '\n'.join(str(item) for item in self.__dict__.items())

	def __str__(self) -> str:
		return f'Contact {self.contact_function_code}: {self.name or "N/A"}'


if __name__ == '__main__':
	pass