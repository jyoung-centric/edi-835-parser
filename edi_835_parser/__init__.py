import os
import tempfile
from typing import List, Dict, Any
from warnings import warn

from edi_835_parser.transaction_set.transaction_set import TransactionSet
from edi_835_parser.transaction_set.transaction_sets import TransactionSets
import re

# Export the main functions
__all__ = ['parse', 'parse_to_json', 'preprocess_edi_content']

# Default extension pattern for EDI files
DEFAULT_EXTENSION_PATTERN = r'\.(DAT|txt|edi|DT\d{8})$'

def normalize_x12_delimiters(edi_text: str) -> str:

	def detect_actual_segment_terminator() -> str:
		isa = edi_text[:106]
		isa_defined = isa[105]

		# check what character actually separates GS and ST
		gs_index = edi_text.find("GS")
		st_index = edi_text.find("ST", gs_index)
		actual = edi_text[st_index - 1]

		# prefer actual if ISA is inconsistent
		if actual != isa_defined:
			return actual

		return isa_defined

    # Extract original delimiters from ISA fixed positions

	segment_terminator = detect_actual_segment_terminator()	

	edi_text = edi_text.replace("\r", "").replace("\n", "")  # Remove newlines for consistent processing

	isa = edi_text[:106]
	element = isa[3]
	repetition = isa[82]
	component = isa[104]
	segment = segment_terminator
	repetition2 = ""
	mapping = {
        element: "*",
        repetition: "^",
        component: ":",
        segment: "~",
		repetition2: "^"
    }
	normalized =  "".join(mapping.get(c, c) for c in edi_text)

	return normalized  # Ensure no newlines remain

