"""
CRUD Operations for Dreamwalkers Database
Create, Read, Update, Delete operations for all models
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime
import json

from . import models, schemas
from .utils.logger import log_notification, log_edit, log_error


# =============================================================================
# STORY OPERATIONS
# =============================================================================


def create_story(db: Session, story: schemas.StoryCreate) -> models.Story:
    """Create a new story template"""
    db_story = models.Story(**story.model_dump())
    db.add(db_story)
    db.commit()
    db.refresh(db_story)

    log_notification(
        db,
        f"Created new story: {story.title}",
        "database",
        {"story_id": db_story.id}
    )

    return db_story


def get_story(db: Session, story_id: int) -> Optional[models.Story]:
    """Get a story by ID"""
    return db.query(models.Story).filter(models.Story.id == story_id).first()


def get_all_stories(db: Session) -> List[models.Story]:
    """Get all stories"""
    return db.query(models.Story).all()


# =============================================================================
# PLAYTHROUGH OPERATIONS
# =============================================================================


def create_playthrough(
    db: Session,
    playthrough: schemas.PlaythroughCreate
) -> models.Playthrough:
    """
    Create a new playthrough for a story
    This also creates instances of all template characters and relationships
    """
    # Create the playthrough
    db_playthrough = models.Playthrough(**playthrough.model_dump())
    db.add(db_playthrough)
    db.commit()
    db.refresh(db_playthrough)

    log_notification(
        db,
        f"Created playthrough: {playthrough.playthrough_name}",
        "database",
        {"playthrough_id": db_playthrough.id, "story_id": playthrough.story_id}
    )

    # Copy template characters to this playthrough
    _copy_template_characters(db, playthrough.story_id, db_playthrough.id)

    # Copy template relationships to this playthrough
    _copy_template_relationships(db, playthrough.story_id, db_playthrough.id)

    # Copy template locations to this playthrough
    _copy_template_locations(db, playthrough.story_id, db_playthrough.id)

    # Copy template story arcs to this playthrough
    _copy_template_arcs(db, playthrough.story_id, db_playthrough.id)

    return db_playthrough


def _copy_template_characters(
    db: Session,
    story_id: int,
    playthrough_id: int
) -> None:
    """Copy all template characters for this story to the playthrough"""
    templates = db.query(models.Character).filter(
        and_(
            models.Character.story_id == story_id,
            models.Character.playthrough_id.is_(None)
        )
    ).all()

    for template in templates:
        instance = models.Character(
            story_id=story_id,
            playthrough_id=playthrough_id,
            character_type=template.character_type,
            character_name=template.character_name,
            appearance=template.appearance,
            age=template.age,
            backstory=template.backstory,
            personality_traits=template.personality_traits,
            speech_patterns=template.speech_patterns,
            template_character_id=template.id
        )
        db.add(instance)

    db.commit()

    log_notification(
        db,
        f"Copied {len(templates)} character templates to playthrough",
        "database",
        {"playthrough_id": playthrough_id}
    )


def _copy_template_relationships(
    db: Session,
    story_id: int,
    playthrough_id: int
) -> None:
    """Copy all template relationships for this story to the playthrough"""
    # First, build a mapping from template character IDs to playthrough character IDs
    playthrough_chars = db.query(models.Character).filter(
        models.Character.playthrough_id == playthrough_id
    ).all()

    template_to_playthrough_map = {
        char.template_character_id: char.id
        for char in playthrough_chars
        if char.template_character_id is not None
    }

    templates = db.query(models.Relationship).filter(
        and_(
            models.Relationship.story_id == story_id,
            models.Relationship.playthrough_id.is_(None)
        )
    ).all()

    for template in templates:
        # Map template character IDs to playthrough character IDs
        entity1_id = template_to_playthrough_map.get(template.entity1_id, template.entity1_id)
        entity2_id = template_to_playthrough_map.get(template.entity2_id, template.entity2_id)

        instance = models.Relationship(
            story_id=story_id,
            playthrough_id=playthrough_id,
            entity1_type=template.entity1_type,
            entity1_id=entity1_id,
            entity2_type=template.entity2_type,
            entity2_id=entity2_id,
            relationship_type=template.relationship_type,
            first_meeting_context=template.first_meeting_context,
            trust=template.trust,
            affection=template.affection,
            familiarity=template.familiarity,
            history_summary=template.history_summary
        )
        db.add(instance)

    db.commit()

    log_notification(
        db,
        f"Copied {len(templates)} relationship templates to playthrough",
        "database",
        {"playthrough_id": playthrough_id}
    )


def _copy_template_locations(
    db: Session,
    story_id: int,
    playthrough_id: int
) -> None:
    """Copy all template locations for this story to the playthrough"""
    templates = db.query(models.Location).filter(
        and_(
            models.Location.story_id == story_id,
            models.Location.playthrough_id.is_(None)
        )
    ).all()

    for template in templates:
        instance = models.Location(
            story_id=story_id,
            playthrough_id=playthrough_id,
            location_name=template.location_name,
            description=template.description,
            location_type=template.location_type,
            location_scope=template.location_scope
        )
        db.add(instance)

    db.commit()

    log_notification(
        db,
        f"Copied {len(templates)} location templates to playthrough",
        "database",
        {"playthrough_id": playthrough_id}
    )


def _copy_template_arcs(
    db: Session,
    story_id: int,
    playthrough_id: int
) -> None:
    """Copy all template story arcs for this story to the playthrough"""
    arcs = db.query(models.StoryArc).filter(
        and_(
            models.StoryArc.story_id == story_id,
            models.StoryArc.playthrough_id.is_(None)
        )
    ).all()

    for arc in arcs:
        arc_instance = models.StoryArc(
            story_id=story_id,
            playthrough_id=playthrough_id,
            arc_name=arc.arc_name,
            description=arc.description,
            arc_order=arc.arc_order,
            is_active=arc.is_active,
            is_completed=arc.is_completed,
            start_condition=arc.start_condition,
            completion_condition=arc.completion_condition
        )
        db.add(arc_instance)
        db.commit()
        db.refresh(arc_instance)

        # Copy episodes for this arc
        episodes = db.query(models.StoryEpisode).filter(
            and_(
                models.StoryEpisode.arc_id == arc.id,
                models.StoryEpisode.playthrough_id.is_(None)
            )
        ).all()

        for episode in episodes:
            episode_instance = models.StoryEpisode(
                arc_id=arc_instance.id,
                playthrough_id=playthrough_id,
                episode_name=episode.episode_name,
                description=episode.description,
                episode_order=episode.episode_order,
                is_active=episode.is_active,
                is_completed=episode.is_completed,
                trigger_flags=episode.trigger_flags,
                completion_flags=episode.completion_flags
            )
            db.add(episode_instance)

    db.commit()

    log_notification(
        db,
        f"Copied {len(arcs)} story arc templates to playthrough",
        "database",
        {"playthrough_id": playthrough_id}
    )


def get_playthrough(db: Session, playthrough_id: int) -> Optional[models.Playthrough]:
    """Get a playthrough by ID"""
    return db.query(models.Playthrough).filter(
        models.Playthrough.id == playthrough_id
    ).first()


def get_playthroughs_for_story(
    db: Session,
    story_id: int
) -> List[models.Playthrough]:
    """Get all playthroughs for a story"""
    return db.query(models.Playthrough).filter(
        models.Playthrough.story_id == story_id
    ).order_by(desc(models.Playthrough.last_played)).all()


def update_playthrough_location(
    db: Session,
    playthrough_id: int,
    location: str,
    time: Optional[str] = None
) -> None:
    """Update the current location and time of a playthrough"""
    playthrough = get_playthrough(db, playthrough_id)
    if playthrough:
        old_location = playthrough.current_location
        playthrough.current_location = location
        if time:
            playthrough.current_time = time
        db.commit()

        log_edit(
            db,
            f"Updated playthrough location",
            "database",
            {
                "playthrough_id": playthrough_id,
                "old_location": old_location,
                "new_location": location,
                "time": time
            }
        )


# =============================================================================
# CHARACTER OPERATIONS
# =============================================================================


def create_character(
    db: Session,
    character: schemas.CharacterCreate
) -> models.Character:
    """Create a new character"""
    db_character = models.Character(**character.model_dump())
    db.add(db_character)
    db.commit()
    db.refresh(db_character)

    log_notification(
        db,
        f"Created character: {character.character_name} ({character.character_type})",
        "database",
        {"character_id": db_character.id}
    )

    return db_character


def get_character(db: Session, character_id: int) -> Optional[models.Character]:
    """Get a character by ID"""
    return db.query(models.Character).filter(
        models.Character.id == character_id
    ).first()


def get_characters_for_playthrough(
    db: Session,
    playthrough_id: int,
    character_type: Optional[str] = None
) -> List[models.Character]:
    """Get all characters for a playthrough, optionally filtered by type"""
    query = db.query(models.Character).filter(
        models.Character.playthrough_id == playthrough_id
    )

    if character_type:
        query = query.filter(models.Character.character_type == character_type)

    return query.all()


def get_user_character(
    db: Session,
    playthrough_id: int
) -> Optional[models.Character]:
    """Get the user's character for a playthrough"""
    return db.query(models.Character).filter(
        and_(
            models.Character.playthrough_id == playthrough_id,
            models.Character.character_type == "User"
        )
    ).first()


