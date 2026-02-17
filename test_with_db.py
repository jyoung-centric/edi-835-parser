#!/usr/bin/env python3

"""
Extended test script that parses EDI 835 files and seeds PostgreSQL database
Combines ShubhamTest.py functionality with database seeding
"""

import os
import json
import traceback
from pathlib import Path
from datetime import datetime
import edi_835_parser
from db.manager import get_database_manager


def test_with_database_seeding(clear_data: bool = True):
    """
    Run all test files, save JSON outputs, and seed database

    Args:
        clear_data: If True, clear existing test data before seeding
    """

    # Directories
    test_dir = Path("tests/test_edi_835_files")
    output_dir = Path("tests/output")

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Get all test files
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return

    test_files = [
        f for f in test_dir.iterdir()
        if f.is_file()
        and not f.name.startswith('.')
        and not f.name.endswith('.processed.tmp')
    ]

    print("🧪 EDI 835 PARSER - DATABASE SEEDING TEST")
    print("=" * 80)
    print(f"📁 Test directory: {test_dir}")
    print(f"📁 Output directory: {output_dir}")
    print(f"📄 Files to test: {len(test_files)}")
    print("=" * 80)

    # Initialize database manager
    db = get_database_manager()

    # Connect to database
    if not db.connect():
        print("❌ Cannot proceed without database connection")
        return

    # Test connection and verify schema
    if not db.test_connection():
        print("❌ Database schema verification failed")
        db.disconnect()
        return

    # Clear existing test data if requested
    if clear_data:
        print("\n🧹 Clearing existing test data...")
        db.clear_all_data()

    # Test results tracking
    results = []
    successful_tests = 0
    failed_tests = 0
    db_inserts = 0

    print("\n" + "=" * 80)
    print("📊 PROCESSING FILES")
    print("=" * 80)

    # Process each test file
    for test_file in sorted(test_files):
        print(f"\n🔍 Processing: {test_file.name}")

        try:
            # Parse to JSON
            start_time = datetime.now()
            json_data = edi_835_parser.parse_to_json(str(test_file))
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # Count claims and services
            total_claims = 0
            total_services = 0

            transactions = json_data.get("interchange", {}).get("transactions", [])

            for transaction in transactions:
                clp_loops = transaction.get("CLP_loop", [])
                total_claims += len(clp_loops)

                for clp_loop in clp_loops:
                    svc_loops = clp_loop.get("SVC_loop", [])
                    total_services += len(svc_loops)

            # Create safe filename for output
            safe_name = test_file.stem.replace(' ', '_').replace('-', '_').replace('.', '_')
            output_file = output_dir / f"{safe_name}_output.json"

            # Save JSON output
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            # Read raw EDI content
            with open(test_file, 'r', encoding='utf-8') as f:
                raw_edi = f.read()

            # Insert into database
            print(f"  💉 Seeding database...")
            file_id = db.insert_payment_835(
                file_name=test_file.name,
                json_data=json_data,
                raw_edi=raw_edi
            )

            # Verify insertion
            db_success = False
            if file_id:
                db_success = db.verify_json_structure(file_id)
                if db_success:
                    db_inserts += 1

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
                'db_inserted': db_success,
                'file_id': str(file_id) if file_id else None,
                'error': None
            }

            print(f"  ✅ SUCCESS")
            print(f"     ⏱️  Processing time: {processing_time:.3f}s")
            print(f"     📊 Transactions: {len(transactions)}")
            print(f"     📋 Claims: {total_claims}")
            print(f"     🔧 Services: {total_services}")
            print(f"     💾 Output: {output_file}")
            print(f"     🗄️  Database: {'✅ Inserted' if db_success else '❌ Failed'}")

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
                'db_inserted': False,
                'file_id': None,
                'error': error_msg,
                'traceback': traceback_str
            }

            print(f"  ❌ FAILED: {error_msg}")
            failed_tests += 1

        results.append(test_result)

    # Get database summary
    print("\n" + "=" * 80)
    print("🗄️  DATABASE SUMMARY")
    print("=" * 80)

    payment_count = db.get_payment_count()
    print(f"📊 Total payments in database: {payment_count}")

    # Show payment details
    if payment_count > 0:
        print("\n📋 Payment Records:")
        payments = db.get_payments_summary()
        for payment in payments:
            print(f"  • {payment['file_name']}")
            print(f"    Check: {payment['check_number']}, Amount: ${payment['payment_amount']}")
            print(f"    Date: {payment['payment_date']}, Transactions: {payment['transaction_count']}")

    # Disconnect from database
    db.disconnect()

    # Generate summary report
    report_file = output_dir / "test_db_summary_report.json"
    summary_file = output_dir / "test_db_summary.txt"

    # JSON report
    summary_data = {
        'test_run': {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(test_files),
            'successful': successful_tests,
            'failed': failed_tests,
            'db_inserts': db_inserts,
            'success_rate': (successful_tests / len(test_files) * 100) if test_files else 0,
            'db_success_rate': (db_inserts / successful_tests * 100) if successful_tests else 0
        },
        'database': {
            'total_payments': payment_count,
            'connection': f"{db.host}:{db.port}/{db.database}"
        },
        'results': results
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    # Text summary
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("EDI 835 PARSER - DATABASE SEEDING TEST REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Test Directory: {test_dir}\n")
        f.write(f"Output Directory: {output_dir}\n")
        f.write(f"Database: {db.host}:{db.port}/{db.database}\n")
        f.write("\n")

        f.write("📊 SUMMARY STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total Files Tested: {len(test_files)}\n")
        f.write(f"Successful Parses:  {successful_tests}\n")
        f.write(f"Failed Parses:      {failed_tests}\n")
        f.write(f"DB Inserts:         {db_inserts}\n")
        f.write(f"Parse Success Rate: {(successful_tests / len(test_files) * 100):.1f}%\n")
        f.write(f"DB Success Rate:    {(db_inserts / successful_tests * 100):.1f}%\n" if successful_tests else "DB Success Rate:    N/A\n")
        f.write(f"Total DB Records:   {payment_count}\n")
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
                f.write(f"  DB Inserted: {'Yes' if result['db_inserted'] else 'No'}\n")
                if result['file_id']:
                    f.write(f"  File ID: {result['file_id']}\n")
            else:
                f.write(f"  Error: {result['error']}\n")

    # Calculate totals
    total_transactions = sum(r['transactions'] for r in results if r['status'] == 'SUCCESS')
    total_claims = sum(r['claims'] for r in results if r['status'] == 'SUCCESS')
    total_services = sum(r['services'] for r in results if r['status'] == 'SUCCESS')
    total_processing_time = sum(r['processing_time'] for r in results if r['status'] == 'SUCCESS')

    # Final summary
    print(f"\n{'=' * 80}")
    print("🎯 TEST COMPLETION SUMMARY")
    print(f"{'=' * 80}")
    print(f"📄 Total files tested: {len(test_files)}")
    print(f"✅ Successful parses: {successful_tests}")
    print(f"❌ Failed parses: {failed_tests}")
    print(f"💾 Database inserts: {db_inserts}")
    print(f"📊 Parse success rate: {(successful_tests / len(test_files) * 100):.1f}%")
    print(f"🗄️  DB success rate: {(db_inserts / successful_tests * 100):.1f}%" if successful_tests else "🗄️  DB success rate: N/A")
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

    if db_inserts < successful_tests:
        print(f"⚠️  {successful_tests - db_inserts} database insert(s) failed.")

    return results


if __name__ == "__main__":
    import sys

    # Check for --keep-data flag
    clear_data = "--keep-data" not in sys.argv

    if not clear_data:
        print("ℹ️  Running in --keep-data mode (existing data will be preserved)")

    test_with_database_seeding(clear_data=clear_data)
