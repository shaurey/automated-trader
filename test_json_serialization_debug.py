#!/usr/bin/env python3
"""
Test script to reproduce and debug the JSON serialization error
that occurs when processing BullishBreakoutService metrics.
"""

import json
import sys
import os
import pandas as pd
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_json_serialization_issue():
    """Reproduce the exact JSON serialization error."""
    
    print("=" * 60)
    print("JSON SERIALIZATION ERROR DIAGNOSIS")
    print("=" * 60)
    
    # Simulate the metrics dictionary as created by BullishBreakoutService
    # Lines 557-559 in bullish_breakout_service.py contain the problematic boolean values:
    sample_metrics = {
        "close": 150.25,
        "sma10": 148.32,
        "sma50": 145.80,
        "sma200": 140.15,
        "macd": 0.5234,
        "macd_signal": 0.4123,
        "macd_hist": 0.1111,
        "rsi14": 65.43,
        "volume": 1500000,
        "vol_avg20": 1200000,
        "volume_multiple": 1.25,
        "ref_high": 148.90,
        "require_52w_high": False,  # Boolean - potential issue
        "change_pct": 1.23,
        "breakout_pct": 0.91,
        "points_sma": 25,
        "points_macd": 20,
        "points_rsi": 20,
        "points_volume": 20,
        "points_high": 15,
        "score": 100,
        "extra_score": 5,
        "risk": "Medium",
        "recommendation": "Buy",
        "sma10_above": True,    # Boolean - potential issue  
        "sma50_above": True,    # Boolean - potential issue
        "sma200_above": True,   # Boolean - potential issue
        "processing_time_ms": 150
    }
    
    print("1. Testing standard JSON serialization...")
    try:
        json_str = json.dumps(sample_metrics)
        print("✅ SUCCESS: Standard JSON serialization works")
        print(f"   JSON length: {len(json_str)} characters")
    except Exception as e:
        print(f"❌ FAILED: Standard JSON serialization: {e}")
        return
    
    # Now test with problematic values that could come from pandas/numpy
    print("\n2. Testing with numpy boolean values...")
    
    # Simulate what happens when pandas/numpy booleans are used
    problematic_metrics = sample_metrics.copy()
    problematic_metrics.update({
        "require_52w_high": np.bool_(False),  # numpy boolean
        "sma10_above": np.bool_(True),        # numpy boolean  
        "sma50_above": np.bool_(True),        # numpy boolean
        "sma200_above": np.bool_(True),       # numpy boolean
    })
    
    try:
        json_str = json.dumps(problematic_metrics)
        print("✅ SUCCESS: JSON serialization with numpy booleans works")
    except Exception as e:
        print(f"❌ FAILED: JSON serialization with numpy booleans: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   This is likely the root cause!")
        
        # Identify the problematic fields
        print("\n3. Identifying problematic field types...")
        for key, value in problematic_metrics.items():
            value_type = type(value)
            try:
                json.dumps(value)
                print(f"   ✅ {key}: {value_type.__name__} = {value}")
            except Exception as field_error:
                print(f"   ❌ {key}: {value_type.__name__} = {value} -> {field_error}")
        
        return problematic_metrics
    
    # Test with other potential problematic types
    print("\n4. Testing with other potentially problematic values...")
    
    edge_case_metrics = sample_metrics.copy()
    edge_case_metrics.update({
        "pandas_na": pd.NA,              # pandas NA
        "numpy_nan": np.nan,             # numpy NaN
        "numpy_float64": np.float64(123.456),  # numpy float64
        "numpy_int64": np.int64(789),    # numpy int64
    })
    
    for key, value in edge_case_metrics.items():
        try:
            json.dumps({key: value})
            print(f"   ✅ {key}: {type(value).__name__}")
        except Exception as e:
            print(f"   ❌ {key}: {type(value).__name__} -> {e}")

def test_solution_approaches():
    """Test different approaches to solve the JSON serialization issue."""
    
    print("\n" + "=" * 60)
    print("SOLUTION APPROACHES")
    print("=" * 60)
    
    # Create metrics with problematic numpy types
    problematic_metrics = {
        "close": 150.25,
        "sma10_above": np.bool_(True),        # numpy boolean
        "sma50_above": np.bool_(True),        # numpy boolean  
        "sma200_above": np.bool_(True),       # numpy boolean
        "require_52w_high": np.bool_(False),  # numpy boolean
        "numpy_float": np.float64(123.456),
        "numpy_int": np.int64(789)
    }
    
    print("1. Approach: Convert numpy types to native Python types...")
    
    def convert_numpy_types(obj):
        """Convert numpy types to native Python types."""
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(v) for v in obj]
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    try:
        converted_metrics = convert_numpy_types(problematic_metrics)
        json_str = json.dumps(converted_metrics)
        print("✅ SUCCESS: Conversion approach works!")
        print("   Converted types:")
        for key, value in converted_metrics.items():
            print(f"     {key}: {type(value).__name__} = {value}")
    except Exception as e:
        print(f"❌ FAILED: Conversion approach: {e}")
    
    print("\n2. Approach: Custom JSON encoder...")
    
    class NumpyJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif pd.isna(obj):
                return None
            return super().default(obj)
    
    try:
        json_str = json.dumps(problematic_metrics, cls=NumpyJSONEncoder)
        print("✅ SUCCESS: Custom encoder approach works!")
    except Exception as e:
        print(f"❌ FAILED: Custom encoder approach: {e}")

if __name__ == "__main__":
    # Test the issue
    problematic_data = test_json_serialization_issue()
    
    # Test solutions
    test_solution_approaches()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)