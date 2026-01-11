"""
FastAPI application factory and configuration.

This module creates the FastAPI application instance,
configures middleware, exception handlers, and lifespan events.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import run_migrations
from src.api.v1 import router as v1_router
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# OpenAPI tags for documentation grouping
tags_metadata = [
    {
        "name": "v1",
        "description": "Trust State Machine Registration API v1 - Register and activate user accounts",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    Manages application startup and shutdown:
    - Creates database connection pool on startup
    - Runs migrations on startup
    - Closes connection pool on shutdown
    """
    settings = get_settings()

    logger.info("Starting application...")
    logger.info("Connecting to database...")

    # Create connection pool with explicit sizing
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
    )

    # Run migrations
    logger.info("Running database migrations...")
    run_migrations(pool)

    # Store pool in app state for dependency injection
    app.state.pool = pool

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    pool.close()
    logger.info("Database connection pool closed")


app = FastAPI(
    title="beefirst",
    description="Trust State Machine Registration API - Demonstrates the Identity Claim Dilemma solution",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Include v1 API routes
app.include_router(v1_router, prefix="/v1")


@app.get("/health")
async def health_check(request: Request) -> dict[str, str]:
    """
    Health check endpoint with database validation.

    Returns 200 OK if application and database are healthy.
    Raises exception if database connection fails.
    """
    # Validate database connectivity
    pool = request.app.state.pool
    with pool.connection() as conn:
        conn.execute("SELECT 1")

    return {"status": "healthy"}
