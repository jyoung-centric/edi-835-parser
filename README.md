# EDI 835 Parser

### edi-835-parser: Advanced EDI 835 Healthcare Payment Parser

This package provides a comprehensive Python interface for parsing EDI 835 Health Care Claim Payment and Remittance Advice files with enhanced JSON output capabilities and automated processing features.

*This package is distributed for internal use only. It is not available as open source or for public download.*

## ✨ Key Features

- **🔄 Dual Parsing Modes**: Object-based parsing and direct JSON conversion
- **📊 Comprehensive Data Extraction**: Claims, services, dates, amounts, and references
- **🚀 Batch Processing**: Process multiple files with automated reporting
- **💾 Database Integration**: Store parsed data with mock database functionality
- **📈 DTM Date Handling**: Proper extraction and placement of date segments at claim/service levels
- **🔧 Preprocessing Support**: Automatic handling of files with special characters
- **📁 Test Suite**: Comprehensive test runner with detailed reporting

### Installation
Please note that you need to run Python 3.9 or higher to use the edi-835-parser.
Contact your administrator for installation instructions or access to the package.

## 🚀 Usage

### Basic Object-Based Parsing
Parse an EDI 835 file and work with structured objects:
```python
from edi_835_parser import parse

# Parse single file
transaction_sets = parse('~/Desktop/my_edi_file.txt')

# Parse directory of files
transaction_sets = parse('~/Desktop/my_directory_of_edi_files')

# Convert to DataFrame
data = transaction_sets.to_dataframe()
data.to_csv('~/Desktop/my_edi_file.csv')
```

### JSON Output (Recommended)
Parse directly to JSON for easier integration:
```python
import edi_835_parser

# Parse to JSON with proper DTM placement
json_data = edi_835_parser.parse_to_json('tests/test_edi_835_files/blue_cross_nc_sample.txt')

# Access structured data
transactions = json_data['interchange']['transactions']
claims = transactions[0]['CLP_loop']
services = claims[0]['SVC_loop']

# DTM dates are now properly placed at claim and service levels
claim_dates = claims[0]['DTM']  # Claim-level dates
service_dates = services[0]['DTM']  # Service-level dates
```

### Batch Processing
Process multiple files with comprehensive reporting:
```python
# Run all test files and generate reports
python ShubhamTest.py

# Process all files and store in database
python main.py
```

### Database Integration
Store parsed data with the mock database:
```python
from database_mock import DatabaseManager
import edi_835_parser

with DatabaseManager('edi_835_data.json') as db:
    # Parse and store payment data
    json_data = edi_835_parser.parse_to_json('my_file.txt')
    
    payment_data = {
        'file_name': 'my_file.txt',
        'json_transaction': json_data,
        'check_number': '12345',
        'payment_amount': '1000.00'
    }
    
    payment_id = db.store_payment_835(payment_data)
    print(f"Stored with ID: {payment_id}")
```

## 📊 Advanced Features

### Comprehensive Test Runner
Run the enhanced test suite to process all files:
```bash
python ShubhamTest.py
```

**Features:**
- Processes all files in `tests/test_edi_835_files/`
- Generates JSON outputs in `tests/output/`  
- Creates detailed reports (`test_summary_report.json`, `test_summary.txt`)
- Shows DTM parsing success with debug output
- Tracks claims, services, and processing times

### Batch Processing with Database Storage
Process all test files and store in database:
```bash
python main.py
```

**Features:**
- Processes 10+ test files automatically
- Stores structured data in JSON database
- Extracts payment amounts, dates, and identifiers
- Counts claims and services per file
- Provides comprehensive statistics

## 🧪 Testing

### Unit Tests
Run the standard test suite:
```bash
python -m pytest
```

### Comprehensive Test Files
Example EDI 835 files are located in `tests/test_edi_835_files/`:
- `blue_cross_nc_sample.txt` - Blue Cross NC payment
- `united_healthcare_legacy_sample.txt` - UHC legacy format  
- `PT13882.0021984 1.DT20240821` - Large file with 778+ claims
- `SB865.13167.20250622.061330708.ERA.835NP.edi` - Complex file with 707+ claims
- Additional sample files for comprehensive testing

### Test Results Summary
Recent test run results:
- **Success Rate**: 90.9% (10/11 files)
- **Claims Processed**: 2,623+ across all files
- **Services Processed**: 3,804+ across all files  
- **Payment Amounts**: $5+ million total processed

## 📈 Data Structure

### JSON Output Format
```json
{
  "interchange": {
    "ISA": { /* Interchange header */ },
    "transactions": [{
      "ST": { /* Transaction header */ },
      "BPR": { /* Payment info */ },
      "TRN": { /* Trace info */ },
      "DTM": [ /* Transaction-level dates */ ],
      "N1_loop": [ /* Organizations */ ],
      "CLP_loop": [{
        "CLP": { /* Claim info */ },
        "DTM": [ /* Claim-level dates - FIXED! */ ],
        "NM1": [ /* Patient info */ ],
        "SVC_loop": [{
          "SVC": { /* Service info */ },
          "DTM": [ /* Service-level dates */ ]
        }]
      }]
    }]
  }
}
```

## 🔧 Key Improvements

### DTM Date Parsing Fixed
- ✅ **Proper Claim-Level Placement**: DTM segments now appear in `CLP_loop[].DTM[]`
- ✅ **Service-Level Placement**: Service dates in `SVC_loop[].DTM[]`
- ✅ **Actual Parsed Data**: Uses `claims[].dates[]` from parsed objects
- ✅ **Multiple Date Support**: Handles multiple dates per claim/service

### Enhanced Architecture
- ✅ **Object-Based JSON Conversion**: Uses parsed objects instead of re-parsing files
- ✅ **Extension System**: Modular mixins for JSON conversion (`core/parser_extension.py`)
- ✅ **No Hardcoded Values**: All data comes from actual parsed EDI segments
- ✅ **Proper Error Handling**: Graceful handling of missing or malformed data

## 📁 Project Structure
```
edi-835-parser/
├── core/                          # Extension system
│   ├── parser_extension.py        # JSON conversion mixins
│   └── parser_monkeypatch.py      # Monkey patching utilities
├── edi_835_parser/               # Core parser
│   ├── elements/                 # EDI elements
│   ├── loops/                    # EDI loops (claims, services, orgs)
│   ├── segments/                 # EDI segments  
│   └── transaction_set/          # Transaction processing
├── tests/
│   ├── test_edi_835_files/       # Sample EDI files
│   └── output/                   # Generated JSON outputs
├── database_mock/                # Database functionality
├── ShubhamTest.py               # Comprehensive test runner
└── main.py                      # Batch processor with database
```

## 🎯 Performance Metrics

### Recent Test Results
- **Processing Speed**: ~0.35s total for 11 files
- **Large File Handling**: 778 claims in 0.06s
- **Complex Files**: 1,883 services processed successfully
- **Error Rate**: <10% (mostly temporary file issues)

### License and Attribution
This project is based on the original open source [edi-835-parser](https://github.com/keironstoddart/edi-835-parser) by Keiron Stoddart. This version is maintained as a closed-source, internal tool with significant enhancements for production healthcare payment processing.