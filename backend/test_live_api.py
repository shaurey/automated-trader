#!/usr/bin/env python3
"""Test live API endpoints."""

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
                    # Show a sample of the data
                    for key, value in list(data.items())[:3]:
                        if isinstance(value, (str, int, float)):
                            print(f"  {key}: {value}")
                        elif isinstance(value, list):
                            print(f"  {key}: [{len(value)} items]")
                        elif isinstance(value, dict):
                            print(f"  {key}: {{...}}")
                else:
                    print(f"  Data: {data}")
            except json.JSONDecodeError:
                print(f"  Raw response: {response.text[:200]}...")
        else:
            print(f"  Error: {response.text}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"\n{name}: FAILED - {e}")
        return False

def main():
    """Test all endpoints."""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing Live API Endpoints...")
    print("=" * 40)
    
    # Wait a moment for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    endpoints = [
        (f"{base_url}/", "Root Endpoint"),
        (f"{base_url}/api/health", "Health Check"),
        (f"{base_url}/api/holdings/summary", "Holdings Summary"),
        (f"{base_url}/api/holdings/positions?limit=3", "Holdings Positions"),
        (f"{base_url}/api/holdings/accounts", "Holdings Accounts"),
        (f"{base_url}/api/holdings/stats", "Holdings Stats"),
        (f"{base_url}/api/instruments?limit=3", "Instruments"),
    ]
    
    results = []
    for url, name in endpoints:
        results.append(test_endpoint(url, name))
    
    print(f"\n{'=' * 40}")
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All API endpoints working!")
    else:
        print("⚠️  Some endpoints failed")

if __name__ == "__main__":
    main()