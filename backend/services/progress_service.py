"""Progress service for managing SSE connections and event broadcasting.

This module provides a ProgressService class that manages Server-Sent Events (SSE)
connections for real-time progress tracking during strategy execution.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, AsyncGenerator
from dataclasses import dataclass

from ..models.schemas import ProgressEvent, ProgressEventType, ExecutionState


logger = logging.getLogger(__name__)


@dataclass
class ActiveConnection:
    """Represents an active SSE connection."""
    run_id: str
    queue: asyncio.Queue
    connected_at: datetime
    last_ping: datetime


class ProgressService:
    """Manages progress tracking and SSE streaming for strategy executions.
    
    This service handles:
    - SSE connection management
    - Progress event broadcasting
    - Connection cleanup and monitoring
    - Event persistence for late connections
    """
    
    def __init__(self, max_events_per_run: int = 1000):
        """Initialize progress service.
        
        Args:
            max_events_per_run: Maximum events to keep in memory per run
        """
        self.max_events_per_run = max_events_per_run
        
        # Active SSE connections: run_id -> set of connection queues
        self._connections: Dict[str, Set[asyncio.Queue]] = {}
        
        # Event history for late connections: run_id -> list of events
        self._event_history: Dict[str, list] = {}
        
        # Execution states: run_id -> ExecutionState
        self._execution_states: Dict[str, ExecutionState] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def emit_progress(self, run_id: str, event: ProgressEvent) -> None:
        """Emit progress event to all subscribers for a run.
        
        Args:
            run_id: Run identifier
            event: Progress event to emit
        """
        async with self._lock:
            # Store event in history
            if run_id not in self._event_history:
                self._event_history[run_id] = []
            
            # Convert event to SSE format
            event_data = {
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "run_id": event.run_id,
                "stage": event.stage,
                "progress_percent": event.progress_percent,
                "current_item": event.current_item,
                "total_items": event.total_items,
                "completed_items": event.completed_items,
                "message": event.message,
                "metrics": event.metrics
            }
            
            self._event_history[run_id].append(event_data)
            
            # Limit event history size
            if len(self._event_history[run_id]) > self.max_events_per_run:
                self._event_history[run_id] = self._event_history[run_id][-self.max_events_per_run:]
            
            # Update execution state based on event type
            if event.event_type == ProgressEventType.STARTED:
                self._execution_states[run_id] = ExecutionState.RUNNING
            elif event.event_type == ProgressEventType.COMPLETED:
                self._execution_states[run_id] = ExecutionState.COMPLETED
            elif event.event_type == ProgressEventType.ERROR:
                self._execution_states[run_id] = ExecutionState.ERROR
            elif event.event_type == ProgressEventType.CANCELLED:
                self._execution_states[run_id] = ExecutionState.CANCELLED
            
            # Broadcast to active connections
            if run_id in self._connections:
                event_json = json.dumps(event_data, separators=(',', ':'))
                disconnected_queues = set()
                
                for queue in self._connections[run_id]:
                    try:
                        queue.put_nowait(event_json)
                    except asyncio.QueueFull:
                        # Queue is full, likely a slow consumer
                        logger.warning(f"SSE queue full for run {run_id}, dropping connection")
                        disconnected_queues.add(queue)
                    except Exception as e:
                        logger.error(f"Error broadcasting to SSE queue for run {run_id}: {e}")
                        disconnected_queues.add(queue)
                
                # Clean up disconnected queues
                for queue in disconnected_queues:
                    self._connections[run_id].discard(queue)
                
                # Remove run from connections if no active connections
                if not self._connections[run_id]:
                    del self._connections[run_id]
    
    async def subscribe_to_progress(self, run_id: str) -> AsyncGenerator[str, None]:
        """SSE stream generator for progress events.
        
        Args:
            run_id: Run identifier to subscribe to
            
        Yields:
            SSE-formatted event strings
        """
        # Create queue for this connection
        queue = asyncio.Queue(maxsize=100)
        
        async with self._lock:
            # Add to active connections
            if run_id not in self._connections:
                self._connections[run_id] = set()
            self._connections[run_id].add(queue)
            
            # Send historical events for late connections
            if run_id in self._event_history:
                for event_data in self._event_history[run_id]:
                    try:
                        event_json = json.dumps(event_data, separators=(',', ':'))
                        queue.put_nowait(event_json)
                    except asyncio.QueueFull:
                        logger.warning(f"Queue full during history replay for run {run_id}")
                        break
        
        try:
            # Send initial connection event
            connection_event = {
                "event_type": "connected",
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": run_id,
                "message": f"Connected to progress stream for run {run_id}"
            }
            yield json.dumps(connection_event, separators=(',', ':'))
            
            # Stream events from queue
            while True:
                try:
                    # Wait for event with timeout for periodic ping
                    event_json = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event_json
                except asyncio.TimeoutError:
                    # Send periodic ping to keep connection alive
                    ping_event = {
                        "event_type": "ping",
                        "timestamp": datetime.utcnow().isoformat(),
                        "run_id": run_id,
                        "message": "Connection keepalive"
                    }
                    yield json.dumps(ping_event, separators=(',', ':'))
                except asyncio.CancelledError:
                    # Client disconnected
                    break
                except Exception as e:
                    logger.error(f"Error in SSE stream for run {run_id}: {e}")
                    break
        
        finally:
            # Clean up connection
            async with self._lock:
                if run_id in self._connections:
                    self._connections[run_id].discard(queue)
                    if not self._connections[run_id]:
                        del self._connections[run_id]
    
    def get_execution_state(self, run_id: str) -> Optional[ExecutionState]:
        """Get current execution state for a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Current execution state or None if not found
        """
        return self._execution_states.get(run_id)
    
    def set_execution_state(self, run_id: str, state: ExecutionState) -> None:
        """Set execution state for a run.
        
        Args:
            run_id: Run identifier
            state: New execution state
        """
        self._execution_states[run_id] = state
    
    def get_active_connections_count(self, run_id: str) -> int:
        """Get number of active SSE connections for a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Number of active connections
        """
        return len(self._connections.get(run_id, set()))
    
    def get_total_active_connections(self) -> int:
        """Get total number of active SSE connections across all runs.
        
        Returns:
            Total number of active connections
        """
        return sum(len(queues) for queues in self._connections.values())
    
    async def cleanup_run(self, run_id: str, keep_history: bool = True) -> None:
        """Clean up resources for a completed run.
        
        Args:
            run_id: Run identifier
            keep_history: Whether to keep event history
        """
        async with self._lock:
            # Close all active connections for this run
            if run_id in self._connections:
                for queue in self._connections[run_id]:
                    try:
                        # Send final disconnect event
                        disconnect_event = {
                            "event_type": "disconnected",
                            "timestamp": datetime.utcnow().isoformat(),
                            "run_id": run_id,
                            "message": "Run completed, closing connection"
                        }
                        queue.put_nowait(json.dumps(disconnect_event, separators=(',', ':')))
                    except:
                        pass  # Ignore errors during cleanup
                
                del self._connections[run_id]
            
            # Optionally clear event history
            if not keep_history and run_id in self._event_history:
                del self._event_history[run_id]
    
    async def cleanup_old_runs(self, max_age_hours: int = 24) -> int:
        """Clean up old run data to prevent memory leaks.
        
        Args:
            max_age_hours: Maximum age in hours for keeping run data
            
        Returns:
            Number of runs cleaned up
        """
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        cleaned_count = 0
        
        async with self._lock:
            runs_to_clean = []
            
            # Find old runs based on last event timestamp
            for run_id, events in self._event_history.items():
                if events:
                    last_event = events[-1]
                    last_timestamp = datetime.fromisoformat(last_event["timestamp"].replace('Z', '+00:00'))
                    if last_timestamp.timestamp() < cutoff_time:
                        runs_to_clean.append(run_id)
            
            # Clean up old runs
            for run_id in runs_to_clean:
                if run_id not in self._connections:  # Don't clean if there are active connections
                    if run_id in self._event_history:
                        del self._event_history[run_id]
                    if run_id in self._execution_states:
                        del self._execution_states[run_id]
                    cleaned_count += 1
        
        return cleaned_count
    
    def get_stats(self) -> Dict[str, int]:
        """Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "active_runs": len(self._connections),
            "total_connections": self.get_total_active_connections(),
            "runs_with_history": len(self._event_history),
            "tracked_states": len(self._execution_states)
        }


# Global progress service instance
_progress_service: Optional[ProgressService] = None


def get_progress_service() -> ProgressService:
    """Get or create the global progress service instance.
    
    Returns:
        Global ProgressService instance
    """
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressService()
    return _progress_service