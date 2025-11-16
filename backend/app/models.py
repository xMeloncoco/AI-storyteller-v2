"""
SQLAlchemy ORM Models for Dreamwalkers
All database tables are defined here

Design Pattern:
- playthrough_id = NULL means template data (belongs to story)
- playthrough_id != NULL means instance data (belongs to specific playthrough)

Character Types (by priority):
- User: The player character description
- Main: Most important story characters (e.g., main love interest)
- Support: Recurring characters
- Antagonist: Opposition characters
- Cameo: Mentioned but rarely seen characters
- NPC: Generic templates (e.g., unnamed bartender)
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    ForeignKey,
    DateTime,
    Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


# =============================================================================
# CORE TABLES
# =============================================================================


class Story(Base):
    """
    Story template - the base definition of a story
    Contains all characters, locations, and story structure
    Users pay once per story, can have unlimited playthroughs
    """
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # The first message shown when starting the story
    initial_message = Column(Text, nullable=False)

    # Starting scene information
    initial_location = Column(String(255))
    initial_time = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships to other tables (for easy querying)
    # Note: These are SQLAlchemy relationships, not story relationships
    playthroughs = relationship("Playthrough", back_populates="story")
    characters = relationship("Character", back_populates="story")
    locations = relationship("Location", back_populates="story")
    story_arcs = relationship("StoryArc", back_populates="story")


class Playthrough(Base):
    """
    Instance of a story being played
    Each playthrough is independent - characters and relationships evolve separately
    """
    __tablename__ = "playthroughs"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)

    # For future multi-user support
    user_id = Column(Integer, nullable=True)

    # User-friendly name for this playthrough
    playthrough_name = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_played = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Is this playthrough currently active?
    is_active = Column(Integer, default=1)

    # Current state of the playthrough
    current_location = Column(String(255))
    current_time = Column(String(100))

    # Relationships
    story = relationship("Story", back_populates="playthroughs")
    sessions = relationship("Session", back_populates="playthrough")

    # Index for faster queries
    __table_args__ = (
        Index("idx_playthrough_story", "story_id"),
        Index("idx_playthrough_active", "is_active"),
    )


# =============================================================================
# ENTITY TABLES (Templates + Instances)
# =============================================================================


class Character(Base):
    """
    Character definition
    If playthrough_id is NULL: This is a template character for the story
    If playthrough_id is NOT NULL: This is an instance for a specific playthrough

    Character types (highest to lowest priority):
    - User: Player character
    - Main: Primary story characters
    - Support: Secondary recurring characters
    - Antagonist: Opposition characters
    - Cameo: Briefly mentioned characters
    - NPC: Generic NPCs that can be reused
    """
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)

    # NULL = template, valued = instance
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=True)

    # Character type determines priority and amount of detail
    character_type = Column(String(50), nullable=False)  # User, Main, Support, Antagonist, Cameo, NPC

    character_name = Column(String(255), nullable=False)
    appearance = Column(Text)
    age = Column(Integer)
    backstory = Column(Text)

    # JSON format: ["trait1", "trait2", "trait3"]
    personality_traits = Column(Text)

    # How the character speaks (formal, casual, uses slang, etc.)
    speech_patterns = Column(Text)

    # Links instance to its template
    template_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="characters")

    # Index for faster queries
    __table_args__ = (
        Index("idx_character_story", "story_id"),
        Index("idx_character_playthrough", "playthrough_id"),
        Index("idx_character_type", "character_type"),
    )


class Location(Base):
    """
    Location in the story world
    Supports hierarchical locations (e.g., Kitchen -> House -> City)
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=True)

    location_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Type of location (indoor, outdoor, urban, rural, etc.)
    location_type = Column(String(100))

    # Parent location for hierarchy (can be NULL for top-level)
    parent_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Scope: city, neighborhood, building, room, etc.
    location_scope = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="locations")

    __table_args__ = (
        Index("idx_location_story", "story_id"),
        Index("idx_location_playthrough", "playthrough_id"),
    )


