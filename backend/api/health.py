"""Health check API endpoints."""

import os
from datetime import datetime
from fastapi import APIRouter, Depends
import sqlite3

from ..models.schemas import HealthResponse
from ..database.connection import get_database_connection

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: sqlite3.Connection = Depends(get_database_connection)):
    """Health check endpoint to verify API and database connectivity."""
    
    # Test database connectivity
    database_connected = True
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    except Exception:
        database_connected = False
    
    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        timestamp=datetime.utcnow(),
        database_connected=database_connected,
        version="1.0.0"
    )