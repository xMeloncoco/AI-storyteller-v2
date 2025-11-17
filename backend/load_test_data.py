#!/usr/bin/env python3
"""
Test Data Loader for Dreamwalkers

This script loads the test story JSON files into the database.
It creates:
1. Story templates
2. Character templates (playthrough_id = NULL)
3. Relationship templates (playthrough_id = NULL)
4. Story arc templates

Run this after starting the backend to populate with test data.
"""
import json
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, init_db
from app import models, schemas, crud
from app.utils.logger import log_notification


def load_story_from_json(db, json_path: str):
    """Load a complete story from a JSON file"""
    print(f"\nLoading story from: {json_path}")

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Check if story already exists
    existing = db.query(models.Story).filter(
        models.Story.title == data["title"]
    ).first()

    if existing:
        print(f"  Story '{data['title']}' already exists (id={existing.id})")
        return existing.id

    # Create the story
    story = models.Story(
        title=data["title"],
        description=data["description"],
        initial_message=data["initial_message"],
        initial_location=data["initial_location"],
        initial_time=data["initial_time"]
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    print(f"  Created story: {story.title} (id={story.id})")

    # Create character templates (playthrough_id = NULL)
    char_id_map = {}  # Maps JSON character name to database ID

    for char_data in data.get("characters", []):
        # Convert personality_traits list to string if needed
        traits = char_data.get("personality_traits", [])
        if isinstance(traits, list):
            traits = ", ".join(traits)

        character = models.Character(
            story_id=story.id,
            playthrough_id=None,  # Template!
            character_type=char_data["type"],
            character_name=char_data["name"],
            appearance=char_data.get("appearance", ""),
            age=char_data.get("age"),
            backstory=char_data.get("backstory", ""),
            personality_traits=traits,
            speech_patterns=char_data.get("speech_patterns", "")
        )
        db.add(character)
        db.commit()
        db.refresh(character)

        char_id_map[char_data["name"]] = character.id
        print(f"    Created character template: {char_data['name']} (id={character.id})")

    # Create relationship templates
    for rel_data in data.get("relationships", []):
        # Find character IDs - support both entity1/entity2 and character1/character2
        char1_name = rel_data.get("entity1") or rel_data.get("character1")
        char2_name = rel_data.get("entity2") or rel_data.get("character2")

        if char1_name not in char_id_map or char2_name not in char_id_map:
            print(f"    WARNING: Could not find characters for relationship {char1_name} <-> {char2_name}")
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
        print(f"    Created relationship template: {char1_name} <-> {char2_name}")

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
            is_active=0,
            is_completed=0,
            arc_order=arc_data.get("order", 0)
        )
        db.add(arc)
        print(f"    Created story arc template: {arc_data['name']}")

    db.commit()

    log_notification(
        db,
        f"Loaded test story: {story.title}",
        "database",
        {
            "story_id": story.id,
            "characters": len(char_id_map),
            "relationships": len(data.get("relationships", [])),
            "arcs": len(data.get("story_arcs", []))
        }
    )

    print(f"  Story loaded successfully!")
    return story.id


def main():
    print("=" * 60)
    print("Dreamwalkers Test Data Loader")
    print("=" * 60)

    # Initialize database
    init_db()

    db = SessionLocal()

    try:
        # Load all test stories
        test_data_dir = Path(__file__).parent / "test_data"

        if not test_data_dir.exists():
            print(f"ERROR: Test data directory not found: {test_data_dir}")
            return

        # Find all JSON files
        json_files = list(test_data_dir.glob("*.json"))

        if not json_files:
            print(f"ERROR: No JSON files found in {test_data_dir}")
            return

        print(f"Found {len(json_files)} test story file(s)")

        story_ids = []
        for json_file in json_files:
            story_id = load_story_from_json(db, str(json_file))
            if story_id:
                story_ids.append(story_id)

        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  Loaded {len(story_ids)} stories")
        print(f"  Total characters: {db.query(models.Character).filter(models.Character.playthrough_id.is_(None)).count()}")
        print(f"  Total relationships: {db.query(models.Relationship).filter(models.Relationship.playthrough_id.is_(None)).count()}")
        print(f"  Total story arcs: {db.query(models.StoryArc).filter(models.StoryArc.playthrough_id.is_(None)).count()}")
        print("=" * 60)

        print("\nTo create a playthrough, use the API:")
        print("  POST /stories/playthroughs")
        print("  Body: {\"story_id\": <id>, \"playthrough_name\": \"My Game\"}")
        print("\nOr use the frontend to select a story and start a new game.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
