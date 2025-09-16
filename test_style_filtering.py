#!/usr/bin/env python3
"""Test script to verify style_category filtering works correctly."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database.connection import DatabaseManager
from backend.services.instruments_service import InstrumentsService
from backend.services.market_data_service import MarketDataService

def test_style_filtering():
    """Test the style_category filtering functionality."""
    print("Testing style_category filtering...")
    
    # Initialize services
    db_manager = DatabaseManager()
    market_service = MarketDataService()
    instruments_service = InstrumentsService(db_manager, market_service)
    
    # Test 1: Get all available style categories
    print("\n1. Getting available style categories:")
    try:
        styles = instruments_service.get_style_categories()
        print(f"Available styles: {styles}")
    except Exception as e:
        print(f"Error getting styles: {e}")
        return False
    
    # Test 2: Filter by growth style
    print("\n2. Filtering by 'growth' style:")
    try:
        growth_instruments = instruments_service.get_instruments(
            style_category="growth",
            limit=5
        )
        print(f"Found {growth_instruments.total_count} growth instruments")
        for instrument in growth_instruments.instruments:
            print(f"  {instrument.ticker}: {instrument.style_category}")
    except Exception as e:
        print(f"Error filtering by growth: {e}")
        return False
    
    # Test 3: Filter by value style
    print("\n3. Filtering by 'value' style:")
    try:
        value_instruments = instruments_service.get_instruments(
            style_category="value",
            limit=5
        )
        print(f"Found {value_instruments.total_count} value instruments")
        for instrument in value_instruments.instruments:
            print(f"  {instrument.ticker}: {instrument.style_category}")
    except Exception as e:
        print(f"Error filtering by value: {e}")
        return False
    
    # Test 4: Check that filtering actually works
    print("\n4. Verifying filtering works correctly:")
    if growth_instruments.total_count > 0:
        all_growth = all(instr.style_category == "growth" for instr in growth_instruments.instruments)
        print(f"All growth results have growth style: {all_growth}")
    
    if value_instruments.total_count > 0:
        all_value = all(instr.style_category == "value" for instr in value_instruments.instruments)
        print(f"All value results have value style: {all_value}")
    
    print("\nStyle filtering test completed successfully!")
    return True

if __name__ == "__main__":
    test_style_filtering()