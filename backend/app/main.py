"""RoadMind AI FastAPI Application Entrypoint.

Provides:
- Application factory with lifespan context manager.
- Safe, non-destructive database table initialization.
- Health check endpoint at /api/health.
- Versioned API mounted at /api/v1.
- CORS middleware and structured error responses.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

# Ensure local packages and workspace root are in sys.path
_workspace_root = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace_root / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.api.v1.router import api_v1_router
from backend.app.config import settings
from backend.app.database import SessionLocal, init_db
from backend.app.schemas.common import ErrorDetail, ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown.

    Ensures storage directories exist and tables are initialized safely
    without dropping or destructively resetting existing data.
    """
    settings.ensure_directories()
    init_db()  # Non-destructive: Base.metadata.create_all()
    yield


app = FastAPI(
    title="RoadMind AI API",
    version=settings.version,
    description=(
        "Evidence-Aware Traffic Decision Support System — "
        "NEXATHON 2026 Hackathon at SDIT Mangaluru (Traffic Intelligence Track)"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"], summary="System health and connectivity status")
def health_check() -> Dict[str, Any]:
    """Check backend operational health and database connectivity."""
    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": settings.version,
        "app_name": settings.app_name,
        "database": db_status,
        "environment": settings.environment,
        "graph_version": settings.graph_version,
    }


# Exception handlers for structured, consistent error reporting
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status="error",
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
                details=getattr(exc, "headers", None),
            ),
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            status="error",
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request payload or parameters failed validation.",
                details=exc.errors(),
            ),
        ).model_dump(mode="json"),
    )


# Mount versioned API routes under /api/v1
app.include_router(api_v1_router, prefix=settings.api_prefix)
