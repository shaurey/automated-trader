"""Stock Validation Service for symbol validation and basic checks.

This service provides stock symbol validation and basic data availability checks.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import re

import yfinance as yf

logger = logging.getLogger(__name__)


class StockValidationService:
    """Service for validating stock symbols and basic data availability."""
    
    def __init__(self):
        """Initialize validation service."""
        self._validation_cache: Dict[str, Dict[str, Any]] = {}
        # Common ticker patterns and rules
        self.ticker_patterns = {
            'us_stock': re.compile(r'^[A-Z]{1,5}$'),  # 1-5 uppercase letters
            'us_stock_extended': re.compile(r'^[A-Z]{1,5}\.[A-Z]{1,2}$'),  # With exchange suffix
            'international': re.compile(r'^[A-Z0-9]{1,12}\.[A-Z]{1,3}$'),  # International with exchange
        }
    
    def validate_symbol(self, ticker: str, check_data_availability: bool = True) -> Dict[str, Any]:
        """Validate a stock symbol and optionally check data availability.
        
        Args:
            ticker: Stock ticker symbol to validate
            check_data_availability: Whether to check if market data is available
            
        Returns:
            Dictionary with validation results including:
            - is_valid: Boolean indicating if ticker is valid
            - symbol: Normalized ticker symbol
            - issues: List of validation issues
            - data_available: Whether market data is available (if checked)
            - symbol_type: Type of symbol (us_stock, international, etc.)
        """
        ticker = ticker.upper().strip()
        
        # Check cache first
        cache_key = f"{ticker}_{check_data_availability}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        result = {
            'symbol': ticker,
            'is_valid': False,
            'issues': [],
            'data_available': None,
            'symbol_type': None,
            'normalized_symbol': ticker
        }
        
        try:
            # Basic format validation
            format_result = self._validate_format(ticker)
            result.update(format_result)
            
            if not result['is_valid']:
                self._validation_cache[cache_key] = result
                return result
            
            # Check data availability if requested
            if check_data_availability:
                data_result = self._check_data_availability(ticker)
                result.update(data_result)
            
            # Cache result
            self._validation_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error validating symbol {ticker}: {e}")
            result['issues'].append(f"Validation error: {str(e)}")
            result['is_valid'] = False
            return result
    
    def validate_multiple_symbols(self, tickers: List[str], check_data_availability: bool = True) -> Dict[str, Dict[str, Any]]:
        """Validate multiple stock symbols.
        
        Args:
            tickers: List of ticker symbols to validate
            check_data_availability: Whether to check data availability for each
            
        Returns:
            Dictionary mapping ticker to validation results
        """
        results = {}
        
        for ticker in tickers:
            try:
                results[ticker] = self.validate_symbol(ticker, check_data_availability)
            except Exception as e:
                logger.error(f"Error validating {ticker}: {e}")
                results[ticker] = {
                    'symbol': ticker,
                    'is_valid': False,
                    'issues': [f"Validation failed: {str(e)}"],
                    'data_available': None,
                    'symbol_type': None,
                    'normalized_symbol': ticker
                }
        
        return results
    
    def get_symbol_suggestions(self, partial_symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get symbol suggestions for partial input.
        
        Args:
            partial_symbol: Partial ticker symbol
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested symbols with metadata
        """
        try:
            partial_symbol = partial_symbol.upper().strip()
            
            if len(partial_symbol) < 1:
                return []
            
            # For now, return basic suggestions based on common prefixes
            # In a production system, this would integrate with a symbol lookup service
            suggestions = []
            
            # Add some common stock suggestions based on input
            common_stocks = {
                'A': ['AAPL', 'AMZN', 'AMD', 'ADBE'],
                'B': ['BABA', 'BAC', 'BERKSHIRE'],
                'C': ['COST', 'CRM', 'CSCO'],
                'G': ['GOOGL', 'GOOG', 'GM', 'GE'],
                'M': ['MSFT', 'META', 'MCD', 'MA'],
                'N': ['NVDA', 'NFLX', 'NKE', 'NOW'],
                'T': ['TSLA', 'AAPL', 'TSM', 'TXN']
            }
            
            first_char = partial_symbol[0] if partial_symbol else ''
            if first_char in common_stocks:
                matching_stocks = [s for s in common_stocks[first_char] 
                                 if s.startswith(partial_symbol)]
                
                for stock in matching_stocks[:limit]:
                    suggestions.append({
                        'symbol': stock,
                        'match_type': 'prefix',
                        'confidence': 0.8 if stock.startswith(partial_symbol) else 0.6
                    })
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting suggestions for {partial_symbol}: {e}")
            return []
    
    def is_market_open(self) -> Dict[str, Any]:
        """Check if major markets are currently open.
        
        Returns:
            Dictionary with market status information
        """
        try:
            from datetime import datetime
            import pytz
            
            now_utc = datetime.utcnow()
            
            # Check US market hours (NYSE/NASDAQ)
            us_tz = pytz.timezone('America/New_York')
            us_time = now_utc.replace(tzinfo=pytz.UTC).astimezone(us_tz)
            
            # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
            us_market_open = (
                us_time.weekday() < 5 and  # Monday = 0, Friday = 4
                9.5 <= us_time.hour + us_time.minute/60 <= 16
            )
            
            return {
                'us_market_open': us_market_open,
                'current_time_et': us_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'current_time_utc': now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'note': 'Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday'
            }
            
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return {
                'us_market_open': None,
                'error': str(e)
            }
    
    def _validate_format(self, ticker: str) -> Dict[str, Any]:
        """Validate ticker symbol format."""
        result = {
            'is_valid': False,
            'symbol_type': None,
            'issues': []
        }
        
        if not ticker:
            result['issues'].append("Empty ticker symbol")
            return result
        
        if len(ticker) > 12:
            result['issues'].append("Ticker too long (max 12 characters)")
            return result
        
        if len(ticker) < 1:
            result['issues'].append("Ticker too short")
            return result
        
        # Check against patterns
        if self.ticker_patterns['us_stock'].match(ticker):
            result['is_valid'] = True
            result['symbol_type'] = 'us_stock'
        elif self.ticker_patterns['us_stock_extended'].match(ticker):
            result['is_valid'] = True
            result['symbol_type'] = 'us_stock_extended'
        elif self.ticker_patterns['international'].match(ticker):
            result['is_valid'] = True
            result['symbol_type'] = 'international'
        else:
            result['issues'].append("Invalid ticker format")
            
        return result
    
    def _check_data_availability(self, ticker: str) -> Dict[str, Any]:
        """Check if market data is available for ticker."""
        result = {
            'data_available': False,
            'data_issues': []
        }
        
        try:
            # Try to fetch basic info
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info or len(info) <= 1:
                result['data_issues'].append("No company information available")
                return result
            
            # Check for basic required fields
            has_price_data = any(key in info for key in [
                'currentPrice', 'regularMarketPrice', 'previousClose'
            ])
            
            if not has_price_data:
                # Try to get recent price data
                try:
                    hist = stock.history(period="5d")
                    if hist.empty:
                        result['data_issues'].append("No historical price data available")
                        return result
                    else:
                        has_price_data = True
                except:
                    result['data_issues'].append("Cannot fetch historical data")
                    return result
            
            if has_price_data:
                result['data_available'] = True
            else:
                result['data_issues'].append("No price data available")
            
        except Exception as e:
            result['data_issues'].append(f"Data check failed: {str(e)}")
            
        return result
    
    def clear_cache(self):
        """Clear the validation cache."""
        self._validation_cache.clear()
        logger.info("Stock validation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get validation cache statistics."""
        return {
            'cached_validations': len(self._validation_cache),
            'valid_symbols': sum(1 for v in self._validation_cache.values() if v.get('is_valid')),
            'invalid_symbols': sum(1 for v in self._validation_cache.values() if not v.get('is_valid'))
        }