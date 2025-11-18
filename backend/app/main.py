"""
Dreamwalkers API - Main Application Entry Point

This is the FastAPI application that serves as the backend for
the Dreamwalkers AI Storytelling application.

Features:
- Story and playthrough management
- AI-powered chat with character consistency
- Relationship tracking
- Story progression management
- Comprehensive logging system
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

from .database import init_db, get_db, SessionLocal
from .config import settings
from .routers import chat, stories, logs, admin
from .utils.logger import log_notification, log_error
from . import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events

    This runs on startup and shutdown
    """
    # Startup
    print("=" * 50)
    print("Starting Dreamwalkers API")
    print(f"Version: {__version__}")
    print(f"AI Provider: {settings.ai_provider}")
    print(f"Database: {settings.database_url}")
    print("=" * 50)

    # Initialize database
    init_db()

    # Log startup
    db = SessionLocal()
    try:
        log_notification(
            db,
            f"Dreamwalkers API started (v{__version__})",
            "system",
            {
                "ai_provider": settings.ai_provider,
                "log_level": settings.log_level
            }
        )
    finally:
        db.close()

    print("API ready to accept connections")
    print("=" * 50)

    yield

    # Shutdown
    print("Shutting down Dreamwalkers API")
    db = SessionLocal()
    try:
        log_notification(db, "Dreamwalkers API shutting down", "system")
    finally:
        db.close()


# Create the FastAPI application
app = FastAPI(
    title="Dreamwalkers API",
    description="AI-powered interactive storytelling backend",
    version=__version__,
    lifespan=lifespan
)

# Configure CORS for frontend communication
# Note: In production, restrict this to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle uncaught exceptions

    Logs the error and returns a user-friendly message
    """
    db = SessionLocal()
    try:
        log_error(
            db,
            f"Unhandled exception: {str(exc)}",
            "system",
            {
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                "error_message": str(exc)
            }
        )
    finally:
        db.close()

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Check the logs for details."
        }
    )


# Include routers
app.include_router(chat.router)
app.include_router(stories.router)
app.include_router(logs.router)
app.include_router(admin.router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================


@app.get("/")
async def root():
    """
    Root endpoint - basic API information
    """
    return {
        "name": "Dreamwalkers API",
        "version": __version__,
        "status": "running",
        "description": "AI-powered interactive storytelling backend"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Verifies:
    - API is running
    - Database is accessible
    - AI provider is configured

    Returns comprehensive health status
    """
    from .database import get_db

    health_status = {
        "status": "healthy",
        "version": __version__,
        "database": "unknown",
        "ai_provider": settings.ai_provider,
        "ai_configured": False
    }

    # Check database
    try:
        db = SessionLocal()
        # Simple query to verify connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
        db.close()
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"

    # Check AI configuration
    if settings.ai_provider == "openrouter":
        health_status["ai_configured"] = bool(settings.openrouter_api_key)
    elif settings.ai_provider == "nebius":
        health_status["ai_configured"] = bool(settings.nebius_api_key)
    else:
        health_status["ai_configured"] = True  # Local doesn't need key

    if not health_status["ai_configured"]:
        health_status["status"] = "degraded"
        health_status["ai_warning"] = "API key not configured for AI provider"

    return health_status


@app.get("/info")
async def api_info():
    """
    Get detailed API information

    Shows configuration and capabilities
    """
    return {
        "name": "Dreamwalkers API",
        "version": __version__,
        "ai_provider": settings.ai_provider,
        "small_model": settings.small_model,
        "large_model": settings.large_model,
        "max_context_messages": settings.max_context_messages,
        "memory_save_interval": settings.memory_save_interval,
        "features": {
            "chat": "Active - Send messages and receive AI story responses",
            "character_decisions": "Active - Characters make autonomous decisions",
            "relationship_tracking": "Active - Relationships evolve over time",
            "story_progression": "Active - Story arcs and flags are tracked",
            "logging": "Active - Comprehensive system logging",
            "generate_more": "Active - Continue story without user input"
        },
        "endpoints": {
            "chat": "/chat/send - Main interaction endpoint",
            "stories": "/stories - Story and playthrough management",
            "logs": "/logs - System log viewing"
        }
    }


@app.get("/stats")
async def get_stats():
    """
    Get basic statistics about the system

    Shows counts of stories, playthroughs, etc.
    """
    from sqlalchemy import func
    from .models import Story, Playthrough, Session, Conversation, Log

    db = SessionLocal()
    try:
        stats = {
            "stories": db.query(func.count(Story.id)).scalar(),
            "playthroughs": db.query(func.count(Playthrough.id)).scalar(),
            "sessions": db.query(func.count(Session.id)).scalar(),
            "conversations": db.query(func.count(Conversation.id)).scalar(),
            "logs": db.query(func.count(Log.id)).scalar()
        }

        log_notification(db, "Retrieved system stats", "system", stats)

        return stats
    finally:
        db.close()


# =============================================================================
# DEVELOPMENT/TESTING ENDPOINTS
# =============================================================================


@app.post("/reset-database")
async def reset_database():
    """
    Reset the database - DEVELOPMENT ONLY

    WARNING: This deletes all data!
    Should be disabled in production
    """
    from .database import Base, engine

    # Drop all tables
    Base.metadata.drop_all(bind=engine)

    # Recreate all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        log_notification(db, "Database reset - all data cleared", "database")
    finally:
        db.close()

    return {"status": "Database reset successfully", "warning": "All data has been deleted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