def get_character_state(
    db: Session,
    character_id: int,
    playthrough_id: int
) -> Optional[models.CharacterState]:
    """Get the current state of a character in a playthrough"""
    return db.query(models.CharacterState).filter(
        and_(
            models.CharacterState.character_id == character_id,
            models.CharacterState.playthrough_id == playthrough_id
        )
    ).first()


def get_character_goals(
    db: Session,
    character_id: int,
    playthrough_id: int,
    status: str = 'active',
    limit: int = 5
) -> List[models.CharacterGoal]:
    """Get active goals for a character in a playthrough, ordered by priority"""
    query = db.query(models.CharacterGoal).filter(
        and_(
            models.CharacterGoal.character_id == character_id,
            models.CharacterGoal.playthrough_id == playthrough_id
        )
    )

    if status:
        query = query.filter(models.CharacterGoal.status == status)

    return query.order_by(models.CharacterGoal.priority.desc()).limit(limit).all()


# =============================================================================
# SESSION OPERATIONS
# =============================================================================


def create_session(
    db: Session,
    session: schemas.SessionCreate
) -> models.Session:
    """Create a new chat session"""
    db_session = models.Session(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    log_notification(
        db,
        f"Created new session",
        "database",
        {"session_id": db_session.id, "playthrough_id": session.playthrough_id}
    )

    return db_session


def get_session(db: Session, session_id: int) -> Optional[models.Session]:
    """Get a session by ID"""
    return db.query(models.Session).filter(
        models.Session.id == session_id
    ).first()


def get_latest_session(db: Session, playthrough_id: int) -> Optional[models.Session]:
    """Get the most recent session for a playthrough"""
    return db.query(models.Session).filter(
        models.Session.playthrough_id == playthrough_id
    ).order_by(desc(models.Session.last_active)).first()


def update_session_activity(db: Session, session_id: int) -> None:
    """Update the last_active timestamp for a session"""
    session = get_session(db, session_id)
    if session:
        session.last_active = datetime.utcnow()
        db.commit()


# =============================================================================
# CONVERSATION OPERATIONS
# =============================================================================


def create_conversation(
    db: Session,
    conversation: schemas.ConversationCreate
) -> models.Conversation:
    """Create a new conversation entry"""
    db_conversation = models.Conversation(**conversation.model_dump())
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)

    log_notification(
        db,
        f"Added conversation message ({conversation.speaker_type})",
        "database",
        {
            "conversation_id": db_conversation.id,
            "session_id": conversation.session_id,
            "speaker": conversation.speaker_type
        }
    )

    return db_conversation


