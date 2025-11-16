"""
Pydantic Schemas for API Request/Response Validation
These define what data goes in and out of the API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =============================================================================
# STORY SCHEMAS
# =============================================================================


class StoryBase(BaseModel):
    """Base story information"""
    title: str
    description: Optional[str] = None
    initial_message: str
    initial_location: Optional[str] = None
    initial_time: Optional[str] = None


class StoryCreate(StoryBase):
    """Schema for creating a new story"""
    pass


class StoryResponse(StoryBase):
    """Schema for story response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    """Schema for listing stories"""
    id: int
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# PLAYTHROUGH SCHEMAS
# =============================================================================


class PlaythroughBase(BaseModel):
    """Base playthrough information"""
    story_id: int
    playthrough_name: str


class PlaythroughCreate(PlaythroughBase):
    """Schema for creating a new playthrough"""
    pass


class PlaythroughResponse(PlaythroughBase):
    """Schema for playthrough response"""
    id: int
    created_at: datetime
    last_played: datetime
    is_active: int
    current_location: Optional[str] = None
    current_time: Optional[str] = None

    class Config:
        from_attributes = True


class PlaythroughListResponse(BaseModel):
    """Schema for listing playthroughs"""
    id: int
    story_id: int
    playthrough_name: str
    last_played: datetime
    is_active: int

    class Config:
        from_attributes = True


# =============================================================================
# CHARACTER SCHEMAS
# =============================================================================


class CharacterBase(BaseModel):
    """Base character information"""
    character_type: str
    character_name: str
    appearance: Optional[str] = None
    age: Optional[int] = None
    backstory: Optional[str] = None
    personality_traits: Optional[str] = None  # JSON string
    speech_patterns: Optional[str] = None


class CharacterCreate(CharacterBase):
    """Schema for creating a character"""
    story_id: int
    playthrough_id: Optional[int] = None
    template_character_id: Optional[int] = None


class CharacterResponse(CharacterBase):
    """Schema for character response"""
    id: int
    story_id: int
    playthrough_id: Optional[int] = None
    template_character_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CharacterInScene(BaseModel):
    """Character as they appear in a scene"""
    character_id: int
    character_name: str
    character_type: str
    mood: Optional[str] = None
    intent: Optional[str] = None
    position: Optional[str] = None


# =============================================================================
# SESSION SCHEMAS
# =============================================================================


class SessionCreate(BaseModel):
    """Schema for creating a session"""
    playthrough_id: int
    user_character_id: Optional[int] = None


class SessionResponse(BaseModel):
    """Schema for session response"""
    id: int
    playthrough_id: int
    user_character_id: Optional[int] = None
    started_at: datetime
    last_active: datetime

    class Config:
        from_attributes = True


# =============================================================================
# CONVERSATION SCHEMAS
# =============================================================================


