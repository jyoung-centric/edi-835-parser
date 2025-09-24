# EDI 835 Parser


### edi-835-parser: a lightweight EDI 835 file parser

This package provides a Python interface to EDI 835 Health Care Claim Payment and Remittance Advice files.

*This package is distributed for internal use only. It is not available as open source or for public download.*

### Installation
Please note that you need to run Python 3.9 or higher to use the edi-835-parser.
Contact your administrator for installation instructions or access to the package.

### Usage
To parse an EDI 835 file simply execute the `parse` function.
```python
from edi_835_parser import parse

path = '~/Desktop/my_edi_file.txt'
transaction_set = parse(path)
```
The `parse` function also works on a directory path.
```python
from edi_835_parser import parse

path = '~/Desktop/my_directory_of_edi_files'
transaction_sets = parse(path)
```
In both cases, `parse` returns an instance of the `TransactionSets` class. 
This is the class you manipulate depending on your needs. 
For example, say you want to work with the transaction sets data as a `pd.DataFrame`.
```python
from edi_835_parser import parse

path = '~/Desktop/my_directory_of_edi_files'
transaction_sets = parse(path)

data = transaction_sets.to_dataframe()
```
And then save that `pd.DataFrame` as a `.csv` file.
```python
data.to_csv('~/Desktop/my_edi_file.csv')
```
The complete set of `TransactionSets` functionality can be found by inspecting the `TransactionSets` 
class found at `edi_parser/transaction_set/transaction_sets.py`

#### Parse to JSON (New)
You can also parse an EDI 835 file directly to JSON:
```python
import edi_835_parser
json_data = edi_835_parser.parse_to_json('testfiles/PT13882.0022345 1.DT20250710')
print(json_data)
```

#### Batch Test Runner
To run all test files in `tests/test_edi_835_files` and save JSON outputs, use the included test runner script:
```bash
python ShubhamTest.py
```
This will process all files in `tests/test_edi_835_files`, save outputs to `tests/output`, and generate summary reports (`test_summary_report.json` and `test_summary.txt`).

You can add additional test files to `tests/test_edi_835_files` to include them in the batch run.

### Tests
Example EDI 835 files can be found in `tests/test_edi_835/files`. To run the tests use `pytest`.
```
python -m pytest
```

### License and Attribution
This project is based on the original open source [edi-835-parser](https://github.com/keironstoddart/edi-835-parser) by Keiron Stoddart. This version is maintained as a closed-source, internal tool.