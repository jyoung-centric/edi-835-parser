#!/usr/bin/env python3
"""
Test script to verify CAS segment parsing at both claim and service levels
"""

import sys
import os

# Add the package to the path
sys.path.insert(0, os.path.dirname(__file__))

import edi_835_parser

def test_cas_parsing():
    """Test CAS segment parsing and JSON conversion"""

    print("=" * 80)
    print("Testing CAS Segment Parsing")
    print("=" * 80)

    # Find a test file with CAS segments
    test_file = "tests/test_edi_835_files/SB865.13167.20250622.061330708.ERA.835NP.edi"

    if not os.path.exists(test_file):
        print(f"ERROR: Test file not found: {test_file}")
        return False

    print(f"\nProcessing file: {test_file}")

    try:
        # Parse to JSON
        print("\n1. Parsing EDI file to JSON...")
        json_data = edi_835_parser.parse_to_json(test_file)

        if not json_data or 'interchange' not in json_data:
            print("ERROR: Failed to parse JSON data")
            return False

        transactions = json_data['interchange']['transactions']
        print(f"   ✓ Found {len(transactions)} transaction(s)")

        # Check CAS segments at service level
        print("\n2. Checking Service-level CAS segments...")
        service_cas_found = 0
        service_cas_total = 0

        for trans in transactions:
            if 'CLP_loop' in trans:
                for claim in trans['CLP_loop']:
                    if 'SVC_loop' in claim:
                        for service in claim['SVC_loop']:
                            service_cas_total += 1
                            if 'CAS' in service and len(service['CAS']) > 0:
                                service_cas_found += 1
                                # Show first CAS segment as example
                                if service_cas_found == 1:
                                    print(f"   ✓ Example Service CAS segment:")
                                    print(f"     Group Code: {service['CAS'][0].get('claim_adjustment_group_code')}")
                                    print(f"     Adjustments: {service['CAS'][0].get('adjustments')}")

        print(f"   ✓ Found CAS segments in {service_cas_found}/{service_cas_total} service lines")

        # Check CAS segments at claim level
        print("\n3. Checking Claim-level CAS segments...")
        claim_cas_found = 0
        claim_cas_total = 0

        for trans in transactions:
            if 'CLP_loop' in trans:
                for claim in trans['CLP_loop']:
                    claim_cas_total += 1
                    if 'CAS' in claim and len(claim['CAS']) > 0:
                        claim_cas_found += 1
                        # Show first CAS segment as example
                        if claim_cas_found == 1:
                            print(f"   ✓ Example Claim CAS segment:")
                            print(f"     Group Code: {claim['CAS'][0].get('claim_adjustment_group_code')}")
                            print(f"     Adjustments: {claim['CAS'][0].get('adjustments')}")

        print(f"   ✓ Found CAS segments in {claim_cas_found}/{claim_cas_total} claims")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Service-level CAS: {service_cas_found} found (expected: many)")
        print(f"Claim-level CAS:   {claim_cas_found} found (expected: few or none in this file)")

        if service_cas_found > 0:
            print("\n✓ SUCCESS: CAS segments are being parsed and converted to JSON!")
            return True
        else:
            print("\n✗ FAILURE: No CAS segments found in JSON output")
            return False

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cas_parsing()
    sys.exit(0 if success else 1)
