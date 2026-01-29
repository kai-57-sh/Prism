"""
FastAPI Main Application
"""

from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import structlog
import os
from pathlib import Path

from src.config.settings import settings


# Configure logging
logger = structlog.get_logger(__name__)


# Create FastAPI app
app = FastAPI(
    title="Prism - Medical Text-to-Video Agent",
    description="Medical emotion video generation with per-shot generation and ffmpeg post-processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _resolve_static_root() -> str:
    static_root = Path(settings.static_root)
    try:
        static_root.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        fallback = Path("data").resolve()
        fallback.mkdir(parents=True, exist_ok=True)
        logger.warning(
            "static_root_fallback",
            configured=str(settings.static_root),
            fallback=str(fallback),
        )
        settings.static_root = str(fallback)
        settings.static_video_dir = os.path.join(settings.static_root, settings.static_video_subdir)
        settings.static_audio_dir = os.path.join(settings.static_root, settings.static_audio_subdir)
        settings.static_metadata_dir = os.path.join(settings.static_root, settings.static_metadata_subdir)
        return str(fallback)
    return str(static_root)


# Static files (videos/audio/metadata)
static_root = _resolve_static_root()
app.mount(settings.static_url_prefix, StaticFiles(directory=static_root), name="static")


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        JSON response with service health status
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "prism-backend",
    }


# Exception handlers
def _serialize_validation_errors(errors):
    cleaned = []
    for err in errors:
        err_copy = err.copy()
        ctx = err_copy.get("ctx")
        if ctx:
            err_copy["ctx"] = {
                key: (str(value) if isinstance(value, Exception) else value)
                for key, value in ctx.items()
            }
        cleaned.append(err_copy)
    return cleaned


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors (400)
    """
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": _serialize_validation_errors(exc.errors()),
            }
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    Handle value errors (400)
    """
    logger.warning(
        "value_error",
        path=request.url.path,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "INVALID_VALUE",
                "message": str(exc),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle generic exceptions (500)
    """
    logger.error(
        "unexpected_error",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize application on startup
    """
    logger.info("application_starting", log_level=settings.log_level)

    # Initialize database and load templates
    from src.models import SessionLocal
    from src.services.storage import init_db as init_storage

    db = SessionLocal()
    try:
        init_storage(db)
    finally:
        db.close()

    logger.info("application_started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    logger.info("application_shutting_down")


# Import routers
from src.api.routes import generation, jobs, finalize, revise

# Register routers
app.include_router(generation.router, prefix="/v1/t2v", tags=["generation"])
app.include_router(jobs.router, prefix="/v1/t2v", tags=["jobs"])
app.include_router(finalize.router, prefix="/v1/t2v", tags=["finalize"])
app.include_router(revise.router, prefix="/v1/t2v", tags=["revise"])


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint

    Returns:
        JSON response with API information
    """
    return {
        "name": "Prism Medical Text-to-Video Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
