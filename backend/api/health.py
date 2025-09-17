"""Health check API endpoints."""

import os
from datetime import datetime
from fastapi import APIRouter
import sqlite3

from ..models.schemas import HealthResponse
from ..database.connection import get_db_connection

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify API and database connectivity."""
    
    # Test database connectivity with a simple connection (no dependency injection)
    database_connected = True
    try:
        # Use direct connection without schema initialization to avoid hangs
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        db.close()
    except Exception:
        database_connected = False
    
    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        timestamp=datetime.utcnow(),
        database_connected=database_connected,
        version="1.0.0"
    )