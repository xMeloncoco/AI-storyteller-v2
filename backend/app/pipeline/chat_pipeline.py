"""
ChatPipeline - orchestrates the per-turn pipeline described in PIPELINE_STAGES.md.

Each stage is its own method so they can be edited in isolation. The HTTP
handlers in routers/chat.py instantiate this class and call run() (or
generate_more()) and shape the response.

Behavior is intentionally preserved from the prior monolithic chat.py:
same inputs produce the same logs and the same outputs. Future refactors
(R2/R3/R4 and M1+) will sharpen the stage signatures, swap concatenated
context strings for typed bundles, and give the validator teeth.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..ai.context_builder import ContextBuilder
from ..ai.llm_manager import LLMManager
from ..ai.prompts import PromptTemplates
from ..ai.validator import ContentValidator
from ..relationships.updater import RelationshipUpdater
from ..story.progression import StoryProgressionManager
from ..utils.logger import AppLogger, log_error


# Narrator system prompts kept as constants so they're easy to find/edit.
STORY_SYSTEM_PROMPT = """You are the narrator of an interactive story. Write engaging, immersive narrative text that:
1. Follows character personalities consistently
2. Respects character decisions (they can refuse or disagree)
3. Uses third-person perspective
4. Includes both narration and dialogue
5. Maintains story continuity
6. Is appropriate for the story's tone"""

GENERATE_MORE_SYSTEM_PROMPT = """You are continuing an interactive story. Write a brief continuation that:
1. Advances the story slightly
2. Maintains character personalities
3. Leaves room for user interaction
4. Is engaging and immersive"""


@dataclass
class IntakeResult:
    """INTAKE stage output - the saved user-message row."""
    user_conversation: models.Conversation
    raw_message: str


@dataclass
class TriggerResult:
    """TRIGGER_DETECTION stage output - detected scene changes (applied here for now)."""
    scene_changes: Dict[str, Any]


@dataclass
class ContextBundle:
    """
    CONTEXT_GATHERING stage output.

    Currently a thin wrapper around the legacy concatenated string. R2 will
    replace `full_context` with structured per-character views; until then
    the rest of the pipeline keeps consuming the string as before.
    """
    full_context: str
    story_info: Dict[str, Any] = field(default_factory=dict)
    # `characters_in_scene` is populated *after* trigger_detection has had a
    # chance to apply scene changes, matching the prior behavior exactly.
    characters_in_scene: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationResult:
    """VALIDATION stage output."""
    is_valid: bool
    issues: List[str]


@dataclass
class StateUpdateSummary:
    """STATE_UPDATE stage output - what changed downstream of generation."""
    relationship_updates: Dict[str, Any] = field(default_factory=dict)
    story_flags_set: List[str] = field(default_factory=list)


