"""Strategy API endpoints for strategy runs and results management."""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3

from ..models.schemas import (
    StrategyRunsResponse, StrategyRunDetail, StrategyResultsResponse, 
    StrategyLatestResponse, StrategyRunSummary, StrategyResultDetail,
    StrategyMetrics, ErrorResponse
)
from ..database.connection import get_database_connection, get_db_manager

router = APIRouter()


def _parse_metrics_json(metrics_json: str) -> StrategyMetrics:
    """Parse metrics JSON string into StrategyMetrics model."""
    try:
        metrics_dict = json.loads(metrics_json) if metrics_json else {}
        return StrategyMetrics(**metrics_dict)
    except (json.JSONDecodeError, TypeError, ValueError):
        return StrategyMetrics()


def _parse_reasons(reasons_str: str) -> List[str]:
    """Parse semicolon-separated reasons string into list."""
    if not reasons_str:
        return []
    return [r.strip() for r in reasons_str.split(';') if r.strip()]


def _calculate_pass_rate(passed_count: int, total_count: int) -> Optional[float]:
    """Calculate pass rate percentage."""
    if total_count == 0:
        return None
    return round((passed_count / total_count) * 100, 2)


@router.get("/strategies/runs", response_model=StrategyRunsResponse)
async def get_strategy_runs(
    strategy_code: Optional[str] = Query(None, description="Filter by strategy code"),
    status: Optional[str] = Query(None, description="Filter by exit status"),
    date_from: Optional[str] = Query(None, description="Filter runs from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter runs to date (ISO format)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    order_by: str = Query("started_at", description="Sort field"),
    order_desc: bool = Query(True, description="Sort in descending order")
):
    """Get list of strategy runs with pagination and filtering.
    
    Returns paginated list of strategy runs with summary statistics.
    Supports filtering by strategy code, status, and date range.
    """
    try:
        db_manager = get_db_manager()
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        if strategy_code:
            where_conditions.append("sr.strategy_code = ?")
            params.append(strategy_code)
            
        if status:
            where_conditions.append("sr.exit_status = ?")
            params.append(status)
            
        if date_from:
            where_conditions.append("sr.started_at >= ?")
            params.append(date_from)
            
        if date_to:
            where_conditions.append("sr.started_at <= ?")
            params.append(date_to)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Validate order_by field
        valid_order_fields = ["started_at", "completed_at", "passed_count", "strategy_code"]
        if order_by not in valid_order_fields:
            order_by = "started_at"
        
        order_direction = "DESC" if order_desc else "ASC"
        
        # Count total matching runs
        count_query = f"""
        SELECT COUNT(DISTINCT sr.run_id)
        FROM strategy_run sr
        {where_clause}
        """
        
        total_count = db_manager.execute_one(count_query, params)[0] if db_manager.execute_one(count_query, params) else 0
        
        # Get runs with aggregated stats
        runs_query = f"""
        SELECT 
            sr.run_id,
            sr.strategy_code,
            sr.started_at,
            sr.completed_at,
            sr.universe_size,
            sr.exit_status,
            sr.duration_ms,
            COUNT(res.ticker) as total_results,
            SUM(CASE WHEN res.passed = 1 THEN 1 ELSE 0 END) as passed_count,
            AVG(res.score) as avg_score
        FROM strategy_run sr
        LEFT JOIN strategy_result res ON sr.run_id = res.run_id
        {where_clause}
        GROUP BY sr.run_id, sr.strategy_code, sr.started_at, sr.completed_at, 
                 sr.universe_size, sr.exit_status, sr.duration_ms
        ORDER BY sr.{order_by} {order_direction}
        LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        rows = db_manager.execute_query(runs_query, params)
        
        # Build response objects
        runs = []
        for row in rows:
            total_results = row[7] or 0
            passed_count = row[8] or 0
            
            run_summary = StrategyRunSummary(
                run_id=row[0],
                strategy_code=row[1],
                started_at=row[2],
                completed_at=row[3],
                universe_size=row[4],
                passed_count=passed_count,
                pass_rate=_calculate_pass_rate(passed_count, total_results),
                avg_score=round(float(row[9]), 2) if row[9] else None,
                duration_ms=row[6],
                exit_status=row[5]
            )
            runs.append(run_summary)
        
        # Calculate strategy stats
        strategy_stats = None
        if runs:
            unique_strategies = len(set(run.strategy_code for run in runs))
            total_runs = len(runs)
            pass_rates = [run.pass_rate for run in runs if run.pass_rate is not None]
            avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0
            last_run = max(run.started_at for run in runs) if runs else None
            
            strategy_stats = {
                "unique_strategies": unique_strategies,
                "total_runs": total_runs,
                "avg_pass_rate": round(avg_pass_rate, 2),
                "last_run": last_run
            }
        
        return StrategyRunsResponse(
            runs=runs,
            total_count=total_count,
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            strategy_stats=strategy_stats
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve strategy runs: {str(e)}"
        )


@router.get("/strategies/runs/{run_id}", response_model=StrategyRunDetail)
async def get_strategy_run_detail(run_id: str):
    """Get detailed information for a specific strategy run.
    
    Returns comprehensive run information including performance stats,
    score distribution, and preview of top results.
    """
    try:
        db_manager = get_db_manager()
        
        # Get run details
        run_query = """
        SELECT run_id, strategy_code, version, params_hash, params_json,
               started_at, completed_at, universe_source, universe_size,
               min_score, exit_status, duration_ms
        FROM strategy_run 
        WHERE run_id = ?
        """
        
        run_row = db_manager.execute_one(run_query, [run_id])
        if not run_row:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy run not found: {run_id}"
            )
        
        # Get aggregated performance stats
        stats_query = """
        SELECT 
            COUNT(*) as total_results,
            SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_count,
            AVG(score) as avg_score,
            MAX(score) as max_score,
            MIN(score) as min_score_actual
        FROM strategy_result
        WHERE run_id = ?
        """
        
        stats_row = db_manager.execute_one(stats_query, [run_id])
        total_results = stats_row[0] if stats_row else 0
        passed_count = stats_row[1] if stats_row else 0
        avg_score = stats_row[2] if stats_row else None
        max_score = stats_row[3] if stats_row else None
        min_score_actual = stats_row[4] if stats_row else None
        
        # Get score distribution
        score_ranges = {}
        if total_results > 0:
            range_query = """
            SELECT 
                CASE 
                    WHEN score >= 0 AND score <= 20 THEN '0-20'
                    WHEN score > 20 AND score <= 40 THEN '21-40'
                    WHEN score > 40 AND score <= 60 THEN '41-60'
                    WHEN score > 60 AND score <= 80 THEN '61-80'
                    WHEN score > 80 AND score <= 100 THEN '81-100'
                    ELSE 'unknown'
                END as score_range,
                COUNT(*) as count
            FROM strategy_result
            WHERE run_id = ? AND score IS NOT NULL
            GROUP BY score_range
            """
            
            range_rows = db_manager.execute_query(range_query, [run_id])
            score_ranges = {row[0]: row[1] for row in range_rows}
        
        # Get top results preview (top 5 by score)
        top_results_query = """
        SELECT res.run_id, res.strategy_code, res.ticker, res.passed, res.score,
               res.classification, res.reasons, res.metrics_json, res.created_at,
               inst.sector, inst.industry, inst.instrument_type
        FROM strategy_result res
        LEFT JOIN instruments inst ON res.ticker = inst.ticker
        WHERE res.run_id = ? AND res.passed = 1
        ORDER BY res.score DESC
        LIMIT 5
        """
        
        top_rows = db_manager.execute_query(top_results_query, [run_id])
        top_results = []
        
        for row in top_rows:
            metrics = _parse_metrics_json(row[7])
            reasons = _parse_reasons(row[6])
            
            result = StrategyResultDetail(
                run_id=row[0],
                strategy_code=row[1],
                ticker=row[2],
                passed=bool(row[3]),
                score=row[4],
                classification=row[5],
                reasons=reasons,
                metrics=metrics,
                created_at=row[8],
                sector=row[9],
                industry=row[10],
                instrument_type=row[11] or "stock"
            )
            top_results.append(result)
        
        # Build detailed run response
        run_detail = StrategyRunDetail(
            run_id=run_row[0],
            strategy_code=run_row[1],
            version=run_row[2],
            params_hash=run_row[3],
            params_json=run_row[4],
            started_at=run_row[5],
            completed_at=run_row[6],
            universe_source=run_row[7],
            universe_size=run_row[8],
            min_score=run_row[9],
            exit_status=run_row[10],
            duration_ms=run_row[11],
            passed_count=passed_count,
            total_results=total_results,
            pass_rate=_calculate_pass_rate(passed_count, total_results),
            avg_score=round(float(avg_score), 2) if avg_score else None,
            max_score=round(float(max_score), 2) if max_score else None,
            min_score_actual=round(float(min_score_actual), 2) if min_score_actual else None,
            score_ranges=score_ranges,
            top_results=top_results
        )
        
        return run_detail
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve strategy run details: {str(e)}"
        )


@router.get("/strategies/runs/{run_id}/results", response_model=StrategyResultsResponse)
async def get_strategy_run_results(
    run_id: str,
    passed: Optional[bool] = Query(None, description="Filter by pass/fail status"),
    min_score: Optional[float] = Query(None, description="Minimum score threshold"),
    max_score: Optional[float] = Query(None, description="Maximum score threshold"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of results (omit for all results)"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    order_by: str = Query("score", description="Sort field"),
    order_desc: bool = Query(True, description="Sort in descending order")
):
    """Get paginated results for a specific strategy run.
    
    Returns detailed results with metrics for individual tickers,
    supporting filtering and pagination.
    """
    try:
        db_manager = get_db_manager()
        
        # Verify run exists and get strategy_code
        run_check_query = "SELECT strategy_code FROM strategy_run WHERE run_id = ?"
        run_check = db_manager.execute_one(run_check_query, [run_id])
        if not run_check:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy run not found: {run_id}"
            )
        
        strategy_code = run_check[0]
        
        # Build WHERE clause for filtering
        where_conditions = ["res.run_id = ?"]
        params = [run_id]
        
        if passed is not None:
            where_conditions.append("res.passed = ?")
            params.append(1 if passed else 0)
            
        if min_score is not None:
            where_conditions.append("res.score >= ?")
            params.append(min_score)
            
        if max_score is not None:
            where_conditions.append("res.score <= ?")
            params.append(max_score)
            
        if classification:
            where_conditions.append("res.classification = ?")
            params.append(classification)
            
        if ticker:
            where_conditions.append("res.ticker = ?")
            params.append(ticker.upper())
            
        if sector:
            where_conditions.append("inst.sector = ?")
            params.append(sector)
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Validate order_by field
        valid_order_fields = ["score", "ticker", "created_at", "classification"]
        if order_by not in valid_order_fields:
            order_by = "score"
        
        order_direction = "DESC" if order_desc else "ASC"
        
        # Count total and passed/failed results
        count_query = f"""
        SELECT 
            COUNT(*) as total_count,
            SUM(CASE WHEN res.passed = 1 THEN 1 ELSE 0 END) as passed_count
        FROM strategy_result res
        LEFT JOIN instruments inst ON res.ticker = inst.ticker
        {where_clause}
        """
        
        count_row = db_manager.execute_one(count_query, params)
        total_count = count_row[0] if count_row else 0
        passed_count = count_row[1] if count_row else 0
        failed_count = total_count - passed_count
        
        # Get paginated results
        results_query = f"""
        SELECT res.run_id, res.strategy_code, res.ticker, res.passed, res.score,
               res.classification, res.reasons, res.metrics_json, res.created_at,
               inst.sector, inst.industry, inst.instrument_type
        FROM strategy_result res
        LEFT JOIN instruments inst ON res.ticker = inst.ticker
        {where_clause}
        ORDER BY res.{order_by} {order_direction}
        """
        
        # Only add LIMIT/OFFSET if limit is specified
        if limit is not None:
            results_query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset > 0:
            results_query += " OFFSET ?"
            params.append(offset)
        rows = db_manager.execute_query(results_query, params)
        
        # Build result objects
        results = []
        for row in rows:
            metrics = _parse_metrics_json(row[7])
            reasons = _parse_reasons(row[6])
            
            result = StrategyResultDetail(
                run_id=row[0],
                strategy_code=row[1],
                ticker=row[2],
                passed=bool(row[3]),
                score=row[4],
                classification=row[5],
                reasons=reasons,
                metrics=metrics,
                created_at=row[8],
                sector=row[9],
                industry=row[10],
                instrument_type=row[11] or "stock"
            )
            results.append(result)
        
        # Calculate summary statistics
        # Calculate summary statistics with safe division
        results_with_scores = [r for r in results if r.score is not None]
        summary = {
            "avg_score": round(sum(r.score for r in results_with_scores) / len(results_with_scores), 2) if results_with_scores else 0,
            "max_score": max(r.score for r in results_with_scores) if results_with_scores else 0,
            "min_score": min(r.score for r in results_with_scores) if results_with_scores else 0,
            "pass_rate": _calculate_pass_rate(passed_count, total_count)
        }
        
        return StrategyResultsResponse(
            run_id=run_id,
            strategy_code=strategy_code,
            results=results,
            total_count=total_count,
            passed_count=passed_count,
            failed_count=failed_count,
            page=1 if limit is None else (offset // limit) + 1,
            page_size=limit or total_count,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve strategy results: {str(e)}"
        )


@router.get("/strategies/latest", response_model=StrategyLatestResponse)
async def get_latest_strategy_runs(
    strategy_codes: Optional[str] = Query(None, description="Comma-separated list of strategy codes"),
    limit: int = Query(10, ge=1, le=50, description="Number of latest runs per strategy")
):
    """Get latest runs by strategy type.
    
    Returns the most recent runs for each strategy type,
    optionally filtered by specific strategy codes.
    """
    try:
        db_manager = get_db_manager()
        
        # Get all available strategy codes if none specified
        if strategy_codes:
            codes_list = [code.strip() for code in strategy_codes.split(',') if code.strip()]
            codes_placeholder = ','.join(['?' for _ in codes_list])
            codes_filter = f"AND sr.strategy_code IN ({codes_placeholder})"
            codes_params = codes_list
        else:
            codes_filter = ""
            codes_params = []
        
        # Get latest runs for each strategy
        latest_query = f"""
        WITH RankedRuns AS (
            SELECT
                sr.run_id,
                sr.strategy_code,
                sr.version,
                sr.params_hash,
                sr.params_json,
                sr.started_at,
                sr.completed_at,
                sr.universe_source,
                sr.universe_size,
                sr.min_score,
                sr.exit_status,
                sr.duration_ms,
                COUNT(res.ticker) as total_results,
                SUM(CASE WHEN res.passed = 1 THEN 1 ELSE 0 END) as passed_count,
                AVG(res.score) as avg_score,
                MAX(res.score) as max_score,
                MIN(res.score) as min_score_actual,
                ROW_NUMBER() OVER (PARTITION BY sr.strategy_code ORDER BY sr.started_at DESC) as rn
            FROM strategy_run sr
            LEFT JOIN strategy_result res ON sr.run_id = res.run_id
            WHERE sr.completed_at IS NOT NULL {codes_filter}
            GROUP BY sr.run_id, sr.strategy_code, sr.version, sr.params_hash,
                     sr.params_json, sr.started_at, sr.completed_at, sr.universe_source,
                     sr.universe_size, sr.min_score, sr.exit_status, sr.duration_ms
        )
        SELECT run_id, strategy_code, version, params_hash, params_json,
               started_at, completed_at, universe_source, universe_size,
               min_score, exit_status, duration_ms, total_results, passed_count,
               avg_score, max_score, min_score_actual
        FROM RankedRuns
        WHERE rn <= ?
        ORDER BY strategy_code, started_at DESC
        """
        
        params = codes_params + [limit]
        rows = db_manager.execute_query(latest_query, params)
        
        # Build detailed run objects
        latest_runs = []
        strategies = set()
        
        for row in rows:
            strategies.add(row[1])  # strategy_code
            total_results = row[12] or 0
            passed_count = row[13] or 0
            
            run_detail = StrategyRunDetail(
                run_id=row[0],
                strategy_code=row[1],
                version=row[2],
                params_hash=row[3],
                params_json=row[4],
                started_at=row[5],
                completed_at=row[6],
                universe_source=row[7],
                universe_size=row[8],
                min_score=row[9],
                exit_status=row[10],
                duration_ms=row[11],
                passed_count=passed_count,
                total_results=total_results,
                pass_rate=_calculate_pass_rate(passed_count, total_results),
                avg_score=round(float(row[14]), 2) if row[14] else None,
                max_score=round(float(row[15]), 2) if row[15] else None,
                min_score_actual=round(float(row[16]), 2) if row[16] else None,
                score_ranges={},  # Not included in latest view for performance
                top_results=[]  # Not included in latest view for performance
            )
            latest_runs.append(run_detail)
        
        return StrategyLatestResponse(
            latest_runs=latest_runs,
            strategies=sorted(list(strategies)),
            total_strategies=len(strategies)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve latest strategy runs: {str(e)}"
        )