"""Strategy execution manager for background task management and queuing.

This module provides the StrategyExecutionManager class that handles:
- Strategy execution lifecycle management
- Background task execution with subprocess management
- Execution queue and concurrent run management
- Progress tracking integration
- Cancellation and error handling
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from ..models.schemas import (
    StrategyExecutionRequest, ExecutionState, ProgressEvent, 
    ProgressEventType, QueuedExecution
)
from .progress_service import get_progress_service
from .progress_reporter import ProgressReporter


logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Custom exception for execution errors."""
    pass


class StrategyExecutionManager:
    """Manages strategy execution lifecycle and queuing.
    
    This manager handles:
    - Queuing strategy executions with priority support
    - Background subprocess execution with progress monitoring
    - Concurrent execution limits and resource management
    - Real-time progress tracking via stdout parsing
    - Cancellation and cleanup operations
    """
    
    def __init__(self, max_concurrent: int = 2, max_queue_size: int = 10):
        """Initialize execution manager.
        
        Args:
            max_concurrent: Maximum number of concurrent executions
            max_queue_size: Maximum size of execution queue
        """
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        
        # Execution queue: list of tuples (priority, timestamp, run_id, request)
        self._execution_queue: List[Tuple[int, datetime, str, StrategyExecutionRequest]] = []
        
        # Active executions: run_id -> process info
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        
        # Execution results: run_id -> result info
        self._execution_results: Dict[str, Dict[str, Any]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Background task for processing queue
        self._queue_processor_task: Optional[asyncio.Task] = None
        
        # Progress service
        self._progress_service = get_progress_service()
        
        # Strategy script mapping
        self._strategy_scripts = {
            "bullish_breakout": "bullish_strategy.py",
            "leap_entry": "leap_entry_strategy.py"
        }
        
        # Queue processor will be started lazily
        self._queue_processor_started = False
    
    def _ensure_queue_processor_started(self) -> None:
        """Ensure the background queue processor is started."""
        if not self._queue_processor_started:
            try:
                if self._queue_processor_task is None or self._queue_processor_task.done():
                    self._queue_processor_task = asyncio.create_task(self._process_execution_queue())
                    self._queue_processor_started = True
            except RuntimeError:
                # No event loop available yet, will retry later
                pass
    
    async def queue_execution(self, request: StrategyExecutionRequest) -> str:
        """Queue strategy for execution.
        
        Args:
            request: Strategy execution request
            
        Returns:
            Run ID for the queued execution
            
        Raises:
            ExecutionError: If queue is full or strategy is invalid
        """
        # Ensure queue processor is started
        self._ensure_queue_processor_started()
        
        # Validate strategy code
        if request.strategy_code not in self._strategy_scripts:
            raise ExecutionError(f"Unknown strategy code: {request.strategy_code}")
        
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Determine priority (lower number = higher priority)
        priority_map = {"high": 1, "normal": 2, "low": 3}
        priority = priority_map.get(request.options.priority if request.options else "normal", 2)
        
        async with self._lock:
            # Check queue size
            if len(self._execution_queue) >= self.max_queue_size:
                raise ExecutionError("Execution queue is full")
            
            # Add to queue with priority and timestamp
            queue_item = (priority, datetime.utcnow(), run_id, request)
            self._execution_queue.append(queue_item)
            
            # Sort queue by priority, then by timestamp
            self._execution_queue.sort(key=lambda x: (x[0], x[1]))
            
            # Set initial state
            self._progress_service.set_execution_state(run_id, ExecutionState.QUEUED)
            
            # Emit queued event
            await self._progress_service.emit_progress(run_id, ProgressEvent(
                event_type=ProgressEventType.STARTED,
                timestamp=datetime.utcnow(),
                run_id=run_id,
                stage="queued",
                progress_percent=0.0,
                message=f"Strategy {request.strategy_code} queued for execution",
                metrics={
                    "position_in_queue": self._get_queue_position(run_id),
                    "queue_size": len(self._execution_queue)
                }
            ))
        
        logger.info(f"Queued strategy execution: {request.strategy_code} (run_id: {run_id})")
        return run_id
    
    def _get_queue_position(self, run_id: str) -> int:
        """Get position of run in queue (1-indexed)."""
        for i, (_, _, qrun_id, _) in enumerate(self._execution_queue):
            if qrun_id == run_id:
                return i + 1
        return -1
    
    async def _process_execution_queue(self) -> None:
        """Background task to process execution queue."""
        logger.info("Started execution queue processor")
        
        try:
            while True:
                await asyncio.sleep(1)  # Check queue every second
                
                async with self._lock:
                    # Check if we can start new executions
                    if (len(self._active_executions) < self.max_concurrent and 
                        len(self._execution_queue) > 0):
                        
                        # Get next item from queue
                        priority, timestamp, run_id, request = self._execution_queue.pop(0)
                        
                        # Start execution in background
                        task = asyncio.create_task(self._execute_strategy(run_id, request))
                        
                        # Track active execution
                        self._active_executions[run_id] = {
                            "request": request,
                            "started_at": datetime.utcnow(),
                            "task": task,
                            "process": None
                        }
                        
                        logger.info(f"Started execution for run {run_id}")
        
        except asyncio.CancelledError:
            logger.info("Execution queue processor cancelled")
        except Exception as e:
            logger.error(f"Error in execution queue processor: {e}", exc_info=True)
    
    async def _execute_strategy(self, run_id: str, request: StrategyExecutionRequest) -> None:
        """Execute strategy in subprocess with progress tracking.
        
        Args:
            run_id: Run identifier
            request: Strategy execution request
        """
        script_name = self._strategy_scripts[request.strategy_code]
        process = None
        
        try:
            # Update state to running
            self._progress_service.set_execution_state(run_id, ExecutionState.RUNNING)
            
            # Emit starting event
            await self._progress_service.emit_progress(run_id, ProgressEvent(
                event_type=ProgressEventType.STARTED,
                timestamp=datetime.utcnow(),
                run_id=run_id,
                stage="starting",
                progress_percent=0.0,
                message=f"Starting {request.strategy_code} execution"
            ))
            
            # Build command line arguments
            cmd = self._build_command(script_name, run_id, request)
            
            # Start subprocess with Windows compatibility
            process = None
            use_windows_wrapper = False
            
            # Check if we're on Windows and skip asyncio subprocess (Windows fix)
            logger.info(f"OS detected: {os.name}")
            if os.name == 'nt':
                # Windows - use our custom wrapper
                logger.info(f"Using Windows subprocess wrapper for {run_id}")
                process = await self._create_windows_subprocess(cmd, run_id)
                use_windows_wrapper = True
            else:
                try:
                    # Unix/Linux - try asyncio subprocess
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(Path(__file__).parent.parent.parent),  # Root directory
                        env={**os.environ, "STRATEGY_RUN_ID": run_id}
                    )
                    logger.info(f"Using asyncio subprocess for {run_id}")
                    
                except NotImplementedError:
                    # Fallback to Windows wrapper even on Unix if asyncio subprocess fails
                    logger.info(f"Falling back to Windows subprocess wrapper for {run_id}")
                    process = await self._create_windows_subprocess(cmd, run_id)
                    use_windows_wrapper = True
            
            # Update process reference
            async with self._lock:
                if run_id in self._active_executions:
                    self._active_executions[run_id]["process"] = process
            
            # Monitor process output for progress
            await self._monitor_process_output(run_id, process)
            
            # Wait for completion
            return_code = await process.wait()
            
            # Handle completion
            if return_code == 0:
                await self._handle_execution_success(run_id)
            else:
                await self._handle_execution_error(run_id, f"Process exited with code {return_code}")
        
        except asyncio.CancelledError:
            # Handle cancellation
            if process:
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            
            await self._handle_execution_cancelled(run_id)
            raise
        
        except Exception as e:
            logger.error(f"Error executing strategy {run_id}: {e}", exc_info=True)
            await self._handle_execution_error(run_id, str(e))
        
        finally:
            # Clean up active execution
            async with self._lock:
                if run_id in self._active_executions:
                    del self._active_executions[run_id]
    
    def _build_command(self, script_name: str, run_id: str, request: StrategyExecutionRequest) -> List[str]:
        """Build command line for strategy execution.
        
        Args:
            script_name: Strategy script filename
            run_id: Run identifier  
            request: Execution request
            
        Returns:
            Command line arguments
        """
        cmd = [sys.executable, script_name]
        
        # Add parameters as command line arguments
        for key, value in request.parameters.items():
            if key == "tickers" and isinstance(value, list):
                # Handle ticker list
                cmd.extend(["--tickers"] + value)
            elif isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
            elif value is not None:
                cmd.extend([f"--{key}", str(value)])
        
        # Add run ID for progress tracking
        cmd.extend(["--run-id", run_id])
        
        return cmd
    
    async def _create_windows_subprocess(self, cmd: List[str], run_id: str):
        """Create a Windows-compatible subprocess wrapper.
        
        Args:
            cmd: Command line arguments
            run_id: Run identifier
            
        Returns:
            WindowsSubprocessWrapper instance
        """
        import threading
        import queue as thread_queue
        
        class WindowsSubprocessWrapper:
            """Wrapper to make threading-based subprocess compatible with asyncio."""
            
            def __init__(self, cmd: List[str], run_id: str, cwd: str, env: dict):
                self.cmd = cmd
                self.run_id = run_id
                self.cwd = cwd
                self.env = env
                self.process = None
                self.stdout_queue = thread_queue.Queue()
                self.stderr_queue = thread_queue.Queue()
                self.return_code = None
                self._started = False
                
            async def start(self):
                """Start the subprocess in a thread."""
                if self._started:
                    return
                    
                def run_process():
                    import subprocess
                    try:
                        self.process = subprocess.Popen(
                            self.cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=self.cwd,
                            env=self.env,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        # Read stdout in a separate thread
                        def read_stdout():
                            for line in iter(self.process.stdout.readline, ''):
                                self.stdout_queue.put(line.strip())
                            self.process.stdout.close()
                            
                        # Read stderr in a separate thread
                        def read_stderr():
                            for line in iter(self.process.stderr.readline, ''):
                                self.stderr_queue.put(line.strip())
                            self.process.stderr.close()
                            
                        stdout_thread = threading.Thread(target=read_stdout)
                        stderr_thread = threading.Thread(target=read_stderr)
                        
                        stdout_thread.start()
                        stderr_thread.start()
                        
                        # Wait for process completion
                        self.return_code = self.process.wait()
                        
                        stdout_thread.join()
                        stderr_thread.join()
                        
                    except Exception as e:
                        logger.error(f"Windows subprocess error for {self.run_id}: {e}")
                        self.return_code = -1
                
                # Start process in background thread
                self.thread = threading.Thread(target=run_process)
                self.thread.start()
                self._started = True
            
            async def wait(self):
                """Wait for process completion."""
                if not self._started:
                    await self.start()
                    
                # Wait for thread completion
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.thread.join)
                return self.return_code
            
            def terminate(self):
                """Terminate the process."""
                if self.process:
                    try:
                        self.process.terminate()
                    except:
                        pass
            
            def kill(self):
                """Kill the process."""
                if self.process:
                    try:
                        self.process.kill()
                    except:
                        pass
            
            async def read_stdout_line(self):
                """Read a line from stdout (non-blocking)."""
                try:
                    return self.stdout_queue.get_nowait()
                except thread_queue.Empty:
                    return None
        
        # Create and start the wrapper
        wrapper = WindowsSubprocessWrapper(
            cmd, run_id,
            str(Path(__file__).parent.parent.parent),
            {**os.environ, "STRATEGY_RUN_ID": run_id}
        )
        await wrapper.start()
        return wrapper
    
    async def _monitor_process_output(self, run_id: str, process) -> None:
        """Monitor subprocess output for progress events.
        
        Args:
            run_id: Run identifier
            process: Subprocess instance (asyncio or Windows wrapper)
        """
        try:
            # Check if this is our Windows wrapper or standard asyncio subprocess
            if hasattr(process, 'read_stdout_line'):
                # Windows wrapper - poll for output
                await self._monitor_windows_process_output(run_id, process)
            else:
                # Standard asyncio subprocess
                await self._monitor_asyncio_process_output(run_id, process)
        
        except Exception as e:
            logger.error(f"Error monitoring process output for {run_id}: {e}")
    
    async def _monitor_asyncio_process_output(self, run_id: str, process) -> None:
        """Monitor asyncio subprocess output."""
        try:
            async for line in process.stdout:
                line_str = line.decode('utf-8').strip()
                await self._process_output_line(run_id, line_str)
        except Exception as e:
            logger.error(f"Error monitoring asyncio process output for {run_id}: {e}")
    
    async def _monitor_windows_process_output(self, run_id: str, process) -> None:
        """Monitor Windows wrapper subprocess output."""
        try:
            while True:
                line_str = await process.read_stdout_line()
                if line_str is None:
                    # No output available, sleep briefly
                    await asyncio.sleep(0.1)
                    
                    # Check if process is still running
                    if hasattr(process, 'return_code') and process.return_code is not None:
                        break
                    continue
                
                await self._process_output_line(run_id, line_str)
        except Exception as e:
            logger.error(f"Error monitoring Windows process output for {run_id}: {e}")
    
    async def _process_output_line(self, run_id: str, line_str: str) -> None:
        """Process a single output line for progress events.
        
        Args:
            run_id: Run identifier
            line_str: Output line to process
        """
        # Check for progress events
        if line_str.startswith("PROGRESS:"):
            try:
                progress_json = line_str[9:]  # Remove "PROGRESS:" prefix
                progress_data = json.loads(progress_json)
                
                # Convert to ProgressEvent and emit
                event = ProgressEvent(
                    event_type=ProgressEventType(progress_data.get("type", "progress")),
                    timestamp=datetime.fromisoformat(progress_data["timestamp"].replace('Z', '+00:00')),
                    run_id=run_id,
                    stage=progress_data.get("stage"),
                    progress_percent=progress_data.get("progress"),
                    current_item=progress_data.get("current_item"),
                    total_items=progress_data.get("total_items"),
                    completed_items=progress_data.get("completed_items"),
                    message=progress_data["message"],
                    metrics=progress_data.get("metrics")
                )
                
                await self._progress_service.emit_progress(run_id, event)
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse progress event for {run_id}: {e}")
        
        # Log regular output
        logger.info(f"[{run_id}] {line_str}")
    
    async def _handle_execution_success(self, run_id: str) -> None:
        """Handle successful execution completion."""
        # Calculate execution duration
        execution_info = self._active_executions.get(run_id)
        duration_ms = None
        if execution_info and "started_at" in execution_info:
            duration = datetime.utcnow() - execution_info["started_at"]
            duration_ms = int(duration.total_seconds() * 1000)
        
        # Update database with completion data
        await self._update_database_completion(run_id, "completed", duration_ms)
        
        self._progress_service.set_execution_state(run_id, ExecutionState.COMPLETED)
        
        await self._progress_service.emit_progress(run_id, ProgressEvent(
            event_type=ProgressEventType.COMPLETED,
            timestamp=datetime.utcnow(),
            run_id=run_id,
            stage="completed",
            progress_percent=100.0,
            message="Strategy execution completed successfully"
        ))
        
        logger.info(f"Strategy execution completed successfully: {run_id}")
    
    async def _handle_execution_error(self, run_id: str, error_message: str) -> None:
        """Handle execution error."""
        # Calculate execution duration
        execution_info = self._active_executions.get(run_id)
        duration_ms = None
        if execution_info and "started_at" in execution_info:
            duration = datetime.utcnow() - execution_info["started_at"]
            duration_ms = int(duration.total_seconds() * 1000)
        
        # Update database with error completion data
        await self._update_database_completion(run_id, "error", duration_ms)
        
        self._progress_service.set_execution_state(run_id, ExecutionState.ERROR)
        
        await self._progress_service.emit_progress(run_id, ProgressEvent(
            event_type=ProgressEventType.ERROR,
            timestamp=datetime.utcnow(),
            run_id=run_id,
            stage="error",
            progress_percent=0.0,
            message=f"Strategy execution failed: {error_message}"
        ))
        
        logger.error(f"Strategy execution failed for {run_id}: {error_message}")
    
    async def _handle_execution_cancelled(self, run_id: str) -> None:
        """Handle execution cancellation."""
        # Calculate execution duration
        execution_info = self._active_executions.get(run_id)
        duration_ms = None
        if execution_info and "started_at" in execution_info:
            duration = datetime.utcnow() - execution_info["started_at"]
            duration_ms = int(duration.total_seconds() * 1000)
        
        # Update database with cancellation data
        await self._update_database_completion(run_id, "cancelled", duration_ms)
        
        self._progress_service.set_execution_state(run_id, ExecutionState.CANCELLED)
        
        await self._progress_service.emit_progress(run_id, ProgressEvent(
            event_type=ProgressEventType.CANCELLED,
            timestamp=datetime.utcnow(),
            run_id=run_id,
            stage="cancelled",
            progress_percent=0.0,
            message="Strategy execution was cancelled"
        ))
        
        logger.info(f"Strategy execution cancelled: {run_id}")
    
    async def _update_database_completion(self, run_id: str, exit_status: str, duration_ms: Optional[int]) -> None:
        """Update database with execution completion data.
        
        Args:
            run_id: Run identifier
            exit_status: Execution exit status (completed, error, cancelled)
            duration_ms: Execution duration in milliseconds
        """
        try:
            # Get database connection
            from ..database.connection import get_db_connection
            
            with get_db_connection() as db:
                # Update strategy_run table with completion data
                completed_at = datetime.utcnow().isoformat()
                
                db.execute("""
                    UPDATE strategy_run 
                    SET completed_at = ?, 
                        exit_status = ?, 
                        duration_ms = ?
                    WHERE run_id = ?
                """, (completed_at, exit_status, duration_ms, run_id))
                
                db.commit()
                logger.info(f"Updated database completion for run {run_id}: {exit_status}, {duration_ms}ms")
                
        except Exception as e:
            logger.error(f"Failed to update database completion for {run_id}: {e}")
    
    async def cancel_execution(self, run_id: str) -> bool:
        """Cancel running execution.
        
        Args:
            run_id: Run identifier
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        async with self._lock:
            # Check if execution is active
            if run_id in self._active_executions:
                execution_info = self._active_executions[run_id]
                task = execution_info.get("task")
                
                if task and not task.done():
                    # Cancel the task
                    task.cancel()
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    logger.info(f"Cancelled active execution: {run_id}")
                    return True
            
            # Check if execution is queued
            for i, (_, _, qrun_id, _) in enumerate(self._execution_queue):
                if qrun_id == run_id:
                    # Remove from queue
                    self._execution_queue.pop(i)
                    
                    # Emit cancelled event
                    await self._handle_execution_cancelled(run_id)
                    
                    logger.info(f"Cancelled queued execution: {run_id}")
                    return True
        
        return False
    
    def get_queue_status(self) -> List[QueuedExecution]:
        """Get current execution queue status.
        
        Returns:
            List of queued and running executions
        """
        queue_items = []
        
        # Add running executions
        for run_id, execution_info in self._active_executions.items():
            queue_items.append(QueuedExecution(
                run_id=run_id,
                strategy_code=execution_info["request"].strategy_code,
                status=ExecutionState.RUNNING,
                position=0,  # Running executions have position 0
                started_at=execution_info["started_at"].isoformat()
            ))
        
        # Add queued executions
        for i, (priority, timestamp, run_id, request) in enumerate(self._execution_queue):
            queue_items.append(QueuedExecution(
                run_id=run_id,
                strategy_code=request.strategy_code,
                status=ExecutionState.QUEUED,
                position=i + 1,
                estimated_start=self._estimate_start_time(i).isoformat()
            ))
        
        return queue_items
    
    def _estimate_start_time(self, queue_position: int) -> datetime:
        """Estimate start time for queued execution.
        
        Args:
            queue_position: Position in queue (0-indexed)
            
        Returns:
            Estimated start time
        """
        # Simple estimation: assume 5 minutes per execution
        avg_execution_time = timedelta(minutes=5)
        slots_ahead = max(0, len(self._active_executions) + queue_position - self.max_concurrent)
        
        return datetime.utcnow() + (avg_execution_time * slots_ahead)
    
    def get_execution_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed execution status.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Execution status dictionary or None if not found
        """
        # Check active executions
        if run_id in self._active_executions:
            execution_info = self._active_executions[run_id]
            return {
                "run_id": run_id,
                "status": ExecutionState.RUNNING,
                "started_at": execution_info["started_at"].isoformat(),
                "can_cancel": True,
                "strategy_code": execution_info["request"].strategy_code
            }
        
        # Check queue
        for i, (priority, timestamp, qrun_id, request) in enumerate(self._execution_queue):
            if qrun_id == run_id:
                return {
                    "run_id": run_id,
                    "status": ExecutionState.QUEUED,
                    "position_in_queue": i + 1,
                    "estimated_start": self._estimate_start_time(i).isoformat(),
                    "can_cancel": True,
                    "strategy_code": request.strategy_code
                }
        
        # Check progress service for completed/error states
        state = self._progress_service.get_execution_state(run_id)
        if state:
            return {
                "run_id": run_id,
                "status": state,
                "can_cancel": False
            }
        
        return None
    
    async def cleanup(self) -> None:
        """Cleanup resources and cancel all running tasks."""
        # Cancel queue processor
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active executions
        tasks_to_cancel = []
        async with self._lock:
            for run_id, execution_info in self._active_executions.items():
                task = execution_info.get("task")
                if task and not task.done():
                    tasks_to_cancel.append(task)
        
        for task in tasks_to_cancel:
            task.cancel()
        
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        
        logger.info("Strategy execution manager cleanup completed")


# Global execution manager instance
_execution_manager: Optional[StrategyExecutionManager] = None


def get_execution_manager() -> StrategyExecutionManager:
    """Get or create the global execution manager instance.
    
    Returns:
        Global StrategyExecutionManager instance
    """
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = StrategyExecutionManager()
    return _execution_manager