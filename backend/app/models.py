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

    # === CHARACTER DEPTH ENHANCEMENTS ===
    # Added for making characters feel like real people with consistent personalities

    # CORE PERSONALITY DEPTH
    # JSON format: ["loyalty", "truth", "family", "freedom"]
    core_values = Column(Text)
    # JSON format: ["abandonment", "failure", "loss_of_control"]
    core_fears = Column(Text)

    # BEHAVIORAL CONSTRAINTS
    # JSON format: ["betray_a_friend", "harm_innocent", "lie_to_family"]
    # Used in VALIDATION stage to check if actions contradict character
    would_never_do = Column(Text)
    # JSON format: ["defend_the_weak", "keep_promises"]
    would_always_do = Column(Text)
    # JSON format: ["fidgets_with_ring", "paces", "makes_jokes"]
    # What they do when stressed or uncomfortable
    comfort_behaviors = Column(Text)

    # SPEECH SPECIFICS (concrete examples, not abstract descriptions)
    # JSON format: {
    #   "greetings": ["Good day", "Greetings"],
    #   "agreement": ["Indeed", "Quite so"],
    #   "disagreement": ["I must differ", "I cannot support that"],
    #   "exclamations": ["Good heavens", "Most extraordinary"],
    #   "fillers": ["As it were", "If you will"],
    #   "avoids": ["yeah", "cool", "awesome", "like"]
    # }
    verbal_patterns = Column(Text)
    # "complex with subordinate clauses", "short and direct", "flowery and verbose"
    sentence_structure = Column(Text)
    # JSON format: ["mark my words", "if you ask me", "as I always say"]
    common_phrases = Column(Text)

    # DECISION MAKING
    # "impulsive", "analytical", "emotional", "cautious"
    # Used in SCENE_SIMULATION stage to determine how they react
    decision_style = Column(String(100))

    # INTERNAL CONFLICT (makes them human!)
    # Example: "Preaches forgiveness but cannot forgive himself for father's death"
    # This creates authentic inconsistency that makes characters MORE believable
    internal_contradiction = Column(Text)

    # SECRETS & HIDDEN LAYERS
    # Something they actively hide from others
    secret_kept = Column(Text)
    # Their deepest weakness
    vulnerability = Column(Text)

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

    # === RELATIONSHIP DEPTH ENHANCEMENTS ===
    # Added to make relationships feel authentic and multi-layered

    # SHARED HISTORY
    # JSON format: ["the coffee incident", "saved each other during the fire", "first meeting at the market"]
    # Important shared experiences that define the relationship
    shared_memories = Column(Text)
    # JSON format: ["the Tuesday disaster", "the 'incident' we don't talk about"]
    # Small details that create authenticity and connection
    inside_jokes = Column(Text)

    # CONFLICTS & PROMISES
    # JSON format: ["disagreement about loyalty", "unspoken tension about the past"]
    # Ongoing tensions that haven't been resolved
    unresolved_conflicts = Column(Text)
    # JSON format: [{"who": "entity1", "promise": "will always be there", "date": "2024-01-15"}]
    # Commitments made to each other
    promises_made = Column(Text)
    # Description of most recent conflict
    last_conflict = Column(Text)
    # When the last conflict happened
    last_conflict_at = Column(DateTime(timezone=True))

    # RELATIONSHIP QUALITY
    # 0.0 to 1.0 scale - overall relationship strength
    # Used in CONTEXT_GATHERING to prioritize which relationships to load
    closeness = Column(Float, default=0.5)
    # 1-10 scale - how important is this relationship? (major vs minor character)
    # Used for context prioritization (load important relationships first)
    importance = Column(Integer, default=5)

    # INTERACTION PATTERNS
    # "playful_banter", "professional", "tense", "warm", "distant"
    # How they typically interact
    typical_interaction_tone = Column(String(100))
    # "entity1 teases, entity2 plays along", "both avoid difficult topics"
    # The dance/pattern of their conversations
    conversational_dynamics = Column(Text)

    __table_args__ = (
        Index("idx_relationship_entities", "entity1_id", "entity2_id"),
        Index("idx_relationship_playthrough", "playthrough_id"),
        Index("idx_relationship_importance", "importance"),
        Index("idx_relationship_closeness", "closeness"),
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
        Index("idx_memory_flag_playthrough", "playthrough_id"),
        Index("idx_memory_flag_importance", "importance"),
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

    # === IMPORTANCE TRACKING ===
    # Added for context prioritization in CONTEXT_GATHERING stage

    # 1-10 scale - how important is this knowledge?
    # Used to prioritize which knowledge to include in limited context window
    importance = Column(Integer, default=5)
    # When was this knowledge last referenced/used in the story?
    # Used for recency-based retrieval
    last_accessed_at = Column(DateTime(timezone=True))
    # How many times has this knowledge been referenced?
    # Frequently accessed knowledge might be more central to character
    access_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_knowledge_character", "character_id"),
        Index("idx_knowledge_playthrough", "playthrough_id"),
        Index("idx_knowledge_importance", "importance"),
    )