def needs_x12_normalization(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        isa = f.read(106)

    if len(isa) < 106 or not isa.startswith("ISA"):
        raise ValueError("Invalid X12 file")

    return not (
        isa[3] == "*"
        and isa[82] == "^"
        and isa[104] == ":"
        and isa[105] == "~"
    )

def preprocess_edi_content(content: str) -> str:
	"""
	Preprocess EDI content by replacing special characters with standard separators.
	
	Character mappings (as requested by user):
	- \\x1d (Group Separator) → * (element separator)
	- \\x1e (Record Separator) → ~ (component separator)  
	- \\n (newline) → empty string (remove line breaks)
	- \\x1f (Unit Separator) → : (segment terminator)
	
	Args:
		content (str): Raw EDI content string
	
	Returns:
		str: Processed EDI content with replaced separators
	"""
	processed_content = content
	print("Preprocessing EDI content with character mappings...")
	# Apply character replacements as requested by user
	processed_content = processed_content.replace('\x1d', '*')  # Element separator
	processed_content = processed_content.replace('\x1e', '~')  # Component separator
	processed_content = processed_content.replace('\n', '')     # Remove newlines
	processed_content = processed_content.replace('\x1f', ':')  # Segment terminator (user request)
	
	return processed_content

def preprocess_edi_content2(content: str) -> str:
	"""
	Preprocess EDI content by replacing special characters with standard separators.
	
	Character mappings (as requested by user):
	- \\x1C (Group Separator) → | (element separator)
	- \\x1D (Record Separator) → ~ (component separator)  
	- \\x1A (newline) → ^ (remove line breaks)
	- \\x1B (Unit Separator) → ^ (segment terminator)
	
	Args:
		content (str): Raw EDI content string
	
	Returns:
		str: Processed EDI content with replaced separators
	"""
	processed_content = content
	print("Preprocessing EDI content with second set of character mappings...")
	# Apply character replacements as requested by user
	processed_content = processed_content.replace('\x1C', '|')  # Element separator
	processed_content = processed_content.replace('\x1D', '~')  # Component separator
	processed_content = processed_content.replace('\x1A', '^')     # Remove newlines
	processed_content = processed_content.replace('\x1B', '^')  # Segment terminator (user request)

	return processed_content

def parse(path: str, debug: bool = False, preprocess: bool = True, extension_pattern: str = DEFAULT_EXTENSION_PATTERN) -> TransactionSets:
	"""
	Parse EDI 835 file(s) and return TransactionSets object.
	
	Args:
		path (str): Path to EDI file or directory
		debug (bool): Enable debug mode
		preprocess (bool): Automatically preprocess files with special characters
		extension_pattern (str): Regex pattern for file extensions
	
	Returns:
		TransactionSets: Parsed transaction sets
	"""
	if path[0] == '~':
		path = os.path.expanduser(path)

	transaction_sets = []
	if os.path.isdir(path):
		files = _find_edi_835_files(path, extension_pattern)
		for file in files:
			file_path = f'{path}/{file}'
			if debug:
				transaction_set = _build_transaction_set(file_path, preprocess)
				transaction_sets.append(transaction_set)
			else:
				try:
					transaction_set = _build_transaction_set(file_path, preprocess)
					transaction_sets.append(transaction_set)
				except Exception as e:
					warn(f'Failed to build a transaction set from {file_path} with error: {e}')
	else:
		transaction_set = _build_transaction_set(path, preprocess)
		transaction_sets.append(transaction_set)

	return TransactionSets(transaction_sets)


def parse_to_json(path: str, debug: bool = False, preprocess: bool = True, extension_pattern: str = DEFAULT_EXTENSION_PATTERN) -> Dict[str, Any]:
	"""
	Parse EDI 835 file(s) and return JSON structured data.
	Properly handles files with multiple ST...SE transaction segments.

	Args:
		path (str): Path to EDI file or directory
		debug (bool): Enable debug mode
		preprocess (bool): Automatically preprocess files with special characters
		extension_pattern (str): Regex pattern for file extensions

	Returns:
		Dict[str, Any]: JSON structured data with all transactions
	"""
	if path[0] == '~':
		path = os.path.expanduser(path)

	# For now, handle single file. Directory handling can be added later if needed
	if os.path.isdir(path):
		files = _find_edi_835_files(path, extension_pattern)
		if not files:
			raise ValueError(f"No EDI 835 files found in directory: {path}")
		# Use the first file found
		file_path = f'{path}/{files[0]}'
	else:
		file_path = path

	if debug:
		transaction_sets = _build_transaction_sets(file_path, preprocess)
		return _merge_transaction_sets_to_json(transaction_sets)
	else:
		transaction_sets = None
		try:
			transaction_sets = _build_transaction_sets(file_path, preprocess)
			return _merge_transaction_sets_to_json(transaction_sets)
		except Exception as e:
			warn(f'Failed to build transaction sets from {file_path} with error: {e}')
			raise
		finally:
			# Clean up temporary file if it was created
			if transaction_sets and len(transaction_sets) > 0:
				first_ts = transaction_sets[0]
				if hasattr(first_ts, 'file_path') and first_ts.file_path.endswith('.processed.tmp'):
					temp_file_path = first_ts.file_path
					if os.path.exists(temp_file_path):
						os.unlink(temp_file_path)
						print(f"Temporary file deleted: {temp_file_path}")


def _merge_transaction_sets_to_json(transaction_sets: List[TransactionSet]) -> Dict[str, Any]:
	"""
	Merge multiple TransactionSet objects into a single JSON structure.

	Args:
		transaction_sets: List of TransactionSet objects

	Returns:
		Dict with interchange containing all transactions
	"""
	if not transaction_sets:
		return {"interchange": {"transactions": []}}

	# Get the first transaction set's JSON to extract envelope info
	first_json = transaction_sets[0].to_json()

	# Start with the interchange structure from first transaction
	merged_json = {
		"interchange": {
			"ISA": first_json.get("interchange", {}).get("ISA"),
			"GS": first_json.get("interchange", {}).get("GS"),
			"transactions": [],
			"GE": first_json.get("interchange", {}).get("GE"),
			"IEA": first_json.get("interchange", {}).get("IEA")
		}
	}

	# Collect all transactions from all transaction sets
	for ts in transaction_sets:
		ts_json = ts.to_json()
		transactions = ts_json.get("interchange", {}).get("transactions", [])
		merged_json["interchange"]["transactions"].extend(transactions)

	return merged_json


def _build_transaction_sets(file_path: str, preprocess: bool = True) -> List[TransactionSet]:
	"""
	Build TransactionSet(s) from a file, with optional preprocessing.
	Handles files with multiple ST...SE segments.

	Args:
		file_path (str): Path to the EDI file
		preprocess (bool): Whether to preprocess the file content

	Returns:
		List[TransactionSet]: List of built transaction sets (one per ST...SE segment)
	"""
	# Check if file needs preprocessing by looking for special characters
	with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
		content = f.read()

	# Check for special characters that need preprocessing
	needs_norm = needs_x12_normalization(file_path)	
	print(f"File {file_path} needs normalization: {needs_norm}")
	if (needs_norm) and preprocess:
		# Preprocess the content
		
		processed_content = normalize_x12_delimiters(content)
		
		# Create a temporary file with processed content that won't be auto-deleted
		temp_file_path = file_path + '.processed.tmp'

		with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
			temp_file.write(processed_content)

		try:
			# Build transaction sets from processed file
			transaction_sets = TransactionSet.build_multiple(temp_file_path)
			# Update the file_path in each transaction set to the original path
			for ts in transaction_sets:
				ts.file_path = temp_file_path
			return transaction_sets
		finally:
			print(f"Temporary file retained for debugging: {temp_file_path}")
	else:
		# No preprocessing needed - use build_multiple to handle multi-transaction files
		return TransactionSet.build_multiple(file_path)


def _build_transaction_set(file_path: str, preprocess: bool = True) -> TransactionSet:
	"""
	Build a single TransactionSet from a file (legacy method for backward compatibility).
	If file contains multiple transactions, returns only the first one.

	Args:
		file_path (str): Path to the EDI file
		preprocess (bool): Whether to preprocess the file content

	Returns:
		TransactionSet: Built transaction set
	"""
	transaction_sets = _build_transaction_sets(file_path, preprocess)
	return transaction_sets[0] if transaction_sets else None


def _find_edi_835_files(path: str, extension_pattern: str = DEFAULT_EXTENSION_PATTERN) -> List[str]:
	"""Find EDI 835 files in a directory using regex pattern matching.
	
	Args:
		path: Directory path to search
		extension_pattern: Regex pattern to match file extensions
		
	Returns:
		List of matching filenames
	"""
	pattern = re.compile(extension_pattern, re.IGNORECASE)
	files = []
	for file in os.listdir(path):
		if pattern.search(file):
			files.append(file)
	return files

	



def main():
	data = parse('~/Desktop/eobs').to_dataframe()
	data.to_csv('~/Desktop/transaction_sets.csv')


if __name__ == '__main__':
	main()
