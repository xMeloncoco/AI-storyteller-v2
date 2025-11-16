"""
Context Builder for AI Storytelling

This module is responsible for building the complete context that gets sent to the AI.
Context includes:
1. Story information
2. Current scene state
3. Characters in the scene
4. Conversation history
5. Relevant memories from ChromaDB
6. Relationship information
7. Active story arcs

Good context = consistent and engaging story!
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from .. import crud, models
from ..config import settings
from ..utils.logger import AppLogger


class ContextBuilder:
    """
    Builds comprehensive context for AI story generation

    The context is what the AI "knows" when generating responses.
    Better context = better, more consistent responses.
    """

    def __init__(self, db: Session, session_id: int):
        """
        Initialize context builder

        Args:
            db: Database session
            session_id: Current session ID
        """
        self.db = db
        self.session_id = session_id
        self.logger = AppLogger(db, session_id)

        # Get session information
        self.session = crud.get_session(db, session_id)
        if not self.session:
            raise ValueError(f"Session {session_id} not found")

        self.playthrough_id = self.session.playthrough_id

        # Get playthrough and story info
        self.playthrough = crud.get_playthrough(db, self.playthrough_id)
        if not self.playthrough:
            raise ValueError(f"Playthrough {self.playthrough_id} not found")

        self.story = crud.get_story(db, self.playthrough.story_id)
        if not self.story:
            raise ValueError(f"Story {self.playthrough.story_id} not found")

        self.logger.context(
            f"Context builder initialized for session {session_id}",
            "memory"
        )

    def build_full_context(self) -> str:
        """
        Build the complete context string for story generation

        This is the main method that assembles all context pieces
        """
        self.logger.context("Building full context", "memory")

        context_parts = []

        # 1. Story information
        story_context = self._get_story_context()
        context_parts.append(f"STORY INFORMATION:\n{story_context}")

        # 2. Current scene state
        scene_context = self._get_scene_context()
        context_parts.append(f"\nCURRENT SCENE:\n{scene_context}")

        # 3. Characters in scene
        characters_context = self._get_characters_in_scene()
        context_parts.append(f"\nCHARACTERS PRESENT:\n{characters_context}")

        # 4. Conversation history
        history_context = self._get_conversation_history()
        context_parts.append(f"\nRECENT CONVERSATION:\n{history_context}")

        # 5. Relationship information
        relationships_context = self._get_relationships_context()
        if relationships_context:
            context_parts.append(f"\nRELATIONSHIP STATUS:\n{relationships_context}")

        # 6. Active story arcs (Phase 2.2)
        arcs_context = self._get_active_arcs_context()
        if arcs_context:
            context_parts.append(f"\nACTIVE STORY ARCS:\n{arcs_context}")

        # 7. Important memory flags (Phase 1.3)
        memory_context = self._get_memory_flags_context()
        if memory_context:
            context_parts.append(f"\nIMPORTANT MEMORIES:\n{memory_context}")

        full_context = "\n".join(context_parts)

        self.logger.context(
            f"Built full context",
            "memory",
            {"context_length": len(full_context), "sections": len(context_parts)}
        )

        return full_context

    def _get_story_context(self) -> str:
        """Get basic story information"""
        context = f"Title: {self.story.title}\n"
        if self.story.description:
            context += f"Description: {self.story.description}\n"
        return context

    def _get_scene_context(self) -> str:
        """Get current scene state"""
        scene_state = crud.get_current_scene_state(self.db, self.session_id)

        if not scene_state:
            # No scene state yet, use playthrough defaults
            location = self.playthrough.current_location or "Unknown location"
            time = self.playthrough.current_time or "Unknown time"
            return f"Location: {location}\nTime: {time}\nScene: Story beginning"

        context = f"Location: {scene_state.location or 'Unknown'}\n"
        context += f"Time: {scene_state.time_of_day or 'Unknown'}\n"

        if scene_state.weather:
            context += f"Weather: {scene_state.weather}\n"

        if scene_state.emotional_tone:
            context += f"Mood: {scene_state.emotional_tone}\n"

        if scene_state.scene_context:
            context += f"Context: {scene_state.scene_context}\n"

        return context

    def _get_characters_in_scene(self) -> str:
        """Get information about characters currently in the scene"""
        scene_state = crud.get_current_scene_state(self.db, self.session_id)

        if not scene_state:
            # No scene state yet, return user character and any initial characters
            user_char = crud.get_user_character(self.db, self.playthrough_id)
            if user_char:
                return f"- {user_char.character_name} (User character)\n"
            return "- Characters not yet established\n"

        # Get characters from scene_characters table
        scene_chars = self.db.query(models.SceneCharacter).filter(
            models.SceneCharacter.scene_state_id == scene_state.id
        ).all()

        if not scene_chars:
            return "- No characters in scene\n"

        context = ""
        for sc in scene_chars:
            context += f"- {sc.character_name}"
            if sc.character_type:
                context += f" ({sc.character_type})"
            if sc.character_mood:
                context += f" - Mood: {sc.character_mood}"
            if sc.character_intent:
                context += f" - Intent: {sc.character_intent}"
            context += "\n"

        return context

    def _get_conversation_history(self) -> str:
        """Get recent conversation history"""
        # Get last N messages (configurable)
        history = crud.get_conversation_history(
            self.db,
            self.session_id,
            limit=settings.max_context_messages
        )

        if not history:
            return "No conversation yet.\n"

        context = ""
        for msg in history:
            speaker = msg.speaker_name or msg.speaker_type.upper()
            context += f"{speaker}: {msg.message}\n\n"

        return context

    def _get_relationships_context(self) -> str:
        """Get relationship information for characters in scene"""
        user_char = crud.get_user_character(self.db, self.playthrough_id)

        if not user_char:
            return ""

        relationships = crud.get_all_relationships_for_character(
            self.db, user_char.id, self.playthrough_id
        )

        if not relationships:
            return ""

        context = ""
        for rel in relationships:
            # Get the other character's name
            if rel.entity1_id == user_char.id:
                other_char = crud.get_character(self.db, rel.entity2_id)
            else:
                other_char = crud.get_character(self.db, rel.entity1_id)

            if other_char:
                context += f"{other_char.character_name}:\n"
                context += f"  Relationship: {rel.relationship_type}\n"
                context += f"  Trust: {rel.trust:.2f}\n"
                context += f"  Affection: {rel.affection:.2f}\n"
                context += f"  Familiarity: {rel.familiarity:.2f}\n"
                if rel.history_summary:
                    context += f"  History: {rel.history_summary}\n"
                context += "\n"

        return context

    def _get_active_arcs_context(self) -> str:
        """Get active story arcs (Phase 2.2)"""
        arcs = crud.get_active_story_arcs(self.db, self.playthrough_id)

        if not arcs:
            return ""

        context = ""
        for arc in arcs:
            context += f"- {arc.arc_name}"
            if arc.description:
                context += f": {arc.description}"
            context += "\n"

        return context

    def _get_memory_flags_context(self) -> str:
        """Get important memory flags (Phase 1.3)"""
        flags = crud.get_important_memory_flags(
            self.db, self.playthrough_id, min_importance=7
        )

        if not flags:
            return ""

        context = ""
        for flag in flags[:10]:  # Limit to 10 most important
            context += f"- [{flag.flag_type}] {flag.flag_value}\n"

        return context

    def get_character_info(self, character_id: int) -> Dict[str, Any]:
        """
        Get complete character information for decision making

        Returns a dictionary with all relevant character data
        """
        character = crud.get_character(self.db, character_id)

        if not character:
            return {}

        info = {
            "id": character.id,
            "name": character.character_name,
            "type": character.character_type,
            "age": character.age,
            "appearance": character.appearance,
            "backstory": character.backstory or "",
            "personality_traits": character.personality_traits or "",
            "speech_patterns": character.speech_patterns or ""
        }

        # Get relationships involving this character
        relationships = crud.get_all_relationships_for_character(
            self.db, character_id, self.playthrough_id
        )

        rel_info = []
        for rel in relationships:
            if rel.entity1_id == character_id:
                other_char = crud.get_character(self.db, rel.entity2_id)
            else:
                other_char = crud.get_character(self.db, rel.entity1_id)

            if other_char:
                rel_info.append({
                    "with": other_char.character_name,
                    "type": rel.relationship_type,
                    "trust": rel.trust,
                    "affection": rel.affection,
                    "familiarity": rel.familiarity
                })

        info["relationships"] = rel_info

        # Future: Add character knowledge (Phase 1.3+)
        # This prevents "mind-reading"
        info["known_facts"] = []  # To be implemented

        return info

    def get_all_characters_in_scene_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all characters currently in the scene

        Used for character decision layer (Phase 1.3+)
        """
        scene_state = crud.get_current_scene_state(self.db, self.session_id)

        if not scene_state:
            return []

        scene_chars = self.db.query(models.SceneCharacter).filter(
            models.SceneCharacter.scene_state_id == scene_state.id
        ).all()

        chars_info = []
        for sc in scene_chars:
            if sc.character_id:
                char_info = self.get_character_info(sc.character_id)
                char_info["mood"] = sc.character_mood
                char_info["intent"] = sc.character_intent
                char_info["position"] = sc.character_physical_position
                chars_info.append(char_info)

        return chars_info

    def get_story_info(self) -> Dict[str, Any]:
        """Get story information dictionary"""
        return {
            "id": self.story.id,
            "title": self.story.title,
            "description": self.story.description
        }

    def update_scene_state(
        self,
        location: Optional[str] = None,
        time_of_day: Optional[str] = None,
        weather: Optional[str] = None,
        scene_context: Optional[str] = None,
        emotional_tone: Optional[str] = None
    ) -> models.SceneState:
        """
        Create a new scene state record

        Called when scene changes are detected
        """
        from .. import schemas

        scene_data = schemas.SceneStateCreate(
            session_id=self.session_id,
            playthrough_id=self.playthrough_id,
            location=location,
            time_of_day=time_of_day,
            weather=weather,
            scene_context=scene_context,
            emotional_tone=emotional_tone
        )

        scene_state = crud.create_scene_state(self.db, scene_data)

        self.logger.context(
            f"Updated scene state",
            "memory",
            {
                "location": location,
                "time": time_of_day,
                "tone": emotional_tone
            }
        )

        # Also update playthrough location
        if location:
            crud.update_playthrough_location(
                self.db, self.playthrough_id, location, time_of_day
            )

        return scene_state
