#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test backend API endpoints to verify SMA metrics are properly returned.
"""
import requests
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_strategy_results_api():
    """Test the strategy results API endpoint for SMA metrics."""
    print("=== Testing Backend API Endpoints ===")
    print()
    
    # First, let's get the run_id from our database check
    run_id = "268315ea-5bdb-4c3e-96b9-e16c2b4fbf5a"  # From our bullish_breakout results
    
    base_url = "http://localhost:8000"
    endpoint = f"/api/strategies/runs/{run_id}/results"
    
    try:
        print(f"Testing endpoint: {base_url}{endpoint}")
        response = requests.get(f"{base_url}{endpoint}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: API endpoint responded successfully")
            print(f"Response status: {response.status_code}")
            
            # Check if we have results
            if 'results' in data and len(data['results']) > 0:
                print(f"Found {len(data['results'])} results")
                
                # Check first few results for SMA metrics
                sma_found = False
                for i, result in enumerate(data['results'][:3], 1):
                    print(f"\nResult {i}:")
                    print(f"  Ticker: {result.get('ticker')}")
                    print(f"  Score: {result.get('score')}")
                    print(f"  Classification: {result.get('classification')}")
                    
                    # Check metrics
                    metrics = result.get('metrics', {})
                    if metrics:
                        print(f"  Metrics keys: {list(metrics.keys())[:10]}...")  # First 10 keys
                        
                        # Check for SMA values
                        sma_keys = [k for k in metrics.keys() if 'sma' in k.lower()]
                        if sma_keys:
                            sma_found = True
                            print(f"  SUCCESS: SMA metrics found in API response!")
                            for key in ['sma10', 'sma50', 'sma200']:
                                if key in metrics:
                                    print(f"     {key}: {metrics[key]}")
                        else:
                            print(f"  WARNING: No SMA metrics in API response")
                    else:
                        print(f"  WARNING: No metrics in API response")
                
                if sma_found:
                    print(f"\nSUCCESS: API properly returns SMA metrics!")
                    return True
                else:
                    print(f"\nISSUE: API does not return SMA metrics")
                    return False
            else:
                print("WARNING: No results found in API response")
                print(f"Response data: {json.dumps(data, indent=2)}")
                return False
        else:
            print(f"ERROR: API request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to backend server. Is it running on localhost:8000?")
        print("Try starting the server with: cd backend && python -m uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"ERROR: API test failed: {e}")
        return False

def test_health_endpoint():
    """Test the health endpoint first."""
    print("Testing health endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Backend server is running")
            return True
        else:
            print(f"WARNING: Health check returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("ERROR: Backend server is not running")
        return False
    except Exception as e:
        print(f"ERROR: Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting API endpoint tests...")
    print()
    
    # Test health first
    health_ok = test_health_endpoint()
    print()
    
    if health_ok:
        # Test strategy results API
        api_ok = test_strategy_results_api()
        
        if api_ok:
            print("\nSUCCESS: All API tests passed!")
        else:
            print("\nFAILED: API tests failed")
    else:
        print("FAILED: Cannot test API - server not running")
        print("\nTo start the server:")
        print("  cd backend")
        print("  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")