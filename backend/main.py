"""
FastAPI Main Application

Entry point for the Quantitative Trading Platform backend API.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import logging
from typing import Callable

from backend.config import settings
from backend.logger_config import setup_logging

# Setup logging
setup_logging(log_level="INFO")

logger = logging.getLogger(__name__)


# Create FastAPI application instance
app = FastAPI(
    title="Quantitative Trading Platform",
    description="Personal backtesting and trading platform",
    version="1.0.0"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development server (default port)
        "http://localhost:3001",  # Next.js development server (alternate port)
        "http://localhost:3002",  # Next.js development server (alternate port)
        "http://localhost:8000",  # FastAPI server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """
    Log all incoming requests with method, path, status code, and duration.

    Args:
        request: The incoming request
        call_next: The next middleware/route handler

    Returns:
        The response from the next handler
    """
    start_time = time.time()

    # Process the request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log the request details
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - {duration:.3f}s"
    )

    return response


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.

    Returns:
        dict: Health status and version information
    """
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


# Exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse: Error response with 500 status code
    """
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors.

    Args:
        request: The request that failed validation
        exc: The validation error

    Returns:
        JSONResponse: Error response with 400 status code
    """
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc}"
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Validation error", "details": exc.errors()}
    )


# Router registration
from backend.api.strategies import router as strategies_router
from backend.api.data import router as data_router
from backend.api.backtest import router as backtest_router
from backend.api.live import router as live_router
from backend.database import Database

app.include_router(strategies_router, prefix="/api/v1")
app.include_router(data_router, prefix="/api/v1")
# Don't add prefix - router already has /api/v1/backtest prefix
app.include_router(backtest_router)
app.include_router(live_router)

# Initialize database
db = Database(settings.database_url)

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize resources on application startup.

    - Initialize database tables
    - Setup any required services
    """
    logger.info("Starting up FastAPI application")
    logger.info(f"Database URL: {settings.database_url}")
    logger.info(f"Binance API URL: {settings.binance_base_url}")
    logger.info(f"HTTP Proxy configured: '{settings.http_proxy}'")
    logger.info(f"HTTPS Proxy configured: '{settings.https_proxy}'")
    logger.info(f"Settings loaded from .env: {settings.dict()}")

    # Initialize database tables
    try:
        db.create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        raise

    logger.info("FastAPI application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup resources on application shutdown.

    - Close database connections
    - Cleanup any resources
    """
    logger.info("Shutting down FastAPI application")

    # SQLAlchemy handles connection cleanup automatically
    # No explicit cleanup needed here

    logger.info("FastAPI application shutdown complete")


if __name__ == "__main__":
    import os
    import uvicorn

    # reload=True 会让 uvicorn 持续 stat 整个工作目录的所有文件（含 node_modules），
    # 长时间运行会导致后端进程 CPU 持续 60%+。
    # 仅在开发时设 DEV_RELOAD=1 启用，并把监视范围限定在 backend/。
    dev_reload = os.getenv("DEV_RELOAD") == "1"

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=dev_reload,
        reload_dirs=["backend"] if dev_reload else None,
        reload_excludes=["*.bak.*", "*.db", "logs/*", "data/*"] if dev_reload else None,
        log_level="info"
    )
