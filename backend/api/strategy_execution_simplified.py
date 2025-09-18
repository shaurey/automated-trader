"""
Simplified Strategy Execution API Endpoints

This module provides simplified synchronous endpoints for strategy execution,
replacing the complex SSE streaming approach with simple HTTP calls and polling.
"""

import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, root_validator

from ..services.strategy_execution_service import get_strategy_execution_service, reset_strategy_execution_service
from ..database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategy-execution"])


# Request/Response Models
class StrategyExecutionRequest(BaseModel):
    """Flexible request model for strategy execution.

    Supports multiple alias field names used by different frontend iterations:
      - strategy_name | strategy_code
      - symbols | tickers
    Also allows specifying a universe hint to auto-populate symbols from DB.
    """
    strategy_name: Optional[str] = Field(None, alias="strategyName", description="Strategy identifier (e.g., 'bullish_breakout')")
    strategy_code: Optional[str] = Field(None, alias="strategy_code", description="Alternate field for strategy identifier")
    symbols: Optional[List[str]] = Field(None, description="List of ticker symbols to evaluate")
    tickers: Optional[List[str]] = Field(None, description="Alternate list field for ticker symbols")
    universe: Optional[str] = Field(None, description="Universe source hint (e.g., 'db_instruments')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")
    run_id: Optional[str] = Field(None, description="Optional run ID (generated if not provided)")

    @root_validator(pre=True)
    def _normalize(cls, values):  # noqa: D401
        # Accept top-level camelCase keys if present
        # (Pydantic alias handles strategyName, but keep future-proofing)
        return values

    def resolve_strategy_code(self) -> str:
        code = self.strategy_name or self.strategy_code
        if not code:
            raise HTTPException(status_code=400, detail="Strategy name/code is required")
        return code

    def resolve_symbols(self, db) -> List[str]:
        sym_list = self.symbols or self.tickers
        if sym_list:
            return list(dict.fromkeys([s.upper().strip() for s in sym_list if s and s.strip()]))
        # If no explicit symbols provided, default to DB instruments (active=1) unless a different universe explicitly set and unsupported
        try:
            if self.universe in (None, 'db_instruments'):
                rows = db.execute("SELECT ticker FROM instruments WHERE active=1 ORDER BY ticker").fetchall()
                if rows:
                    return [r[0].upper() for r in rows]
        except Exception as e:
            logger.warning(f"Universe symbol resolution failed: {e}")
        raise HTTPException(status_code=400, detail="No symbols provided and unable to resolve from universe")


class StrategyExecutionResponse(BaseModel):
    """Response model for strategy execution."""
    run_id: str
    status: str  # 'running', 'completed', 'error'
    message: str
    strategy_code: str
    total_tickers: int
    execution_started_at: str


class StrategyProgressResponse(BaseModel):
    """Response model for strategy execution progress."""
    run_id: str
    status: str
    current_ticker: Optional[str]
    progress_percent: float
    processed_count: int
    total_count: int
    qualifying_count: int
    last_update: str
    recent_results: List[Dict[str, Any]]


class StrategyResultsResponse(BaseModel):
    """Response model for complete strategy results."""
    run_id: str
    strategy_code: str
    status: str
    total_evaluated: int
    qualifying_count: int
    execution_time_ms: int
    qualifying_results: List[Dict[str, Any]]
    summary_metrics: Optional[str]


class StrategyListResponse(BaseModel):
    """Response model for available strategies."""
    strategies: List[Dict[str, str]]


class StrategyInfoResponse(BaseModel):
    """Response model for strategy information."""
    code: str
    name: str
    default_parameters: Dict[str, Any]
    parameter_schema: Dict[str, Any]


# Database dependency
def get_db():
    """Get database connection for dependency injection."""
    return get_db_connection()


