#!/usr/bin/env python3
"""
Simple test to reproduce the JSON serialization error.
"""

import json
import sys
import os
import pandas as pd
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_json_issue():
    """Test the JSON serialization issue with numpy booleans."""
    
    print("Testing JSON serialization with numpy boolean values...")
    
    # This simulates the exact metrics created by BullishBreakoutService
    # Lines 557-559 in bullish_breakout_service.py:
    metrics_with_numpy_bools = {
        "close": 150.25,
        "sma10": 148.32,
        "sma50_above": bool(True),           # Python bool - should work
        "sma200_above": np.bool_(True),      # numpy bool - likely the problem
        "require_52w_high": np.bool_(False), # numpy bool - likely the problem
        "processing_time_ms": 150
    }
    
    print("Metrics with mixed boolean types:")
    for key, value in metrics_with_numpy_bools.items():
        print(f"  {key}: {type(value).__name__} = {value}")
    
    print("\nTesting JSON serialization...")
    try:
        json_str = json.dumps(metrics_with_numpy_bools)
        print("SUCCESS: JSON serialization worked")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Test each field individually
        print("\nTesting individual fields:")
        for key, value in metrics_with_numpy_bools.items():
            try:
                json.dumps({key: value})
                print(f"  OK: {key}")
            except Exception as field_error:
                print(f"  ERROR: {key} -> {field_error}")
        return False

def test_solution():
    """Test the conversion solution."""
    
    print("\n" + "="*50)
    print("TESTING SOLUTION")
    print("="*50)
    
    # Create problematic metrics
    problematic_metrics = {
        "sma10_above": np.bool_(True),
        "sma50_above": np.bool_(True), 
        "sma200_above": np.bool_(True),
        "require_52w_high": np.bool_(False),
        "score": np.int64(85),
        "close": np.float64(150.25)
    }
    
    def convert_numpy_types(obj):
        """Convert numpy types to native Python types."""
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        else:
            return obj
    
    print("Original metrics:")
    for key, value in problematic_metrics.items():
        print(f"  {key}: {type(value).__name__} = {value}")
    
    print("\nConverting numpy types...")
    converted = convert_numpy_types(problematic_metrics)
    
    print("Converted metrics:")
    for key, value in converted.items():
        print(f"  {key}: {type(value).__name__} = {value}")
    
    print("\nTesting JSON serialization after conversion...")
    try:
        json_str = json.dumps(converted)
        print("SUCCESS: JSON serialization worked after conversion!")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    # Test the issue
    issue_reproduced = not test_json_issue()
    
    if issue_reproduced:
        print("\nJSON serialization issue reproduced!")
        
        # Test the solution
        solution_works = test_solution()
        
        if solution_works:
            print("\nSOLUTION CONFIRMED: Convert numpy types before JSON serialization")
        else:
            print("\nSOLUTION FAILED: Need alternative approach")
    else:
        print("\nCould not reproduce the issue - may be environment specific")