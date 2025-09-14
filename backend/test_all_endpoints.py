#!/usr/bin/env python3

import requests
import json

def test_endpoint(url, name):
    """Test an endpoint and print the results."""
    try:
        response = requests.get(url)
        print(f"\n=== {name} ===")
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            except json.JSONDecodeError:
                print(f"Raw response: {response.text}")
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {name}: {e}")

def main():
    """Test all endpoints."""
    base_url = "http://localhost:8000"
    
    endpoints = [
        (f"{base_url}/", "Root endpoint"),
        (f"{base_url}/api/health", "Health check"),
        (f"{base_url}/api/holdings/summary", "Holdings summary"),
        (f"{base_url}/api/holdings/positions", "Holdings positions"),
        (f"{base_url}/api/instruments", "Instruments list"),
        (f"{base_url}/docs", "API documentation"),
    ]
    
    print("Testing all FastAPI endpoints...")
    
    for url, name in endpoints:
        test_endpoint(url, name)
    
    print("\n=== Test Summary Complete ===")

if __name__ == "__main__":
    main()