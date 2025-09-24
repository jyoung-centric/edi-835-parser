from edi_835_parser.elements import Element

# Contact function codes commonly used in EDI 835
contact_function_codes = {
	'BL': 'billing contact',
	'CX': 'correspondence contact',
	'IC': 'information contact',
	'TE': 'technical contact',
}


class ContactFunctionCode(Element):

	def parser(self, value: str) -> str:
		return contact_function_codes.get(value, value)