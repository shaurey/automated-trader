#!/usr/bin/env python3
"""
Debug script to trace SMA metrics through the complete data pipeline
"""
import sqlite3
import json
import requests
from datetime import datetime

def check_database_sma_content():
    """Check actual SMA values stored in database metrics_json"""
    print("=== STEP 1: DATABASE CONTENT CHECK ===")
    
    try:
        conn = sqlite3.connect('at_data.sqlite')
        cursor = conn.cursor()
        
        # Get recent strategy results with metrics
        query = """
        SELECT
            sr.run_id,
            sr.ticker,
            sr.passed,
            sr.score,
            sr.classification,
            sr.metrics_json,
            sr.created_at
        FROM strategy_result sr
        ORDER BY sr.created_at DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"Found {len(results)} recent strategy results")
        
        for result in results:
            run_id, ticker, passed, score, classification, metrics_json, created_at = result
            print(f"\n--- Run ID: {run_id} ---")
            print(f"Ticker: {ticker}")
            print(f"Passed: {passed}")
            print(f"Score: {score}")
            print(f"Classification: {classification}")
            print(f"Created: {created_at}")
            
            if metrics_json:
                try:
                    metrics = json.loads(metrics_json)
                    print("Metrics JSON structure:")
                    print(json.dumps(metrics, indent=2))
                    
                    # Check specifically for SMA values
                    sma_keys = [k for k in metrics.keys() if 'sma' in k.lower() or 'ma' in k.lower()]
                    print(f"\nSMA-related keys found: {sma_keys}")
                    
                    for key in sma_keys:
                        value = metrics[key]
                        print(f"  {key}: {value} (type: {type(value)})")
                        
                except json.JSONDecodeError as e:
                    print(f"ERROR parsing metrics JSON: {e}")
                    print(f"Raw metrics_json: {metrics_json}")
            else:
                print("No metrics_json found")
        
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

def test_api_response():
    """Test API endpoint to see what SMA data is returned"""
    print("\n=== STEP 2: API RESPONSE CHECK ===")
    
    try:
        # First get recent strategy runs
        runs_response = requests.get("http://localhost:8000/api/strategies/runs")
        if runs_response.status_code == 200:
            runs = runs_response.json()
            print(f"Found {len(runs)} strategy runs")
            
            if runs:
                # Get the most recent run
                latest_run = runs[0]
                run_id = latest_run['run_id']
                print(f"Testing with latest run ID: {run_id}")
                
                # Get results for this run
                results_url = f"http://localhost:8000/api/strategies/runs/{run_id}/results"
                print(f"Calling API: {results_url}")
                results_response = requests.get(results_url)
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    print(f"API returned {len(results)} results")
                    
                    # Check first few results for SMA data
                    for i, result in enumerate(results[:3]):
                        print(f"\n--- API Result {i+1} ---")
                        print(f"Ticker: {result.get('ticker', 'N/A')}")
                        print(f"Classification: {result.get('classification', 'N/A')}")
                        print(f"Score: {result.get('score', 'N/A')}")
                        
                        metrics = result.get('metrics', {})
                        print(f"Metrics object: {metrics}")
                        if metrics:
                            sma_keys = [k for k in metrics.keys() if 'sma' in k.lower() or 'ma' in k.lower()]
                            print(f"SMA keys in API response: {sma_keys}")
                            
                            for key in sma_keys:
                                value = metrics[key]
                                print(f"  {key}: {value}")
                        else:
                            print("No metrics in API response")
                else:
                    print(f"API error getting results: {results_response.status_code}")
                    print(f"Response text: {results_response.text}")
            else:
                print("No runs found")
        else:
            print(f"API error getting runs: {runs_response.status_code}")
            print(runs_response.text)
            
    except Exception as e:
        print(f"API test error: {e}")

def check_recent_execution():
    """Check what the most recent strategy execution contains"""
    print("\n=== STEP 3: RECENT EXECUTION CHECK ===")
    
    try:
        conn = sqlite3.connect('at_data.sqlite')
        cursor = conn.cursor()
        
        # Get the most recent strategy run
        query = """
        SELECT
            run_id, strategy_code, exit_status, universe_size,
            started_at, completed_at
        FROM strategy_run
        ORDER BY started_at DESC
        LIMIT 1
        """
        
        cursor.execute(query)
        run = cursor.fetchone()
        
        if run:
            run_id, strategy_code, exit_status, universe_size, started_at, completed_at = run
            print(f"Most recent run:")
            print(f"  ID: {run_id}")
            print(f"  Strategy: {strategy_code}")
            print(f"  Status: {exit_status}")
            print(f"  Universe size: {universe_size}")
            print(f"  Started: {started_at}")
            print(f"  Completed: {completed_at}")
            
            # Get some results from this run
            results_query = """
            SELECT ticker, classification, metrics_json
            FROM strategy_result
            WHERE run_id = ?
            LIMIT 5
            """
            
            cursor.execute(results_query, (run_id,))
            results = cursor.fetchall()
            
            print(f"\nSample results from this run ({len(results)} total):")
            for ticker, classification, metrics_json in results:
                print(f"  {ticker}: {classification}")
                if metrics_json:
                    try:
                        metrics = json.loads(metrics_json)
                        sma_values = {k: v for k, v in metrics.items() if 'sma' in k.lower() or 'ma' in k.lower()}
                        if sma_values:
                            print(f"    SMA values: {sma_values}")
                        else:
                            print("    No SMA values found")
                    except:
                        print("    Invalid JSON")
                else:
                    print("    No metrics")
        
        conn.close()
        
    except Exception as e:
        print(f"Recent execution check error: {e}")

if __name__ == "__main__":
    print("SMA METRICS PIPELINE DEBUG")
    print("=" * 50)
    
    check_database_sma_content()
    test_api_response()
    check_recent_execution()
    
    print("\n" + "=" * 50)
    print("DEBUG COMPLETE")