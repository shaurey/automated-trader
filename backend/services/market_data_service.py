"""Market data service using yfinance integration.

This service provides real-time market data by integrating with
the existing yfinance dependency and caching mechanisms.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching market data using yfinance."""
    
    def __init__(self, cache_duration_minutes: int = 5):
        """Initialize market data service.
        
        Args:
            cache_duration_minutes: How long to cache price data in minutes
        """
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current prices for a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary mapping ticker to price data
        """
        if not tickers:
            return {}
        
        # Filter out cached tickers that are still valid
        now = datetime.utcnow()
        fresh_tickers = []
        result = {}
        
        for ticker in tickers:
            cache_time = self._cache_timestamps.get(ticker)
            if cache_time and (now - cache_time) < self.cache_duration:
                # Use cached data
                result[ticker] = self._price_cache[ticker]
            else:
                fresh_tickers.append(ticker)
        
        # Fetch fresh data for uncached/expired tickers
        if fresh_tickers:
            fresh_data = self._fetch_prices_batch(fresh_tickers)
            result.update(fresh_data)
            
            # Update cache
            for ticker, data in fresh_data.items():
                self._price_cache[ticker] = data
                self._cache_timestamps[ticker] = now
        
        return result
    
    def get_single_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get current price for a single ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Price data dictionary or None if failed
        """
        result = self.get_current_prices([ticker])
        return result.get(ticker)
    
    def get_historical_data(
        self, 
        ticker: str, 
        period: str = "1y", 
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Get historical price data for a ticker.
        
        Args:
            ticker: Ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            pandas DataFrame with historical data or None if failed
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"No historical data found for {ticker}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {ticker}: {e}")
            return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company information for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Company info dictionary or None if failed
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                logger.warning(f"No company info found for {ticker}")
                return None
            
            # Extract relevant fields
            company_data = {
                'ticker': ticker,
                'company_name': info.get('longName') or info.get('shortName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap'),
                'description': info.get('longBusinessSummary'),
                'website': info.get('website'),
                'employees': info.get('fullTimeEmployees')
            }
            
            return company_data
            
        except Exception as e:
            logger.error(f"Failed to fetch company info for {ticker}: {e}")
            return None
    
    def _fetch_prices_batch(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch current prices for multiple tickers in batch.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary mapping ticker to price data
        """
        result = {}
        
        if len(tickers) == 1:
            # Single ticker - use direct API
            ticker = tickers[0]
            data = self._fetch_single_price(ticker)
            if data:
                result[ticker] = data
        else:
            # Multiple tickers - use batch API
            try:
                # Join tickers with spaces for yfinance batch request
                tickers_str = ' '.join(tickers)
                data = yf.download(
                    tickers_str, 
                    period="1d", 
                    interval="1m",
                    progress=False,
                    show_errors=False
                )
                
                if data.empty:
                    logger.warning(f"No data returned for tickers: {tickers}")
                    return result
                
                # Process multi-ticker data
                if len(tickers) > 1 and isinstance(data.columns, pd.MultiIndex):
                    for ticker in tickers:
                        try:
                            ticker_data = data.xs(ticker, level=1, axis=1)
                            if not ticker_data.empty:
                                latest = ticker_data.iloc[-1]
                                prev = ticker_data.iloc[-2] if len(ticker_data) > 1 else latest
                                
                                price_data = self._format_price_data(latest, prev, ticker)
                                if price_data:
                                    result[ticker] = price_data
                        except Exception as e:
                            logger.warning(f"Failed to process data for {ticker}: {e}")
                            # Fallback to single ticker fetch
                            fallback_data = self._fetch_single_price(ticker)
                            if fallback_data:
                                result[ticker] = fallback_data
                else:
                    # Single ticker in batch call
                    if not data.empty:
                        latest = data.iloc[-1]
                        prev = data.iloc[-2] if len(data) > 1 else latest
                        price_data = self._format_price_data(latest, prev, tickers[0])
                        if price_data:
                            result[tickers[0]] = price_data
                            
            except Exception as e:
                logger.error(f"Batch price fetch failed: {e}")
                # Fallback to individual fetches
                for ticker in tickers:
                    data = self._fetch_single_price(ticker)
                    if data:
                        result[ticker] = data
        
        return result
    
    def _fetch_single_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch current price for a single ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Price data dictionary or None if failed
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get recent data
            data = stock.history(period="2d", interval="1d")
            
            if data.empty:
                logger.warning(f"No price data found for {ticker}")
                return None
            
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            
            return self._format_price_data(latest, prev, ticker)
            
        except Exception as e:
            logger.error(f"Failed to fetch price for {ticker}: {e}")
            return None
    
    def _format_price_data(self, latest: pd.Series, prev: pd.Series, ticker: str) -> Optional[Dict[str, Any]]:
        """Format price data into standard dictionary.
        
        Args:
            latest: Latest price data
            prev: Previous price data
            ticker: Ticker symbol
            
        Returns:
            Formatted price data dictionary
        """
        try:
            current_price = latest.get('Close')
            prev_price = prev.get('Close')
            
            if pd.isna(current_price):
                return None
            
            change = None
            change_percent = None
            
            if not pd.isna(prev_price) and prev_price > 0:
                change = current_price - prev_price
                change_percent = (change / prev_price) * 100
            
            return {
                'ticker': ticker,
                'price': float(current_price),
                'change': float(change) if change is not None else None,
                'change_percent': float(change_percent) if change_percent is not None else None,
                'timestamp': datetime.utcnow(),
                'volume': float(latest.get('Volume', 0)) if not pd.isna(latest.get('Volume')) else None,
                'high': float(latest.get('High')) if not pd.isna(latest.get('High')) else None,
                'low': float(latest.get('Low')) if not pd.isna(latest.get('Low')) else None,
                'open': float(latest.get('Open')) if not pd.isna(latest.get('Open')) else None
            }
            
        except Exception as e:
            logger.error(f"Failed to format price data for {ticker}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the price cache."""
        self._price_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Market data cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache state.
        
        Returns:
            Dictionary with cache statistics
        """
        now = datetime.utcnow()
        valid_entries = 0
        expired_entries = 0
        
        for ticker, cache_time in self._cache_timestamps.items():
            if (now - cache_time) < self.cache_duration:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self._price_cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_duration_minutes': self.cache_duration.total_seconds() / 60
        }