"""
Test script for the simplified strategy execution endpoints.

This script tests the new HTTP polling endpoints that replace
the complex SSE streaming system.
"""

import requests
import time
import json
from datetime import datetime


def test_simplified_endpoints():
    """Test the simplified strategy execution endpoints."""
    
    base_url = "http://127.0.0.1:8000/api/strategies"
    
    print("Testing Simplified Strategy Execution Endpoints")
    print("=" * 50)
    
    # Test 1: List available strategies
    print("\n1. Testing strategy listing...")
    try:
        response = requests.get(f"{base_url}/list")
        if response.status_code == 200:
            strategies = response.json()
            print(f"✅ Available strategies: {strategies}")
        else:
            print(f"❌ Failed to list strategies: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error listing strategies: {e}")
        return False
    
    # Test 2: Get strategy info
    print("\n2. Testing strategy info...")
    if strategies and strategies.get('strategies'):
        strategy_code = strategies['strategies'][0]['code']
        try:
            response = requests.get(f"{base_url}/info/{strategy_code}")
            if response.status_code == 200:
                info = response.json()
                print(f"✅ Strategy info for '{strategy_code}': {info['name']}")
                print(f"   Default parameters: {len(info['default_parameters'])} params")
            else:
                print(f"❌ Failed to get strategy info: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error getting strategy info: {e}")
            return False
    else:
        print("❌ No strategies available for testing")
        return False
    
    # Test 3: Execute strategy synchronously (small test)
    print("\n3. Testing synchronous execution...")
    execution_request = {
        "strategy_code": strategy_code,
        "tickers": ["AAPL", "MSFT"],
        "parameters": {
            "min_volume": 1000000,
            "min_price": 10.0
        }
    }
    
    try:
        print(f"   Executing {strategy_code} on {execution_request['tickers']}...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/execute-sync", 
            json=execution_request,
            headers={"Content-Type": "application/json"}
        )
        
        execution_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Synchronous execution completed in {execution_time:.2f}s")
            print(f"   Status: {result['status']}")
            print(f"   Total evaluated: {result['total_evaluated']}")
            print(f"   Qualifying count: {result['qualifying_count']}")
            print(f"   Execution time: {result['execution_time_ms']}ms")
            
            sync_run_id = result['run_id']
        else:
            print(f"❌ Synchronous execution failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error in synchronous execution: {e}")
        return False
    
    # Test 4: Execute strategy asynchronously with polling
    print("\n4. Testing asynchronous execution with polling...")
    execution_request['tickers'] = ["GOOGL", "TSLA", "NVDA"]  # Different tickers for async test
    
    try:
        print(f"   Starting async execution on {execution_request['tickers']}...")
        
        # Start async execution
        response = requests.post(
            f"{base_url}/execute", 
            json=execution_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            execution_response = response.json()
            run_id = execution_response['run_id']
            print(f"✅ Async execution started with run_id: {run_id}")
            print(f"   Status: {execution_response['status']}")
            print(f"   Total tickers: {execution_response['total_tickers']}")
        else:
            print(f"❌ Failed to start async execution: {response.status_code} - {response.text}")
            return False
        
        # Poll for progress
        print("\n   Polling for progress...")
        max_polls = 30  # Maximum 30 polls (30 seconds)
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                progress_response = requests.get(f"{base_url}/progress/{run_id}")
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    status = progress['status']
                    progress_pct = progress['progress_percent']
                    processed = progress['processed_count']
                    total = progress['total_count']
                    current_ticker = progress.get('current_ticker', 'None')
                    
                    print(f"   Poll {poll_count + 1}: {status} - {progress_pct:.1f}% ({processed}/{total}) - Current: {current_ticker}")
                    
                    if status in ['completed', 'error']:
                        break
                        
                else:
                    print(f"❌ Failed to get progress: {progress_response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error polling progress: {e}")
                return False
            
            poll_count += 1
            time.sleep(1)  # Wait 1 second between polls
        
        # Get final results
        if status == 'completed':
            print("\n   Getting final results...")
            try:
                results_response = requests.get(f"{base_url}/results/{run_id}")
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    print(f"✅ Async execution completed successfully!")
                    print(f"   Total evaluated: {results['total_evaluated']}")
                    print(f"   Qualifying count: {results['qualifying_count']}")
                    print(f"   Execution time: {results['execution_time_ms']}ms")
                    
                    if results['qualifying_results']:
                        print("   Qualifying tickers:")
                        for result in results['qualifying_results']:
                            print(f"     - {result['ticker']}: {result['score']:.2f}")
                    else:
                        print("   No qualifying tickers found")
                        
                else:
                    print(f"❌ Failed to get results: {results_response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error getting results: {e}")
                return False
        else:
            print(f"❌ Execution did not complete successfully. Final status: {status}")
            return False
            
    except Exception as e:
        print(f"❌ Error in async execution test: {e}")
        return False
    
    return True


def check_server_health():
    """Check if the server is running and accessible."""
    try:
        response = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("Simplified Strategy Execution Endpoints Test")
    print("===========================================")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check server health first
    if not check_server_health():
        print("❌ Server is not accessible at http://127.0.0.1:8000")
        print("   Make sure the FastAPI server is running with:")
        print("   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000")
        exit(1)
    
    print("✅ Server is accessible")
    
    # Run endpoint tests
    success = test_simplified_endpoints()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All simplified endpoint tests passed!")
        print("   The new HTTP polling system is working correctly.")
        print("   The complex SSE streaming can now be replaced.")
    else:
        print("❌ Some endpoint tests failed.")
        print("   Check the error messages above for details.")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")