class ChatPipeline:
    """
    Per-turn pipeline for a chat session.

    Construct once per request, call `await run(user_message)`. The returned
    ChatResponse mirrors the prior monolithic behavior exactly.
    """

    def __init__(self, db: Session, session_id: int):
        self.db = db
        self.session_id = session_id
        self.logger = AppLogger(db, session_id)

        self.session = crud.get_session(db, session_id)
        if not self.session:
            # Same loud failure mode the router had before: log + 404.
            log_error(db, f"Session {session_id} not found", "system")
            raise HTTPException(status_code=404, detail="Session not found")

        self.playthrough_id = self.session.playthrough_id

        # Stage actors are shared across the methods of this pipeline.
        self.context_builder = ContextBuilder(db, session_id)
        self.llm_manager = LLMManager(db, session_id)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def run(self, user_message: str) -> schemas.ChatResponse:
        """Run the full per-turn pipeline and return the chat response."""
        self.logger.notification(
            "=== STARTING CHAT PROCESSING ===",
            "system",
            {
                "session_id": self.session_id,
                "playthrough_id": self.playthrough_id,
                "user_message": user_message,
            },
        )

        intake = self.intake(user_message)
        context = self.context_gather()
        trigger = await self.trigger_detection(context, user_message)
        self._populate_characters_in_scene(context)
        decisions = await self.scene_simulation(context, user_message)
        generated_text = await self.generate(context, user_message, decisions)
        validation = self.validate(generated_text, decisions)
        ai_conversation = self.present(generated_text)
        state_update = await self.state_update(
            user_message, generated_text, decisions
        )

        # Touch session activity (was step 10 in the old handler).
        crud.update_session_activity(self.db, self.session_id)

        response = self._build_response(
            generated_text=generated_text,
            ai_conversation=ai_conversation,
            characters_in_scene=context.characters_in_scene,
            state_update=state_update,
        )

        self.logger.notification(
            "Chat response completed successfully",
            "system",
        )

        # Reference unused locals to make intent obvious; intake/trigger/validation
        # carry data future stages will need but the response shape doesn't.
        _ = (intake, trigger, validation)

        return response

    async def generate_more(self) -> schemas.ChatResponse:
        """Continuation path: no user message, just push the story along."""
        self.logger.notification(
            "Generate more request received",
            "system",
        )

        full_context = self.context_builder.build_full_context()
        characters_in_scene = self.context_builder.get_all_characters_in_scene_info()
        last_narrative = self._get_last_narrative()

        prompt = PromptTemplates.generate_more_prompt(
            full_context,
            last_narrative,
            characters_in_scene,
        )

        generated_response = await self.llm_manager.generate_text(
            prompt,
            model_size="large",
            max_tokens=1000,  # Continuations are intentionally shorter.
            system_prompt=GENERATE_MORE_SYSTEM_PROMPT,
        )

        self.logger.ai_decision(
            "Generated continuation",
            "ai",
            {"response_length": len(generated_response)},
        )

        ai_conversation = self.present(generated_response)
        crud.update_session_activity(self.db, self.session_id)

        return schemas.ChatResponse(
            message=generated_response,
            session_id=self.session_id,
            conversation_id=ai_conversation.id,
        )

    # ------------------------------------------------------------------
    # Stage methods (one per PIPELINE_STAGES.md entry)
    # ------------------------------------------------------------------

    def intake(self, user_message: str) -> IntakeResult:
        """Stage 1 - persist the user's raw input."""
        user_conversation = crud.create_conversation(
            self.db,
            schemas.ConversationCreate(
                session_id=self.session_id,
                playthrough_id=self.playthrough_id,
                speaker_type="user",
                speaker_name="User",
                message=user_message,
            ),
        )

        self.logger.notification(
            "User message saved to database",
            "database",
            {"conversation_id": user_conversation.id},
        )

        return IntakeResult(user_conversation=user_conversation, raw_message=user_message)

    def context_gather(self) -> ContextBundle:
        """Stage 3 - capture the context snapshot used by every later stage.

        Built once per turn so that detection, simulation and generation all
        see the same scene state. Characters-in-scene is populated *after*
        trigger_detection (the old handler did the same).
        """
        self.logger.context(
            "Building full context for AI...",
            "memory",
        )

        full_context = self.context_builder.build_full_context()

        self.logger.context(
            "FULL CONTEXT BUILT",
            "memory",
            {
                "context_length": len(full_context),
                "context_preview": (
                    full_context[:1000] + "..." if len(full_context) > 1000 else full_context
                ),
            },
        )

        return ContextBundle(
            full_context=full_context,
            story_info=self.context_builder.get_story_info(),
        )

    async def trigger_detection(
        self,
        context: ContextBundle,
        user_message: str,
    ) -> TriggerResult:
        """Stage 2 - detect (and apply) scene changes against the snapshot."""
        self.logger.ai_decision(
            "Analyzing user input for scene changes...",
            "ai",
        )

        scene_changes = await self.llm_manager.detect_scene_changes(
            context.full_context,
            user_message,
        )

        self.logger.ai_decision(
            "Scene change analysis complete",
            "ai",
            scene_changes,
        )

        if scene_changes.get("location_changed") or scene_changes.get("time_changed"):
            self.context_builder.update_scene_state(
                location=scene_changes.get("new_location"),
                time_of_day=scene_changes.get("new_time"),
            )

            self.logger.notification(
                "Scene changed - updating state",
                "story",
                {
                    "new_location": scene_changes.get("new_location"),
                    "new_time": scene_changes.get("new_time"),
                },
            )

        return TriggerResult(scene_changes=scene_changes)

    async def scene_simulation(
        self,
        context: ContextBundle,
        user_message: str,
    ) -> List[Dict[str, Any]]:
        """Stage 4 - ask each NPC what they'd do this turn."""
        character_decisions: List[Dict[str, Any]] = []

        for char_info in context.characters_in_scene:
            if char_info.get("type") == "User":
                self.logger.notification(
                    f"Skipping user character: {char_info.get('name')}",
                    "character",
                )
                continue

            self.logger.ai_decision(
                f"Analyzing what {char_info.get('name')} would do...",
                "character",
                {
                    "character_name": char_info.get("name"),
                    "character_type": char_info.get("type"),
                    "personality": char_info.get("personality_traits"),
                    "user_action": user_message,
                },
            )

            decision = await self.llm_manager.analyze_character_decision(
                char_info,
                context.full_context,
                user_message,
            )
            decision["character_name"] = char_info.get("name")
            decision["character_id"] = char_info.get("id")
            character_decisions.append(decision)

            self.logger.ai_decision(
                f"CHARACTER DECISION: {char_info.get('name')}",
                "character",
                {
                    "character": char_info.get("name"),
                    "action": decision.get("action"),
                    "dialogue": decision.get("dialogue"),
                    "emotion": decision.get("emotion"),
                    "refuses_user": decision.get("refuses"),
                    "reasoning": decision.get("reason"),
                },
            )

        return character_decisions

    async def generate(
        self,
        context: ContextBundle,
        user_message: str,
        character_decisions: List[Dict[str, Any]],
    ) -> str:
        """Stage 6 - the big-model story generation call."""
        self.logger.ai_decision(
            "Building story generation prompt...",
            "ai",
            {
                "story_title": context.story_info.get("title"),
                "num_character_decisions": len(character_decisions),
            },
        )

        story_prompt = PromptTemplates.story_generation_prompt(
            context.full_context,
            user_message,
            character_decisions,
            context.story_info,
        )

        self.logger.context(
            "FULL STORY PROMPT (what AI sees)",
            "ai",
            {
                "prompt_length": len(story_prompt),
                "prompt_content": (
                    story_prompt[:2000] + "..." if len(story_prompt) > 2000 else story_prompt
                ),
            },
        )

        self.logger.ai_decision(
            "Sending prompt to AI for story generation...",
            "ai",
            {"model_size": "large", "system_prompt_length": len(STORY_SYSTEM_PROMPT)},
        )

        generated_response = await self.llm_manager.generate_text(
            story_prompt,
            model_size="large",
            system_prompt=STORY_SYSTEM_PROMPT,
        )

        self.logger.ai_decision(
            "AI GENERATED RESPONSE",
            "ai",
            {
                "response_length": len(generated_response),
                "full_response": generated_response,
            },
        )

        return generated_response

    def validate(
        self,
        generated_text: str,
        character_decisions: List[Dict[str, Any]],
    ) -> ValidationResult:
        """Stage 7 - currently warn-only. R4 promotes this to repair/block."""
        validator = ContentValidator(self.db, self.session_id)
        user_character = crud.get_user_character(self.db, self.playthrough_id)
        user_char_id = user_character.id if user_character else None

        is_valid, validation_issues = validator.validate_generated_content(
            generated_text,
            character_decisions,
            user_char_id,
        )

        if not is_valid:
            self.logger.warning(
                f"Generated content failed validation. Issues: {', '.join(validation_issues)}",
                "validation",
                {"issues": validation_issues, "content": generated_text[:500]},
            )
            # Same as the old comment: don't block the story yet. R4 wires
            # repair/block behind VALIDATION_MODE.

        return ValidationResult(is_valid=is_valid, issues=validation_issues)

    def present(self, generated_text: str) -> models.Conversation:
        """Stage 8 - persist the narrator row."""
        return crud.create_conversation(
            self.db,
            schemas.ConversationCreate(
                session_id=self.session_id,
                playthrough_id=self.playthrough_id,
                speaker_type="narrator",
                speaker_name="Narrator",
                message=generated_text,
            ),
        )

    async def state_update(
        self,
        user_message: str,
        generated_text: str,
        character_decisions: List[Dict[str, Any]],
    ) -> StateUpdateSummary:
        """Stage 9 - downstream side-effects (relationships, arc/flag progression)."""
        summary = StateUpdateSummary()

        try:
            updater = RelationshipUpdater(self.db, self.session_id)
            summary.relationship_updates = (
                await updater.update_relationships_from_interaction(
                    user_message,
                    generated_text,
                    character_decisions,
                )
            )
        except Exception as e:
            self.logger.error(
                f"Error updating relationships: {str(e)}",
                "character",
                {"error": str(e)},
            )

        try:
            progression_manager = StoryProgressionManager(self.db, self.playthrough_id)
            summary.story_flags_set = await progression_manager.check_progression(
                user_message,
                generated_text,
                character_decisions,
            )
        except Exception as e:
            self.logger.error(
                f"Error checking story progression: {str(e)}",
                "story",
                {"error": str(e)},
            )

        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _populate_characters_in_scene(self, context: ContextBundle) -> None:
        """Fill in `context.characters_in_scene` after trigger_detection has run.

        The old handler queried scene characters here (after any scene change
        was applied), so we keep that ordering.
        """
        context.characters_in_scene = self.context_builder.get_all_characters_in_scene_info()

        self.logger.context(
            f"Characters in scene: {len(context.characters_in_scene)}",
            "character",
            {
                "characters": [
                    c.get("name", "Unknown") for c in context.characters_in_scene
                ]
            },
        )

    def _get_last_narrative(self) -> str:
        """Most recent narrator message - used to seed generate_more."""
        history = crud.get_conversation_history(self.db, self.session_id, limit=1)
        for msg in reversed(history):
            if msg.speaker_type == "narrator":
                return msg.message
        return ""

    def _build_response(
        self,
        *,
        generated_text: str,
        ai_conversation: models.Conversation,
        characters_in_scene: List[Dict[str, Any]],
        state_update: StateUpdateSummary,
    ) -> schemas.ChatResponse:
        chars_in_scene = [
            schemas.CharacterInScene(
                character_id=c.get("id", 0),
                character_name=c.get("name", "Unknown"),
                character_type=c.get("type", "Unknown"),
                mood=c.get("mood"),
                intent=c.get("intent"),
                position=c.get("position"),
            )
            for c in characters_in_scene
        ]

        current_scene = crud.get_current_scene_state(self.db, self.session_id)
        current_location = current_scene.location if current_scene else None
        current_time = current_scene.time_of_day if current_scene else None

        return schemas.ChatResponse(
            message=generated_text,
            session_id=self.session_id,
            conversation_id=ai_conversation.id,
            characters_in_scene=chars_in_scene if chars_in_scene else None,
            current_location=current_location,
            current_time=current_time,
            relationship_updates=(
                state_update.relationship_updates
                if state_update.relationship_updates
                else None
            ),
            story_flags_set=(
                state_update.story_flags_set if state_update.story_flags_set else None
            ),
        )
