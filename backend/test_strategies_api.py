"""Test script for the new strategy API endpoints."""

import asyncio
import sys
import os

# Add the parent directory to the path to enable proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from backend.main import app

def test_strategies_endpoints():
    """Test the strategy endpoints with a test client."""
    client = TestClient(app)
    
    print("Testing Strategy API Endpoints")
    print("=" * 40)
    
    # Test 1: Get strategy runs
    print("\n1. Testing GET /api/strategies/runs")
    response = client.get("/api/strategies/runs")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total runs found: {data.get('total_count', 0)}")
        print(f"Returned runs: {len(data.get('runs', []))}")
        if data.get('runs'):
            first_run = data['runs'][0]
            print(f"First run ID: {first_run.get('run_id', 'N/A')}")
            print(f"Strategy: {first_run.get('strategy_code', 'N/A')}")
    else:
        print(f"Error: {response.text}")
    
    # Test 2: Get strategy runs with filter
    print("\n2. Testing GET /api/strategies/runs with filter")
    response = client.get("/api/strategies/runs?strategy_code=bullish_breakout&limit=5")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Bullish breakout runs found: {data.get('total_count', 0)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 3: Get latest strategy runs
    print("\n3. Testing GET /api/strategies/latest")
    response = client.get("/api/strategies/latest")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Latest runs found: {len(data.get('latest_runs', []))}")
        print(f"Available strategies: {data.get('strategies', [])}")
    else:
        print(f"Error: {response.text}")
    
    # Test 4: Try to get specific run details (might not exist)
    print("\n4. Testing GET /api/strategies/runs/{run_id}")
    response = client.get("/api/strategies/runs")
    if response.status_code == 200:
        runs_data = response.json()
        if runs_data.get('runs'):
            first_run_id = runs_data['runs'][0]['run_id']
            response = client.get(f"/api/strategies/runs/{first_run_id}")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Run details for {first_run_id}")
                print(f"Strategy: {data.get('strategy_code')}")
                print(f"Total results: {data.get('total_results', 0)}")
                print(f"Passed: {data.get('passed_count', 0)}")
                print(f"Pass rate: {data.get('pass_rate', 0)}%")
            else:
                print(f"Error: {response.text}")
        else:
            print("No runs available to test details endpoint")
    
    # Test 5: Get results for a run (if available)
    print("\n5. Testing GET /api/strategies/runs/{run_id}/results")
    response = client.get("/api/strategies/runs")
    if response.status_code == 200:
        runs_data = response.json()
        if runs_data.get('runs'):
            first_run_id = runs_data['runs'][0]['run_id']
            response = client.get(f"/api/strategies/runs/{first_run_id}/results?limit=5")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Results for run {first_run_id}")
                print(f"Total results: {data.get('total_count', 0)}")
                print(f"Passed: {data.get('passed_count', 0)}")
                print(f"Failed: {data.get('failed_count', 0)}")
                print(f"Returned results: {len(data.get('results', []))}")
            else:
                print(f"Error: {response.text}")
        else:
            print("No runs available to test results endpoint")

if __name__ == "__main__":
    test_strategies_endpoints()