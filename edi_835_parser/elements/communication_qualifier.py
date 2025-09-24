from edi_835_parser.elements import Element

# Communication number qualifiers commonly used in EDI 835
communication_qualifiers = {
	'TE': 'telephone',
	'FX': 'facsimile',
	'UR': 'uniform resource locator (URL)',
	'EM': 'electronic mail',
	'EX': 'telephone extension',
}


class CommunicationQualifier(Element):

	def parser(self, value: str) -> str:
		return communication_qualifiers.get(value, value)