# Endpoints
@router.post("/execute", response_model=StrategyExecutionResponse)
async def execute_strategy(
    request: StrategyExecutionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Execute a strategy synchronously (in background) with simplified progress tracking.
    
    This endpoint starts strategy execution and returns immediately with a run_id.
    Use the progress endpoint to monitor execution progress.
    """
    try:
        run_id = request.run_id or str(uuid.uuid4())
        strategy_code = request.resolve_strategy_code()
        symbols = request.resolve_symbols(db)

        execution_service = get_strategy_execution_service(db)
        strategy_info = execution_service.get_strategy_info(strategy_code)
        if not strategy_info:
            raise HTTPException(status_code=404, detail=f"Strategy '{strategy_code}' not found")

        execution_started_at = datetime.utcnow().isoformat()

        def run_strategy():
            try:
                execution_service.execute_strategy_sync(
                    strategy_code=strategy_code,
                    tickers=symbols,
                    parameters=request.parameters,
                    run_id=run_id
                )
            except Exception as e:  # Background execution errors logged only
                logger.error(f"Background strategy execution failed: {e}")

        background_tasks.add_task(run_strategy)

        logger.info(f"Started strategy execution: {strategy_code} with {len(symbols)} tickers (run_id: {run_id})")

        return StrategyExecutionResponse(
            run_id=run_id,
            status="running",
            message=f"Strategy '{strategy_code}' execution started",
            strategy_code=strategy_code,
            total_tickers=len(symbols),
            execution_started_at=execution_started_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start strategy execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start strategy execution: {str(e)}")


@router.post("/queue", response_model=StrategyExecutionResponse)
async def queue_strategy(
    request: StrategyExecutionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Alias endpoint for legacy frontend expecting /strategies/queue.

    Mirrors /strategies/execute behavior for backward compatibility.
    """
    return await execute_strategy(request, background_tasks, db)


@router.get("/status/{run_id}", response_model=StrategyProgressResponse)
async def get_strategy_progress(run_id: str, db=Depends(get_db)):
    """
    Get current progress of a strategy execution.
    
    This endpoint provides real-time progress information for monitoring
    strategy execution without complex SSE streams.
    """
    try:
        execution_service = get_strategy_execution_service(db)
        progress = execution_service.get_execution_progress(run_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Strategy execution '{run_id}' not found")
        
        return StrategyProgressResponse(
            run_id=progress['run_id'],
            status=progress['status'],
            current_ticker=progress['current_ticker'],
            progress_percent=progress['progress_percent'],
            processed_count=progress['processed_count'],
            total_count=progress['total_count'],
            qualifying_count=progress['qualifying_count'],
            last_update=progress['last_update'],
            recent_results=progress['recent_results']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/results/{run_id}", response_model=StrategyResultsResponse)
async def get_strategy_results(run_id: str, db=Depends(get_db)):
    """
    Get complete results of a strategy execution.
    
    This endpoint provides complete execution results including all
    qualifying tickers and detailed metrics.
    """
    try:
        execution_service = get_strategy_execution_service(db)
        results = execution_service.get_execution_results(run_id)
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Strategy execution '{run_id}' not found")
        
        return StrategyResultsResponse(
            run_id=results['run_id'],
            strategy_code=results['strategy_code'],
            status=results['status'],
            total_evaluated=results['total_evaluated'],
            qualifying_count=results['qualifying_count'],
            execution_time_ms=results['execution_time_ms'],
            qualifying_results=results['qualifying_results'],
            summary_metrics=results['summary_metrics']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/list", response_model=StrategyListResponse)
async def list_available_strategies(db=Depends(get_db)):
    """
    List all available strategy services.
    
    This endpoint provides information about all registered strategies
    that can be executed through the simplified execution system.
    """
    try:
        # Force reset of global service instance to pick up new registrations
        reset_strategy_execution_service()
        execution_service = get_strategy_execution_service(db)
        strategies = execution_service.list_available_strategies()
        
        return StrategyListResponse(strategies=strategies)
        
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list strategies: {str(e)}")


@router.get("/info/{strategy_code}", response_model=StrategyInfoResponse)
async def get_strategy_info(strategy_code: str, db=Depends(get_db)):
    """
    Get detailed information about a specific strategy.
    
    This endpoint provides strategy metadata including default parameters
    and parameter schema for building dynamic UIs.
    """
    try:
        execution_service = get_strategy_execution_service(db)
        info = execution_service.get_strategy_info(strategy_code)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Strategy '{strategy_code}' not found")
        
        return StrategyInfoResponse(
            code=info['code'],
            name=info['name'],
            default_parameters=info['default_parameters'],
            parameter_schema=info['parameter_schema']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy info for {strategy_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategy info: {str(e)}")


@router.get("/queue")
async def get_execution_queue(db=Depends(get_db)):
    """
    Get the current execution queue status.
    
    This endpoint provides information about queued and running strategy executions.
    """
    try:
        execution_service = get_strategy_execution_service(db)
        
        # Get active executions from the database
        # Query strategy_run table for running/active executions based on completion status
        query = """
        SELECT sr.run_id, sr.strategy_code,
               CASE
                   WHEN sr.completed_at IS NULL THEN 'running'
                   ELSE 'completed'
               END as status,
               sr.started_at as created_at,
               sr.universe_size as total_count,
               COALESCE(progress_counts.processed_count, 0) as processed_count
        FROM strategy_run sr
        LEFT JOIN (
            SELECT run_id, COUNT(*) as processed_count
            FROM strategy_execution_progress
            GROUP BY run_id
        ) progress_counts ON sr.run_id = progress_counts.run_id
        WHERE sr.completed_at IS NULL OR sr.started_at > datetime('now', '-1 hour')
        ORDER BY sr.started_at DESC
        LIMIT 20
        """
        
        rows = db.execute(query).fetchall()
        
        queue_items = []
        for row in rows:
            total_count = row[4] or 0
            processed_count = row[5] or 0
            queue_items.append({
                'run_id': row[0],
                'strategy_code': row[1],
                'status': row[2],
                'created_at': row[3],
                'total_count': total_count,
                'processed_count': processed_count,
                'progress_percent': (processed_count / total_count * 100) if total_count > 0 else 0
            })
        
        return {
            'queue': queue_items,
            'total_queued': len([item for item in queue_items if item['status'] == 'queued']),
            'total_running': len([item for item in queue_items if item['status'] == 'running']),
            'total_items': len(queue_items)
        }
        
    except Exception as e:
        logger.error(f"Failed to get execution queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution queue: {str(e)}")


@router.post("/execute-sync", response_model=StrategyResultsResponse)
async def execute_strategy_sync(
    request: StrategyExecutionRequest,
    db=Depends(get_db)
):
    """
    Execute a strategy synchronously and return complete results.
    
    This endpoint executes the strategy and waits for completion before
    returning results. Use for smaller ticker lists or when immediate
    results are needed.
    
    Note: For large ticker lists, prefer the async execute endpoint
    with progress polling to avoid request timeouts.
    """
    try:
        run_id = request.run_id or str(uuid.uuid4())
        strategy_code = request.resolve_strategy_code()
        symbols = request.resolve_symbols(db)
        execution_service = get_strategy_execution_service(db)
        strategy_info = execution_service.get_strategy_info(strategy_code)
        if not strategy_info:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_code}' not found"
            )
        execution_started_at = datetime.utcnow().isoformat()

        result = execution_service.execute_strategy_sync(
            strategy_code=strategy_code,
            tickers=symbols,
            parameters=request.parameters,
            run_id=run_id
        )
        
        # Return results in the same format as async results endpoint
        qualifying_results = [
            {
                'ticker': ticker_result.ticker,
                'passed': True,
                'score': ticker_result.score,
                'classification': ticker_result.classification,
                'metrics': ticker_result.metrics
            }
            for ticker_result in result.qualifying_stocks
        ]
        
        logger.info(f"Synchronous strategy execution completed: {strategy_code} - {result.qualifying_count}/{result.total_evaluated} passed")
        
        return StrategyResultsResponse(
            run_id=run_id,
            strategy_code=strategy_code,
            status="completed",
            total_evaluated=result.total_evaluated,
            qualifying_count=result.qualifying_count,
            execution_time_ms=result.execution_time_ms,
            qualifying_results=qualifying_results,
            summary_metrics=str(result.summary_metrics)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute strategy synchronously: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute strategy: {str(e)}")