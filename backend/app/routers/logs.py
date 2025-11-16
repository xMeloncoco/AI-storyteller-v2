"""
Logs Router - View System Logs

CRITICAL for development and testing!
This router provides access to all system logs.

The log viewer in the frontend will use these endpoints to show:
- What's happening in the system
- AI decisions
- Database changes
- Errors
- Context building
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from .. import schemas, crud
from ..utils.logger import log_notification

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=List[schemas.LogResponse])
async def get_logs(
    session_id: Optional[int] = Query(None, description="Filter by session ID"),
    log_type: Optional[str] = Query(None, description="Filter by log type (notification, error, edit, ai_decision, context)"),
    log_category: Optional[str] = Query(None, description="Filter by category (database, ai, memory, character, story, system)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Get logs with optional filtering

    This is the main endpoint for the log viewer.
    Can filter by:
    - session_id: See logs for a specific session
    - log_type: See only errors, or only AI decisions, etc.
    - log_category: See database operations, AI operations, etc.

    Logs are returned in chronological order (oldest first within the limit)
    """
    filter_params = schemas.LogFilter(
        session_id=session_id,
        log_type=log_type,
        log_category=log_category,
        limit=limit,
        offset=offset
    )

    logs = crud.get_logs(db, filter_params)

    # Don't log the log retrieval itself to avoid infinite loops
    # Just return the logs

    return logs


@router.get("/recent", response_model=List[schemas.LogResponse])
async def get_recent_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get most recent logs (quick access)

    Useful for seeing what just happened
    """
    logs = crud.get_all_logs(db, limit=limit)
    return logs


@router.get("/errors", response_model=List[schemas.LogResponse])
async def get_error_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get only error logs

    Useful for debugging problems
    """
    filter_params = schemas.LogFilter(
        log_type="error",
        limit=limit,
        offset=0
    )

    logs = crud.get_logs(db, filter_params)
    return logs


@router.get("/ai-decisions", response_model=List[schemas.LogResponse])
async def get_ai_decision_logs(
    session_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get AI decision logs

    See what the AI decided and why
    This is crucial for understanding character behavior
    """
    filter_params = schemas.LogFilter(
        session_id=session_id,
        log_type="ai_decision",
        limit=limit,
        offset=0
    )

    logs = crud.get_logs(db, filter_params)
    return logs


@router.get("/database-edits", response_model=List[schemas.LogResponse])
async def get_database_edit_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get database edit logs

    See what changed in the database
    Useful for tracking relationship updates, story flag changes, etc.
    """
    filter_params = schemas.LogFilter(
        log_type="edit",
        limit=limit,
        offset=0
    )

    logs = crud.get_logs(db, filter_params)
    return logs


@router.get("/session/{session_id}", response_model=List[schemas.LogResponse])
async def get_session_logs(
    session_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all logs for a specific session

    See everything that happened in one session
    """
    filter_params = schemas.LogFilter(
        session_id=session_id,
        limit=limit,
        offset=0
    )

    logs = crud.get_logs(db, filter_params)
    return logs


@router.get("/stats")
async def get_log_stats(db: Session = Depends(get_db)):
    """
    Get statistics about logs

    Shows counts of different log types
    Useful for seeing overall system health
    """
    # Count logs by type
    from sqlalchemy import func
    from ..models import Log

    stats = {}

    # Total logs
    total = db.query(func.count(Log.id)).scalar()
    stats["total_logs"] = total

    # Count by type
    type_counts = db.query(
        Log.log_type,
        func.count(Log.id)
    ).group_by(Log.log_type).all()

    stats["by_type"] = {t: c for t, c in type_counts}

    # Count by category
    category_counts = db.query(
        Log.log_category,
        func.count(Log.id)
    ).group_by(Log.log_category).all()

    stats["by_category"] = {c: cnt for c, cnt in category_counts if c}

    return stats
