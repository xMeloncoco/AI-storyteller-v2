"""
Database Connection and Session Management
Uses SQLAlchemy with SQLite for local storage
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from .config import settings

# Create the database engine
# check_same_thread=False is required for SQLite to work with FastAPI
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False  # Set to True to see SQL queries in console (for debugging)
)

# Create session factory
# autocommit=False: We manually control transactions
# autoflush=False: We manually control when changes are flushed
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db():
    """
    Dependency injection for FastAPI routes
    Yields a database session and ensures it's closed after use

    Usage in routes:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            # use db here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database
    Creates all tables if they don't exist
    Call this on application startup
    """
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Import all models so SQLAlchemy knows about them
    # This must happen before create_all()
    from . import models  # noqa: F401

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        error_msg = str(e)
        if "index" in error_msg.lower() and "already exists" in error_msg.lower():
            print("\n" + "="*50)
            print("DATABASE SCHEMA CONFLICT DETECTED")
            print("="*50)
            print(f"Error: {error_msg}")
            print("\nThis usually means the database schema has changed.")
            print("To fix this, you have two options:")
            print("\n1. Delete the database and recreate it (recommended for development):")
            print("   - Delete the file: ./data/dreamwalkers.db")
            print("   - Restart the application")
            print("\n2. Use database migrations (for production):")
            print("   - This feature is not yet implemented")
            print("="*50 + "\n")
            raise
        else:
            # Re-raise other exceptions
            raise

    # Log successful initialization
    # Note: Actual logging will be done through our logging system in Phase 1.1
    print("Database initialized successfully")
    print(f"Database location: {settings.database_url}")
