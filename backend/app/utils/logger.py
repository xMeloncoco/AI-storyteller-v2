"""
Centralized Logging System for Dreamwalkers

CRITICAL: Almost everything should be logged!
This replaces console.log and provides structured logging to the database.

Log Types:
- notification: Normal system events (just stating something happened)
- warning: Something unusual or potentially problematic (but not blocking)
- error: Something went wrong
- edit: Database was modified
- ai_decision: AI made a decision
- context: Context/memory related events

Log Categories:
- database: Database operations
- ai: AI/LLM related operations
- memory: Memory/ChromaDB operations
- character: Character decision making
- story: Story progression
- system: General system events

The logs are stored in the database and can be viewed in the frontend log viewer.

Pipeline-stage tagging:
The `pipeline_stage("STAGE_NAME")` context manager (or `@pipeline_stage_method`
decorator) auto-tags every log line emitted inside it with the active stage.
The stage gets written into `details["stage"]` so the tester panel can filter
by it, and the printed console line is prefixed with `[STAGE:NAME]`. This
lets readers see immediately which pipeline stage a log came from without
the caller having to remember.
"""
import contextvars
import functools
import inspect
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import Log


# Active pipeline stage for the current task. contextvars (not threading.local)
# because the pipeline is async and contextvars propagate through await chains.
_current_stage: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "pipeline_stage", default=None
)


@contextmanager
def pipeline_stage(stage_name: str):
    """Tag every AppLogger call inside this block with `stage_name`.

    Used by ChatPipeline methods so log readers can answer "which stage did
    this come from?" without grepping the source.
    """
    token = _current_stage.set(stage_name)
    try:
        yield stage_name
    finally:
        _current_stage.reset(token)


def pipeline_stage_method(stage_name: str):
    """Decorator form of `pipeline_stage` for ChatPipeline methods.

    Handles both sync and async methods. Wrap the whole stage body so every
    log inside (including ones the called collaborators emit) is tagged.
    """
    def decorate(fn):
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def awrapper(*args, **kwargs):
                with pipeline_stage(stage_name):
                    return await fn(*args, **kwargs)
            return awrapper

        @functools.wraps(fn)
        def swrapper(*args, **kwargs):
            with pipeline_stage(stage_name):
                return fn(*args, **kwargs)
        return swrapper
    return decorate


def get_current_stage() -> Optional[str]:
    """Inspector for tests / debugging."""
    return _current_stage.get()


