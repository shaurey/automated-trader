#!/usr/bin/env python3

import requests
import json

def test_health_endpoint():
    """Test the health endpoint and print the response."""
    try:
        response = requests.get("http://localhost:8000/api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode failed: {e}")
        print(f"Raw response: {response.text}")

if __name__ == "__main__":
    test_health_endpoint()