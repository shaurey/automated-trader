#!/usr/bin/env python3
"""
Test script to validate the CSV holdings import backend API endpoint.
This script tests the /api/holdings/import endpoint directly.
"""

import requests
import json
import os
from pathlib import Path

# API configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/holdings/import"

def test_csv_import():
    """Test the CSV import endpoint with our test file."""
    
    # Check if test CSV file exists
    csv_file_path = Path("test_holdings_import.csv")
    if not csv_file_path.exists():
        print("ERROR: test_holdings_import.csv file not found!")
        return False
    
    print("Testing CSV Holdings Import Backend API")
    print("=" * 50)
    
    # Test 1: Health check first
    print("1. Testing API health check...")
    try:
        health_response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        if health_response.status_code == 200:
            print("PASS - API health check passed")
        else:
            print(f"WARN - API health check returned status: {health_response.status_code}")
    except Exception as e:
        print(f"FAIL - API health check failed: {e}")
        return False
    
    # Test 2: Import CSV file
    print("\n2. Testing CSV import...")
    
    try:
        # Read the CSV file
        with open(csv_file_path, 'rb') as f:
            csv_content = f.read()
        
        # Prepare the multipart form data
        files = {
            'file': ('test_holdings_import.csv', csv_content, 'text/csv')
        }
        
        form_data = {
            'account': 'TEST_ROTH_IRA',
            'replace_existing': 'true'
        }
        
        print(f"   - Account: {form_data['account']}")
        print(f"   - Replace existing: {form_data['replace_existing']}")
        print(f"   - File size: {len(csv_content)} bytes")
        
        # Make the API request
        print("   - Sending request to backend...")
        response = requests.post(
            API_ENDPOINT,
            files=files,
            data=form_data,
            timeout=30
        )
        
        print(f"   - Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Parse and display results
            result = response.json()
            print("PASS - CSV import successful!")
            print("\nImport Summary:")
            summary = result.get('import_summary', {})
            print(f"   - Total rows processed: {summary.get('total_rows_processed', 0)}")
            print(f"   - Records imported: {summary.get('records_imported', 0)}")
            print(f"   - Records skipped: {summary.get('records_skipped', 0)}")
            print(f"   - Records failed: {summary.get('records_failed', 0)}")
            print(f"   - Existing holdings deleted: {summary.get('existing_holdings_deleted', 0)}")
            print(f"   - Import successful: {summary.get('import_successful', False)}")
            
            # Show imported records
            imported_records = result.get('imported_records', [])
            if imported_records:
                print(f"\nImported Records ({len(imported_records)}):")
                for record in imported_records:
                    status = record.get('status', 'unknown')
                    ticker = record.get('ticker', 'N/A')
                    quantity = record.get('quantity', 0)
                    cost_basis = record.get('cost_basis', 0)
                    print(f"   - {ticker}: {quantity} shares, ${cost_basis:.2f} cost basis [{status}]")
            
            # Show warnings
            warnings = result.get('warnings', [])
            if warnings:
                print(f"\nWarnings ({len(warnings)}):")
                for warning in warnings:
                    print(f"   - {warning}")
            
            # Show errors
            errors = result.get('errors', [])
            if errors:
                print(f"\nErrors ({len(errors)}):")
                for error in errors:
                    print(f"   - {error}")
            
            return True
            
        else:
            print(f"FAIL - CSV import failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   - Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   - Response body: {response.text}")
            return False
            
    except Exception as e:
        print(f"FAIL - CSV import request failed: {e}")
        return False

def test_holdings_endpoints():
    """Test related holdings endpoints to verify the import worked."""
    
    print("\n3. Testing related endpoints...")
    
    # Test accounts endpoint
    try:
        print("   - Testing /api/holdings/accounts...")
        accounts_response = requests.get(f"{BASE_URL}/api/holdings/accounts", timeout=10)
        if accounts_response.status_code == 200:
            accounts_data = accounts_response.json()
            accounts = accounts_data.get('accounts', [])
            print(f"     PASS - Found {len(accounts)} accounts:")
            for account in accounts:
                account_name = account.get('account', 'N/A')
                position_count = account.get('position_count', 0)
                print(f"       - {account_name}: {position_count} positions")
        else:
            print(f"     FAIL - Accounts endpoint failed: {accounts_response.status_code}")
    except Exception as e:
        print(f"     FAIL - Accounts endpoint error: {e}")
    
    # Test positions endpoint
    try:
        print("   - Testing /api/holdings/positions...")
        positions_response = requests.get(f"{BASE_URL}/api/holdings/positions?account=TEST_ROTH_IRA", timeout=10)
        if positions_response.status_code == 200:
            positions_data = positions_response.json()
            positions = positions_data.get('positions', [])
            total_count = positions_data.get('total_count', 0)
            print(f"     PASS - Found {total_count} total positions for TEST_ROTH_IRA:")
            for position in positions[:5]:  # Show first 5
                ticker = position.get('ticker', 'N/A')
                quantity = position.get('quantity', 0)
                market_value = position.get('market_value', 0)
                print(f"       - {ticker}: {quantity} shares, ${market_value or 0:.2f} value")
            if len(positions) > 5:
                print(f"       - ... and {len(positions) - 5} more")
        else:
            print(f"     FAIL - Positions endpoint failed: {positions_response.status_code}")
    except Exception as e:
        print(f"     FAIL - Positions endpoint error: {e}")

if __name__ == "__main__":
    print("Starting CSV Holdings Import Backend Test")
    print(f"Testing API at: {BASE_URL}")
    print()
    
    success = test_csv_import()
    
    if success:
        test_holdings_endpoints()
        print("\nBackend CSV import test completed successfully!")
    else:
        print("\nBackend CSV import test failed!")
    
    print("\n" + "=" * 50)