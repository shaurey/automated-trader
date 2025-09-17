"""Lightweight progress reporter for strategy scripts.

This module provides a ProgressReporter class that can be used by strategy scripts
to report progress during execution. It's designed to be optional and non-intrusive,
allowing scripts to work both standalone and with real-time progress tracking.
"""

import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any


class ProgressReporter:
    """Lightweight progress reporter for strategy scripts.
    
    This class provides a simple interface for strategy scripts to report progress
    during execution. When run_id is provided, progress is reported via stdout in
    JSON format. When run_id is None (standalone execution), progress reporting
    is silently disabled.
    """
    
    def __init__(self, run_id: Optional[str] = None):
        """Initialize progress reporter.
        
        Args:
            run_id: Unique run identifier. If None, progress reporting is disabled.
        """
        self.run_id = run_id
        self.enabled = run_id is not None
        self._stage_start_times: Dict[str, datetime] = {}
    
    def report_progress(
        self,
        stage: str,
        progress: float,
        message: str,
        current_item: Optional[str] = None,
        total_items: Optional[int] = None,
        completed_items: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Report progress if tracking is enabled.
        
        Args:
            stage: Current execution stage (e.g., 'initialization', 'data_download', 'analysis')
            progress: Progress percentage (0-100)
            message: Human-readable progress message
            current_item: Current item being processed (e.g., ticker symbol)
            total_items: Total number of items to process
            completed_items: Number of completed items
            metrics: Additional metrics dictionary
        """
        if not self.enabled:
            return
        
        # Track stage timing
        if stage not in self._stage_start_times:
            self._stage_start_times[stage] = datetime.utcnow()
        
        # Prepare progress data
        progress_data = {
            "type": "progress",
            "run_id": self.run_id,
            "stage": stage,
            "progress": min(100.0, max(0.0, progress)),  # Clamp to 0-100
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "current_item": current_item,
            "total_items": total_items,
            "completed_items": completed_items,
            "metrics": metrics or {}
        }
        
        # Add timing metrics if available
        if stage in self._stage_start_times:
            elapsed = (datetime.utcnow() - self._stage_start_times[stage]).total_seconds()
            progress_data["metrics"]["stage_elapsed_seconds"] = elapsed
        
        # Output progress to stdout in a format that can be parsed by the execution manager
        try:
            progress_json = json.dumps(progress_data, separators=(',', ':'))
            print(f"PROGRESS:{progress_json}", flush=True, file=sys.stdout)
        except Exception:
            # Silently ignore JSON serialization errors to prevent disrupting script execution
            pass
    
    def report_stage_start(self, stage: str, message: str) -> None:
        """Report the start of a new execution stage.
        
        Args:
            stage: Stage name
            message: Stage description
        """
        self.report_progress(stage, 0.0, f"Starting {stage}: {message}")
    
    def report_stage_complete(self, stage: str, message: str) -> None:
        """Report completion of an execution stage.
        
        Args:
            stage: Stage name
            message: Completion message
        """
        self.report_progress(stage, 100.0, f"Completed {stage}: {message}")
    
    def report_ticker_progress(
        self,
        stage: str,
        ticker: str,
        current_index: int,
        total_tickers: int,
        message: Optional[str] = None
    ) -> None:
        """Report progress for ticker processing.
        
        Args:
            stage: Current execution stage
            ticker: Current ticker being processed
            current_index: 0-based index of current ticker
            total_tickers: Total number of tickers to process
            message: Optional custom message (defaults to ticker processing message)
        """
        if total_tickers <= 0:
            return
        
        progress = ((current_index + 1) / total_tickers) * 100
        default_message = f"Processing {ticker} ({current_index + 1}/{total_tickers})"
        
        # Calculate throughput metrics
        metrics = {}
        if stage in self._stage_start_times:
            elapsed = (datetime.utcnow() - self._stage_start_times[stage]).total_seconds()
            if elapsed > 0:
                tickers_per_second = (current_index + 1) / elapsed
                remaining_tickers = total_tickers - (current_index + 1)
                estimated_remaining_seconds = remaining_tickers / tickers_per_second if tickers_per_second > 0 else 0
                
                metrics.update({
                    "tickers_per_second": round(tickers_per_second, 2),
                    "estimated_remaining_seconds": round(estimated_remaining_seconds, 1)
                })
        
        self.report_progress(
            stage=stage,
            progress=progress,
            message=message or default_message,
            current_item=ticker,
            total_items=total_tickers,
            completed_items=current_index + 1,
            metrics=metrics
        )
    
    def report_error(self, stage: str, error_message: str, exception: Optional[Exception] = None) -> None:
        """Report an error during execution.
        
        Args:
            stage: Stage where error occurred
            error_message: Human-readable error message
            exception: Optional exception object
        """
        if not self.enabled:
            return
        
        error_data = {
            "type": "error",
            "run_id": self.run_id,
            "stage": stage,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(exception).__name__ if exception else "Unknown",
            "error_details": str(exception) if exception else None
        }
        
        try:
            error_json = json.dumps(error_data, separators=(',', ':'))
            print(f"PROGRESS:{error_json}", flush=True, file=sys.stdout)
        except Exception:
            # Silently ignore JSON serialization errors
            pass
    
    def report_completion(self, message: str, summary_metrics: Optional[Dict[str, Any]] = None) -> None:
        """Report successful completion of execution.
        
        Args:
            message: Completion message
            summary_metrics: Optional summary metrics
        """
        if not self.enabled:
            return
        
        completion_data = {
            "type": "completed",
            "run_id": self.run_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "summary_metrics": summary_metrics or {}
        }
        
        try:
            completion_json = json.dumps(completion_data, separators=(',', ':'))
            print(f"PROGRESS:{completion_json}", flush=True, file=sys.stdout)
        except Exception:
            # Silently ignore JSON serialization errors
            pass