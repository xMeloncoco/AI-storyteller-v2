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
