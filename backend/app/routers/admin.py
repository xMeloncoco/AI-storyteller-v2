"""
Admin Router - Administrative and Test Data Functions

Handles:
- Test data loading
- Database management
- System administration
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import DateTime, Date
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List, Optional
from datetime import datetime, date
import json
import re

from ..database import get_db
from .. import models, schemas
from ..config import settings
from ..utils.logger import log_notification, log_error
from ..ai.model_config import (
    model_registry,
    provider_status,
    provider_connection,
    TASKS,
    TASK_LABELS,
    PROVIDER_TYPES,
)
from ..ai.llm_manager import probe_task

import httpx

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# VALIDATION MODE
# =============================================================================

VALID_MODES = {"warn", "block", "repair"}


@router.get("/validation-mode")
async def get_validation_mode():
    """Return the current runtime validation mode."""
    return {"validation_mode": settings.validation_mode}


@router.patch("/validation-mode")
async def set_validation_mode(body: dict, db: Session = Depends(get_db)):
    """Change the runtime validation mode (warn / block / repair)."""
    mode = body.get("validation_mode", "")
    if mode not in VALID_MODES:
        raise HTTPException(status_code=422, detail=f"Invalid mode '{mode}'. Must be one of: {sorted(VALID_MODES)}")
    settings.validation_mode = mode
    log_notification(db, f"Validation mode set to: {mode}", "system")
    return {"validation_mode": settings.validation_mode}


# =============================================================================
# AI MODEL CONFIGURATION (per-task provider/model assignment)
# =============================================================================


@router.get("/models/config")
async def get_models_config():
    """Return per-task model assignments plus available providers."""
    return {
        "tasks": [
            {"task": t, "label": TASK_LABELS.get(t, t), **model_registry.get_task(t)}
            for t in TASKS
        ],
        "providers": provider_status(),
    }


@router.patch("/models/config")
async def set_model_config(body: dict, db: Session = Depends(get_db)):
    """Update one task's provider/model/max_tokens assignment."""
    task = body.get("task")
    if task not in TASKS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown task '{task}'. Must be one of: {TASKS}",
        )

    provider = body.get("provider")
    if provider is not None and provider not in PROVIDER_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown provider '{provider}'. Must be one of: {sorted(PROVIDER_TYPES)}",
        )

    max_tokens = body.get("max_tokens")
    if max_tokens is not None:
        try:
            max_tokens = int(max_tokens)
            if max_tokens <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="max_tokens must be a positive integer")

    cfg = model_registry.set_task(
        task,
        provider=provider,
        model=body.get("model"),
        max_tokens=max_tokens,
    )
    log_notification(db, f"Task '{task}' set to {cfg['provider']}/{cfg['model']}", "system")
    return {"task": task, "label": TASK_LABELS.get(task, task), **cfg}


@router.post("/models/test")
async def test_models(db: Session = Depends(get_db)):
    """
    Test each task's assigned provider/model with a tiny prompt.

    Tasks sharing the same (provider, model) are probed once and the result is
    reused, so this fires at most one request per distinct model.
    """
    results = {}
    seen = {}
    for task in TASKS:
        cfg = model_registry.get_task(task)
        key = (cfg["provider"], cfg["model"])
        if key not in seen:
            seen[key] = await probe_task(db, task)
        results[task] = {"label": TASK_LABELS.get(task, task), **seen[key]}
    return {"results": results}


