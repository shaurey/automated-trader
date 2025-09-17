"""Strategy execution API endpoints for real-time progress tracking.

This module provides API endpoints for:
- Starting strategy executions with real-time progress tracking
- Server-Sent Events (SSE) for live progress streaming
- Execution status monitoring and control
- Execution queue management
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..models.schemas import (
    StrategyExecutionRequest, StrategyExecutionResponse, ExecutionStatus,
    ExecutionCancelResponse, ExecutionQueueResponse, ExecutionState,
    ErrorResponse
)
from ..services.execution_manager import get_execution_manager, ExecutionError
from ..services.progress_service import get_progress_service


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/strategies/execute", response_model=StrategyExecutionResponse)
async def execute_strategy(
    request: StrategyExecutionRequest,
    background_tasks: BackgroundTasks,
    execution_manager=Depends(get_execution_manager)
):
    """Start strategy execution with real-time progress tracking.
    
    This endpoint queues a strategy for execution and returns immediately
    with a run ID and SSE endpoint for real-time progress monitoring.
    
    Args:
        request: Strategy execution request with parameters
        background_tasks: FastAPI background tasks
        execution_manager: Strategy execution manager dependency
        
    Returns:
        Execution response with run ID and SSE endpoint
        
    Raises:
        HTTPException: If validation fails or queue is full
    """
    try:
        logger.info(f"Received execution request for strategy: {request.strategy_code}")
        
        # Queue the execution
        run_id = await execution_manager.queue_execution(request)
        
        # Get queue status for position estimate
        queue_status = execution_manager.get_queue_status()
        position_in_queue = None
        estimated_start_time = None
        
        # Find this run in the queue
        for item in queue_status:
            if item.run_id == run_id:
                if item.status == ExecutionState.QUEUED:
                    position_in_queue = item.position
                    estimated_start_time = item.estimated_start
                break
        
        # Build response
        response = StrategyExecutionResponse(
            run_id=run_id,
            status=ExecutionState.QUEUED,
            position_in_queue=position_in_queue,
            estimated_start_time=estimated_start_time,
            sse_endpoint=f"/api/strategies/sse/{run_id}"
        )
        
        logger.info(f"Queued strategy execution: {run_id}")
        return response
        
    except ExecutionError as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to queue execution: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error queuing execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/strategies/sse/{run_id}")
async def strategy_progress_stream(
    run_id: str,
    progress_service=Depends(get_progress_service)
):
    """Server-Sent Events endpoint for real-time progress streaming.
    
    This endpoint provides a continuous stream of progress events for a
    specific strategy execution run. The stream remains open until the
    execution completes or the client disconnects.
    
    Args:
        run_id: Strategy run identifier
        progress_service: Progress service dependency
        
    Returns:
        Server-Sent Events stream
    """
    logger.info(f"SSE connection requested for run: {run_id}")
    
    async def event_generator():
        """Generate SSE events from progress service."""
        try:
            async for event_data in progress_service.subscribe_to_progress(run_id):
                yield {
                    "event": "progress",
                    "data": event_data
                }
        except Exception as e:
            logger.error(f"Error in SSE stream for {run_id}: {e}")
            yield {
                "event": "error",
                "data": f'{{"error": "Stream error: {str(e)}"}}'
            }
    
    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/strategies/runs/{run_id}/status", response_model=ExecutionStatus)
async def get_execution_status(
    run_id: str,
    execution_manager=Depends(get_execution_manager),
    progress_service=Depends(get_progress_service)
):
    """Get current execution status for polling-based monitoring.
    
    This endpoint provides a polling-based alternative to SSE for
    clients that cannot use Server-Sent Events.
    
    Args:
        run_id: Strategy run identifier
        execution_manager: Execution manager dependency
        progress_service: Progress service dependency
        
    Returns:
        Current execution status
        
    Raises:
        HTTPException: If run ID is not found
    """
    try:
        # Get execution status from manager
        status_info = execution_manager.get_execution_status(run_id)
        
        if not status_info:
            # Check if it's a completed run in progress service
            state = progress_service.get_execution_state(run_id)
            if state:
                return ExecutionStatus(
                    run_id=run_id,
                    status=state,
                    can_cancel=False
                )
            
            raise HTTPException(
                status_code=404,
                detail=f"Execution run not found: {run_id}"
            )
        
        # Build comprehensive status response
        response = ExecutionStatus(
            run_id=run_id,
            status=status_info["status"],
            current_stage=status_info.get("current_stage"),
            started_at=status_info.get("started_at"),
            estimated_completion=status_info.get("estimated_completion"),
            can_cancel=status_info.get("can_cancel", False),
            metrics=status_info.get("metrics")
        )
        
        # Add progress percentage if available
        if status_info["status"] == ExecutionState.RUNNING:
            # Could get latest progress from progress service
            # For now, just indicate running without specific percentage
            response.progress_percent = None
        elif status_info["status"] == ExecutionState.COMPLETED:
            response.progress_percent = 100.0
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status for {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution status: {str(e)}"
        )


@router.post("/strategies/runs/{run_id}/cancel", response_model=ExecutionCancelResponse)
async def cancel_execution(
    run_id: str,
    execution_manager=Depends(get_execution_manager)
):
    """Cancel a running or queued strategy execution.
    
    This endpoint attempts to cancel an execution. Running executions
    will be terminated gracefully, while queued executions will be
    removed from the queue.
    
    Args:
        run_id: Strategy run identifier
        execution_manager: Execution manager dependency
        
    Returns:
        Cancellation result
        
    Raises:
        HTTPException: If run ID is not found or cannot be cancelled
    """
    try:
        logger.info(f"Cancellation requested for run: {run_id}")
        
        # Attempt to cancel the execution
        cancelled = await execution_manager.cancel_execution(run_id)
        
        if cancelled:
            logger.info(f"Successfully cancelled execution: {run_id}")
            return ExecutionCancelResponse(
                cancelled=True,
                message=f"Execution {run_id} cancelled successfully"
            )
        else:
            logger.warning(f"Failed to cancel execution: {run_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Unable to cancel execution {run_id} (may be completed or not found)"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.get("/strategies/queue", response_model=ExecutionQueueResponse)
async def get_execution_queue(
    execution_manager=Depends(get_execution_manager)
):
    """Get current execution queue status.
    
    This endpoint returns the current state of the execution queue,
    including running and queued executions with their positions
    and estimated start times.
    
    Args:
        execution_manager: Execution manager dependency
        
    Returns:
        Current execution queue status
    """
    try:
        # Get queue status from execution manager
        queue_items = execution_manager.get_queue_status()
        
        # Count queued items (exclude running executions)
        queued_count = sum(1 for item in queue_items if item.status == ExecutionState.QUEUED)
        
        response = ExecutionQueueResponse(
            queue=queue_items,
            total_queued=queued_count,
            max_concurrent=execution_manager.max_concurrent
        )
        
        logger.info(f"Queue status requested: {len(queue_items)} total items, {queued_count} queued")
        return response
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.get("/strategies/execution/stats")
async def get_execution_stats(
    execution_manager=Depends(get_execution_manager),
    progress_service=Depends(get_progress_service)
):
    """Get execution system statistics.
    
    This endpoint provides statistics about the execution system,
    including queue status, active connections, and system health.
    
    Args:
        execution_manager: Execution manager dependency
        progress_service: Progress service dependency
        
    Returns:
        System statistics
    """
    try:
        # Get statistics from both services
        progress_stats = progress_service.get_stats()
        queue_items = execution_manager.get_queue_status()
        
        running_count = sum(1 for item in queue_items if item.status == ExecutionState.RUNNING)
        queued_count = sum(1 for item in queue_items if item.status == ExecutionState.QUEUED)
        
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "execution_queue": {
                "running_executions": running_count,
                "queued_executions": queued_count,
                "max_concurrent": execution_manager.max_concurrent,
                "max_queue_size": execution_manager.max_queue_size
            },
            "progress_service": progress_stats,
            "system_health": {
                "queue_utilization": (running_count + queued_count) / (execution_manager.max_concurrent + execution_manager.max_queue_size),
                "connection_load": progress_stats.get("total_connections", 0)
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting execution stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution statistics: {str(e)}"
        )