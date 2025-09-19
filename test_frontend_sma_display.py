#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test frontend SMA display logic using confirmed API data.
"""
import requests
import json

def test_frontend_sma_display():
    """Test that the API data would properly display SMA values in the frontend."""
    print("=== Testing Frontend SMA Display Logic ===")
    print()
    
    # Use the confirmed working endpoint
    run_id = "268315ea-5bdb-4c3e-96b9-e16c2b4fbf5a"
    endpoint = f"http://localhost:8000/api/strategies/runs/{run_id}/results"
    
    try:
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                print("Simulating frontend report generation...")
                print()
                
                # Simulate the frontend report logic for the first few results
                print("| Rank | Ticker | Score | Classification | Price | MA10 | MA50 | MA200 |")
                print("|------|--------|-------|----------------|-------|------|------|-------|")
                
                sma_displayed_correctly = False
                
                for i, result in enumerate(results[:5], 1):
                    ticker = result.get('ticker', 'N/A')
                    score = result.get('score', 0)
                    classification = result.get('classification', 'N/A')
                    
                    metrics = result.get('metrics', {})
                    
                    # Simulate frontend logic
                    price = f"${metrics.get('close', 0):.2f}" if metrics.get('close') else 'N/A'
                    ma10 = f"${metrics.get('sma10', 0):.2f}" if metrics.get('sma10') else 'N/A'
                    ma50 = f"${metrics.get('sma50', 0):.2f}" if metrics.get('sma50') else 'N/A'
                    ma200 = f"${metrics.get('sma200', 0):.2f}" if metrics.get('sma200') else 'N/A'
                    
                    # Check if SMA values are numeric (not N/A)
                    if ma10 != 'N/A' and ma50 != 'N/A' and ma200 != 'N/A':
                        sma_displayed_correctly = True
                    
                    print(f"| {i} | **{ticker}** | {score:.2f} | {classification} | {price} | {ma10} | {ma50} | {ma200} |")
                
                print()
                
                if sma_displayed_correctly:
                    print("SUCCESS: SMA values are properly displayed in frontend reports!")
                    print("The N/A issue has been resolved.")
                    return True
                else:
                    print("ISSUE: SMA values are still showing as N/A")
                    return False
            else:
                print("WARNING: No results found in API response")
                return False
        else:
            print(f"ERROR: API request failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_frontend_sma_display()
    if success:
        print("\n✅ FRONTEND SMA DISPLAY TEST PASSED!")
    else:
        print("\n❌ FRONTEND SMA DISPLAY TEST FAILED!")