from edi_835_parser.elements.identifier import Identifier
from edi_835_parser.segments.utilities import split_segment


class Trace:
	identification = 'TRN'

	identifier = Identifier()

	def __init__(self, segment: str):
		self.segment = segment
		segment = split_segment(segment)

		self.identifier = segment[0]
		self.trace_type = segment[1]
		self.trace_number = segment[2]
		self.entity_identifier = segment[3] if len(segment) > 3 else None

	def __repr__(self) -> str:
		return '\n'.join(str(item) for item in self.__dict__.items())

	def __str__(self) -> str:
		return f'Trace {self.trace_type}: {self.trace_number}'


if __name__ == '__main__':
	pass