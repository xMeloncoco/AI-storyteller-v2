"""
Admin Router - Administrative and Test Data Functions

Handles:
- Test data loading
- Database management
- System administration
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List, Optional
import json

from ..database import get_db
from .. import models, schemas
from ..utils.logger import log_notification, log_error

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# TEST DATA LOADING
# =============================================================================


@router.get("/test-data/available")
async def get_available_test_data():
    """
    List all available test data files

    Returns information about JSON story files in the test_data directory
    """
    try:
        test_data_dir = Path(__file__).parent.parent.parent / "test_data"

        if not test_data_dir.exists():
            return {
                "available": [],
                "count": 0,
                "directory": str(test_data_dir),
                "error": "Test data directory not found"
            }

        # Find all JSON files (excluding template)
        json_files = []
        for json_file in test_data_dir.glob("*.json"):
            # Skip the template file
            if "TEMPLATE" in json_file.name:
                continue

            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                json_files.append({
                    "filename": json_file.name,
                    "title": data.get("title", "Unknown"),
                    "description": data.get("description", "No description"),
                    "path": str(json_file)
                })
            except Exception as e:
                json_files.append({
                    "filename": json_file.name,
                    "title": "Error loading file",
                    "description": str(e),
                    "path": str(json_file),
                    "error": True
                })

        return {
            "available": json_files,
            "count": len(json_files),
            "directory": str(test_data_dir)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning test data: {str(e)}")


@router.post("/test-data/load")
async def load_test_data(
    filename: Optional[str] = None,
    load_all: bool = False,
    db: Session = Depends(get_db)
):
    """
    Load test data from JSON files

    Parameters:
    - filename: Specific file to load (optional)
    - load_all: Load all available test data files (default: false)

    If neither is specified, returns list of available files
    """
    try:
        test_data_dir = Path(__file__).parent.parent.parent / "test_data"

        if not test_data_dir.exists():
            raise HTTPException(status_code=404, detail="Test data directory not found")

        # Determine which files to load
        files_to_load = []

        if load_all:
            files_to_load = [f for f in test_data_dir.glob("*.json") if "TEMPLATE" not in f.name]
        elif filename:
            file_path = test_data_dir / filename
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {filename}")
            files_to_load = [file_path]
        else:
            raise HTTPException(
                status_code=400,
                detail="Must specify filename or load_all=true"
            )

        if not files_to_load:
            raise HTTPException(status_code=404, detail="No test data files found")

        # Load each file
        loaded_stories = []
        errors = []

        for json_file in files_to_load:
            try:
                story_id = load_story_from_json(db, str(json_file))

                # Get story details
                story = db.query(models.Story).filter(models.Story.id == story_id).first()

                loaded_stories.append({
                    "filename": json_file.name,
                    "story_id": story_id,
                    "title": story.title if story else "Unknown"
                })

            except Exception as e:
                errors.append({
                    "filename": json_file.name,
                    "error": str(e)
                })

        # Get summary counts
        summary = {
            "loaded_stories": len(loaded_stories),
            "errors": len(errors),
            "total_characters": db.query(models.Character).filter(
                models.Character.playthrough_id.is_(None)
            ).count(),
            "total_relationships": db.query(models.Relationship).filter(
                models.Relationship.playthrough_id.is_(None)
            ).count(),
            "total_story_arcs": db.query(models.StoryArc).filter(
                models.StoryArc.playthrough_id.is_(None)
            ).count()
        }

        log_notification(
            db,
            f"Loaded {len(loaded_stories)} test stories",
            "database",
            summary
        )

        return {
            "status": "success",
            "loaded": loaded_stories,
            "errors": errors,
            "summary": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(db, f"Error loading test data: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error loading test data: {str(e)}")


def load_story_from_json(db: Session, json_path: str) -> int:
    """
    Load a complete story from a JSON file

    Creates:
    - Story
    - Character templates (playthrough_id = NULL)
    - Relationship templates (playthrough_id = NULL)
    - Location templates
    - Story arc templates

    Returns the story ID
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Check if story already exists
    existing = db.query(models.Story).filter(
        models.Story.title == data["title"]
    ).first()

    if existing:
        # Story already exists, return its ID
        return existing.id

    # Create the story
    story = models.Story(
        title=data["title"],
        description=data["description"],
        initial_message=data["initial_message"],
        initial_location=data.get("initial_location", ""),
        initial_time=data.get("initial_time", "")
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    # Create character templates (playthrough_id = NULL)
    char_id_map = {}  # Maps JSON character name to database ID

    for char_data in data.get("characters", []):
        # Convert lists to comma-separated strings if needed
        traits = char_data.get("personality_traits", [])
        if isinstance(traits, list):
            traits = ", ".join(traits)

        # Handle enhanced character fields
        core_values = char_data.get("core_values", [])
        if isinstance(core_values, list):
            core_values = json.dumps(core_values)

        core_fears = char_data.get("core_fears", [])
        if isinstance(core_fears, list):
            core_fears = json.dumps(core_fears)

        would_never_do = char_data.get("would_never_do", [])
        if isinstance(would_never_do, list):
            would_never_do = json.dumps(would_never_do)

        would_always_do = char_data.get("would_always_do", [])
        if isinstance(would_always_do, list):
            would_always_do = json.dumps(would_always_do)

        comfort_behaviors = char_data.get("comfort_behaviors", [])
        if isinstance(comfort_behaviors, list):
            comfort_behaviors = json.dumps(comfort_behaviors)

        verbal_patterns = char_data.get("verbal_patterns", {})
        if isinstance(verbal_patterns, dict):
            verbal_patterns = json.dumps(verbal_patterns)

        common_phrases = char_data.get("common_phrases", [])
        if isinstance(common_phrases, list):
            common_phrases = json.dumps(common_phrases)

        character = models.Character(
            story_id=story.id,
            playthrough_id=None,  # Template!
            character_type=char_data["type"],
            character_name=char_data["name"],
            appearance=char_data.get("appearance", ""),
            age=char_data.get("age"),
            backstory=char_data.get("backstory", ""),
            personality_traits=traits,
            speech_patterns=char_data.get("speech_patterns", ""),
            # Enhanced fields
            core_values=core_values,
            core_fears=core_fears,
            would_never_do=would_never_do,
            would_always_do=would_always_do,
            comfort_behaviors=comfort_behaviors,
            verbal_patterns=verbal_patterns,
            sentence_structure=char_data.get("sentence_structure"),
            common_phrases=common_phrases,
            decision_style=char_data.get("decision_style"),
            internal_contradiction=char_data.get("internal_contradiction"),
            secret_kept=char_data.get("secret_kept"),
            vulnerability=char_data.get("vulnerability")
        )
        db.add(character)
        db.commit()
        db.refresh(character)

        char_id_map[char_data["name"]] = character.id

    # Create location templates
    for loc_data in data.get("locations", []):
        location = models.Location(
            story_id=story.id,
            playthrough_id=None,  # Template!
            location_name=loc_data["name"],
            description=loc_data.get("description", ""),
            location_type=loc_data.get("type", "indoor"),
            location_scope=loc_data.get("scope", "room")
        )
        db.add(location)

    db.commit()

    # Create relationship templates
    for rel_data in data.get("relationships", []):
        # Find character IDs
        char1_name = rel_data.get("entity1") or rel_data.get("character1")
        char2_name = rel_data.get("entity2") or rel_data.get("character2")

        if char1_name not in char_id_map or char2_name not in char_id_map:
            continue

        relationship = models.Relationship(
            story_id=story.id,
            playthrough_id=None,  # Template!
            entity1_type="character",
            entity1_id=char_id_map[char1_name],
            entity2_type="character",
            entity2_id=char_id_map[char2_name],
            relationship_type=rel_data.get("type", "acquaintances"),
            first_meeting_context=rel_data.get("first_meeting", ""),
            trust=rel_data.get("trust", 0.5),
            affection=rel_data.get("affection", 0.5),
            familiarity=rel_data.get("familiarity", 0.0),
            history_summary=rel_data.get("history", "")
        )
        db.add(relationship)

    db.commit()

    # Create story arc templates
    for arc_data in data.get("story_arcs", []):
        arc = models.StoryArc(
            story_id=story.id,
            playthrough_id=None,  # Template!
            arc_name=arc_data["name"],
            description=arc_data.get("description", ""),
            start_condition=json.dumps(arc_data.get("start_condition", {})),
            completion_condition=json.dumps(arc_data.get("completion_condition", {})),
            is_active=arc_data.get("is_active", 0),
            is_completed=0,
            arc_order=arc_data.get("order", 0)
        )
        db.add(arc)

    db.commit()

    return story.id


@router.delete("/test-data/clear")
async def clear_test_data(db: Session = Depends(get_db)):
    """
    Clear all template data (stories without playthroughs)

    WARNING: This removes all stories that don't have active playthroughs
    """
    try:
        # Get all stories
        stories = db.query(models.Story).all()

        deleted_count = 0
        kept_count = 0

        for story in stories:
            # Check if story has any playthroughs
            has_playthroughs = db.query(models.Playthrough).filter(
                models.Playthrough.story_id == story.id
            ).count() > 0

            if not has_playthroughs:
                # Delete all related template data
                db.query(models.Character).filter(
                    models.Character.story_id == story.id,
                    models.Character.playthrough_id.is_(None)
                ).delete()

                db.query(models.Relationship).filter(
                    models.Relationship.story_id == story.id,
                    models.Relationship.playthrough_id.is_(None)
                ).delete()

                db.query(models.Location).filter(
                    models.Location.story_id == story.id,
                    models.Location.playthrough_id.is_(None)
                ).delete()

                db.query(models.StoryArc).filter(
                    models.StoryArc.story_id == story.id,
                    models.StoryArc.playthrough_id.is_(None)
                ).delete()

                db.delete(story)
                deleted_count += 1
            else:
                kept_count += 1

        db.commit()

        log_notification(
            db,
            f"Cleared {deleted_count} template stories (kept {kept_count} with playthroughs)",
            "database"
        )

        return {
            "status": "success",
            "deleted": deleted_count,
            "kept": kept_count,
            "message": f"Removed {deleted_count} stories without playthroughs"
        }

    except Exception as e:
        db.rollback()
        log_error(db, f"Error clearing test data: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error clearing test data: {str(e)}")


# =============================================================================
# TESTER / DEBUG ENDPOINTS
# =============================================================================


@router.get("/tester/playthrough/{playthrough_id}")
async def get_playthrough_data(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Get complete playthrough data for testing/debugging

    Returns all data associated with a playthrough:
    - Playthrough info
    - All characters with full details
    - All relationships
    - All locations
    - All story arcs
    - All story flags
    - All memory flags
    - Current scene state
    - Sessions and recent conversations
    """
    try:
        # Get playthrough
        playthrough = db.query(models.Playthrough).filter(
            models.Playthrough.id == playthrough_id
        ).first()

        if not playthrough:
            raise HTTPException(status_code=404, detail="Playthrough not found")

        # Get story info
        story = db.query(models.Story).filter(
            models.Story.id == playthrough.story_id
        ).first()

        # Get all characters for this playthrough
        characters = db.query(models.Character).filter(
            models.Character.playthrough_id == playthrough_id
        ).all()

        characters_data = []
        for char in characters:
            char_dict = {
                "id": char.id,
                "name": char.character_name,
                "type": char.character_type,
                "age": char.age,
                "appearance": char.appearance,
                "backstory": char.backstory,
                "personality_traits": char.personality_traits,
                "speech_patterns": char.speech_patterns,
                "core_values": char.core_values,
                "core_fears": char.core_fears,
                "would_never_do": char.would_never_do,
                "would_always_do": char.would_always_do,
                "comfort_behaviors": char.comfort_behaviors,
                "verbal_patterns": char.verbal_patterns,
                "sentence_structure": char.sentence_structure,
                "common_phrases": char.common_phrases,
                "decision_style": char.decision_style,
                "internal_contradiction": char.internal_contradiction,
                "secret_kept": char.secret_kept,
                "vulnerability": char.vulnerability
            }
            characters_data.append(char_dict)

        # Get all relationships
        relationships = db.query(models.Relationship).filter(
            models.Relationship.playthrough_id == playthrough_id
        ).all()

        relationships_data = []
        for rel in relationships:
            # Get character names
            char1 = db.query(models.Character).filter(models.Character.id == rel.entity1_id).first()
            char2 = db.query(models.Character).filter(models.Character.id == rel.entity2_id).first()

            rel_dict = {
                "id": rel.id,
                "character1": char1.character_name if char1 else "Unknown",
                "character2": char2.character_name if char2 else "Unknown",
                "type": rel.relationship_type,
                "trust": rel.trust,
                "affection": rel.affection,
                "familiarity": rel.familiarity,
                "closeness": rel.closeness,
                "importance": rel.importance,
                "history": rel.history_summary,
                "first_meeting": rel.first_meeting_context,
                "last_interaction": rel.last_interaction
            }
            relationships_data.append(rel_dict)

        # Get all locations
        locations = db.query(models.Location).filter(
            models.Location.playthrough_id == playthrough_id
        ).all()

        locations_data = [{
            "id": loc.id,
            "name": loc.location_name,
            "description": loc.description,
            "type": loc.location_type,
            "scope": loc.location_scope
        } for loc in locations]

        # Get all story arcs
        story_arcs = db.query(models.StoryArc).filter(
            models.StoryArc.playthrough_id == playthrough_id
        ).all()

        arcs_data = [{
            "id": arc.id,
            "name": arc.arc_name,
            "description": arc.description,
            "order": arc.arc_order,
            "is_active": bool(arc.is_active),
            "is_completed": bool(arc.is_completed),
            "start_condition": arc.start_condition,
            "completion_condition": arc.completion_condition
        } for arc in story_arcs]

        # Get story flags
        story_flags = db.query(models.StoryFlag).filter(
            models.StoryFlag.playthrough_id == playthrough_id
        ).all()

        flags_data = [{
            "id": flag.id,
            "flag_name": flag.flag_name,
            "flag_value": flag.flag_value,
            "set_at": flag.set_at.isoformat() if flag.set_at else None
        } for flag in story_flags]

        # Get memory flags
        memory_flags = db.query(models.MemoryFlag).filter(
            models.MemoryFlag.playthrough_id == playthrough_id
        ).all()

        memory_data = [{
            "id": mem.id,
            "flag_name": mem.flag_name,
            "flag_value": mem.flag_value,
            "description": mem.description,
            "importance": mem.importance
        } for mem in memory_flags]

        # Get sessions
        sessions = db.query(models.Session).filter(
            models.Session.playthrough_id == playthrough_id
        ).order_by(models.Session.created_at.desc()).limit(10).all()

        sessions_data = [{
            "id": session.id,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "conversation_count": db.query(models.Conversation).filter(
                models.Conversation.session_id == session.id
            ).count()
        } for session in sessions]

        # Get current scene state (from most recent session)
        scene_state = None
        if sessions:
            latest_session = sessions[0]
            scene = db.query(models.SceneState).filter(
                models.SceneState.session_id == latest_session.id
            ).order_by(models.SceneState.created_at.desc()).first()

            if scene:
                scene_state = {
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "weather": scene.weather,
                    "emotional_tone": scene.emotional_tone,
                    "scene_context": scene.scene_context,
                    "characters_present": scene.characters_present
                }

        return {
            "playthrough": {
                "id": playthrough.id,
                "name": playthrough.playthrough_name,
                "story_id": playthrough.story_id,
                "story_title": story.title if story else "Unknown",
                "created_at": playthrough.created_at.isoformat() if playthrough.created_at else None,
                "last_played": playthrough.last_played.isoformat() if playthrough.last_played else None,
                "current_location": playthrough.current_location,
                "current_time": playthrough.current_time
            },
            "characters": characters_data,
            "relationships": relationships_data,
            "locations": locations_data,
            "story_arcs": arcs_data,
            "story_flags": flags_data,
            "memory_flags": memory_data,
            "sessions": sessions_data,
            "current_scene": scene_state
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(db, f"Error getting playthrough data: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error getting playthrough data: {str(e)}")


@router.get("/tester/context/{session_id}")
async def get_context_window(session_id: int, db: Session = Depends(get_db)):
    """
    Get the current context window that would be sent to the AI

    This shows exactly what context the AI sees when generating responses
    """
    try:
        from ..ai.context_builder import ContextBuilder

        # Validate session exists
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Build context
        context_builder = ContextBuilder(db, session_id)
        full_context = context_builder.build_full_context()

        # Get conversation history for this session
        conversations = db.query(models.Conversation).filter(
            models.Conversation.session_id == session_id
        ).order_by(models.Conversation.created_at.desc()).limit(20).all()

        conversation_history = [{
            "id": conv.id,
            "speaker_type": conv.speaker_type,
            "speaker_name": conv.speaker_name,
            "message": conv.message,
            "created_at": conv.created_at.isoformat() if conv.created_at else None
        } for conv in reversed(conversations)]

        return {
            "session_id": session_id,
            "full_context": full_context,
            "context_length": len(full_context),
            "conversation_history": conversation_history,
            "metadata": {
                "playthrough_id": session.playthrough_id,
                "max_context_messages": 20
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(db, f"Error getting context window: {str(e)}", "system")
        raise HTTPException(status_code=500, detail=f"Error getting context window: {str(e)}")


@router.delete("/tester/playthrough/{playthrough_id}/reset")
async def reset_playthrough(playthrough_id: int, db: Session = Depends(get_db)):
    """
    Reset a playthrough to its initial state

    WARNING: This deletes all progress:
    - All sessions
    - All conversations
    - All scene states
    - All story flags
    - All memory flags
    - Resets characters and relationships to template state
    - Resets story arcs to initial state
    """
    try:
        # Get playthrough
        playthrough = db.query(models.Playthrough).filter(
            models.Playthrough.id == playthrough_id
        ).first()

        if not playthrough:
            raise HTTPException(status_code=404, detail="Playthrough not found")

        story_id = playthrough.story_id

        # Delete all sessions and their conversations
        sessions = db.query(models.Session).filter(
            models.Session.playthrough_id == playthrough_id
        ).all()

        for session in sessions:
            # Delete conversations
            db.query(models.Conversation).filter(
                models.Conversation.session_id == session.id
            ).delete()

            # Delete scene states
            db.query(models.SceneState).filter(
                models.SceneState.session_id == session.id
            ).delete()

            # Delete scene characters
            db.query(models.SceneCharacter).filter(
                models.SceneCharacter.session_id == session.id
            ).delete()

        # Delete sessions
        db.query(models.Session).filter(
            models.Session.playthrough_id == playthrough_id
        ).delete()

        # Delete story flags
        db.query(models.StoryFlag).filter(
            models.StoryFlag.playthrough_id == playthrough_id
        ).delete()

        # Delete memory flags
        db.query(models.MemoryFlag).filter(
            models.MemoryFlag.playthrough_id == playthrough_id
        ).delete()

        # Delete playthrough-specific characters
        db.query(models.Character).filter(
            models.Character.playthrough_id == playthrough_id
        ).delete()

        # Delete playthrough-specific relationships
        db.query(models.Relationship).filter(
            models.Relationship.playthrough_id == playthrough_id
        ).delete()

        # Delete playthrough-specific locations
        db.query(models.Location).filter(
            models.Location.playthrough_id == playthrough_id
        ).delete()

        # Delete playthrough-specific story arcs
        db.query(models.StoryArc).filter(
            models.StoryArc.playthrough_id == playthrough_id
        ).delete()

        # Reset playthrough to initial state
        story = db.query(models.Story).filter(models.Story.id == story_id).first()
        if story:
            playthrough.current_location = story.initial_location
            playthrough.current_time = story.initial_time

        db.commit()

        log_notification(
            db,
            f"Reset playthrough {playthrough_id} to initial state",
            "database",
            {"playthrough_id": playthrough_id}
        )

        return {
            "status": "success",
            "message": f"Playthrough {playthrough_id} has been reset to initial state",
            "playthrough_id": playthrough_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_error(db, f"Error resetting playthrough: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error resetting playthrough: {str(e)}")


@router.get("/tester/logs/{session_id}")
async def get_session_logs_grouped(
    session_id: int,
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get logs for a session, grouped by conversation turn

    Groups all logs that happened during each user response
    """
    try:
        # Get session
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get all conversations for this session
        conversations = db.query(models.Conversation).filter(
            models.Conversation.session_id == session_id
        ).order_by(models.Conversation.created_at).all()

        # Get all logs for this session
        logs = db.query(models.Log).filter(
            models.Log.session_id == session_id
        ).order_by(models.Log.created_at).limit(limit).all()

        # Group logs by conversation turn
        grouped_logs = []
        current_group = None

        for conv in conversations:
            if conv.speaker_type == "user":
                # Start new group
                if current_group:
                    grouped_logs.append(current_group)

                current_group = {
                    "user_message": conv.message,
                    "timestamp": conv.created_at.isoformat() if conv.created_at else None,
                    "logs": [],
                    "ai_response": None
                }
            elif conv.speaker_type == "narrator" and current_group:
                current_group["ai_response"] = conv.message

        # Add last group if exists
        if current_group:
            grouped_logs.append(current_group)

        # Assign logs to appropriate groups
        for log in logs:
            # Find the appropriate group based on timestamp
            for group in grouped_logs:
                if log.created_at and group["timestamp"]:
                    if log.created_at.isoformat() >= group["timestamp"]:
                        group["logs"].append({
                            "type": log.log_type,
                            "category": log.log_category,
                            "message": log.log_message,
                            "timestamp": log.created_at.isoformat() if log.created_at else None,
                            "metadata": log.metadata
                        })

        return {
            "session_id": session_id,
            "playthrough_id": session.playthrough_id,
            "grouped_logs": grouped_logs,
            "total_conversations": len(conversations),
            "total_logs": len(logs)
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(db, f"Error getting grouped logs: {str(e)}", "system")
        raise HTTPException(status_code=500, detail=f"Error getting grouped logs: {str(e)}")