class CharacterState(Base):
    """
    Persistent emotional and mental state of characters across playthrough

    CRITICAL for handling time skips and maintaining consistent character emotions.

    Design:
    - baseline_emotional_state: Character's "normal" mood (e.g., "generally optimistic")
    - current_emotional_state: What they feel RIGHT NOW (e.g., "angry", "heartbroken")
    - Time skips: Acute emotions decay toward baseline, deep emotions persist

    Used in pipeline:
    - CONTEXT_GATHERING: Load character's current state
    - SCENE_SIMULATION: Use stress/clarity to determine how they react
    - STATE_UPDATE: Update emotional state based on what happened
    """
    __tablename__ = "character_state"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # === EMOTIONAL STATE ===
    # Baseline: their "normal" emotional state when nothing special is happening
    # Examples: "generally optimistic", "chronically anxious", "cautiously hopeful"
    baseline_emotional_state = Column(String(100))

    # Current: what they feel RIGHT NOW (can differ from baseline)
    # Examples: "angry", "heartbroken", "excited", "terrified"
    current_emotional_state = Column(String(100))

    # Why they feel this way (critical for understanding and decay logic)
    # Example: "Just discovered friend's betrayal"
    emotion_cause = Column(Text)

    # How strongly they feel it (0.0 to 1.0)
    # 1.0 = overwhelming emotion, 0.0 = barely noticeable
    emotion_intensity = Column(Float, default=0.5)

    # When this emotional state started (for time-based decay)
    # Acute emotions (anger, surprise) decay fast
    # Deep emotions (grief, love) persist longer
    emotion_started_at = Column(DateTime(timezone=True))

    # === MENTAL STATE ===
    # Stress level affects decision-making quality (0.0 to 1.0)
    # High stress = more impulsive, less rational decisions
    stress_level = Column(Float, default=0.5)

    # Energy level affects engagement (0.0 to 1.0)
    # Low energy = shorter responses, less initiative
    energy_level = Column(Float, default=0.7)

    # Mental clarity affects rationality (0.0 to 1.0)
    # Low clarity = emotional reasoning, confusion
    mental_clarity = Column(Float, default=0.8)

    # === CURRENT FOCUS ===
    # What's on their mind right now
    # Example: "Worried about upcoming confrontation with antagonist"
    primary_concern = Column(Text)

    # JSON array of other things they're thinking about
    # Example: ["need to repair relationship with sister", "running out of time"]
    secondary_concerns = Column(Text)

    # === TIMESTAMPS ===
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_char_state_character", "character_id"),
        Index("idx_char_state_playthrough", "playthrough_id"),
    )


# =============================================================================
# CHARACTER DEPTH TABLES (Goals, Memories, Beliefs, Avoidances)
# =============================================================================


class CharacterGoal(Base):
    """
    What characters want - critical for consistent motivation

    Goals drive character behavior and decision-making.
    Without goals, AI doesn't know what characters are trying to achieve.

    Goal types:
    - immediate: Right now in this scene ("get away from this conversation")
    - short_term: Current arc/episode ("win protagonist's trust")
    - long_term: Life ambitions ("become the most powerful mage")

    Used in pipeline:
    - CONTEXT_GATHERING: Retrieve top 3-5 active goals by priority
    - SCENE_SIMULATION: Characters act to advance their goals
    - VALIDATION: Check if actions contradict stated goals
    """
    __tablename__ = "character_goals"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # === GOAL DEFINITION ===
    # "short_term", "long_term", "immediate"
    goal_type = Column(String(50), nullable=False)

    # What they want
    # Example: "Get close to the protagonist", "Find out who killed my father"
    goal_content = Column(Text, nullable=False)

    # === PRIORITY & STATUS ===
    # 1-10, used for context prioritization (which goals to include in limited context)
    priority = Column(Integer, default=5)

    # "active", "achieved", "abandoned", "blocked"
    status = Column(String(50), default='active')

    # === BLOCKING FACTORS ===
    # JSON array of what's preventing them from achieving this
    # Example: ["protagonist_distrust", "time_constraints", "lack_of_resources"]
    blocking_factors = Column(Text)

    # === MOTIVATION ===
    # WHY they want this (links to backstory/values/fears)
    # Example: "Father was murdered and I need justice" or "Proving I'm worthy of love"
    underlying_reason = Column(Text)

    # === PROGRESS ===
    # How far along they are, steps taken, etc.
    progress_notes = Column(Text)

    # === TIMESTAMPS ===
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_goal_character", "character_id"),
        Index("idx_goal_playthrough", "playthrough_id"),
        Index("idx_goal_status", "status"),
        Index("idx_goal_priority", "priority"),
    )


