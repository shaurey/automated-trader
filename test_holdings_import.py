#!/usr/bin/env python3
"""Test script for holdings CSV import functionality."""

import requests
import json
import io
from datetime import datetime

# Sample CSV content for testing
SAMPLE_CSV = """Account Number,Symbol,Description,Quantity,Current Value,Cost Basis Total,Type
123456789,AAPL,Apple Inc,100.0,$15000.00,$12000.00,Stock
123456789,MSFT,Microsoft Corp,50.0,$17500.00,$14000.00,Stock
123456789,CASH,Cash and Cash Equivalents,0.0,$5000.00,$5000.00,Cash
123456789, -TSLA240315C00200000,Tesla Call Option,1.0,$500.00,$400.00,Option
123456789,GOOGL,Alphabet Inc Class A,25.0,$8750.00,$7500.00,Stock
"Pending activity",,"",,"",,"",""
"Disclaimer: This information is provided for informational purposes only."
"""

def test_holdings_import():
    """Test the holdings import endpoint."""
    
    # API endpoint
    base_url = "http://localhost:8000"
    import_url = f"{base_url}/api/holdings/import"
    
    # Test data
    test_account = "TEST_ACCOUNT"
    
    try:
        # Create CSV file-like object
        csv_file = io.BytesIO(SAMPLE_CSV.encode('utf-8'))
        
        # Prepare request
        files = {
            'file': ('test_holdings.csv', csv_file, 'text/csv')
        }
        data = {
            'account': test_account,
            'replace_existing': True
        }
        
        print(f"Testing holdings import for account: {test_account}")
        print("CSV content:")
        print(SAMPLE_CSV)
        print("-" * 50)
        
        # Make request
        response = requests.post(import_url, files=files, data=data)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("Import successful!")
            print(f"Import Summary:")
            print(f"  - Total rows processed: {result['import_summary']['total_rows_processed']}")
            print(f"  - Records imported: {result['import_summary']['records_imported']}")
            print(f"  - Records skipped: {result['import_summary']['records_skipped']}")
            print(f"  - Records failed: {result['import_summary']['records_failed']}")
            print(f"  - Existing holdings deleted: {result['import_summary']['existing_holdings_deleted']}")
            print(f"  - Import successful: {result['import_summary']['import_successful']}")
            
            if result['imported_records']:
                print(f"\nImported Records:")
                for record in result['imported_records']:
                    print(f"  - {record['ticker']}: {record['quantity']} shares @ ${record['cost_basis']:.2f} cost basis")
            
            if result['warnings']:
                print(f"\nWarnings:")
                for warning in result['warnings']:
                    print(f"  - {warning}")
            
            if result['errors']:
                print(f"\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")
                    
        else:
            print(f"Import failed with status {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the FastAPI server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error testing import: {e}")

def test_get_holdings():
    """Test getting holdings after import."""
    
    base_url = "http://localhost:8000"
    positions_url = f"{base_url}/api/holdings/positions"
    
    try:
        # Get positions for test account
        params = {'account': 'TEST_ACCOUNT'}
        response = requests.get(positions_url, params=params)
        
        print(f"\nGetting holdings for TEST_ACCOUNT:")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Found {len(result['positions'])} positions:")
            
            for position in result['positions']:
                print(f"  - {position['ticker']}: {position['quantity']} shares")
                if position['cost_basis']:
                    print(f"    Cost basis: ${position['cost_basis']:.2f}")
                
        else:
            print(f"Failed to get holdings: {response.text}")
            
    except Exception as e:
        print(f"Error getting holdings: {e}")

if __name__ == "__main__":
    # Test the import
    test_holdings_import()
    
    # Test getting the imported holdings
    test_get_holdings()