def get_conversation_history(
    db: Session,
    session_id: int,
    limit: int = 20
) -> List[models.Conversation]:
    """Get recent conversation history for a session"""
    return db.query(models.Conversation).filter(
        models.Conversation.session_id == session_id
    ).order_by(desc(models.Conversation.timestamp)).limit(limit).all()[::-1]


def get_all_playthrough_conversations(
    db: Session,
    playthrough_id: int,
    limit: int = 100
) -> List[models.Conversation]:
    """Get all conversations for a playthrough (across all sessions)"""
    return db.query(models.Conversation).filter(
        models.Conversation.playthrough_id == playthrough_id
    ).order_by(desc(models.Conversation.timestamp)).limit(limit).all()[::-1]


# =============================================================================
# SCENE STATE OPERATIONS
# =============================================================================


def create_scene_state(
    db: Session,
    scene_state: schemas.SceneStateCreate
) -> models.SceneState:
    """Create a new scene state"""
    db_scene = models.SceneState(**scene_state.model_dump())
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)

    log_notification(
        db,
        f"Created scene state",
        "database",
        {
            "scene_id": db_scene.id,
            "location": scene_state.location,
            "time": scene_state.time_of_day
        }
    )

    return db_scene


def get_current_scene_state(
    db: Session,
    session_id: int
) -> Optional[models.SceneState]:
    """Get the most recent scene state for a session"""
    return db.query(models.SceneState).filter(
        models.SceneState.session_id == session_id
    ).order_by(desc(models.SceneState.created_at)).first()


