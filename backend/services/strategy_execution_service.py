"""
Synchronous Strategy Execution Service

This service replaces the complex subprocess-based execution manager with
direct in-process strategy execution and database-centric progress tracking.
"""

import uuid
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import asdict

from .base_strategy_service import (
    BaseStrategyService, StrategyExecutionSummary, ProgressCallback, get_strategy_registry
)
from .bullish_breakout_service import BullishBreakoutService

logger = logging.getLogger(__name__)


class DatabaseProgressTracker:
    """Database-centric progress tracking for strategy execution."""
    
    def __init__(self, db_connection, run_id: str, strategy_code: str, total_tickers: int):
        self.db = db_connection
        self.run_id = run_id
        self.strategy_code = strategy_code
        self.total_tickers = total_tickers
        self.processed_count = 0
        self.passed_count = 0
        self.current_ticker = None
        self.start_time = datetime.utcnow()
        
        # Initialize progress in database
        self._initialize_progress()
    
    def _initialize_progress(self):
        """Initialize execution progress in database."""
        try:
            # Update strategy_execution_status table with initial progress
            self.db.execute("""
                UPDATE strategy_execution_status
                SET execution_status = ?,
                    current_ticker = ?,
                    progress_percent = ?,
                    processed_count = ?,
                    total_count = ?,
                    last_progress_update = ?
                WHERE run_id = ?
            """, (
                'running',
                None,
                0.0,
                0,
                self.total_tickers,
                datetime.utcnow().isoformat(),
                self.run_id
            ))
            
            logger.info(f"Initialized progress tracking for run {self.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize progress tracking: {e}")
    
    def update_ticker_progress(self, ticker: str, passed: bool, score: float,
                             classification: str, sequence_number: int,
                             processing_time_ms: int, error_message: Optional[str] = None,
                             reasons: Optional[List[str]] = None, metrics: Optional[Dict[str, Any]] = None):
        """Update progress for individual ticker."""
        try:
            self.processed_count += 1
            if passed:
                self.passed_count += 1
            self.current_ticker = ticker
            
            progress_percent = (self.processed_count / self.total_tickers) * 100
            created_at = datetime.utcnow().isoformat()
            
            # Insert ticker progress
            self.db.execute("""
                INSERT OR REPLACE INTO strategy_execution_progress
                (run_id, ticker, sequence_number, processed_at, passed, score,
                 classification, error_message, processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.run_id,
                ticker,
                sequence_number,
                created_at,
                passed,
                score,
                classification,
                error_message,
                processing_time_ms
            ))
            
            # Also insert into strategy_result table for API compatibility
            import json
            reasons_str = ';'.join(reasons) if reasons else ''
            metrics_json = json.dumps(metrics) if metrics else '{}'
            
            self.db.execute("""
                INSERT OR REPLACE INTO strategy_result
                (run_id, strategy_code, ticker, passed, score, classification,
                 reasons, metrics_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.run_id,
                self.strategy_code,
                ticker,
                passed,
                score,
                classification,
                reasons_str,
                metrics_json,
                created_at
            ))
            
            # Update overall progress
            self.db.execute("""
                UPDATE strategy_execution_status
                SET current_ticker = ?,
                    progress_percent = ?,
                    processed_count = ?,
                    last_progress_update = ?
                WHERE run_id = ?
            """, (
                ticker,
                round(progress_percent, 1),
                self.processed_count,
                created_at,
                self.run_id
            ))
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update ticker progress for {ticker}: {e}")
    
    def finalize_execution(self, status: str, execution_time_ms: int, 
                          qualifying_count: int, summary_metrics: Dict[str, Any]):
        """Finalize execution with results."""
        try:
            self.db.execute("""
                UPDATE strategy_execution_status
                SET execution_status = ?,
                    progress_percent = ?,
                    last_progress_update = ?,
                    execution_time_ms = ?,
                    qualifying_count = ?,
                    summary = ?
                WHERE run_id = ?
            """, (
                status,
                100.0,
                datetime.utcnow().isoformat(),
                execution_time_ms,
                qualifying_count,
                str(summary_metrics),  # Store as string for now
                self.run_id
            ))
            
            self.db.commit()
            logger.info(f"Finalized execution for run {self.run_id}: {status}")
            
        except Exception as e:
            logger.error(f"Failed to finalize execution: {e}")


