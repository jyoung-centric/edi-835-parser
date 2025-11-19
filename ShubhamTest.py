#!/usr/bin/env python3

"""
Test script to run all test files in tests\test_edi_835_files and save JSON outputs
"""

import os
import json
import traceback
from pathlib import Path
from datetime import datetime
import edi_835_parser
from edi_835_parser.transaction_set.transaction_set import TransactionSet
from edi_835_parser.loops.claim import Claim as ClaimLoop
from edi_835_parser.loops.service import Service as ServiceLoop

def create_test_runner():
    """Run all test files and save JSON outputs"""
    
    # Directories
    # Add additional Test file in to the tests\test_edi_835_files directory to have it included in the test run
    test_dir = Path("tests/test_edi_835_files")
    # Outputs will be saved to tests\output directory
    output_dir = Path("tests/output")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Get all test files
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    test_files = [f for f in test_dir.iterdir() if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.processed.tmp')]
    
    print("🧪 EDI 835 PARSER - COMPREHENSIVE TEST RUNNER")
    print("=" * 80)
    print(f"📁 Test directory: {test_dir}")
    print(f"📁 Output directory: {output_dir}")
    print(f"📄 Files to test: {len(test_files)}")
    print("=" * 80)
    
    # Test results tracking
    results = []
    successful_tests = 0
    failed_tests = 0
    
    # Process each test file
    for test_file in sorted(test_files):
        print(f"\n🔍 Testing: {test_file.name}")
        
        try:
            # Parse to JSON
            start_time = datetime.now()
            json_data = edi_835_parser.parse_to_json(str(test_file))
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Count claims and services from JSON structure
            total_claims = 0
            total_services = 0
            
            # Get transactions from the JSON structure
            transactions = json_data.get("interchange", {}).get("transactions", [])
            
            for transaction in transactions:
                clp_loops = transaction.get("CLP_loop", [])
                total_claims += len(clp_loops)
                
                # Count services in each claim
                for clp_loop in clp_loops:
                    svc_loops = clp_loop.get("SVC_loop", [])
                    total_services += len(svc_loops)
            
            # Debug print for first claim's first date if available
            if transactions and transactions[0].get("CLP_loop") and transactions[0]["CLP_loop"][0].get("DTM"):
                first_dtm = transactions[0]["CLP_loop"][0]["DTM"][0]
                print(f"***************************************DTM*{first_dtm.get('date_time_qualifier', '')}*{first_dtm.get('date', '')}")
            else:
                print("***************************************No DTM data found")
            # Create safe filename for output
            safe_name = test_file.stem.replace(' ', '_').replace('-', '_').replace('.', '_')
            output_file = output_dir / f"{safe_name}_output.json"
            



            # Save JSON output
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Test result
            test_result = {
                'file': test_file.name,
                'status': 'SUCCESS',
                'output_file': str(output_file),
                'processing_time': processing_time,
                'file_size': test_file.stat().st_size,
                'transactions': len(transactions),
                'claims': total_claims,
                'services': total_services,
                'error': None
            }
            
            print(f"  ✅ SUCCESS")
            print(f"     ⏱️  Processing time: {processing_time:.3f}s")
            print(f"     📊 Transactions: {len(transactions)}")
            print(f"     📋 Claims: {total_claims}")
            print(f"     🔧 Services: {total_services}")
            print(f"     💾 Output: {output_file}")
            
            successful_tests += 1
            
        except Exception as e:
            # Test failed
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            
            test_result = {
                'file': test_file.name,
                'status': 'FAILED',
                'output_file': None,
                'processing_time': 0,
                'file_size': test_file.stat().st_size if test_file.exists() else 0,
                'transactions': 0,
                'claims': 0,
                'services': 0,
                'error': error_msg,
                'traceback': traceback_str
            }
            
            print(f"  ❌ FAILED: {error_msg}")
            failed_tests += 1
        
        results.append(test_result)
    
    # Generate summary report
    report_file = output_dir / "test_summary_report.json"
    summary_file = output_dir / "test_summary.txt"
    
    # JSON report
    summary_data = {
        'test_run': {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(test_files),
            'successful': successful_tests,
            'failed': failed_tests,
            'success_rate': (successful_tests / len(test_files) * 100) if test_files else 0
        },
        'results': results
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    # Text summary
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("EDI 835 PARSER - TEST SUMMARY REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Test Directory: {test_dir}\n")
        f.write(f"Output Directory: {output_dir}\n")
        f.write("\n")
        
        f.write("📊 SUMMARY STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total Files Tested: {len(test_files)}\n")
        f.write(f"Successful Tests:   {successful_tests}\n")
        f.write(f"Failed Tests:       {failed_tests}\n")
        f.write(f"Success Rate:       {(successful_tests / len(test_files) * 100):.1f}%\n")
        f.write("\n")
        
        # Detailed results
        f.write("📋 DETAILED RESULTS\n")
        f.write("-" * 40 + "\n")
        
        for result in results:
            f.write(f"\nFile: {result['file']}\n")
            f.write(f"Status: {result['status']}\n")
            
            if result['status'] == 'SUCCESS':
                f.write(f"  Processing Time: {result['processing_time']:.3f}s\n")
                f.write(f"  File Size: {result['file_size']:,} bytes\n")
                f.write(f"  Transactions: {result['transactions']}\n")
                f.write(f"  Claims: {result['claims']}\n")
                f.write(f"  Services: {result['services']}\n")
                f.write(f"  Output File: {result['output_file']}\n")
            else:
                f.write(f"  Error: {result['error']}\n")
                f.write(f"  File Size: {result['file_size']:,} bytes\n")
        
        if failed_tests > 0:
            f.write(f"\n❌ FAILED TESTS ({failed_tests})\n")
            f.write("-" * 40 + "\n")
            for result in results:
                if result['status'] == 'FAILED':
                    f.write(f"\n{result['file']}:\n")
                    f.write(f"  Error: {result['error']}\n")
                    if 'traceback' in result:
                        f.write(f"  Traceback:\n")
                        for line in result['traceback'].split('\n'):
                            if line.strip():
                                f.write(f"    {line}\n")
    
    # Calculate totals across all successful tests
    total_transactions = sum(r['transactions'] for r in results if r['status'] == 'SUCCESS')
    total_claims = sum(r['claims'] for r in results if r['status'] == 'SUCCESS')
    total_services = sum(r['services'] for r in results if r['status'] == 'SUCCESS')
    total_processing_time = sum(r['processing_time'] for r in results if r['status'] == 'SUCCESS')
    
    # Final summary
    print(f"\n{'=' * 80}")
    print("🎯 TEST COMPLETION SUMMARY")
    print(f"{'=' * 80}")
    print(f"📄 Total files tested: {len(test_files)}")
    print(f"✅ Successful tests: {successful_tests}")
    print(f"❌ Failed tests: {failed_tests}")
    print(f"📊 Success rate: {(successful_tests / len(test_files) * 100):.1f}%")
    print(f"⏱️  Total processing time: {total_processing_time:.3f}s")
    print(f"📋 Total transactions processed: {total_transactions}")
    print(f"📄 Total claims processed: {total_claims}")
    print(f"🔧 Total services processed: {total_services}")
    print(f"\n📁 All outputs saved to: {output_dir}")
    print(f"📊 Summary report: {report_file}")
    print(f"📝 Text summary: {summary_file}")
    
    if failed_tests > 0:
        print(f"\n⚠️  {failed_tests} test(s) failed. Check the summary report for details.")
    else:
        print(f"\n🎉 All tests passed successfully!")
    
    return results

if __name__ == "__main__":
    create_test_runner()