class Relationship(Base):
    """
    Relationship between two characters
    Tracks trust, affection, and familiarity over time

    Note: This is MEMORY between characters
    - How they know each other
    - Their history together
    - Current relationship status

    Future consideration: Group relationships, relationships between NPCs
    For now: Focus on relationships involving the User character
    """
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=True)

    # Entity 1 (usually the User character)
    entity1_type = Column(String(50), nullable=False)
    entity1_id = Column(Integer, ForeignKey("characters.id"), nullable=False)

    # Entity 2 (the other character)
    entity2_type = Column(String(50), nullable=False)
    entity2_id = Column(Integer, ForeignKey("characters.id"), nullable=False)

    # Type of relationship: friends, rivals, lovers, acquaintances, etc.
    relationship_type = Column(String(100), nullable=False)

    # How they first met
    first_meeting_context = Column(Text)

    # Relationship metrics (0.0 to 1.0 scale)
    trust = Column(Float, default=0.5)       # How much they trust each other
    affection = Column(Float, default=0.5)   # How much they care for each other
    familiarity = Column(Float, default=0.0) # How well they know each other

    # Last time they interacted
    last_interaction = Column(DateTime(timezone=True))

    # Summary of their relationship history
    # This gets updated/summarized over time (Phase 4: SUMMARIZE MEMORY)
    history_summary = Column(Text)

    __table_args__ = (
        Index("idx_relationship_entities", "entity1_id", "entity2_id"),
        Index("idx_relationship_playthrough", "playthrough_id"),
    )


# =============================================================================
# GAMEPLAY/SESSION TABLES
# =============================================================================


class Session(Base):
    """
    A chat session within a playthrough
    Each time the user opens the app and continues their story, a new session starts
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # The character the user is playing as
    user_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    playthrough = relationship("Playthrough", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session")
    scene_states = relationship("SceneState", back_populates="session")
    logs = relationship("Log", back_populates="session")

    __table_args__ = (Index("idx_session_playthrough", "playthrough_id"),)


class Conversation(Base):
    """
    Individual messages in a session
    Either from the narrator (AI) or the user
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # Who sent this message
    # "narrator" = AI-generated story text
    # "user" = User input
    speaker_type = Column(String(50), nullable=False)

    # Name of the speaker (if applicable)
    speaker_name = Column(String(255))

    # The actual message content
    message = Column(Text, nullable=False)

    # Metadata about the message (for future analysis)
    emotion_expressed = Column(String(100))
    topics_discussed = Column(Text)  # JSON array

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="conversations")

    __table_args__ = (
        Index("idx_conversation_session", "session_id"),
        Index("idx_conversation_playthrough", "playthrough_id"),
    )


class SceneState(Base):
    """
    Current state of the scene
    Updated after each interaction based on what happened
    Critical for maintaining context and consistency
    """
    __tablename__ = "scene_state"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # Physical setting
    location = Column(String(255))
    time_of_day = Column(String(100))
    weather = Column(String(100))

    # What's happening in the scene
    scene_context = Column(Text)

    # Overall mood/tone of the scene
    emotional_tone = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="scene_states")
    characters_in_scene = relationship("SceneCharacter", back_populates="scene_state")

    __table_args__ = (
        Index("idx_scene_session", "session_id"),
        Index("idx_scene_playthrough", "playthrough_id"),
    )


class SceneCharacter(Base):
    """
    Characters present in the current scene
    Tracks their mood, intent, and physical position
    Used in Phase 2+ for character tracking
    """
    __tablename__ = "scene_characters"

    id = Column(Integer, primary_key=True, index=True)
    scene_state_id = Column(Integer, ForeignKey("scene_state.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    character_name = Column(String(255))
    character_type = Column(String(50))

    # Is this a temporary/unnamed character?
    is_temporary = Column(Integer, default=0)

    # Character's current state
    character_mood = Column(String(100))
    character_intent = Column(Text)
    character_physical_position = Column(String(255))

    # Is this character currently speaking?
    is_speaking = Column(Integer, default=0)

    # Relationships
    scene_state = relationship("SceneState", back_populates="characters_in_scene")

    __table_args__ = (Index("idx_scene_char_scene", "scene_state_id"),)


# =============================================================================
# MEMORY AND FLAGS
# =============================================================================


class MemoryFlag(Base):
    """
    Important events that should be remembered
    Things like: first kiss, betrayal, promises made, etc.
    These are "anchored" memories that don't decay over time
    Used for story consistency and continuity
    """
    __tablename__ = "memory_flags"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # Type of flag: event, promise, revelation, relationship_change, etc.
    flag_type = Column(String(100), nullable=False)

    # The actual content of the flag
    flag_value = Column(Text)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # How important is this flag? (1-10 scale)
    # Higher importance = more likely to be included in context
    importance = Column(Integer, default=5)

    __table_args__ = (
        Index("idx_memory_playthrough", "playthrough_id"),
        Index("idx_memory_importance", "importance"),
    )


class CharacterKnowledge(Base):
    """
    Track what each character knows
    Prevents "mind reading" - characters shouldn't know things they weren't told
    Phase 1.3+ feature: CHARACTER KNOWLEDGE TRACKING
    """
    __tablename__ = "character_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)

    # Type of knowledge: fact, secret, observation, rumor, etc.
    knowledge_type = Column(String(100), nullable=False)

    # What do they know?
    knowledge_content = Column(Text, nullable=False)

    # When did they learn this?
    learned_at = Column(DateTime(timezone=True), server_default=func.now())

    # How did they learn it? (told by someone, observed, overheard, etc.)
    source = Column(String(255))

    # How certain are they? (0.0 to 1.0)
    certainty = Column(Float, default=1.0)

    __table_args__ = (
        Index("idx_knowledge_character", "character_id"),
        Index("idx_knowledge_playthrough", "playthrough_id"),
    )


# =============================================================================
# STORY STRUCTURE TABLES
# =============================================================================


class StoryArc(Base):
    """
    Major story arcs (like chapters or questlines)
    Phase 2.2 feature: STORY ARCS & EPISODES
    """
    __tablename__ = "story_arcs"

    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)

    # NULL = template, valued = instance
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=True)

    arc_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Order in which arcs should be completed (1, 2, 3, etc.)
    arc_order = Column(Integer, nullable=False)

    # Status flags
    is_active = Column(Integer, default=0)
    is_completed = Column(Integer, default=0)

    # Conditions for starting/completing the arc (JSON format)
    # e.g., {"flags": ["met_love_interest"], "relationship": {"trust": 0.6}}
    start_condition = Column(Text)
    completion_condition = Column(Text)

    # Relationships
    story = relationship("Story", back_populates="story_arcs")
    episodes = relationship("StoryEpisode", back_populates="arc")

    __table_args__ = (
        Index("idx_arc_story", "story_id"),
        Index("idx_arc_playthrough", "playthrough_id"),
        Index("idx_arc_active", "is_active"),
    )