class StrategyExecutionService:
    """
    Synchronous strategy execution service.
    
    This service provides direct in-process execution of strategies with
    database-centric progress tracking, replacing the complex subprocess
    execution manager.
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.registry = get_strategy_registry()
        
        # Register available services
        self._register_services()
        
        logger.info("StrategyExecutionService initialized")
    
    def _register_services(self):
        """Register all available strategy services."""
        try:
            # Register bullish breakout service
            bullish_service = BullishBreakoutService()
            self.registry.register(bullish_service)
            
            logger.info(f"Registered {len(self.registry.list_strategies())} strategy services")
            
        except Exception as e:
            logger.error(f"Failed to register strategy services: {e}")
    
    def execute_strategy_sync(self, strategy_code: str, tickers: List[str], 
                            parameters: Dict[str, Any], 
                            run_id: Optional[str] = None) -> StrategyExecutionSummary:
        """
        Execute strategy synchronously with database progress tracking.
        
        Args:
            strategy_code: Strategy identifier (e.g., 'bullish_breakout')
            tickers: List of ticker symbols to evaluate
            parameters: Strategy parameters
            run_id: Optional run ID (generated if not provided)
            
        Returns:
            StrategyExecutionSummary with complete results
            
        Raises:
            ValueError: If strategy not found or invalid parameters
            Exception: If execution fails
        """
        # Generate run ID if not provided
        if not run_id:
            run_id = str(uuid.uuid4())
        
        # Add run_id to parameters for service
        parameters = parameters.copy()
        parameters['run_id'] = run_id
        
        start_time = time.time()
        
        try:
            # Validate strategy exists
            service = self.registry.get(strategy_code)
            if not service:
                raise ValueError(f"Strategy '{strategy_code}' not found")
            
            # Validate parameters
            if not service.validate_parameters({'tickers': tickers, **parameters}):
                raise ValueError(f"Invalid parameters for strategy '{strategy_code}'")
            
            logger.info(f"Starting synchronous execution: {strategy_code} with {len(tickers)} tickers (run_id: {run_id})")
            
            # Create run record in database
            if self.db:
                self._create_run_record(run_id, strategy_code, parameters, len(tickers))
            
            # Initialize database progress tracking
            progress_tracker = None
            if self.db:
                progress_tracker = DatabaseProgressTracker(
                    self.db, run_id, strategy_code, len(tickers)
                )
            
            # Create progress callback for database updates
            def database_progress_callback(**kwargs):
                if progress_tracker:
                    stage = kwargs.get('stage')
                    
                    if stage == 'evaluation':
                        # Individual ticker progress
                        ticker = kwargs.get('ticker', '')
                        passed = kwargs.get('passed', False)
                        score = kwargs.get('score', 0)
                        classification = kwargs.get('classification', 'N/A')
                        sequence_number = kwargs.get('sequence_number', 0)
                        reasons = kwargs.get('reasons', [])
                        metrics = kwargs.get('metrics', {})
                        
                        # Estimate processing time (can be enhanced)
                        processing_time_ms = int((time.time() - start_time) * 1000 / max(1, sequence_number))
                        
                        progress_tracker.update_ticker_progress(
                            ticker, passed, score, classification,
                            sequence_number, processing_time_ms, None, reasons, metrics
                        )
                        
                        logger.debug(f"Ticker progress: {ticker} - {'PASS' if passed else 'FAIL'} (Score: {score})")
            
            # Execute strategy with progress callback
            progress_callback = ProgressCallback(database_progress_callback)
            result = service.execute(tickers, parameters, progress_callback)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Finalize database tracking
            if progress_tracker:
                progress_tracker.finalize_execution(
                    status='completed',
                    execution_time_ms=execution_time_ms,
                    qualifying_count=result.qualifying_count,
                    summary_metrics=result.summary_metrics
                )
            
            # Update strategy_run table with completion data
            if self.db:
                self._update_run_completion(run_id, 'completed', execution_time_ms)
            
            logger.info(f"Strategy execution completed: {strategy_code} - {result.qualifying_count}/{result.total_evaluated} passed in {execution_time_ms}ms")
            
            return result
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Update database with error status
            if self.db and run_id:
                try:
                    self.db.execute("""
                        UPDATE strategy_execution_status
                        SET execution_status = ?,
                            last_progress_update = ?,
                            execution_time_ms = ?
                        WHERE run_id = ?
                    """, (
                        'error',
                        datetime.utcnow().isoformat(),
                        execution_time_ms,
                        run_id
                    ))
                    self.db.commit()
                    
                    # Also update strategy_run table with error completion
                    self._update_run_completion(run_id, 'error', execution_time_ms)
                except Exception as db_error:
                    logger.error(f"Failed to update error status in database: {db_error}")
            
            logger.error(f"Strategy execution failed: {strategy_code} - {str(e)}")
            raise
    def _create_run_record(self, run_id: str, strategy_code: str, 
                          parameters: Dict[str, Any], total_count: int):
        """Create initial run record in both tables."""
        try:
            import json
            import hashlib
            
            # Get strategy version and create hash
            version = "1.0"
            params_json = json.dumps(parameters, sort_keys=True)
            params_hash = hashlib.md5(params_json.encode()).hexdigest()[:16]
            
            # Insert into strategy_run table for backward compatibility
            self.db.execute("""
                INSERT INTO strategy_run 
                (run_id, strategy_code, version, params_hash, params_json, 
                 started_at, universe_source, universe_size, min_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, strategy_code, version, params_hash, params_json,
                datetime.now().isoformat(), "api", total_count, 
                parameters.get("min_score", 70)
            ))
            
            # Insert into strategy_execution_status table for progress tracking
            self.db.execute("""
                INSERT INTO strategy_execution_status 
                (run_id, strategy_code, execution_status, total_count, 
                 processed_count, qualifying_count, current_ticker, 
                 progress_percent, execution_started_at, last_progress_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, strategy_code, "queued", total_count, 
                0, 0, None, 0.0, datetime.now().isoformat(), 
                datetime.now().isoformat()
            ))
            
            self.db.commit()
            logger.info(f"Created run record for {run_id}")
            
        except Exception as e:
            logger.error(f"Failed to create run record for {run_id}: {e}")
            raise
    
    def _update_run_completion(self, run_id: str, exit_status: str, duration_ms: int):
        """Update strategy_run table with completion information."""
        try:
            completed_at = datetime.now().isoformat()
            
            self.db.execute("""
                UPDATE strategy_run
                SET completed_at = ?, exit_status = ?, duration_ms = ?
                WHERE run_id = ?
            """, (completed_at, exit_status, duration_ms, run_id))
            
            self.db.commit()
            logger.info(f"Updated completion data for run {run_id}: {exit_status} in {duration_ms}ms")
            
        except Exception as e:
            logger.error(f"Failed to update run completion for {run_id}: {e}")
    
    def get_execution_progress(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current execution progress from database.
        
        Args:
            run_id: Execution run identifier
            
        Returns:
            Progress information or None if not found
        """
        if not self.db:
            return None
        
        try:
            # Get overall progress
            cursor = self.db.execute("""
                SELECT execution_status, current_ticker, progress_percent,
                       processed_count, total_count, last_progress_update,
                       qualifying_count
                FROM strategy_execution_status
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get recent ticker progress
            recent_cursor = self.db.execute("""
                SELECT ticker, passed, score, classification, processed_at, processing_time_ms
                FROM strategy_execution_progress 
                WHERE run_id = ? 
                ORDER BY sequence_number DESC 
                LIMIT 10
            """, (run_id,))
            
            recent_results = []
            for result_row in recent_cursor.fetchall():
                recent_results.append({
                    'ticker': result_row[0],
                    'passed': bool(result_row[1]),
                    'score': result_row[2],
                    'classification': result_row[3],
                    'processed_at': result_row[4],
                    'processing_time_ms': result_row[5]
                })
            
            return {
                'run_id': run_id,
                'status': row[0],
                'current_ticker': row[1],
                'progress_percent': row[2] or 0.0,
                'processed_count': row[3] or 0,
                'total_count': row[4] or 0,
                'last_update': row[5],
                'qualifying_count': row[6] or 0,
                'recent_results': recent_results
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution progress for {run_id}: {e}")
            return None
    
    def get_execution_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete execution results.
        
        Args:
            run_id: Execution run identifier
            
        Returns:
            Complete results or None if not found
        """
        if not self.db:
            return None
        
        try:
            # Get run information
            cursor = self.db.execute("""
                SELECT strategy_code, execution_status, total_count,
                       qualifying_count, execution_time_ms, summary
                FROM strategy_execution_status
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get all results
            results_cursor = self.db.execute("""
                SELECT ticker, passed, score, classification, processed_at,
                       processing_time_ms, error_message
                FROM strategy_execution_progress 
                WHERE run_id = ? 
                ORDER BY sequence_number ASC
            """, (run_id,))
            
            all_results = []
            for result_row in results_cursor.fetchall():
                all_results.append({
                    'ticker': result_row[0],
                    'passed': bool(result_row[1]),
                    'score': result_row[2],
                    'classification': result_row[3],
                    'processed_at': result_row[4],
                    'processing_time_ms': result_row[5],
                    'error_message': result_row[6]
                })
            
            # Separate qualifying and non-qualifying
            qualifying_results = [r for r in all_results if r['passed']]
            
            return {
                'run_id': run_id,
                'strategy_code': row[0],
                'status': row[1],
                'total_evaluated': row[2] or 0,
                'qualifying_count': row[3] or 0,
                'execution_time_ms': row[4] or 0,
                'summary_metrics': row[5],  # Could parse JSON if needed
                'qualifying_results': qualifying_results,
                'all_results': all_results
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution results for {run_id}: {e}")
            return None
    
    def list_available_strategies(self) -> List[Dict[str, str]]:
        """List all available strategy services."""
        return self.registry.list_strategies()
    
    def get_strategy_info(self, strategy_code: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific strategy."""
        service = self.registry.get(strategy_code)
        if not service:
            return None
        
        return {
            'code': service.get_strategy_code(),
            'name': service.get_strategy_name(),
            'default_parameters': service.get_default_parameters(),
            'parameter_schema': service.get_parameter_schema()
        }


# Global service instance
_execution_service: Optional[StrategyExecutionService] = None


def get_strategy_execution_service(db_connection=None) -> StrategyExecutionService:
    """Get or create global strategy execution service."""
    global _execution_service
    if _execution_service is None:
        _execution_service = StrategyExecutionService(db_connection)
    return _execution_service