@router.get("/models/ollama-tags")
async def get_ollama_tags():
    """List models available in the local Ollama install (best-effort)."""
    conn = provider_connection("ollama")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{conn['base_url']}/api/tags")
            resp.raise_for_status()
            data = resp.json()
        models_list = [m.get("name") for m in data.get("models", []) if m.get("name")]
        return {"available": True, "models": models_list}
    except Exception as e:
        return {"available": False, "models": [], "error": str(e)[:200]}


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
                with open(json_file, 'r', encoding='utf-8') as f:
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
        loaded_fixtures = []
        errors = []

        for json_file in files_to_load:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                if isinstance(raw, dict) and raw.get("kind") == "playthrough_fixture":
                    result = _load_playthrough_fixture(db, raw)
                    loaded_fixtures.append({
                        "filename": json_file.name,
                        **result,
                    })
                else:
                    story_id = load_story_from_json(db, str(json_file))
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
            "loaded_fixtures": len(loaded_fixtures),
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
            f"Loaded {len(loaded_stories)} stories and {len(loaded_fixtures)} fixtures",
            "database",
            summary
        )

        # Surface fixtures in `loaded` so existing UI shows them too.
        loaded_combined = list(loaded_stories) + [
            {"filename": f["filename"],
             "story_id": f["story_id"],
             "title": f"{f['story_title']} — {f['playthrough_name']}",
             "kind": "playthrough_fixture",
             "playthrough_id": f["playthrough_id"]}
            for f in loaded_fixtures
        ]

        return {
            "status": "success",
            "loaded": loaded_combined,
            "loaded_fixtures": loaded_fixtures,
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
    with open(json_path, 'r', encoding='utf-8') as f:
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


_PLAYTHROUGH_SCOPED_MODELS = (
    # Conversation/scene rows first (leaves), then their parents, then the
    # rest. Each model has a playthrough_id column we can filter on directly,
    # so no session_id detour is needed.
    models.Conversation,
    models.SceneCharacter,
    models.SceneState,
    models.MemoryFlag,
    models.CharacterKnowledge,
    models.CharacterState,
    models.CharacterGoal,
    models.CharacterMemory,
    models.CharacterBelief,
    models.CharacterAvoidance,
    models.StoryFlag,
    models.StoryEpisode,
    models.StoryArc,
    models.Relationship,
    models.Location,
    models.Character,
    models.Session,
)


def _delete_playthrough_cascade(db: Session, playthrough_id: int) -> None:
    """Delete a playthrough and every playthrough-scoped row that references it."""
    for model in _PLAYTHROUGH_SCOPED_MODELS:
        db.query(model).filter(
            model.playthrough_id == playthrough_id
        ).delete(synchronize_session=False)
    db.query(models.Playthrough).filter(
        models.Playthrough.id == playthrough_id
    ).delete(synchronize_session=False)


@router.delete("/playthroughs/all")
async def delete_all_playthroughs(db: Session = Depends(get_db)):
    """
    Delete every playthrough and all of its sessions, conversations,
    scene state, flags, and playthrough-scoped characters/relationships/
    locations/story arcs. Stories and template data are kept intact.
    """
    try:
        playthrough_ids = [pid for (pid,) in db.query(models.Playthrough.id).all()]

        for pid in playthrough_ids:
            _delete_playthrough_cascade(db, pid)

        db.commit()

        log_notification(
            db,
            f"Deleted {len(playthrough_ids)} playthroughs",
            "database",
            {"deleted_playthroughs": len(playthrough_ids)}
        )

        return {
            "status": "success",
            "deleted_playthroughs": len(playthrough_ids)
        }

    except Exception as e:
        db.rollback()
        log_error(db, f"Error deleting playthroughs: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error deleting playthroughs: {str(e)}")


@router.delete("/all")
async def delete_all_stories_and_playthroughs(db: Session = Depends(get_db)):
    """
    Nuke everything: every playthrough (with cascade) and every story
    (with its template characters/relationships/locations/arcs).
    Leaves the schema in place but empty.
    """
    try:
        playthrough_ids = [pid for (pid,) in db.query(models.Playthrough.id).all()]
        for pid in playthrough_ids:
            _delete_playthrough_cascade(db, pid)

        story_ids = [sid for (sid,) in db.query(models.Story.id).all()]

        if story_ids:
            db.query(models.Character).filter(
                models.Character.story_id.in_(story_ids),
                models.Character.playthrough_id.is_(None)
            ).delete(synchronize_session=False)
            db.query(models.Relationship).filter(
                models.Relationship.story_id.in_(story_ids),
                models.Relationship.playthrough_id.is_(None)
            ).delete(synchronize_session=False)
            db.query(models.Location).filter(
                models.Location.story_id.in_(story_ids),
                models.Location.playthrough_id.is_(None)
            ).delete(synchronize_session=False)
            db.query(models.StoryArc).filter(
                models.StoryArc.story_id.in_(story_ids),
                models.StoryArc.playthrough_id.is_(None)
            ).delete(synchronize_session=False)

        deleted_stories = db.query(models.Story).delete(synchronize_session=False)

        db.commit()

        log_notification(
            db,
            f"Deleted everything: {len(playthrough_ids)} playthroughs, {deleted_stories} stories",
            "database",
            {
                "deleted_playthroughs": len(playthrough_ids),
                "deleted_stories": deleted_stories
            }
        )

        return {
            "status": "success",
            "deleted_playthroughs": len(playthrough_ids),
            "deleted_stories": deleted_stories
        }

    except Exception as e:
        db.rollback()
        log_error(db, f"Error deleting all data: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error deleting all data: {str(e)}")


# =============================================================================
# PLAYTHROUGH EXPORT (fixture authoring)
# =============================================================================

EXPORT_FORMAT_VERSION = 1


def _row_to_dict(row, exclude: Optional[set] = None) -> dict:
    """Serialize a SQLAlchemy row by introspecting its columns. Datetimes go to
    ISO strings; everything else is left as-is."""
    exclude = exclude or set()
    out = {}
    for col in row.__table__.columns:
        if col.name in exclude:
            continue
        value = getattr(row, col.name)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        out[col.name] = value
    return out


def _safe_filename(text: str) -> str:
    """Turn a playthrough name into a filesystem-safe filename slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", text or "playthrough").strip("_")
    return slug.lower() or "playthrough"


def _export_playthrough(db: Session, playthrough_id: int) -> dict:
    """Build the full fixture dict for a playthrough.

    Includes the story + every template row (characters/relationships/
    locations/story_arcs/episodes with playthrough_id IS NULL) plus the
    playthrough itself with every playthrough-scoped row and every session's
    conversations, scene_states, and scene_characters.

    Character references in playthrough-scoped tables get a sidecar
    `_character_name` so the future loader can remap IDs without depending
    on the export's original primary keys.
    """
    playthrough = db.query(models.Playthrough).filter(
        models.Playthrough.id == playthrough_id
    ).first()
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    story = db.query(models.Story).filter(models.Story.id == playthrough.story_id).first()
    if not story:
        raise HTTPException(status_code=500, detail="Story for playthrough is missing")

    story_id = story.id

    char_name_by_id: dict[int, str] = {
        cid: name for (cid, name) in db.query(
            models.Character.id, models.Character.character_name
        ).filter(models.Character.story_id == story_id).all()
    }
    loc_name_by_id: dict[int, str] = {
        lid: name for (lid, name) in db.query(
            models.Location.id, models.Location.location_name
        ).filter(models.Location.story_id == story_id).all()
    }

    def name_for_character(cid):
        return char_name_by_id.get(cid) if cid is not None else None

    def name_for_location(lid):
        return loc_name_by_id.get(lid) if lid is not None else None

    def by_story_template(model):
        return db.query(model).filter(
            model.story_id == story_id,
            model.playthrough_id.is_(None)
        ).all()

    def by_playthrough(model):
        return db.query(model).filter(
            model.playthrough_id == playthrough_id
        ).all()

    def story_episodes_template():
        # StoryEpisode is attached via arc_id, not story_id directly.
        return db.query(models.StoryEpisode).join(
            models.StoryArc, models.StoryEpisode.arc_id == models.StoryArc.id
        ).filter(
            models.StoryArc.story_id == story_id,
            models.StoryEpisode.playthrough_id.is_(None)
        ).all()

    def dump_character(c):
        d = _row_to_dict(c)
        if c.template_character_id is not None:
            d["_template_character_name"] = name_for_character(c.template_character_id)
        return d

    def dump_relationship(r):
        d = _row_to_dict(r)
        d["_entity1_name"] = name_for_character(r.entity1_id)
        d["_entity2_name"] = name_for_character(r.entity2_id)
        return d

    def dump_with_character_name(row):
        d = _row_to_dict(row)
        d["_character_name"] = name_for_character(getattr(row, "character_id", None))
        return d

    def dump_memory(m):
        d = _row_to_dict(m)
        d["_character_name"] = name_for_character(getattr(m, "character_id", None))
        if getattr(m, "location_id", None) is not None:
            d["_location_name"] = name_for_location(m.location_id)
        return d

    def dump_episode(e):
        d = _row_to_dict(e)
        arc = db.query(models.StoryArc).filter(models.StoryArc.id == e.arc_id).first()
        d["_arc_name"] = arc.arc_name if arc else None
        return d

    # Story templates (playthrough_id IS NULL for the relevant tables)
    templates = {
        "characters": [dump_character(c) for c in by_story_template(models.Character)],
        "locations": [_row_to_dict(l) for l in by_story_template(models.Location)],
        "relationships": [dump_relationship(r) for r in by_story_template(models.Relationship)],
        "story_arcs": [_row_to_dict(a) for a in by_story_template(models.StoryArc)],
        "story_episodes": [dump_episode(e) for e in story_episodes_template()],
    }

    # Playthrough-scoped state
    playthrough_data = _row_to_dict(playthrough)
    playthrough_data.update({
        "characters": [dump_character(c) for c in by_playthrough(models.Character)],
        "locations": [_row_to_dict(l) for l in by_playthrough(models.Location)],
        "relationships": [dump_relationship(r) for r in by_playthrough(models.Relationship)],
        "story_arcs": [_row_to_dict(a) for a in by_playthrough(models.StoryArc)],
        "story_episodes": [dump_episode(e) for e in by_playthrough(models.StoryEpisode)],
        "story_flags": [_row_to_dict(f) for f in by_playthrough(models.StoryFlag)],
        "memory_flags": [_row_to_dict(m) for m in by_playthrough(models.MemoryFlag)],
        "character_knowledge": [dump_with_character_name(k) for k in by_playthrough(models.CharacterKnowledge)],
        "character_states": [dump_with_character_name(s) for s in by_playthrough(models.CharacterState)],
        "character_goals": [dump_with_character_name(g) for g in by_playthrough(models.CharacterGoal)],
        "character_memories": [dump_memory(m) for m in by_playthrough(models.CharacterMemory)],
        "character_beliefs": [dump_with_character_name(b) for b in by_playthrough(models.CharacterBelief)],
        "character_avoidances": [dump_with_character_name(a) for a in by_playthrough(models.CharacterAvoidance)],
        "sessions": [],
    })

    sessions = db.query(models.Session).filter(
        models.Session.playthrough_id == playthrough_id
    ).order_by(models.Session.started_at).all()

    for session in sessions:
        session_dict = _row_to_dict(session)
        session_dict["_user_character_name"] = name_for_character(session.user_character_id)

        session_dict["conversations"] = [
            _row_to_dict(c) for c in db.query(models.Conversation).filter(
                models.Conversation.session_id == session.id
            ).order_by(models.Conversation.timestamp).all()
        ]

        scene_states_rows = db.query(models.SceneState).filter(
            models.SceneState.session_id == session.id
        ).order_by(models.SceneState.created_at).all()

        scene_states_out = []
        for scene in scene_states_rows:
            scene_dict = _row_to_dict(scene)
            scene_dict["characters_in_scene"] = [
                dump_with_character_name(sc) for sc in db.query(models.SceneCharacter).filter(
                    models.SceneCharacter.scene_state_id == scene.id
                ).all()
            ]
            scene_states_out.append(scene_dict)

        session_dict["scene_states"] = scene_states_out
        playthrough_data["sessions"].append(session_dict)

    return {
        "format_version": EXPORT_FORMAT_VERSION,
        "kind": "playthrough_fixture",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "title": story.title,
        "description": story.description,
        "story": _row_to_dict(story),
        "templates": templates,
        "playthrough": playthrough_data,
    }


@router.get("/playthroughs/{playthrough_id}/export")
async def preview_playthrough_export(playthrough_id: int, db: Session = Depends(get_db)):
    """Return the export JSON without writing to disk (for inspection)."""
    return _export_playthrough(db, playthrough_id)


@router.post("/playthroughs/{playthrough_id}/export")
async def export_playthrough_to_file(
    playthrough_id: int,
    filename: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export a playthrough to a JSON file in backend/test_data/.

    If `filename` is not supplied, one is generated from the story title
    and playthrough name. Existing files are overwritten.
    """
    try:
        data = _export_playthrough(db, playthrough_id)

        test_data_dir = Path(__file__).parent.parent.parent / "test_data"
        test_data_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            slug = f"{_safe_filename(data['title'])}__{_safe_filename(data['playthrough'].get('playthrough_name', ''))}.json"
            filename = slug
        elif not filename.endswith(".json"):
            filename = f"{filename}.json"

        out_path = test_data_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        log_notification(
            db,
            f"Exported playthrough {playthrough_id} to {filename}",
            "database",
            {"playthrough_id": playthrough_id, "filename": filename}
        )

        return {
            "status": "success",
            "filename": filename,
            "path": str(out_path),
            "bytes": out_path.stat().st_size,
            "summary": {
                "templates": {k: len(v) for k, v in data["templates"].items()},
                "playthrough_characters": len(data["playthrough"]["characters"]),
                "sessions": len(data["playthrough"]["sessions"]),
                "conversations": sum(len(s["conversations"]) for s in data["playthrough"]["sessions"]),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(db, f"Error exporting playthrough: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Error exporting playthrough: {str(e)}")


# =============================================================================
# PLAYTHROUGH FIXTURE LOADER
# =============================================================================


def _parse_dt(value):
    """Parse an ISO datetime string back to a datetime. Accepts trailing 'Z'."""
    if value is None or isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _model_kwargs(model, row_dict: dict, fk_overrides: dict, drop: set = None) -> dict:
    """Build constructor kwargs for `model` from an exported `row_dict`.

    - Drops the `id` column (DB assigns a fresh one) and any keys in `drop`.
    - Skips sidecar keys (anything starting with `_`).
    - Applies `fk_overrides` for any foreign keys we've already remapped.
    - Parses ISO datetime strings into datetimes for DateTime/Date columns.
    """
    drop = drop or set()
    kwargs = {}
    for col in model.__table__.columns:
        name = col.name
        if name == "id" or name in drop:
            continue
        if name in fk_overrides:
            kwargs[name] = fk_overrides[name]
            continue
        if name not in row_dict:
            continue
        value = row_dict[name]
        if isinstance(col.type, (DateTime, Date)) and isinstance(value, str):
            parsed = _parse_dt(value)
            if parsed is not None:
                value = parsed
        kwargs[name] = value
    return kwargs


def _load_playthrough_fixture(db: Session, data: dict) -> dict:
    """Import a fixture produced by the exporter.

    Strategy:
    - Reuse an existing story by title if present; otherwise create it and
      its template rows from the `templates` section.
    - Always create a new playthrough (fixtures are meant to be re-runnable).
    - Resolve character/location references via `_character_name`,
      `_entity*_name`, `_user_character_name`, `_location_name` sidecars
      so old IDs in the JSON are never trusted.
    """
    story_data = data.get("story") or {}
    templates = data.get("templates") or {}
    pt_data = data.get("playthrough") or {}

    if not story_data.get("title"):
        raise ValueError("Fixture missing story.title")
    if not pt_data:
        raise ValueError("Fixture missing playthrough section")

    # ----- 1. Story (reuse by title or create fresh) -----
    story = db.query(models.Story).filter(
        models.Story.title == story_data["title"]
    ).first()
    story_is_new = False

    if not story:
        story = models.Story(**_model_kwargs(models.Story, story_data, fk_overrides={}))
        db.add(story)
        db.commit()
        db.refresh(story)
        story_is_new = True

    # When the story already exists, look up its template character names so
    # instance characters can still resolve `_template_character_name` to an id.
    template_char_id_by_name: dict[str, int] = {}
    template_loc_id_by_name: dict[str, int] = {}
    template_arc_id_by_name: dict[str, int] = {}

    if story_is_new:
        # Templates first: characters, locations, arcs, then relationships
        # (relationships reference character ids).
        for ct in templates.get("characters", []):
            row = models.Character(**_model_kwargs(
                models.Character, ct,
                fk_overrides={"story_id": story.id, "playthrough_id": None,
                              "template_character_id": None},
            ))
            db.add(row)
            db.commit()
            db.refresh(row)
            template_char_id_by_name[row.character_name] = row.id

        for lt in templates.get("locations", []):
            row = models.Location(**_model_kwargs(
                models.Location, lt,
                fk_overrides={"story_id": story.id, "playthrough_id": None,
                              "parent_location_id": None},
            ))
            db.add(row)
            db.commit()
            db.refresh(row)
            template_loc_id_by_name[row.location_name] = row.id

        for at in templates.get("story_arcs", []):
            row = models.StoryArc(**_model_kwargs(
                models.StoryArc, at,
                fk_overrides={"story_id": story.id, "playthrough_id": None},
            ))
            db.add(row)
            db.commit()
            db.refresh(row)
            template_arc_id_by_name[row.arc_name] = row.id

        for rt in templates.get("relationships", []):
            e1 = template_char_id_by_name.get(rt.get("_entity1_name"))
            e2 = template_char_id_by_name.get(rt.get("_entity2_name"))
            if e1 is None or e2 is None:
                continue
            row = models.Relationship(**_model_kwargs(
                models.Relationship, rt,
                fk_overrides={"story_id": story.id, "playthrough_id": None,
                              "entity1_id": e1, "entity2_id": e2},
            ))
            db.add(row)
        db.commit()

        for et in templates.get("story_episodes", []):
            arc_id = template_arc_id_by_name.get(et.get("_arc_name"))
            if arc_id is None:
                continue
            row = models.StoryEpisode(**_model_kwargs(
                models.StoryEpisode, et,
                fk_overrides={"arc_id": arc_id, "playthrough_id": None},
            ))
            db.add(row)
        db.commit()
    else:
        # Story already existed — populate the template name maps from DB.
        for cid, name in db.query(models.Character.id, models.Character.character_name).filter(
            models.Character.story_id == story.id,
            models.Character.playthrough_id.is_(None)
        ).all():
            template_char_id_by_name[name] = cid
        for lid, name in db.query(models.Location.id, models.Location.location_name).filter(
            models.Location.story_id == story.id,
            models.Location.playthrough_id.is_(None)
        ).all():
            template_loc_id_by_name[name] = lid
        for aid, name in db.query(models.StoryArc.id, models.StoryArc.arc_name).filter(
            models.StoryArc.story_id == story.id,
            models.StoryArc.playthrough_id.is_(None)
        ).all():
            template_arc_id_by_name[name] = aid

    # ----- 2. Playthrough (always new) -----
    pt = models.Playthrough(**_model_kwargs(
        models.Playthrough, pt_data,
        fk_overrides={"story_id": story.id, "user_id": None},
    ))
    db.add(pt)
    db.commit()
    db.refresh(pt)

    # ----- 3. Per-playthrough instance rows -----
    inst_char_id_by_name: dict[str, int] = {}
    inst_loc_id_by_name: dict[str, int] = {}
    inst_arc_id_by_name: dict[str, int] = {}

    for c in pt_data.get("characters", []):
        tpl_id = template_char_id_by_name.get(c.get("_template_character_name"))
        row = models.Character(**_model_kwargs(
            models.Character, c,
            fk_overrides={"story_id": story.id, "playthrough_id": pt.id,
                          "template_character_id": tpl_id},
        ))
        db.add(row)
        db.commit()
        db.refresh(row)
        inst_char_id_by_name[row.character_name] = row.id

    for l in pt_data.get("locations", []):
        row = models.Location(**_model_kwargs(
            models.Location, l,
            fk_overrides={"story_id": story.id, "playthrough_id": pt.id,
                          "parent_location_id": None},
        ))
        db.add(row)
        db.commit()
        db.refresh(row)
        inst_loc_id_by_name[row.location_name] = row.id

    for a in pt_data.get("story_arcs", []):
        row = models.StoryArc(**_model_kwargs(
            models.StoryArc, a,
            fk_overrides={"story_id": story.id, "playthrough_id": pt.id},
        ))
        db.add(row)
        db.commit()
        db.refresh(row)
        inst_arc_id_by_name[row.arc_name] = row.id

    for r in pt_data.get("relationships", []):
        e1 = inst_char_id_by_name.get(r.get("_entity1_name"))
        e2 = inst_char_id_by_name.get(r.get("_entity2_name"))
        if e1 is None or e2 is None:
            continue
        row = models.Relationship(**_model_kwargs(
            models.Relationship, r,
            fk_overrides={"story_id": story.id, "playthrough_id": pt.id,
                          "entity1_id": e1, "entity2_id": e2},
        ))
        db.add(row)
    db.commit()

    for e in pt_data.get("story_episodes", []):
        arc_id = inst_arc_id_by_name.get(e.get("_arc_name"))
        if arc_id is None:
            continue
        row = models.StoryEpisode(**_model_kwargs(
            models.StoryEpisode, e,
            fk_overrides={"arc_id": arc_id, "playthrough_id": pt.id},
        ))
        db.add(row)
    db.commit()

    # Story flags (no character_id)
    for f in pt_data.get("story_flags", []):
        row = models.StoryFlag(**_model_kwargs(
            models.StoryFlag, f,
            fk_overrides={"playthrough_id": pt.id},
        ))
        db.add(row)
    db.commit()

    # Character-scoped tables (knowledge / state / goals / beliefs / avoidances)
    def add_char_scoped(model, rows):
        for r in rows:
            cid = inst_char_id_by_name.get(r.get("_character_name"))
            if cid is None:
                continue
            row = model(**_model_kwargs(
                model, r,
                fk_overrides={"playthrough_id": pt.id, "character_id": cid},
            ))
            db.add(row)

    add_char_scoped(models.CharacterKnowledge, pt_data.get("character_knowledge", []))
    add_char_scoped(models.CharacterState, pt_data.get("character_states", []))
    add_char_scoped(models.CharacterGoal, pt_data.get("character_goals", []))
    add_char_scoped(models.CharacterBelief, pt_data.get("character_beliefs", []))
    add_char_scoped(models.CharacterAvoidance, pt_data.get("character_avoidances", []))
    db.commit()

    # CharacterMemory has an extra location_id ref + session_id (deferred —
    # session_id fixed up after sessions are created).
    memories_to_fix_session: list[tuple[models.CharacterMemory, Optional[int]]] = []
    for m in pt_data.get("character_memories", []):
        cid = inst_char_id_by_name.get(m.get("_character_name"))
        if cid is None:
            continue
        loc_id = inst_loc_id_by_name.get(m.get("_location_name"))
        row = models.CharacterMemory(**_model_kwargs(
            models.CharacterMemory, m,
            fk_overrides={"playthrough_id": pt.id, "character_id": cid,
                          "location_id": loc_id, "session_id": None},
            drop={"session_id"},
        ))
        db.add(row)
        memories_to_fix_session.append((row, m.get("session_id")))
    db.commit()

    # ----- 4. Sessions + conversations + scene states -----
    session_id_remap: dict[int, int] = {}

    for sess in pt_data.get("sessions", []):
        old_session_id = sess.get("id")
        user_char_id = inst_char_id_by_name.get(sess.get("_user_character_name"))
        s_row = models.Session(**_model_kwargs(
            models.Session, sess,
            fk_overrides={"playthrough_id": pt.id, "user_character_id": user_char_id},
        ))
        db.add(s_row)
        db.commit()
        db.refresh(s_row)
        if old_session_id is not None:
            session_id_remap[old_session_id] = s_row.id

        for conv in sess.get("conversations", []):
            row = models.Conversation(**_model_kwargs(
                models.Conversation, conv,
                fk_overrides={"session_id": s_row.id, "playthrough_id": pt.id},
            ))
            db.add(row)
        db.commit()

        for scene in sess.get("scene_states", []):
            sc_row = models.SceneState(**_model_kwargs(
                models.SceneState, scene,
                fk_overrides={"session_id": s_row.id, "playthrough_id": pt.id},
            ))
            db.add(sc_row)
            db.commit()
            db.refresh(sc_row)

            for char_in_scene in scene.get("characters_in_scene", []):
                cid = inst_char_id_by_name.get(char_in_scene.get("_character_name"))
                row = models.SceneCharacter(**_model_kwargs(
                    models.SceneCharacter, char_in_scene,
                    fk_overrides={"scene_state_id": sc_row.id,
                                  "playthrough_id": pt.id,
                                  "character_id": cid},
                ))
                db.add(row)
            db.commit()

    # Memory flags - need session_id remap; fall back to first session
    fallback_session_id = next(iter(session_id_remap.values()), None)
    for m in pt_data.get("memory_flags", []):
        old_sid = m.get("session_id")
        new_sid = session_id_remap.get(old_sid, fallback_session_id)
        if new_sid is None:
            continue  # no session to attach to
        row = models.MemoryFlag(**_model_kwargs(
            models.MemoryFlag, m,
            fk_overrides={"playthrough_id": pt.id, "session_id": new_sid},
        ))
        db.add(row)

    # Backfill character_memory.session_id from the remap
    for mem_row, old_sid in memories_to_fix_session:
        mem_row.session_id = session_id_remap.get(old_sid)
    db.commit()

    return {
        "story_id": story.id,
        "story_title": story.title,
        "story_was_new": story_is_new,
        "playthrough_id": pt.id,
        "playthrough_name": pt.playthrough_name,
        "counts": {
            "characters": len(inst_char_id_by_name),
            "sessions": len(session_id_remap),
            "conversations": sum(len(s.get("conversations", [])) for s in pt_data.get("sessions", [])),
        },
    }


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
            "flag_type": mem.flag_type,
            "flag_value": mem.flag_value,
            "importance": mem.importance
        } for mem in memory_flags]

        # Get sessions
        sessions = db.query(models.Session).filter(
            models.Session.playthrough_id == playthrough_id
        ).order_by(models.Session.started_at.desc()).limit(10).all()

        sessions_data = [{
            "id": session.id,
            "created_at": session.started_at.isoformat() if session.started_at else None,
            "last_activity": session.last_active.isoformat() if session.last_active else None,
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
                # Get characters in scene
                scene_characters = db.query(models.SceneCharacter).filter(
                    models.SceneCharacter.scene_state_id == scene.id
                ).all()

                characters_present = [{
                    "character_name": sc.character_name,
                    "character_type": sc.character_type,
                    "mood": sc.character_mood,
                    "intent": sc.character_intent
                } for sc in scene_characters]

                scene_state = {
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "weather": scene.weather,
                    "emotional_tone": scene.emotional_tone,
                    "scene_context": scene.scene_context,
                    "characters_present": characters_present
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


@router.get("/tester/prompt/{session_id}")
async def get_prompt_window(session_id: int, db: Session = Depends(get_db)):
    """
    Get the full prompt that would be sent to the AI for story generation.

    Returns the system prompt and the assembled user prompt (with a placeholder
    for user input and empty character decisions, since no turn is in flight).
    Backs the Tester panel's "Prompt" tab.
    """
    try:
        from ..ai.prompt_builder import PromptBuilder
        from ..ai.prompts import PromptTemplates
        from ..pipeline.chat_pipeline import STORY_SYSTEM_PROMPT

        # Validate session exists
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        prompt_builder = PromptBuilder(db, session_id)
        bundle = prompt_builder.build_prompt_bundle()
        story_info = prompt_builder.get_story_info()

        # No active turn, so decisions and user input are placeholders.
        story_prompt = PromptTemplates.story_generation_prompt(
            bundle,
            "[user input will appear here]",
            [],
            story_info,
        )

        full_prompt = (
            f"=== SYSTEM PROMPT ===\n{STORY_SYSTEM_PROMPT}\n\n"
            f"=== USER PROMPT ===\n{story_prompt}"
        )

        # Get conversation history for this session
        conversations = db.query(models.Conversation).filter(
            models.Conversation.session_id == session_id
        ).order_by(models.Conversation.timestamp.desc()).limit(20).all()

        conversation_history = [{
            "id": conv.id,
            "speaker_type": conv.speaker_type,
            "speaker_name": conv.speaker_name,
            "message": conv.message,
            "created_at": conv.timestamp.isoformat() if conv.timestamp else None
        } for conv in reversed(conversations)]

        return {
            "session_id": session_id,
            "full_prompt": full_prompt,
            "prompt_length": len(full_prompt),
            "conversation_history": conversation_history,
            "metadata": {
                "playthrough_id": session.playthrough_id,
                "max_context_messages": settings.max_context_messages
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(db, f"Error getting prompt window: {str(e)}", "system")
        raise HTTPException(status_code=500, detail=f"Error getting prompt window: {str(e)}")


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

        # Delete every playthrough-scoped row (keeps the Playthrough itself
        # so we can reset its current_location/current_time below).
        for model in _PLAYTHROUGH_SCOPED_MODELS:
            db.query(model).filter(
                model.playthrough_id == playthrough_id
            ).delete(synchronize_session=False)

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
    limit: int = 1000
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
        ).order_by(models.Conversation.timestamp).all()

        # Get the most recent `limit` logs for this session. We order DESC so a
        # long session keeps the latest turns (a single turn emits many logs, so
        # an ASC limit would only ever show the first turn), then reverse back to
        # chronological order for the turn-grouping below.
        logs = db.query(models.Log).filter(
            models.Log.session_id == session_id
        ).order_by(models.Log.timestamp.desc()).limit(limit).all()
        logs = list(reversed(logs))

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
                    "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                    "logs": [],
                    "ai_response": None
                }
            elif conv.speaker_type == "narrator" and current_group:
                current_group["ai_response"] = conv.message

        # Add last group if exists
        if current_group:
            grouped_logs.append(current_group)

        # Assign each log to the single group whose user turn started it.
        # A log belongs to the latest group whose timestamp is <= log timestamp.
        for log in logs:
            if not log.timestamp:
                continue

            log_ts = log.timestamp.isoformat()
            target_group = None
            for group in grouped_logs:
                if group["timestamp"] and log_ts >= group["timestamp"]:
                    target_group = group
                else:
                    break

            if target_group is not None:
                target_group["logs"].append({
                    "type": log.log_type,
                    "category": log.log_category,
                    "message": log.message,
                    "timestamp": log_ts,
                    "details": log.details
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
