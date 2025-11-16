"""
Stories Router - Manage Stories and Playthroughs

Endpoints for:
1. Listing available stories
2. Creating new playthroughs
3. Managing sessions
4. Getting story/playthrough information
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud
from ..utils.logger import log_notification, log_error

router = APIRouter(prefix="/stories", tags=["stories"])


# =============================================================================
# STORY ENDPOINTS
# =============================================================================


@router.get("/", response_model=List[schemas.StoryListResponse])
async def list_stories(db: Session = Depends(get_db)):
    """
    Get list of all available stories

    This shows what stories the user can play
    """
    stories = crud.get_all_stories(db)

    log_notification(
        db,
        f"Listed all stories",
        "system",
        {"count": len(stories)}
    )

    return stories


@router.get("/{story_id}", response_model=schemas.StoryResponse)
async def get_story(story_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific story
    """
    story = crud.get_story(db, story_id)
    if not story:
        log_error(db, f"Story {story_id} not found", "system")
        raise HTTPException(status_code=404, detail="Story not found")

    log_notification(
        db,
        f"Retrieved story details",
        "system",
        {"story_id": story_id, "title": story.title}
    )

    return story


@router.post("/", response_model=schemas.StoryResponse)
async def create_story(story: schemas.StoryCreate, db: Session = Depends(get_db)):
    """
    Create a new story template

    Note: In production, stories would be pre-created or imported
    This endpoint is mainly for testing and development
    """
    db_story = crud.create_story(db, story)

    log_notification(
        db,
        f"Created new story: {story.title}",
        "database",
        {"story_id": db_story.id}
    )

    return db_story


# =============================================================================
# PLAYTHROUGH ENDPOINTS
# =============================================================================


@router.get("/{story_id}/playthroughs", response_model=List[schemas.PlaythroughListResponse])
async def list_playthroughs(story_id: int, db: Session = Depends(get_db)):
    """
    Get all playthroughs for a specific story

    Shows user's saved games for this story
    """
    story = crud.get_story(db, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    playthroughs = crud.get_playthroughs_for_story(db, story_id)

    log_notification(
        db,
        f"Listed playthroughs for story {story_id}",
        "system",
        {"count": len(playthroughs)}
    )

    return playthroughs


@router.post("/playthroughs", response_model=schemas.PlaythroughResponse)
async def create_playthrough(
    playthrough: schemas.PlaythroughCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new playthrough for a story

    This starts a new game/save for the user
    All template characters and relationships are copied to this playthrough
    """
    story = crud.get_story(db, playthrough.story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    db_playthrough = crud.create_playthrough(db, playthrough)

    log_notification(
        db,
        f"Created new playthrough: {playthrough.playthrough_name}",
        "database",
        {
            "playthrough_id": db_playthrough.id,
            "story_id": playthrough.story_id
        }
    )

    return db_playthrough


@router.get("/playthroughs/{playthrough_id}", response_model=schemas.PlaythroughResponse)
async def get_playthrough(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a playthrough
    """
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    log_notification(
        db,
        f"Retrieved playthrough details",
        "system",
        {"playthrough_id": playthrough_id}
    )

    return playthrough


# =============================================================================
# SESSION ENDPOINTS
# =============================================================================


@router.post("/sessions", response_model=schemas.SessionResponse)
async def create_session(
    session_data: schemas.SessionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new chat session for a playthrough

    Called when user starts or continues playing
    """
    playthrough = crud.get_playthrough(db, session_data.playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    db_session = crud.create_session(db, session_data)

    log_notification(
        db,
        f"Created new session for playthrough {session_data.playthrough_id}",
        "database",
        {"session_id": db_session.id}
    )

    return db_session


@router.get("/sessions/{session_id}", response_model=schemas.SessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """
    Get session information
    """
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.get("/playthroughs/{playthrough_id}/latest-session", response_model=schemas.SessionResponse)
async def get_latest_session(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Get the most recent session for a playthrough

    Useful for resuming a game
    """
    session = crud.get_latest_session(db, playthrough_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No sessions found for this playthrough"
        )

    return session


# =============================================================================
# CHARACTER ENDPOINTS
# =============================================================================


@router.get("/playthroughs/{playthrough_id}/characters", response_model=List[schemas.CharacterResponse])
async def get_playthrough_characters(
    playthrough_id: int,
    character_type: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all characters for a playthrough

    Optionally filter by character type (User, Main, Support, etc.)
    """
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    characters = crud.get_characters_for_playthrough(db, playthrough_id, character_type)

    log_notification(
        db,
        f"Retrieved characters for playthrough",
        "system",
        {
            "playthrough_id": playthrough_id,
            "count": len(characters),
            "type_filter": character_type
        }
    )

    return characters


@router.get("/characters/{character_id}", response_model=schemas.CharacterResponse)
async def get_character(character_id: int, db: Session = Depends(get_db)):
    """
    Get detailed character information
    """
    character = crud.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    return character


# =============================================================================
# RELATIONSHIP ENDPOINTS
# =============================================================================


@router.get("/playthroughs/{playthrough_id}/relationships", response_model=List[schemas.RelationshipResponse])
async def get_all_relationships(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Get all relationships for a playthrough
    """
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    # Get user character first
    user_char = crud.get_user_character(db, playthrough_id)
    if not user_char:
        return []

    relationships = crud.get_all_relationships_for_character(db, user_char.id, playthrough_id)

    log_notification(
        db,
        f"Retrieved relationships",
        "system",
        {"playthrough_id": playthrough_id, "count": len(relationships)}
    )

    return relationships


# =============================================================================
# STORY PROGRESS ENDPOINTS
# =============================================================================


@router.get("/playthroughs/{playthrough_id}/flags", response_model=List[schemas.StoryFlagResponse])
async def get_story_flags(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Get all story flags for a playthrough

    Shows story progression state
    """
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    flags = crud.get_story_flags(db, playthrough_id)

    return flags


@router.get("/playthroughs/{playthrough_id}/arcs", response_model=List[schemas.StoryArcResponse])
async def get_story_arcs(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Get all story arcs for a playthrough
    """
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    arcs = crud.get_active_story_arcs(db, playthrough_id)

    return arcs