def add_character_to_scene(
    db: Session,
    scene_state_id: int,
    playthrough_id: int,
    character_id: int,
    character_name: str,
    character_type: str,
    mood: Optional[str] = None,
    intent: Optional[str] = None,
    position: Optional[str] = None
) -> models.SceneCharacter:
    """Add a character to the current scene"""
    scene_char = models.SceneCharacter(
        scene_state_id=scene_state_id,
        playthrough_id=playthrough_id,
        character_id=character_id,
        character_name=character_name,
        character_type=character_type,
        character_mood=mood,
        character_intent=intent,
        character_physical_position=position
    )
    db.add(scene_char)
    db.commit()
    db.refresh(scene_char)

    log_notification(
        db,
        f"Added character to scene: {character_name}",
        "database",
        {"scene_state_id": scene_state_id, "character_id": character_id}
    )

    return scene_char


# =============================================================================
# RELATIONSHIP OPERATIONS
# =============================================================================


def create_relationship(
    db: Session,
    relationship: schemas.RelationshipCreate
) -> models.Relationship:
    """Create a new relationship"""
    db_relationship = models.Relationship(**relationship.model_dump())
    db.add(db_relationship)
    db.commit()
    db.refresh(db_relationship)

    log_notification(
        db,
        f"Created relationship",
        "database",
        {"relationship_id": db_relationship.id}
    )

    return db_relationship


def get_relationship(
    db: Session,
    entity1_id: int,
    entity2_id: int,
    playthrough_id: int
) -> Optional[models.Relationship]:
    """Get relationship between two characters"""
    return db.query(models.Relationship).filter(
        and_(
            models.Relationship.playthrough_id == playthrough_id,
            models.Relationship.entity1_id == entity1_id,
            models.Relationship.entity2_id == entity2_id
        )
    ).first()


def get_all_relationships_for_character(
    db: Session,
    character_id: int,
    playthrough_id: int
) -> List[models.Relationship]:
    """Get all relationships involving a character"""
    return db.query(models.Relationship).filter(
        and_(
            models.Relationship.playthrough_id == playthrough_id,
            (
                (models.Relationship.entity1_id == character_id) |
                (models.Relationship.entity2_id == character_id)
            )
        )
    ).all()


def update_relationship(
    db: Session,
    relationship_id: int,
    update_data: schemas.RelationshipUpdate
) -> Optional[models.Relationship]:
    """Update relationship values"""
    relationship = db.query(models.Relationship).filter(
        models.Relationship.id == relationship_id
    ).first()

    if not relationship:
        return None

    old_values = {
        "trust": relationship.trust,
        "affection": relationship.affection,
        "familiarity": relationship.familiarity
    }

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            setattr(relationship, key, value)

    relationship.last_interaction = datetime.utcnow()
    db.commit()
    db.refresh(relationship)

    new_values = {
        "trust": relationship.trust,
        "affection": relationship.affection,
        "familiarity": relationship.familiarity
    }

    log_edit(
        db,
        f"Updated relationship",
        "database",
        {
            "relationship_id": relationship_id,
            "old_values": old_values,
            "new_values": new_values
        }
    )

    return relationship


# =============================================================================
# LOG OPERATIONS
# =============================================================================


