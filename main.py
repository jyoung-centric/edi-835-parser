import edi_835_parser

# Parse to JSON (new functionality)
json_data = edi_835_parser.parse_to_json('testfiles\PT13882.0022345 1.DT20250710')
print(json_data)