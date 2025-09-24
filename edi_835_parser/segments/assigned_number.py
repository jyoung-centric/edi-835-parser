from edi_835_parser.elements.identifier import Identifier
from edi_835_parser.elements.integer import Integer
from edi_835_parser.segments.utilities import split_segment


class AssignedNumber:
	identification = 'LX'

	identifier = Identifier()
	assigned_number = Integer()

	def __init__(self, segment: str):
		self.segment = segment
		segment = split_segment(segment)

		self.identifier = segment[0]
		self.assigned_number = segment[1]

	def __repr__(self) -> str:
		return '\n'.join(str(item) for item in self.__dict__.items())

	def __str__(self) -> str:
		return f'Assigned Number: {self.assigned_number}'


if __name__ == '__main__':
	pass