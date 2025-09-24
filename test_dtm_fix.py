#!/usr/bin/env python3
"""Test DTM segment placement fix"""

import json
import edi_835_parser

def test_dtm_placement():
    """Test that DTM segments are placed at correct levels after fix"""
    
    # Parse the emedny sample file
    data = edi_835_parser.parse_to_json('tests/test_edi_835_files/emedny_sample.txt')
    
    # Check first transaction
    transaction = data['interchange']['transactions'][0]
    print(f"Transaction has {len(transaction['CLP_loop'])} claims")
    
    # Check first claim
    first_claim = transaction['CLP_loop'][0]
    
    print(f"\nFirst claim DTM segments: {len(first_claim['DTM'])}")
    if first_claim['DTM']:
        for i, dtm in enumerate(first_claim['DTM']):
            print(f"  DTM {i+1}: {dtm}")
    
    print(f"\nFirst claim services: {len(first_claim['SVC_loop'])}")
    if first_claim['SVC_loop']:
        first_service = first_claim['SVC_loop'][0]
        print(f"First service DTM segments: {len(first_service['DTM'])}")
        if first_service['DTM']:
            for i, dtm in enumerate(first_service['DTM']):
                print(f"  Service DTM {i+1}: {dtm}")

if __name__ == "__main__":
    test_dtm_placement()