class StoryEpisode(Base):
    """
    Episodes within story arcs (like scenes or quests)
    More granular than arcs
    """
    __tablename__ = "story_episodes"

    id = Column(Integer, primary_key=True, index=True)
    arc_id = Column(Integer, ForeignKey("story_arcs.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=True)

    episode_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Order within the arc
    episode_order = Column(Integer, nullable=False)

    # Status
    is_active = Column(Integer, default=0)
    is_completed = Column(Integer, default=0)

    # Flags that trigger/complete this episode (JSON format)
    trigger_flags = Column(Text)
    completion_flags = Column(Text)

    # Relationships
    arc = relationship("StoryArc", back_populates="episodes")

    __table_args__ = (
        Index("idx_episode_arc", "arc_id"),
        Index("idx_episode_playthrough", "playthrough_id"),
    )


class StoryFlag(Base):
    """
    Story progression flags
    Boolean or string flags that track story state
    e.g., "met_love_interest", "discovered_secret", "trust_level_high"
    """
    __tablename__ = "story_flags"

    id = Column(Integer, primary_key=True, index=True)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    flag_name = Column(String(255), nullable=False)
    flag_value = Column(String(255), nullable=False)

    # When was this flag set?
    set_at = Column(DateTime(timezone=True), server_default=func.now())

    # What set this flag? (user action, AI decision, arc completion, etc.)
    set_by = Column(String(255))

    __table_args__ = (
        Index("idx_flag_playthrough", "playthrough_id"),
        Index("idx_flag_name", "flag_name"),
    )


# =============================================================================
# LOGGING TABLE (CRITICAL FOR DEVELOPMENT)
# =============================================================================


class Log(Base):
    """
    System logs for debugging and development
    VERY IMPORTANT: Almost everything should be logged
    This is how we understand what's happening in the system

    Log Types:
    - notification: Normal system events (just stating something happened)
    - error: Something went wrong
    - edit: Database was modified
    - ai_decision: AI made a decision (character analysis, story generation)
    - context: Context/memory related events

    Log Categories:
    - database: Database operations
    - ai: AI/LLM related
    - memory: Memory/ChromaDB operations
    - character: Character decision making
    - story: Story progression
    - system: General system events
    """
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)

    # Optional: Link to a specific session
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    # Type of log entry
    log_type = Column(String(50), nullable=False)

    # Category for filtering
    log_category = Column(String(50))

    # Human-readable message
    message = Column(Text, nullable=False)

    # Additional structured data (JSON format)
    # Can contain anything relevant to the log entry
    details = Column(Text)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="logs")

    __table_args__ = (
        Index("idx_log_session", "session_id"),
        Index("idx_log_type", "log_type"),
        Index("idx_log_category", "log_category"),
        Index("idx_log_timestamp", "timestamp"),
    )
