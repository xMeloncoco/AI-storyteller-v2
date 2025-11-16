"""
Centralized Logging System for Dreamwalkers

CRITICAL: Almost everything should be logged!
This replaces console.log and provides structured logging to the database.

Log Types:
- notification: Normal system events (just stating something happened)
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
"""
import json
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from ..models import Log


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
        print(f"[{timestamp}] [{log_type.upper()}] [{category or 'general'}] {message}")

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

    def context(
        self,
        message: str,
        category: Optional[str] = None,
        details: Optional[Any] = None
    ) -> Log:
        """
        Log context/memory related events

        Example:
            logger.context("Retrieved relevant memories", "memory", {"count": 5})
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
