#!/usr/bin/env python3
"""Final API endpoint testing with fixed port."""

import time
import requests
import json

def test_endpoint(url, name):
    """Test an API endpoint."""
    try:
        response = requests.get(url, timeout=10)
        print(f"\n{name}:")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())}")
                else:
                    print(f"  Data: {data}")
                return True
            except json.JSONDecodeError:
                print(f"  Raw response: {response.text[:200]}...")
                return False
        else:
            print(f"  Error: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"\n{name}: FAILED - {e}")
        return False

def main():
    """Test all endpoints."""
    base_url = "http://127.0.0.1:8001"
    
    print("Testing Final API Endpoints on Port 8001...")
    print("=" * 50)
    
    # Wait for server
    print("Waiting for server to be ready...")
    time.sleep(3)
    
    endpoints = [
        (f"{base_url}/", "Root Endpoint"),
        (f"{base_url}/api/health", "Health Check"),
        (f"{base_url}/api/holdings/summary", "Holdings Summary"),
        (f"{base_url}/api/holdings/positions?limit=3", "Holdings Positions"),
        (f"{base_url}/api/holdings/accounts", "Holdings Accounts"),
        (f"{base_url}/api/holdings/stats", "Holdings Stats (FIXED)"),
        (f"{base_url}/api/instruments?limit=3", "Instruments"),
    ]
    
    results = []
    for url, name in endpoints:
        results.append(test_endpoint(url, name))
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("SUCCESS: All API endpoints working!")
        return 0
    else:
        print("WARNING: Some endpoints failed")
        return 1

if __name__ == "__main__":
    exit(main())