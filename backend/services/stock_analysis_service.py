"""Stock Analysis Service for comprehensive stock data retrieval.

This service provides comprehensive stock analysis capabilities by integrating
real-time market data, technical indicators, and company information.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

import yfinance as yf
import pandas as pd
import numpy as np

from .market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class StockAnalysisService:
    """Service for comprehensive stock analysis and data retrieval."""
    
    def __init__(self, market_data_service: Optional[MarketDataService] = None):
        """Initialize stock analysis service.
        
        Args:
            market_data_service: Optional market data service instance
        """
        self.market_service = market_data_service or MarketDataService()
        self._info_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self.cache_duration = timedelta(hours=1)  # Cache company info for 1 hour
    
    def get_comprehensive_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive stock information including all available data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with comprehensive stock data or None if failed
        """
        try:
            ticker = ticker.upper()
            
            # Get basic market data
            market_data = self.market_service.get_single_price(ticker)
            if not market_data:
                logger.warning(f"No market data available for {ticker}")
                return None
            
            # Get company information (cached)
            company_info = self._get_cached_company_info(ticker)
            
            # Get technical indicators
            technical_data = self.get_technical_indicators(ticker)
            
            # Get historical performance
            performance_data = self.get_performance_metrics(ticker)
            
            # Combine all data
            comprehensive_data = {
                'ticker': ticker,
                'timestamp': datetime.utcnow(),
                
                # Market data
                'market_data': market_data,
                
                # Company information
                'company_info': company_info or {},
                
                # Technical analysis
                'technical_indicators': technical_data or {},
                
                # Performance metrics
                'performance_metrics': performance_data or {},
                
                # Data availability flags
                'data_quality': {
                    'has_market_data': market_data is not None,
                    'has_company_info': company_info is not None,
                    'has_technical_data': technical_data is not None,
                    'has_performance_data': performance_data is not None
                }
            }
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive stock info for {ticker}: {e}")
            return None
    
    def get_technical_indicators(self, ticker: str, period: str = "3mo") -> Optional[Dict[str, Any]]:
        """Calculate technical indicators for a stock.
        
        Args:
            ticker: Stock ticker symbol
            period: Historical data period
            
        Returns:
            Dictionary with technical indicators or None if failed
        """
        try:
            # Get historical data
            historical_data = self.market_service.get_historical_data(ticker, period=period, interval="1d")
            if historical_data is None or historical_data.empty:
                logger.warning(f"No historical data available for {ticker}")
                return None
            
            indicators = {}
            
            # Moving averages
            indicators['sma_10'] = float(historical_data['Close'].rolling(window=10).mean().iloc[-1])
            indicators['sma_20'] = float(historical_data['Close'].rolling(window=20).mean().iloc[-1])
            indicators['sma_50'] = float(historical_data['Close'].rolling(window=50).mean().iloc[-1])
            indicators['sma_200'] = float(historical_data['Close'].rolling(window=200).mean().iloc[-1]) if len(historical_data) >= 200 else None
            
            # Exponential moving averages
            indicators['ema_12'] = float(historical_data['Close'].ewm(span=12).mean().iloc[-1])
            indicators['ema_26'] = float(historical_data['Close'].ewm(span=26).mean().iloc[-1])
            
            # RSI (14-day)
            indicators['rsi_14'] = float(self._calculate_rsi(historical_data['Close'], 14))
            
            # MACD
            macd_data = self._calculate_macd(historical_data['Close'])
            indicators.update(macd_data)
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(historical_data['Close'])
            indicators.update(bb_data)
            
            # Volume indicators
            if 'Volume' in historical_data.columns:
                indicators['volume_sma_20'] = float(historical_data['Volume'].rolling(window=20).mean().iloc[-1])
                indicators['volume_ratio'] = float(historical_data['Volume'].iloc[-1] / indicators['volume_sma_20'])
            
            # Price position indicators
            current_price = float(historical_data['Close'].iloc[-1])
            indicators['price_vs_sma10'] = (current_price / indicators['sma_10'] - 1) * 100
            indicators['price_vs_sma20'] = (current_price / indicators['sma_20'] - 1) * 100
            indicators['price_vs_sma50'] = (current_price / indicators['sma_50'] - 1) * 100
            if indicators['sma_200']:
                indicators['price_vs_sma200'] = (current_price / indicators['sma_200'] - 1) * 100
            
            # ATR (Average True Range)
            indicators['atr_14'] = float(self._calculate_atr(historical_data, 14))
            
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators for {ticker}: {e}")
            return None
    
    def get_performance_metrics(self, ticker: str, period: str = "1y") -> Optional[Dict[str, Any]]:
        """Calculate performance metrics for a stock.
        
        Args:
            ticker: Stock ticker symbol
            period: Period for performance calculation
            
        Returns:
            Dictionary with performance metrics or None if failed
        """
        try:
            # Get historical data
            historical_data = self.market_service.get_historical_data(ticker, period=period, interval="1d")
            if historical_data is None or historical_data.empty:
                return None
            
            prices = historical_data['Close']
            returns = prices.pct_change().dropna()
            
            performance = {}
            
            # Basic performance metrics
            performance['total_return'] = float((prices.iloc[-1] / prices.iloc[0] - 1) * 100)
            performance['annualized_return'] = float(((prices.iloc[-1] / prices.iloc[0]) ** (252 / len(prices)) - 1) * 100)
            
            # Volatility metrics
            performance['volatility'] = float(returns.std() * np.sqrt(252) * 100)
            performance['daily_volatility'] = float(returns.std() * 100)
            
            # Risk metrics
            performance['max_drawdown'] = float(self._calculate_max_drawdown(prices))
            performance['sharpe_ratio'] = float(performance['annualized_return'] / performance['volatility']) if performance['volatility'] > 0 else 0
            
            # Recent performance
            performance['1_month_return'] = float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100) if len(prices) >= 21 else None
            performance['3_month_return'] = float((prices.iloc[-1] / prices.iloc[-63] - 1) * 100) if len(prices) >= 63 else None
            performance['6_month_return'] = float((prices.iloc[-1] / prices.iloc[-126] - 1) * 100) if len(prices) >= 126 else None
            
            # High/low metrics
            high_52w = float(prices.rolling(window=252).max().iloc[-1]) if len(prices) >= 252 else float(prices.max())
            low_52w = float(prices.rolling(window=252).min().iloc[-1]) if len(prices) >= 252 else float(prices.min())
            current_price = float(prices.iloc[-1])
            
            performance['52_week_high'] = high_52w
            performance['52_week_low'] = low_52w
            performance['distance_from_52w_high'] = (current_price / high_52w - 1) * 100
            performance['distance_from_52w_low'] = (current_price / low_52w - 1) * 100
            
            return performance
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics for {ticker}: {e}")
            return None
    
    def get_strategy_history(self, ticker: str, db_manager, limit: int = 10) -> List[Dict[str, Any]]:
        """Get strategy execution history for a ticker from database.
        
        Args:
            ticker: Stock ticker symbol
            db_manager: Database manager instance
            limit: Maximum number of results
            
        Returns:
            List of strategy execution results
        """
        try:
            query = """
            SELECT sr.run_id, sr.strategy_code, sr.ticker, sr.passed, sr.score, 
                   sr.classification, sr.reasons, sr.metrics_json, sr.created_at,
                   run.started_at, run.completed_at, run.params_json
            FROM strategy_result sr
            JOIN strategy_run run ON sr.run_id = run.run_id
            WHERE sr.ticker = ?
            ORDER BY sr.created_at DESC
            LIMIT ?
            """

            if hasattr(db_manager, "get_connection"):
                conn = db_manager.get_connection()
            else:
                conn = db_manager

            if conn is None or not hasattr(conn, "execute"):
                raise AttributeError("Database manager does not provide an executable connection")

            cursor = conn.execute(query, (ticker.upper(), limit))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = {
                    'run_id': row[0],
                    'strategy_code': row[1],
                    'ticker': row[2],
                    'passed': bool(row[3]),
                    'score': row[4],
                    'classification': row[5],
                    'reasons': row[6].split(',') if row[6] else [],
                    'metrics': json.loads(row[7]) if row[7] else {},
                    'created_at': row[8],
                    'run_started_at': row[9],
                    'run_completed_at': row[10],
                    'run_params': json.loads(row[11]) if row[11] else {}
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to get strategy history for {ticker}: {e}")
            return []
    
    def _get_cached_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company info with caching."""
        now = datetime.utcnow()
        cache_time = self._cache_timestamps.get(ticker)
        
        if cache_time and (now - cache_time) < self.cache_duration:
            return self._info_cache.get(ticker)
        
        # Fetch fresh data
        company_info = self.market_service.get_company_info(ticker)
        if company_info:
            self._info_cache[ticker] = company_info
            self._cache_timestamps[ticker] = now
        
        return company_info
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate MACD indicator."""
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd_line': float(macd_line.iloc[-1]),
            'macd_signal': float(signal_line.iloc[-1]),
            'macd_histogram': float(histogram.iloc[-1])
        }
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        
        current_price = prices.iloc[-1]
        bb_position = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])
        
        return {
            'bb_upper': float(upper_band.iloc[-1]),
            'bb_middle': float(sma.iloc[-1]),
            'bb_lower': float(lower_band.iloc[-1]),
            'bb_position': float(bb_position)  # 0 = at lower band, 1 = at upper band
        }
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0.0
    
    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + prices.pct_change()).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative / running_max - 1) * 100
        return drawdown.min()
    
    def clear_cache(self):
        """Clear the company info cache."""
        self._info_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Stock analysis cache cleared")