"""
Script to load mock data into the TinyDB database from existing parsed JSON files.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the parent directory to the Python path to import database
sys.path.append(str(Path(__file__).parent.parent))

from database_mock import DatabaseManager


def find_matching_raw_edi_file(json_filename: str, edi_files_dir: Path) -> str:
    """
    Find the matching raw EDI file for a given JSON output file.
    
    Args:
        json_filename: Name of the JSON file
        edi_files_dir: Directory containing raw EDI files
        
    Returns:
        Raw EDI content or None if not found
    """
    # Remove _output.json suffix and try to find matching EDI file
    base_name = json_filename.replace('_output.json', '')
    base_name = base_name.replace('.json', '')
    
    # Common mapping patterns
    edi_patterns = [
        f"{base_name}.txt",
        f"{base_name}.edi", 
        f"{base_name}",
        f"{base_name}.DT*",  # Files with date extensions
        f"{base_name}_pretty.txt"
    ]
    
    # Try to find matching files
    for pattern in edi_patterns:
        if '*' in pattern:
            # Handle wildcard patterns
            matching_files = list(edi_files_dir.glob(pattern.replace('*', '*')))
            if matching_files:
                edi_file = matching_files[0]
                break
        else:
            edi_file = edi_files_dir / pattern
            if edi_file.exists():
                break
    else:
        # Special case mappings for known files
        special_mappings = {
            'blue_cross_nc_sample': 'blue_cross_nc_sample.txt',
            'emedny_sample': 'emedny_sample.txt',
            'united_healthcare_legacy_sample': 'united_healthcare_legacy_sample.txt',
            'PT13882_0021984_1': 'PT13882.0021984 1.DT20240821',
            'PT13882_0021984_1_processed': 'PT13882.0021984 1_processed.DT20240821',
            'PT13882_0022164___Copy': 'PT13882.0022164 - Copy.DT20250207',
            'PT13882_0022164___Copy_1_copy': 'PT13882.0022164 - Copy 1 copy.DT20250207',
            'PT13882_0022164_Copy1_pretty': 'PT13882_0022164_Copy1_pretty.txt',
            'PT13882_0022345_1': 'PT13882.0022345 1.DT20250710',
            'PT13882_0022345_1_copy': 'PT13882.0022345 1 copy.DT20250710',
            'SB865_13167_20250622_061330708_ERA_835NP': 'SB865.13167.20250622.061330708.ERA.835NP.edi'
        }
        
        if base_name in special_mappings:
            edi_file = edi_files_dir / special_mappings[base_name]
        else:
            return None
    
    # Read the EDI file content
    try:
        if edi_file.exists():
            with open(edi_file, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    except Exception as e:
        print(f"    Warning: Could not read EDI file {edi_file}: {e}")
    
    return None


def load_mock_data():
    """Load mock data from existing parsed JSON files into TinyDB."""
    
    # Database path
    db_path = Path(__file__).parent.parent / "edi_835_data.json"
    
    # Directory containing parsed JSON files
    output_dir = Path(__file__).parent.parent / "output"
    
    # Directory containing raw EDI files
    edi_files_dir = Path(__file__).parent.parent / "tests" / "test_edi_835_files"
    
    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        return
    
    if not edi_files_dir.exists():
        print(f"EDI files directory not found: {edi_files_dir}")
        return
    
    print(f"Loading mock data from: {output_dir}")
    print(f"Raw EDI files from: {edi_files_dir}")
    print(f"Database location: {db_path}")
    
    # Find JSON files
    json_files = list(output_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON files found in output directory")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    with DatabaseManager(str(db_path)) as db:
        # Clear existing data
        db.clear_all_data()
        print("Cleared existing data from database")
        
        loaded_count = 0
        
        for json_file in json_files:
            try:
                print(f"\nProcessing: {json_file.name}")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Find matching raw EDI file
                raw_edi_content = find_matching_raw_edi_file(json_file.name, edi_files_dir)
                
                if raw_edi_content:
                    print(f"  ✓ Found matching raw EDI file ({len(raw_edi_content)} chars)")
                else:
                    print(f"  ⚠ No matching raw EDI file found")
                    raw_edi_content = f"Mock raw EDI content for {json_file.name}"
                
                # Extract payment information from the parsed data
                financial_info = data.get('financial_information', {})
                
                # Create mock payment record
                payment_data = {
                    'file_name': json_file.name,
                    'check_number': financial_info.get('trace_number', f"CHK{loaded_count + 1:03d}"),
                    'payment_date': financial_info.get('check_issue_date', '2024-01-15'),
                    'payment_amount': financial_info.get('payer_identifier', 1000.00),
                    'payer_id': financial_info.get('payer_identifier', f"PAYER{loaded_count + 1:03d}"),
                    'payee_id': financial_info.get('payee_identification_number', f"PAYEE{loaded_count + 1:03d}"),
                    'json_transaction': data,
                    'raw_edi': raw_edi_content  # Now uses actual raw EDI content
                }
                
                # Store in database
                payment_id = db.store_payment_835(payment_data)
                loaded_count += 1
                
                print(f"  ✓ Loaded payment ID: {payment_id}")
                print(f"    Check Number: {payment_data['check_number']}")
                print(f"    Payer ID: {payment_data['payer_id']}")
                print(f"    Payment Amount: {payment_data['payment_amount']}")
                
            except Exception as e:
                print(f"  ✗ Error processing {json_file.name}: {str(e)}")
                continue
        
        print(f"\n🎉 Successfully loaded {loaded_count} payment records into the database!")
        
        # Display summary
        all_payments = db.get_all_payments()
        print(f"\nDatabase Summary:")
        print(f"Total records: {len(all_payments)}")
        
        if all_payments:
            print(f"\nSample check numbers in database:")
            for i, payment in enumerate(all_payments[:5]):
                print(f"  - {payment.get('check_number', 'N/A')}")
                if i >= 4:  # Show max 5 examples
                    break


if __name__ == "__main__":
    print("EDI 835 Mock Data Loader")
    print("=" * 40)
    load_mock_data()