"""
Test Data Importer for Dreamwalkers

This script imports test stories into the database.
Run this after setting up the backend to have stories to test with.

Usage:
    python test_data/import_test_data.py --story sterling
    python test_data/import_test_data.py --story moonweaver
    python test_data/import_test_data.py --story both
    python test_data/import_test_data.py --story both --reset
    python test_data/import_test_data.py --story both --create-playthroughs

Arguments:
    --story: Which story to import (sterling, moonweaver, both)
    --reset: Clear the database before importing
    --create-playthroughs: Also create a test playthrough for each story
"""
import json
import argparse
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db, Base, engine
from app import models, crud, schemas
from app.utils.logger import log_notification


def load_json_file(filename: str) -> dict:
    """Load a JSON file from the test_data directory"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def import_story(db: Session, story_data: dict) -> models.Story:
    """
    Import a story and all its components

    Args:
        db: Database session
        story_data: Story data dictionary from JSON file

    Returns:
        Created story object
    """
    print(f"Importing story: {story_data['title']}")

    # Create the story
    story_schema = schemas.StoryCreate(
        title=story_data['title'],
        description=story_data.get('description', ''),
        initial_message=story_data['initial_message'],
        initial_location=story_data.get('initial_location', ''),
        initial_time=story_data.get('initial_time', '')
    )

    db_story = crud.create_story(db, story_schema)
    print(f"  Created story with ID: {db_story.id}")

    # Import characters (as templates)
    print(f"  Importing {len(story_data.get('characters', []))} characters...")
    for char_data in story_data.get('characters', []):
        character = models.Character(
            story_id=db_story.id,
            playthrough_id=None,  # Template
            character_type=char_data['type'],
            character_name=char_data['name'],
            appearance=char_data.get('appearance', ''),
            age=char_data.get('age'),
            backstory=char_data.get('backstory', ''),
            personality_traits=json.dumps(char_data.get('personality_traits', [])),
            speech_patterns=char_data.get('speech_patterns', '')
        )
        db.add(character)

    db.commit()
    print(f"    Characters imported")

    # Import locations (as templates)
    print(f"  Importing {len(story_data.get('locations', []))} locations...")
    for loc_data in story_data.get('locations', []):
        location = models.Location(
            story_id=db_story.id,
            playthrough_id=None,  # Template
            location_name=loc_data['name'],
            description=loc_data.get('description', ''),
            location_type=loc_data.get('type', ''),
            location_scope=loc_data.get('scope', '')
        )
        db.add(location)

    db.commit()
    print(f"    Locations imported")

    # Import relationships (as templates)
    # First, get character IDs
    characters = db.query(models.Character).filter(
        models.Character.story_id == db_story.id,
        models.Character.playthrough_id.is_(None)
    ).all()

    char_name_to_id = {c.character_name: c.id for c in characters}

    print(f"  Importing {len(story_data.get('relationships', []))} relationships...")
    for rel_data in story_data.get('relationships', []):
        entity1_name = rel_data['entity1']
        entity2_name = rel_data['entity2']

        if entity1_name not in char_name_to_id or entity2_name not in char_name_to_id:
            print(f"    Warning: Skipping relationship {entity1_name} - {entity2_name} (character not found)")
            continue

        relationship = models.Relationship(
            story_id=db_story.id,
            playthrough_id=None,  # Template
            entity1_type="Character",
            entity1_id=char_name_to_id[entity1_name],
            entity2_type="Character",
            entity2_id=char_name_to_id[entity2_name],
            relationship_type=rel_data.get('type', 'acquaintances'),
            first_meeting_context=rel_data.get('first_meeting', ''),
            trust=rel_data.get('trust', 0.5),
            affection=rel_data.get('affection', 0.5),
            familiarity=rel_data.get('familiarity', 0.0),
            history_summary=rel_data.get('history', '')
        )
        db.add(relationship)

    db.commit()
    print(f"    Relationships imported")

    # Import story arcs (as templates)
    print(f"  Importing {len(story_data.get('story_arcs', []))} story arcs...")
    for arc_data in story_data.get('story_arcs', []):
        arc = models.StoryArc(
            story_id=db_story.id,
            playthrough_id=None,  # Template
            arc_name=arc_data['name'],
            description=arc_data.get('description', ''),
            arc_order=arc_data.get('order', 1),
            is_active=arc_data.get('is_active', 0),
            is_completed=0,
            start_condition=json.dumps(arc_data.get('start_condition', {})),
            completion_condition=json.dumps(arc_data.get('completion_condition', {}))
        )
        db.add(arc)
        db.commit()
        db.refresh(arc)

        # Import episodes for this arc
        for episode_data in arc_data.get('episodes', []):
            episode = models.StoryEpisode(
                arc_id=arc.id,
                playthrough_id=None,  # Template
                episode_name=episode_data['name'],
                description=episode_data.get('description', ''),
                episode_order=episode_data.get('order', 1),
                is_active=0,
                is_completed=0,
                trigger_flags=json.dumps(episode_data.get('trigger_flags', [])),
                completion_flags=json.dumps(episode_data.get('completion_flags', []))
            )
            db.add(episode)

    db.commit()
    print(f"    Story arcs imported")

    log_notification(
        db,
        f"Imported story: {story_data['title']}",
        "database",
        {"story_id": db_story.id}
    )

    return db_story


def create_test_playthrough(db: Session, story_id: int, name: str) -> models.Playthrough:
    """
    Create a test playthrough for a story

    This copies all templates to instances
    """
    print(f"  Creating test playthrough: {name}")

    playthrough_data = schemas.PlaythroughCreate(
        story_id=story_id,
        playthrough_name=name
    )

    playthrough = crud.create_playthrough(db, playthrough_data)
    print(f"    Playthrough created with ID: {playthrough.id}")

    return playthrough


def reset_database():
    """Drop and recreate all tables"""
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("  Database reset complete")


def main():
    parser = argparse.ArgumentParser(description="Import test data for Dreamwalkers")
    parser.add_argument(
        '--story',
        choices=['sterling', 'moonweaver', 'both'],
        default='both',
        help='Which story to import'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database before importing'
    )
    parser.add_argument(
        '--create-playthroughs',
        action='store_true',
        help='Create test playthroughs for imported stories'
    )

    args = parser.parse_args()

    # Initialize database
    if args.reset:
        reset_database()
    else:
        init_db()

    # Create database session
    db = SessionLocal()

    try:
        stories_imported = []

        # Import Sterling Hearts
        if args.story in ['sterling', 'both']:
            print("\n" + "=" * 50)
            print("IMPORTING STERLING HEARTS")
            print("=" * 50)
            sterling_data = load_json_file('sterling_story.json')
            sterling = import_story(db, sterling_data)
            stories_imported.append(('Sterling Hearts', sterling.id))

            if args.create_playthroughs:
                create_test_playthrough(db, sterling.id, "Sterling Hearts Test Run")

        # Import Moonweaver's Apprentice
        if args.story in ['moonweaver', 'both']:
            print("\n" + "=" * 50)
            print("IMPORTING THE MOONWEAVER'S APPRENTICE")
            print("=" * 50)
            moonweaver_data = load_json_file('moonweaver_story.json')
            moonweaver = import_story(db, moonweaver_data)
            stories_imported.append(("The Moonweaver's Apprentice", moonweaver.id))

            if args.create_playthroughs:
                create_test_playthrough(db, moonweaver.id, "Moonweaver Test Run")

        # Summary
        print("\n" + "=" * 50)
        print("IMPORT COMPLETE")
        print("=" * 50)
        for name, story_id in stories_imported:
            print(f"  - {name} (ID: {story_id})")

        if args.create_playthroughs:
            print("\nTest playthroughs created for each story")

        print("\nYou can now start the backend and test the API!")
        print("  uvicorn app.main:app --reload")

    finally:
        db.close()


if __name__ == "__main__":
    main()