class AppLogger:
    """
    Application logger that writes logs to the database
    Provides methods for different types of log entries
    """

    def __init__(self, db: Session, session_id: Optional[int] = None):
        """
        Initialize logger with database session

        Args:
            db: SQLAlchemy database session
            session_id: Optional session ID for contextual logging
        """
        self.db = db
        self.session_id = session_id

    def _create_log(
        self,
        log_type: str,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Internal method to create a log entry

        Args:
            log_type: Type of log (notification, error, edit, ai_decision, context)
            message: Human-readable log message
            category: Category for filtering (database, ai, memory, etc.)
            details: Additional structured data (will be converted to JSON)

        Returns:
            The created Log object
        """
        stage = _current_stage.get()

        # Mix the active stage into the details payload so the tester panel
        # can filter by it. We never overwrite an explicit caller-provided
        # `stage` key — the explicit value wins.
        if stage is not None:
            if details is None:
                details = {"stage": stage}
            elif isinstance(details, dict) and "stage" not in details:
                details = {**details, "stage": stage}

        # Convert details to JSON string if it's a dict/list
        details_str = None
        if details is not None:
            if isinstance(details, (dict, list)):
                details_str = json.dumps(details, default=str, indent=2)
            else:
                details_str = str(details)

        log_entry = Log(
            session_id=self.session_id,
            log_type=log_type,
            log_category=category,
            message=message,
            details=details_str
        )

        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)

        # Also print to console for development
        timestamp = datetime.now().strftime("%H:%M:%S")
        stage_prefix = f" [STAGE:{stage}]" if stage else ""
        print(
            f"[{timestamp}] [{log_type.upper()}] [{category or 'general'}]{stage_prefix} {message}"
        )

        return log_entry

    def notification(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log a notification (normal system event)

        Example:
            logger.notification("User sent message", "system", {"message_length": 50})
        """
        return self._create_log("notification", message, category, details)

    def error(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log an error

        Example:
            logger.error("Failed to connect to AI", "ai", {"error": str(e)})
        """
        return self._create_log("error", message, category, details)

    def warning(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log a warning (something unusual but not blocking)

        Example:
            logger.warning("Validation failed but continuing", "validation", {"issues": issues})
        """
        return self._create_log("warning", message, category, details)

    def edit(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log a database edit

        Example:
            logger.edit("Updated relationship trust", "database", {"old": 0.5, "new": 0.7})
        """
        return self._create_log("edit", message, category, details)

    def ai_decision(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log an AI decision

        Example:
            logger.ai_decision("Character decided to refuse request", "character", {"reason": "out of character"})
        """
        return self._create_log("ai_decision", message, category, details)

    def prompt(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log prompt-build events (PROMPT_BUILD stage / what we sent to the LLM).

        Vocabulary (R8): "prompt" = the LLM input. For in-world background
        events (scene state, what a character knows, where they are), use
        the existing log types/categories like "character" or "story".

        Example:
            logger.prompt("Built prompt bundle", "prompt", {"history_messages": 12})
        """
        return self._create_log("prompt", message, category, details)

    def context(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        DEPRECATED (R8): use `prompt()` for prompt-build events.

        Kept for one commit so existing call sites keep working. The log
        type remains "context" here — no DB migration — so old logs and
        new ones written through this alias stay queryable together.
        """
        return self._create_log("context", message, category, details)


# =============================================================================
# CONVENIENCE FUNCTIONS
# These can be used without creating a logger instance
# =============================================================================


def log_notification(
    db: Session,
    message: str,
    category: Optional[str] = None,
    details: Optional[Any] = None,
    session_id: Optional[int] = None
) -> Log:
    """
    Log a notification without creating a logger instance

    Args:
        db: SQLAlchemy database session
        message: Log message
        category: Log category
        details: Additional details
        session_id: Optional session ID

    Returns:
        Created log entry
    """
    logger = AppLogger(db, session_id)
    return logger.notification(message, category, details)


def log_error(
    db: Session,
    message: str,
    category: Optional[str] = None,
    details: Optional[Any] = None,
    session_id: Optional[int] = None
) -> Log:
    """Log an error without creating a logger instance"""
    logger = AppLogger(db, session_id)
    return logger.error(message, category, details)


def log_warning(
    db: Session,
    message: str,
    category: Optional[str] = None,
    details: Optional[Any] = None,
    session_id: Optional[int] = None
) -> Log:
    """Log a warning without creating a logger instance"""
    logger = AppLogger(db, session_id)
    return logger.warning(message, category, details)


def log_edit(
    db: Session,
    message: str,
    category: Optional[str] = None,
    details: Optional[Any] = None,
    session_id: Optional[int] = None
) -> Log:
    """Log a database edit without creating a logger instance"""
    logger = AppLogger(db, session_id)
    return logger.edit(message, category, details)


def log_ai_decision(
    db: Session,
    message: str,
    category: Optional[str] = None,
    details: Optional[Any] = None,
    session_id: Optional[int] = None
) -> Log:
    """Log an AI decision without creating a logger instance"""
    logger = AppLogger(db, session_id)
    return logger.ai_decision(message, category, details)


def log_context(
    db: Session,
    message: str,
    category: Optional[str] = None,
    details: Optional[Any] = None,
    session_id: Optional[int] = None
) -> Log:
    """Log a context/memory event without creating a logger instance"""
    logger = AppLogger(db, session_id)
    return logger.context(message, category, details)