class CharacterMemory(Base):
    """
    Episodic memory - what happened to the character

    This is the character's personal experience history.
    Memories shape how characters react to similar situations.

    Memory types:
    - personal_experience: They experienced it directly
    - witnessed: They saw it happen to someone else
    - told_about: Someone told them about it

    Retrieval strategy:
    - ChromaDB semantic search (find similar memories to current situation)
    - Importance × recency × emotional_intensity ranking
    - Limit to top 5-10 most relevant

    Used in pipeline:
    - CONTEXT_GATHERING: Semantic search + importance/recency ranking
    - SCENE_SIMULATION: Characters react based on similar past experiences
    - STATE_UPDATE: Create new memories after significant events
    """
    __tablename__ = "character_memories"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # === MEMORY CONTENT ===
    # "personal_experience", "witnessed", "told_about"
    memory_type = Column(String(50), nullable=False)

    # The actual memory description
    # Example: "Watched my father die in front of me, powerless to help"
    memory_content = Column(Text, nullable=False)

    # === EMOTIONAL IMPACT ===
    # "positive", "negative", "neutral", "mixed"
    emotional_valence = Column(String(50))

    # 0.0 to 1.0 - how emotionally charged is this memory?
    # High intensity memories are more likely to influence current behavior
    emotional_intensity = Column(Float, default=0.5)

    # === IMPORTANCE & RETRIEVAL ===
    # 1-10 scale - critical for context selection
    # Important memories should be retrieved even if not recent
    importance = Column(Integer, default=5)

    # When was this memory last recalled/referenced in the story?
    # Used for recency-based retrieval (recent memories more accessible)
    last_recalled_at = Column(DateTime(timezone=True))

    # How many times has this memory been accessed?
    # Frequently recalled memories are strengthened (like real memory)
    recall_count = Column(Integer, default=0)

    # === CONTEXT ===
    # JSON array of character IDs involved in this memory
    # Example: [23, 45, 67]
    related_characters = Column(Text)

    # Where this happened
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # When this memory was formed (session it happened in)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    # === ASSOCIATIONS (for semantic search) ===
    # JSON array of tags for finding related memories
    # Example: ["betrayal", "trust_broken", "friendship", "violence"]
    tags = Column(Text)

    # === TIMESTAMPS ===
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_memory_character", "character_id"),
        Index("idx_memory_playthrough", "playthrough_id"),
        Index("idx_memory_importance", "importance"),
        Index("idx_memory_type", "memory_type"),
        Index("idx_memory_emotional", "emotional_valence"),
    )


