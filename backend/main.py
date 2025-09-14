"""Main FastAPI application for the automated trading backend.

This module sets up the FastAPI application with CORS middleware,
error handling, and route registration.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.holdings import router as holdings_router
from .api.instruments import router as instruments_router
from .api.health import router as health_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database path - default to existing database location
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "at_data.sqlite")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    logger.info("Starting up automated trading API")
    logger.info(f"Using database at: {DB_PATH}")
    
    # Verify database exists
    if not os.path.exists(DB_PATH):
        logger.warning(f"Database file not found at {DB_PATH}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down automated trading API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Automated Trading API",
        description="RESTful API for automated trading application with holdings visualization",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # CORS middleware configuration - allow all origins for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"], # Expose all headers
    )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url} - Origin: {request.headers.get('origin', 'None')}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        if response.status_code >= 400:
            logger.error(f"Error response {response.status_code} for {request.method} {request.url}")
        return response
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception handler caught: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "detail": str(exc) if app.debug else "Contact support for assistance"
            }
        )
    
    # HTTP exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    # Register routers
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(holdings_router, prefix="/api", tags=["holdings"])
    app.include_router(instruments_router, prefix="/api", tags=["instruments"])
    
    return app


# Create the application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Automated Trading API",
        "version": "1.0.0",
        "description": "RESTful API for automated trading application",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )