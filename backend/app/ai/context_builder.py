"""
ContextBuilder - assembles the per-turn ContextBundle that downstream
pipeline stages and prompt templates consume.

Post-R2 surface:
- `build_bundle()` - typed ContextBundle (preferred path going forward).
- `build_for_character(character_id)` - same bundle plus a populated
  `target_character`. M2.3 will add witness-based filtering of memories,
  knowledge and flags; for R2 it just attaches the character profile.
- `build_full_context()` - DEPRECATED alias for backwards compat
  (admin/tester panel still calls it). Will be removed once M2.3 lands.

The legacy concatenated string format lives in
`pipeline/context_bundle.py:render_legacy_context()` and is byte-for-byte
reproducible from the bundle, so the model sees the same input it did
before R2.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .. import crud, models
from ..config import settings
from ..pipeline.context_bundle import (
    ActiveArcView,
    CharacterPresenceView,
    CharacterView,
    ContextBundle,
    ConversationMessageView,
    MemoryFlagView,
    RelationshipView,
    SceneView,
    StoryView,
)
from ..utils.logger import AppLogger


class ContextBuilder:
    """Assembles ContextBundle objects from the playthrough's current state."""

    def __init__(self, db: Session, session_id: int):
        self.db = db
        self.session_id = session_id
        self.logger = AppLogger(db, session_id)

        self.session = crud.get_session(db, session_id)
        if not self.session:
            raise ValueError(f"Session {session_id} not found")

        self.playthrough_id = self.session.playthrough_id

        self.playthrough = crud.get_playthrough(db, self.playthrough_id)
        if not self.playthrough:
            raise ValueError(f"Playthrough {self.playthrough_id} not found")

        self.story = crud.get_story(db, self.playthrough.story_id)
        if not self.story:
            raise ValueError(f"Story {self.playthrough.story_id} not found")

        self.logger.context(
            f"Context builder initialized for session {session_id}",
            "memory",
        )

    # ------------------------------------------------------------------
    # New public surface (R2+)
    # ------------------------------------------------------------------

    def build_bundle(self) -> ContextBundle:
        """Gather every piece of context the model and pipeline need this turn."""
        self.logger.context("Building context bundle", "memory")

        bundle = ContextBundle(
            story=self._collect_story(),
            scene=self._collect_scene(),
            characters_present=self._collect_characters_present(),
            history=self._collect_history(),
            relationships=self._collect_relationships(),
            active_arcs=self._collect_active_arcs(),
            memory_flags=self._collect_memory_flags(),
        )

        self.logger.context(
            "Built context bundle",
            "memory",
            {
                "characters_present": len(bundle.characters_present),
                "history_messages": len(bundle.history),
                "relationships": len(bundle.relationships),
                "active_arcs": len(bundle.active_arcs),
                "memory_flags": len(bundle.memory_flags),
            },
        )

        return bundle

    def build_for_character(self, character_id: int) -> ContextBundle:
        """Bundle plus the requested character's full profile.

        R2 ships this without witness-based filtering — `CharacterMemory`,
        `CharacterKnowledge` and `MemoryFlag` are still global. M2.3 flips
        on filtering using the witness columns R6 adds.
        """
        bundle = self.build_bundle()
        bundle.target_character = self._build_character_view(character_id)
        return bundle

    # ------------------------------------------------------------------
    # Deprecated string surface (kept for admin/tester until M2.3)
    # ------------------------------------------------------------------

    def build_full_context(self) -> str:
        """DEPRECATED. Use `build_bundle()`.

        Renders the bundle through the legacy formatter so older callers
        (admin tester panel, etc.) keep getting the same string.
        """
        return self.build_bundle().to_string()

    # ------------------------------------------------------------------
    # Pipeline-facing helpers that aren't part of the bundle
    # ------------------------------------------------------------------

    def get_character_info(self, character_id: int) -> Dict[str, Any]:
        """
        Rich character info dict used by scene_simulation and per-character
        prompt building. Returns the same shape downstream code already
        expects; the typed CharacterView is for prompt assembly only.
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
            "speech_patterns": character.speech_patterns or "",
            "core_values": character.core_values or "",
            "core_fears": character.core_fears or "",
            "would_never_do": character.would_never_do or "",
            "would_always_do": character.would_always_do or "",
        }

        char_state = crud.get_character_state(self.db, character_id, self.playthrough_id)
        if char_state:
            info["current_state"] = {
                "emotional_state": (
                    char_state.current_emotional_state
                    or char_state.baseline_emotional_state
                ),
                "emotion_cause": char_state.emotion_cause,
                "emotion_intensity": char_state.emotion_intensity,
                "stress_level": char_state.stress_level,
                "energy_level": char_state.energy_level,
                "mental_clarity": char_state.mental_clarity,
                "primary_concern": char_state.primary_concern,
                "secondary_concerns": char_state.secondary_concerns,
            }
        else:
            info["current_state"] = None

        char_goals = crud.get_character_goals(self.db, character_id, self.playthrough_id)
        info["goals"] = [
            {
                "type": goal.goal_type,
                "content": goal.goal_content,
                "priority": goal.priority,
                "status": goal.status,
            }
            for goal in char_goals
        ]

        rel_info: List[Dict[str, Any]] = []
        for rel in crud.get_all_relationships_for_character(
            self.db, character_id, self.playthrough_id
        ):
            other_char = crud.get_character(
                self.db,
                rel.entity2_id if rel.entity1_id == character_id else rel.entity1_id,
            )
            if other_char:
                rel_info.append(
                    {
                        "with": other_char.character_name,
                        "type": rel.relationship_type,
                        "trust": rel.trust,
                        "affection": rel.affection,
                        "familiarity": rel.familiarity,
                    }
                )
        info["relationships"] = rel_info

        # CharacterKnowledge filtering arrives with M2.3 + the M9 stack.
        info["known_facts"] = []

        return info

    def get_all_characters_in_scene_info(self) -> List[Dict[str, Any]]:
        """Rich info for every character currently in scene (post-trigger view)."""
        scene_state = crud.get_current_scene_state(self.db, self.session_id)
        if not scene_state:
            return []

        scene_chars = (
            self.db.query(models.SceneCharacter)
            .filter(models.SceneCharacter.scene_state_id == scene_state.id)
            .all()
        )

        chars_info: List[Dict[str, Any]] = []
        for sc in scene_chars:
            if sc.character_id:
                char_info = self.get_character_info(sc.character_id)
                char_info["mood"] = sc.character_mood
                char_info["intent"] = sc.character_intent
                char_info["position"] = sc.character_physical_position
                chars_info.append(char_info)

        return chars_info

    def get_story_info(self) -> Dict[str, Any]:
        """Story metadata as a dict (legacy callers).  Prefer `bundle.story`."""
        return {
            "id": self.story.id,
            "title": self.story.title,
            "description": self.story.description,
        }

    def update_scene_state(
        self,
        location: Optional[str] = None,
        time_of_day: Optional[str] = None,
        weather: Optional[str] = None,
        scene_context: Optional[str] = None,
        emotional_tone: Optional[str] = None,
    ) -> models.SceneState:
        """Create a new SceneState row (called when a scene change is detected)."""
        from .. import schemas

        scene_data = schemas.SceneStateCreate(
            session_id=self.session_id,
            playthrough_id=self.playthrough_id,
            location=location,
            time_of_day=time_of_day,
            weather=weather,
            scene_context=scene_context,
            emotional_tone=emotional_tone,
        )

        scene_state = crud.create_scene_state(self.db, scene_data)

        self.logger.context(
            "Updated scene state",
            "memory",
            {
                "location": location,
                "time": time_of_day,
                "tone": emotional_tone,
            },
        )

        if location:
            crud.update_playthrough_location(
                self.db, self.playthrough_id, location, time_of_day
            )

        return scene_state

    # ------------------------------------------------------------------
    # Internal collectors (pure data → views)
    # ------------------------------------------------------------------

    def _collect_story(self) -> StoryView:
        return StoryView(
            id=self.story.id,
            title=self.story.title,
            description=self.story.description,
        )

    def _collect_scene(self) -> SceneView:
        scene_state = crud.get_current_scene_state(self.db, self.session_id)

        if not scene_state:
            return SceneView(
                location=self.playthrough.current_location,
                time_of_day=self.playthrough.current_time,
                is_initial=True,
            )

        return SceneView(
            location=scene_state.location,
            time_of_day=scene_state.time_of_day,
            weather=scene_state.weather,
            emotional_tone=scene_state.emotional_tone,
            scene_context=scene_state.scene_context,
            is_initial=False,
        )

    def _collect_characters_present(self) -> List[CharacterPresenceView]:
        """Match the legacy `_get_characters_in_scene` branching exactly.

        - No scene_state, user char exists → single row for the user.
        - No scene_state, no user char → a single placeholder row.
        - Scene_state with no chars → empty list (renderer prints
          "No characters in scene").
        - Scene_state with chars → one row per SceneCharacter.
        """
        scene_state = crud.get_current_scene_state(self.db, self.session_id)

        if not scene_state:
            user_char = crud.get_user_character(self.db, self.playthrough_id)
            if user_char:
                return [
                    CharacterPresenceView(
                        name=user_char.character_name,
                        character_type="User character",
                    )
                ]
            return [CharacterPresenceView(name="Characters not yet established")]

        scene_chars = (
            self.db.query(models.SceneCharacter)
            .filter(models.SceneCharacter.scene_state_id == scene_state.id)
            .all()
        )

        return [
            CharacterPresenceView(
                name=sc.character_name,
                character_type=sc.character_type,
                mood=sc.character_mood,
                intent=sc.character_intent,
            )
            for sc in scene_chars
        ]

    def _collect_history(self) -> List[ConversationMessageView]:
        history = crud.get_conversation_history(
            self.db,
            self.session_id,
            limit=settings.max_context_messages,
        )

        return [
            ConversationMessageView(
                speaker_label=msg.speaker_name or msg.speaker_type.upper(),
                message=msg.message,
            )
            for msg in history
        ]

    def _collect_relationships(self) -> List[RelationshipView]:
        user_char = crud.get_user_character(self.db, self.playthrough_id)
        if not user_char:
            return []

        relationships = crud.get_all_relationships_for_character(
            self.db, user_char.id, self.playthrough_id
        )

        views: List[RelationshipView] = []
        for rel in relationships:
            other_char = crud.get_character(
                self.db,
                rel.entity2_id if rel.entity1_id == user_char.id else rel.entity1_id,
            )
            if not other_char:
                continue
            views.append(
                RelationshipView(
                    other_character_name=other_char.character_name,
                    relationship_type=rel.relationship_type,
                    trust=rel.trust,
                    affection=rel.affection,
                    familiarity=rel.familiarity,
                    history_summary=rel.history_summary,
                )
            )
        return views

    def _collect_active_arcs(self) -> List[ActiveArcView]:
        arcs = crud.get_active_story_arcs(self.db, self.playthrough_id)
        return [
            ActiveArcView(arc_name=arc.arc_name, description=arc.description)
            for arc in arcs
        ]

    def _collect_memory_flags(self) -> List[MemoryFlagView]:
        # min_importance and the slice limit are still hardcoded; R5 lifts them
        # into config.py.
        flags = crud.get_important_memory_flags(
            self.db, self.playthrough_id, min_importance=7
        )
        return [
            MemoryFlagView(flag_type=flag.flag_type, flag_value=flag.flag_value)
            for flag in flags[:10]
        ]

    def _build_character_view(self, character_id: int) -> Optional[CharacterView]:
        info = self.get_character_info(character_id)
        if not info:
            return None

        sheet_keys = (
            "age",
            "appearance",
            "backstory",
            "personality_traits",
            "speech_patterns",
            "core_values",
            "core_fears",
            "would_never_do",
            "would_always_do",
        )

        return CharacterView(
            id=info["id"],
            name=info["name"],
            character_type=info["type"],
            sheet={key: info.get(key) for key in sheet_keys},
            state=info.get("current_state"),
            goals=info.get("goals", []),
            relationships=info.get("relationships", []),
        )