class ConversationBase(BaseModel):
    """Base conversation message"""
    speaker_type: str  # "narrator" or "user"
    message: str
    speaker_name: Optional[str] = None


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation entry"""
    session_id: int
    playthrough_id: int
    emotion_expressed: Optional[str] = None
    topics_discussed: Optional[str] = None  # JSON string


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: int
    session_id: int
    playthrough_id: int
    emotion_expressed: Optional[str] = None
    topics_discussed: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# =============================================================================
# CHAT SCHEMAS (Main interaction with AI)
# =============================================================================


class ChatRequest(BaseModel):
    """
    Request to send a message to the AI
    This is the main user interaction endpoint
    """
    session_id: int
    message: str  # User's input/action


class ChatResponse(BaseModel):
    """
    Response from the AI
    Contains the generated story text and metadata
    """
    message: str  # AI-generated story text
    session_id: int
    conversation_id: int

    # Phase 2+ metadata
    characters_in_scene: Optional[List[CharacterInScene]] = None
    current_location: Optional[str] = None
    current_time: Optional[str] = None

    # Phase 3+ metadata
    relationship_updates: Optional[dict] = None
    story_flags_set: Optional[List[str]] = None


class GenerateMoreRequest(BaseModel):
    """
    Request to generate more story content without user input
    Phase 4 feature: GENERATE MORE option
    """
    session_id: int


# =============================================================================
# SCENE STATE SCHEMAS
# =============================================================================


class SceneStateBase(BaseModel):
    """Base scene state"""
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    scene_context: Optional[str] = None
    emotional_tone: Optional[str] = None


class SceneStateCreate(SceneStateBase):
    """Schema for creating scene state"""
    session_id: int
    playthrough_id: int


class SceneStateResponse(SceneStateBase):
    """Schema for scene state response"""
    id: int
    session_id: int
    playthrough_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# RELATIONSHIP SCHEMAS
# =============================================================================


class RelationshipBase(BaseModel):
    """Base relationship information"""
    entity1_type: str
    entity1_id: int
    entity2_type: str
    entity2_id: int
    relationship_type: str
    first_meeting_context: Optional[str] = None
    trust: float = Field(default=0.5, ge=0.0, le=1.0)
    affection: float = Field(default=0.5, ge=0.0, le=1.0)
    familiarity: float = Field(default=0.0, ge=0.0, le=1.0)
    history_summary: Optional[str] = None


class RelationshipCreate(RelationshipBase):
    """Schema for creating a relationship"""
    story_id: int
    playthrough_id: Optional[int] = None


class RelationshipResponse(RelationshipBase):
    """Schema for relationship response"""
    id: int
    story_id: int
    playthrough_id: Optional[int] = None
    last_interaction: Optional[datetime] = None

    class Config:
        from_attributes = True


class RelationshipUpdate(BaseModel):
    """Schema for updating relationship values"""
    trust: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    affection: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    familiarity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    history_summary: Optional[str] = None


# =============================================================================
# LOG SCHEMAS
# =============================================================================


class LogCreate(BaseModel):
    """Schema for creating a log entry"""
    session_id: Optional[int] = None
    log_type: str  # notification, error, edit, ai_decision, context
    log_category: Optional[str] = None  # database, ai, memory, character, story, system
    message: str
    details: Optional[str] = None  # JSON string


class LogResponse(BaseModel):
    """Schema for log response"""
    id: int
    session_id: Optional[int] = None
    log_type: str
    log_category: Optional[str] = None
    message: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class LogFilter(BaseModel):
    """Schema for filtering logs"""
    session_id: Optional[int] = None
    log_type: Optional[str] = None
    log_category: Optional[str] = None
    limit: int = 100
    offset: int = 0


# =============================================================================
# STORY STRUCTURE SCHEMAS
# =============================================================================


class StoryArcResponse(BaseModel):
    """Schema for story arc response"""
    id: int
    story_id: int
    playthrough_id: Optional[int] = None
    arc_name: str
    description: Optional[str] = None
    arc_order: int
    is_active: int
    is_completed: int

    class Config:
        from_attributes = True


class StoryFlagCreate(BaseModel):
    """Schema for creating a story flag"""
    playthrough_id: int
    flag_name: str
    flag_value: str
    set_by: Optional[str] = None


class StoryFlagResponse(BaseModel):
    """Schema for story flag response"""
    id: int
    playthrough_id: int
    flag_name: str
    flag_value: str
    set_at: datetime
    set_by: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# MEMORY SCHEMAS
# =============================================================================


class MemoryFlagCreate(BaseModel):
    """Schema for creating a memory flag"""
    session_id: int
    playthrough_id: int
    flag_type: str
    flag_value: Optional[str] = None
    importance: int = Field(default=5, ge=1, le=10)


class MemoryFlagResponse(BaseModel):
    """Schema for memory flag response"""
    id: int
    session_id: int
    playthrough_id: int
    flag_type: str
    flag_value: Optional[str] = None
    timestamp: datetime
    importance: int

    class Config:
        from_attributes = True


# =============================================================================
# HEALTH CHECK SCHEMA
# =============================================================================


class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str
    database: str
    ai_provider: str
    version: str
