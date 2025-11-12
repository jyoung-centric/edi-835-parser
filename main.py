import edi_835_parser
from database_mock import DatabaseManager

# Parse to JSON (new functionality)
json_data = edi_835_parser.parse_to_json('testfiles\PT13882.0022345 1.DT20250710')
print(json_data)

# Example: Store parsed data in the database using single table approach
# Initialize the database (creates edi_835_data.json in project root)
with DatabaseManager('edi_835_data.json') as db:
    # Prepare payment data matching the payments_835 schema
    payment_data = {
        'file_name': 'PT13882.0022345 1.DT20250710',
        'json_transaction': json_data,
        'raw_edi': None,  # You could store the original EDI content here
        'check_number': json_data.get('financial_information', {}).get('trace_number'),
        'payment_date': json_data.get('financial_information', {}).get('check_issue_date'),
        'payment_amount': json_data.get('financial_information', {}).get('payer_identifier'),
        'payer_id': json_data.get('financial_information', {}).get('payer_identifier'),
        'payee_id': json_data.get('financial_information', {}).get('payee_identification_number')
    }
    
    # Store the parsed payment in the single table
    payment_id = db.store_payment_835(payment_data)
    print(f"\nPayment stored with ID: {payment_id}")
    
    # Retrieve and display the stored payment
    stored_payment = db.get_payment_by_id(payment_id)
    print(f"Retrieved payment file: {stored_payment.get('file_name', 'N/A')}")
    
   