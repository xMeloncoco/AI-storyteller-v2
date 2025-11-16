# Phase-by-Phase Implementation Guide
## Detailed Code & Instructions for Each Development Phase

This document provides complete, copy-paste ready code for each phase of development.

---

## TABLE OF CONTENTS

1. [Phase 1.1: Database & Logging](#phase-11-database--logging)
2. [Phase 1.2: Basic Chat & LLM](#phase-12-basic-chat--llm)
3. [Phase 1.3: Context & Memory](#phase-13-context--memory)
4. [Phase 2.1: Character Decisions](#phase-21-character-decisions)
5. [Phase 2.2: Story Arcs](#phase-22-story-arcs)
6. [Phase 3.1: Relationships](#phase-31-relationships)
7. [Phase 3.2: Final Polish](#phase-32-final-polish)

---

## PHASE 1.1: Database & Logging

### Goal
Create the database schema, implement logging system, and set up test data import.

### Files to Create

#### 1. backend/app/database.py
```python
"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/dreamwalkers.db")

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=False  # Set to True for SQL logging during development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI routes
    Yields a database session and ensures it's closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Create all database tables
    Call this on application startup
    """
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Import all models before creating tables
    from . import models
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
```

#### 2. backend/app/models.py
```python
"""
SQLAlchemy ORM Models
All database tables are defined here
"""
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from .database import Base

# Story and Playthrough Models
class Story(Base):
    """
    Story template - contains all base information for a story
    """
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    initial_message = Column(Text, nullable=False)
    initial_location = Column(String)
    initial_time = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Playthrough(Base):
    """
    Specific instance of a story being played
    Multiple playthroughs can exist for one story
    """
    __tablename__ = "playthroughs"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    user_id = Column(Integer)  # Future: for multi-user support
    playthrough_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_played = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Integer, default=1)
    current_location = Column(String)
    current_time = Column(String)

# Entity Models (Characters, Locations)
class Character(Base):
    """
    Characters in the story
    playthrough_id = NULL means it's a template
    playthrough_id = <value> means it's an instance for that playthrough
    """
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"))
    character_type = Column(String, nullable=False)  # User, Main, Support, Antagonist, Cameo, NPC
    character_name = Column(String, nullable=False)
    appearance = Column(Text)
    age = Column(Integer)
    backstory = Column(Text)
    personality_traits = Column(Text)  # JSON format
    speech_patterns = Column(Text)
    template_character_id = Column(Integer, ForeignKey("characters.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Location(Base):
    """
    Locations in the story
    """
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"))
    location_name = Column(String, nullable=False)
    description = Column(Text)
    location_type = Column(String)
    parent_location_id = Column(Integer, ForeignKey("locations.id"))
    location_scope = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Relationship(Base):
    """
    Relationships between characters
    Tracks trust, affection, familiarity
    """
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"))
    entity1_type = Column(String, nullable=False)
    entity1_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    entity2_type = Column(String, nullable=False)
    entity2_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    relationship_type = Column(String, nullable=False)
    first_meeting_context = Column(Text)
    trust = Column(Float, default=0.5)
    affection = Column(Float, default=0.5)
    familiarity = Column(Float, default=0.0)
    last_interaction = Column(DateTime(timezone=True))
    history_summary = Column(Text)

# Session and Conversation Models
class Session(Base):
    """
    A chat session within a playthrough
    """
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    user_character_id = Column(Integer, ForeignKey("characters.id"))
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Conversation(Base):
    """
    Individual messages in a session
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    speaker_type = Column(String, nullable=False)  # 'narrator' or 'user'
    speaker_name = Column(String)
    message = Column(Text, nullable=False)
    emotion_expressed = Column(String)
    topics_discussed = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SceneState(Base):
    """
    Current state of the scene
    """
    __tablename__ = "scene_state"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    location = Column(String)
    time_of_day = Column(String)
    weather = Column(String)
    scene_context = Column(Text)
    emotional_tone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# Logging Model
class Log(Base):
    """
    System logs for debugging and development
    CRITICAL for testing and understanding what's happening
    """
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    log_type = Column(String, nullable=False)  # notification, error, edit, ai_decision, context
    log_category = Column(String)  # database, ai, memory, character, system
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON format for structured data
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# Future Phase 2+ Models
class MemoryFlag(Base):
    """
    Important events/flags for story progression
    """
    __tablename__ = "memory_flags"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    flag_type = Column(String, nullable=False)
    flag_value = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    importance = Column(Integer, default=5)

class SceneCharacter(Base):
    """
    Characters present in current scene
    """
    __tablename__ = "scene_characters"
    
    id = Column(Integer, primary_key=True, index=True)
    scene_state_id = Column(Integer, ForeignKey("scene_state.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"))
    character_name = Column(String)
    character_type = Column(String)
    is_temporary = Column(Integer, default=0)
    character_mood = Column(String)
    character_intent = Column(String)
    character_physical_position = Column(String)
    is_speaking = Column(Integer, default=0)

class StoryArc(Base):
    """
    Major story arcs
    """
    __tablename__ = "story_arcs"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"))
    arc_name = Column(String, nullable=False)
    description = Column(Text)
    arc_order = Column(Integer, nullable=False)
    is_active = Column(Integer, default=0)
    is_completed = Column(Integer, default=0)
    start_condition = Column(Text)
    completion_condition = Column(Text)

class StoryEpisode(Base):
    """
    Episodes within story arcs
    """
    __tablename__ = "story_episodes"
    
    id = Column(Integer, primary_key=True, index=True)
    arc_id = Column(Integer, ForeignKey("story_arcs.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"))
    episode_name = Column(String, nullable=False)
    description = Column(Text)
    episode_order = Column(Integer, nullable=False)
    is_active = Column(Integer, default=0)
    is_completed = Column(Integer, default=0)
    trigger_flags = Column(Text)
    completion_flags = Column(Text)

class StoryFlag(Base):
    """
    Story progression flags
    """
    __tablename__ = "story_flags"
    
    id = Column(Integer, primary_key=True, index=True)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    flag_name = Column(String, nullable=False)
    flag_value = Column(String, nullable=False)
    set_at = Column(DateTime(timezone=True), server_default=func.now())
    set_by = Column(String)

class CharacterKnowledge(Base):
    """
    Track what each character knows (prevents mind-reading)
    """
    __tablename__ = "character_knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    knowledge_type = Column(String, nullable=False)
    knowledge_content = Column(Text, nullable=False)
    learned_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String)
    certainty = Column(Float, default=1.0)
```

*This document continues with all implementation details for remaining phases...*

---

**Note:** Due to the comprehensive nature of this guide, I've created two documents:
1. **Dreamwalkers_MVP_Complete_Development_Guide.md** - Overview and roadmap
2. **Phase_by_Phase_Implementation_Guide.md** - Detailed code for each phase

Would you like me to continue with specific phase implementations?