class CharacterBelief(Base):
    """
    Semantic memory - beliefs and worldviews characters hold

    Beliefs are different from memories:
    - Memories: "X happened"
    - Beliefs: "X is true" or "Y is how the world works"

    Examples:
    - "Humans cannot be trusted"
    - "Violence is never the answer"
    - "The ends justify the means"
    - "Love conquers all"

    Beliefs guide character judgments and decisions.
    Characters should act consistently with their beliefs unless:
    1. The belief is weakly held (low strength)
    2. The belief is being challenged (is_challenged = 1)
    3. They're in extreme circumstances

    Used in pipeline:
    - CONTEXT_GATHERING: Load beliefs relevant to current situation
    - SCENE_SIMULATION: Beliefs guide character reactions and judgments
    - VALIDATION: Actions shouldn't contradict strongly-held beliefs without reason
    - STATE_UPDATE: Beliefs can be challenged or reinforced by events
    """
    __tablename__ = "character_beliefs"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # === BELIEF CONTENT ===
    # What they believe
    # Example: "Humans cannot be trusted", "Family is everything"
    belief_content = Column(Text, nullable=False)

    # "worldview", "moral_stance", "factual_belief", "self_belief"
    belief_category = Column(String(100))

    # === STRENGTH & ORIGIN ===
    # 0.0 to 1.0 - how firmly held is this belief?
    # 1.0 = core conviction, won't change easily
    # 0.3 = tentative belief, easily swayed
    strength = Column(Float, default=0.5)

    # WHY they believe this
    # Example: "Betrayed by best friend in childhood" or "Taught by father"
    origin = Column(Text)

    # Link to the memory that caused this belief (if applicable)
    origin_memory_id = Column(Integer, ForeignKey("character_memories.id"), nullable=True)

    # === IMPORTANCE ===
    # 1-10, for context prioritization
    # Central beliefs (importance=10) should always be in context
    importance = Column(Integer, default=5)

    # === CHANGE TRACKING ===
    # Has this belief been questioned or contradicted by recent events?
    is_challenged = Column(Integer, default=0)

    # JSON array of contradicting evidence/events
    # Example: ["protagonist proved trustworthy despite being human", "father's advice led to disaster"]
    challenged_by = Column(Text)

    # === TIMESTAMPS ===
    # When this belief was formed
    formed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Last time evidence supported this belief
    last_reinforced_at = Column(DateTime(timezone=True))

    # Last time evidence contradicted this belief
    last_challenged_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_belief_character", "character_id"),
        Index("idx_belief_playthrough", "playthrough_id"),
        Index("idx_belief_importance", "importance"),
    )


class CharacterAvoidance(Base):
    """
    Things characters avoid and WHY (avoidances need underlying reasons)

    Avoidances make characters feel real and complex.
    They're NOT arbitrary - they're linked to trauma, fears, or values.

    Avoidance types:
    - topic: Subjects they won't discuss ("talking about father")
    - location: Places they avoid ("the old house")
    - person: People they stay away from
    - activity: Things they won't do ("swimming in deep water")
    - emotion: Feelings they suppress ("showing vulnerability")

    CRITICAL: Every avoidance must have a reason_memory_id or reason_description.
    "They just avoid it" is not enough - we need to know WHY.

    Used in pipeline:
    - SCENE_SIMULATION: Check if scene contains avoided elements
    - GENERATION: Character shows discomfort/avoidance behavior
    - VALIDATION: Character shouldn't casually engage with avoided topics
    """
    __tablename__ = "character_avoidances"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    playthrough_id = Column(Integer, ForeignKey("playthroughs.id"), nullable=False)

    # === AVOIDANCE DEFINITION ===
    # "topic", "location", "person", "activity", "emotion"
    avoidance_type = Column(String(50))

    # What they avoid
    # Examples: "deep water", "talking about father", "showing vulnerability"
    avoidance_target = Column(Text, nullable=False)

    # === UNDERLYING REASON (critical!) ===
    # "trauma", "fear", "shame", "social_norm", "moral_stance"
    reason_type = Column(String(50))

    # Detailed explanation of WHY they avoid this
    # Example: "Nearly drowned as a child and never recovered from the fear"
    reason_description = Column(Text, nullable=False)

    # Link to the memory/trauma that caused this avoidance
    # Example: memory of nearly drowning
    reason_memory_id = Column(Integer, ForeignKey("character_memories.id"), nullable=True)

    # === SEVERITY ===
    # 1-10, how strongly they avoid it
    # 10 = will leave immediately, refuse to discuss
    # 3 = uncomfortable but can push through if needed
    severity = Column(Integer, default=5)

    # 1-10, for context prioritization
    # High importance avoidances should always be checked
    importance = Column(Integer, default=5)

    # === BEHAVIORAL MANIFESTATION ===
    # How they show the avoidance
    # Example: "becomes silent, makes excuses to leave, changes subject"
    manifestation = Column(Text)

    # JSON: When would they face this anyway despite the avoidance?
    # Example: {"to_save_loved_one": true, "if_life_depends_on_it": true}
    override_conditions = Column(Text)

    # === TIMESTAMPS ===
    started_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_avoidance_character", "character_id"),
        Index("idx_avoidance_playthrough", "playthrough_id"),
        Index("idx_avoidance_severity", "severity"),
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
