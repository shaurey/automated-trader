#!/usr/bin/env python3
"""
Test script to verify the numpy JSON serialization fix.
"""

import sys
import os
import json
import numpy as np
import pandas as pd

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.strategy_execution_service import convert_numpy_types

def test_convert_numpy_types():
    """Test the convert_numpy_types function with various numpy types."""
    print("Testing convert_numpy_types function...")
    
    # Test data with various numpy types that commonly cause JSON serialization errors
    test_metrics = {
        'numpy_bool_true': np.bool_(True),
        'numpy_bool_false': np.bool_(False),
        'numpy_int32': np.int32(42),
        'numpy_int64': np.int64(1000),
        'numpy_float32': np.float32(3.14159),
        'numpy_float64': np.float64(2.71828),
        'regular_bool': True,
        'regular_int': 100,
        'regular_float': 1.23,
        'regular_string': 'test',
        'nested_dict': {
            'inner_numpy_bool': np.bool_(False),
            'inner_numpy_float': np.float64(99.99),
            'inner_list': [np.int32(1), np.int32(2), np.int32(3)]
        },
        'numpy_array_as_list': [np.float32(1.1), np.float32(2.2), np.float32(3.3)],
        'pandas_na': pd.NA,
        'numpy_nan': np.nan
    }
    
    print("Original metrics (with numpy types):")
    for key, value in test_metrics.items():
        print(f"  {key}: {value} (type: {type(value)})")
    
    # Test direct JSON serialization (should fail)
    print("\nTesting direct JSON serialization (should fail)...")
    try:
        json_str = json.dumps(test_metrics)
        print("FAIL: Direct JSON serialization succeeded - this is unexpected!")
    except TypeError as e:
        print(f"PASS: Direct JSON serialization failed as expected: {e}")
    
    # Test with conversion function
    print("\nTesting JSON serialization with convert_numpy_types...")
    try:
        converted_metrics = convert_numpy_types(test_metrics)
        json_str = json.dumps(converted_metrics)
        print("PASS: JSON serialization with conversion succeeded!")
        
        print("\nConverted metrics (native Python types):")
        for key, value in converted_metrics.items():
            print(f"  {key}: {value} (type: {type(value)})")
        
        print(f"\nGenerated JSON (first 200 chars):")
        print(json_str[:200] + "..." if len(json_str) > 200 else json_str)
        
        # Test round-trip
        parsed_back = json.loads(json_str)
        print("\nPASS: JSON round-trip parsing succeeded!")
        
        return True
        
    except Exception as e:
        print(f"FAIL: JSON serialization with conversion failed: {e}")
        return False

def test_edge_cases():
    """Test edge cases for the conversion function."""
    print("\n" + "="*50)
    print("Testing edge cases...")
    
    # Test empty structures
    empty_dict = {}
    empty_list = []
    
    # Test None values
    none_value = None
    
    # Test mixed nested structures
    complex_structure = {
        'empty_dict': {},
        'empty_list': [],
        'none_value': None,
        'deeply_nested': {
            'level2': {
                'level3': {
                    'numpy_val': np.float64(42.0),
                    'list_with_numpy': [np.int32(1), np.bool_(True), None]
                }
            }
        }
    }
    
    try:
        converted = convert_numpy_types(complex_structure)
        json_str = json.dumps(converted)
        print("PASS: Edge cases conversion succeeded!")
        return True
    except Exception as e:
        print(f"FAIL: Edge cases conversion failed: {e}")
        return False

if __name__ == "__main__":
    print("Numpy JSON Serialization Fix Test")
    print("=" * 50)
    
    success1 = test_convert_numpy_types()
    success2 = test_edge_cases()
    
    print("\n" + "="*50)
    if success1 and success2:
        print("PASS: All tests passed! The numpy JSON serialization fix is working correctly.")
        sys.exit(0)
    else:
        print("FAIL: Some tests failed. Please check the implementation.")
        sys.exit(1)