def get_logs(
    db: Session,
    filter_params: schemas.LogFilter
) -> List[models.Log]:
    """Get logs with optional filtering"""
    query = db.query(models.Log)

    if filter_params.session_id:
        query = query.filter(models.Log.session_id == filter_params.session_id)

    if filter_params.log_type:
        query = query.filter(models.Log.log_type == filter_params.log_type)

    if filter_params.log_category:
        query = query.filter(models.Log.log_category == filter_params.log_category)

    return query.order_by(desc(models.Log.timestamp)).offset(
        filter_params.offset
    ).limit(filter_params.limit).all()


def get_all_logs(db: Session, limit: int = 100) -> List[models.Log]:
    """Get all logs (most recent first)"""
    return db.query(models.Log).order_by(
        desc(models.Log.timestamp)
    ).limit(limit).all()


# =============================================================================
# STORY FLAG OPERATIONS
# =============================================================================


def create_story_flag(
    db: Session,
    flag: schemas.StoryFlagCreate
) -> models.StoryFlag:
    """Create a new story flag"""
    db_flag = models.StoryFlag(**flag.model_dump())
    db.add(db_flag)
    db.commit()
    db.refresh(db_flag)

    log_notification(
        db,
        f"Set story flag: {flag.flag_name} = {flag.flag_value}",
        "story",
        {"flag_id": db_flag.id, "playthrough_id": flag.playthrough_id}
    )

    return db_flag


def get_story_flags(
    db: Session,
    playthrough_id: int
) -> List[models.StoryFlag]:
    """Get all story flags for a playthrough"""
    return db.query(models.StoryFlag).filter(
        models.StoryFlag.playthrough_id == playthrough_id
    ).all()


def check_story_flag(
    db: Session,
    playthrough_id: int,
    flag_name: str
) -> Optional[str]:
    """Check if a story flag is set and return its value"""
    flag = db.query(models.StoryFlag).filter(
        and_(
            models.StoryFlag.playthrough_id == playthrough_id,
            models.StoryFlag.flag_name == flag_name
        )
    ).first()

    return flag.flag_value if flag else None


# =============================================================================
# MEMORY FLAG OPERATIONS
# =============================================================================


def create_memory_flag(
    db: Session,
    memory_flag: schemas.MemoryFlagCreate
) -> models.MemoryFlag:
    """Create a new memory flag (important event)"""
    db_flag = models.MemoryFlag(**memory_flag.model_dump())
    db.add(db_flag)
    db.commit()
    db.refresh(db_flag)

    log_notification(
        db,
        f"Created memory flag: {memory_flag.flag_type}",
        "memory",
        {
            "flag_id": db_flag.id,
            "importance": memory_flag.importance
        }
    )

    return db_flag


def get_important_memory_flags(
    db: Session,
    playthrough_id: int,
    min_importance: int = 5
) -> List[models.MemoryFlag]:
    """Get memory flags above a certain importance threshold"""
    return db.query(models.MemoryFlag).filter(
        and_(
            models.MemoryFlag.playthrough_id == playthrough_id,
            models.MemoryFlag.importance >= min_importance
        )
    ).order_by(desc(models.MemoryFlag.importance)).all()


# =============================================================================
# STORY ARC OPERATIONS
# =============================================================================


def get_active_story_arcs(
    db: Session,
    playthrough_id: int
) -> List[models.StoryArc]:
    """Get currently active story arcs"""
    return db.query(models.StoryArc).filter(
        and_(
            models.StoryArc.playthrough_id == playthrough_id,
            models.StoryArc.is_active == 1
        )
    ).order_by(models.StoryArc.arc_order).all()


def activate_story_arc(
    db: Session,
    arc_id: int
) -> Optional[models.StoryArc]:
    """Activate a story arc"""
    arc = db.query(models.StoryArc).filter(
        models.StoryArc.id == arc_id
    ).first()

    if arc:
        arc.is_active = 1
        db.commit()

        log_edit(
            db,
            f"Activated story arc: {arc.arc_name}",
            "story",
            {"arc_id": arc_id}
        )

    return arc


def complete_story_arc(
    db: Session,
    arc_id: int
) -> Optional[models.StoryArc]:
    """Mark a story arc as completed"""
    arc = db.query(models.StoryArc).filter(
        models.StoryArc.id == arc_id
    ).first()

    if arc:
        arc.is_completed = 1
        arc.is_active = 0
        db.commit()

        log_edit(
            db,
            f"Completed story arc: {arc.arc_name}",
            "story",
            {"arc_id": arc_id}
        )

    return arc
