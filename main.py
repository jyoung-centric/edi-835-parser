import edi_835_parser
from database_mock import DatabaseManager
from pathlib import Path
import json

def process_all_test_files():
    """Process all test files and store them in the database"""
    
    # Test files directory
    test_dir = Path("tests/test_edi_835_files")
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    # Get all test files (excluding temporary files)
    test_files = [f for f in test_dir.iterdir() 
                  if f.is_file() 
                  and not f.name.startswith('.') 
                  and not f.name.endswith('.processed.tmp')]
    
    print(f"🔍 Found {len(test_files)} test files to process")
    print("=" * 60)
    
    # Initialize the database
    with DatabaseManager('edi_835_data.json') as db:
        successful_files = 0
        failed_files = 0
        
        for test_file in sorted(test_files):
            print(f"\n📄 Processing: {test_file.name}")
            
            try:
                # Parse to JSON
                json_data = edi_835_parser.parse_to_json(str(test_file))
                
                # Extract transaction data safely
                interchange = json_data.get('interchange', {})
                transactions = interchange.get('transactions', [])
                
                if transactions and len(transactions) > 0:
                    transaction = transactions[0]
                    bpr = transaction.get('BPR', {}) if transaction else {}
                    trn = transaction.get('TRN', {}) if transaction else {}
                    
                    # Count claims and services
                    clp_loops = transaction.get('CLP_loop', [])
                    total_claims = len(clp_loops)
                    total_services = sum(len(clp.get('SVC_loop', [])) for clp in clp_loops)
                    
                    # Prepare payment data
                    payment_data = {
                        'file_name': test_file.name,
                        'json_transaction': json_data,
                        'raw_edi': None,
                        'check_number': trn.get('reference_identification'),
                        'payment_date': bpr.get('check_issue_or_eft_effective_date'),
                        'payment_amount': bpr.get('monetary_amount'),
                        'payer_id': trn.get('originating_company_identifier'),
                        'payee_id': None,
                        'claims_count': total_claims,
                        'services_count': total_services
                    }
                    
                    # Store in database
                    payment_id = db.store_payment_835(payment_data)
                    
                    print(f"  ✅ SUCCESS - ID: {payment_id}")
                    print(f"     📋 Claims: {total_claims}")
                    print(f"     🔧 Services: {total_services}")
                    print(f"     💰 Amount: ${payment_data['payment_amount'] or 'N/A'}")
                    
                    successful_files += 1
                else:
                    print(f"  ⚠️  No transactions found in file")
                    failed_files += 1
                    
            except Exception as e:
                print(f"  ❌ FAILED: {str(e)}")
                failed_files += 1
        
        print(f"\n{'=' * 60}")
        print("🎯 PROCESSING SUMMARY")
        print(f"{'=' * 60}")
        print(f"✅ Successful: {successful_files}")
        print(f"❌ Failed: {failed_files}")
        print(f"📊 Success Rate: {(successful_files / len(test_files) * 100):.1f}%")
        
        # Show some database statistics
        all_payments = db.get_all_payments()
        total_stored = len(all_payments)
        total_claims = sum(p.get('claims_count', 0) for p in all_payments if p.get('claims_count'))
        total_services = sum(p.get('services_count', 0) for p in all_payments if p.get('services_count'))
        
        print(f"\n📁 DATABASE STATISTICS")
        print(f"Total payments stored: {total_stored}")
        print(f"Total claims: {total_claims}")
        print(f"Total services: {total_services}")

if __name__ == "__main__":
    process_all_test_files()