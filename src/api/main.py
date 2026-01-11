"""
FastAPI application factory and configuration.

This module creates the FastAPI application instance,
configures middleware, exception handlers, and lifespan events.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import run_migrations
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


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
    logger.info(f"Connecting to database: {settings.database_url.split('@')[-1]}")

    # Create connection pool
    pool = ConnectionPool(conninfo=settings.database_url)

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
    description="Trust State Machine Registration API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
