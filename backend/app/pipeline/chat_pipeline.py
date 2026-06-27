"""
ChatPipeline - orchestrates the per-turn pipeline described in PIPELINE_STAGES.md.

Each stage is its own method so they can be edited in isolation. The HTTP
handlers in routers/chat.py instantiate this class and call run() (or
generate_more()) and shape the response.

Behavior is intentionally preserved from the prior monolithic chat.py:
same inputs produce the same logs and the same outputs. Future refactors
(R3/R4 and M1+) will tag log lines per stage and give the validator teeth.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..ai.context_builder import ContextBuilder
from ..ai.llm_manager import LLMManager
from ..ai.prompts import PromptTemplates
from ..ai.validator import ContentValidator
from ..config import settings
from ..relationships.updater import RelationshipUpdater
from ..story.progression import StoryProgressionManager
from ..utils.logger import AppLogger, log_error, pipeline_stage, pipeline_stage_method
from .context_bundle import ContextBundle


# How many characters of the offending text to quote back to the model in
# the repair addendum. M3.3 will replace this with the actual offending
# span identified by the AI critic.
_REPAIR_QUOTE_CHARS = 300


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
class ValidationResult:
    """VALIDATION stage output.

    `final_text` is the text the pipeline should present — either the
    original generation, the repaired one, or (on unrepairable failure)
    the original again as a fallback.
    """
    is_valid: bool
    issues: List[str]
    final_text: str
    repaired: bool = False


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
        with pipeline_stage("PIPELINE"):
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
        bundle = self.context_gather()
        trigger = await self.trigger_detection(bundle, user_message)
        # `bundle` is captured pre-scene-change; rich character info is
        # re-queried post-scene-change for simulation + response shaping
        # (matches the prior handler's ordering exactly).
        rich_characters = self._gather_rich_characters_in_scene()
        decisions = await self.scene_simulation(bundle, rich_characters, user_message)
        generated_text = await self.generate(bundle, user_message, decisions)
        validation = await self.validate(
            bundle, user_message, decisions, generated_text
        )
        # In `repair` mode the validator may have substituted a regenerated
        # text; everywhere downstream uses validation.final_text so we present
        # and persist exactly what passed (or what we fell back to).
        final_text = validation.final_text
        ai_conversation = self.present(final_text)
        state_update = await self.state_update(
            user_message, final_text, decisions
        )

        with pipeline_stage("PIPELINE"):
            # Touch session activity (was step 10 in the old handler).
            crud.update_session_activity(self.db, self.session_id)

            response = self._build_response(
                generated_text=final_text,
                ai_conversation=ai_conversation,
                rich_characters=rich_characters,
                state_update=state_update,
            )

            self.logger.notification(
                "Chat response completed successfully",
                "system",
            )

        # Reference unused locals to make intent obvious; intake/trigger
        # carry data future stages will need but the response shape doesn't.
        _ = (intake, trigger, validation, generated_text)

        return response

    @pipeline_stage_method("GENERATE_MORE")
    async def generate_more(self) -> schemas.ChatResponse:
        """Continuation path: no user message, just push the story along."""
        self.logger.notification(
            "Generate more request received",
            "system",
        )

        bundle = self.context_builder.build_bundle()
        rich_characters = self.context_builder.get_all_characters_in_scene_info()
        last_narrative = self._get_last_narrative()

        prompt = PromptTemplates.generate_more_prompt(
            bundle.to_string(),
            last_narrative,
            rich_characters,
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

    @pipeline_stage_method("INTAKE")
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

    @pipeline_stage_method("CONTEXT")
    def context_gather(self) -> ContextBundle:
        """Stage 3 - capture the structured bundle every later stage reads.

        Built once per turn so that detection and generation see the same
        scene state. Rich character info is queried separately after
        trigger_detection to keep behavior aligned with the prior handler.
        """
        self.logger.context(
            "Building full context for AI...",
            "memory",
        )

        bundle = self.context_builder.build_bundle()
        rendered = bundle.to_string()

        self.logger.context(
            "FULL CONTEXT BUILT",
            "memory",
            {
                "context_length": len(rendered),
                "context_preview": (
                    rendered[:1000] + "..." if len(rendered) > 1000 else rendered
                ),
            },
        )

        return bundle

    @pipeline_stage_method("TRIGGER")
    async def trigger_detection(
        self,
        bundle: ContextBundle,
        user_message: str,
    ) -> TriggerResult:
        """Stage 2 - detect (and apply) scene changes against the snapshot."""
        self.logger.ai_decision(
            "Analyzing user input for scene changes...",
            "ai",
        )

        scene_changes = await self.llm_manager.detect_scene_changes(
            bundle.to_string(),
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

    @pipeline_stage_method("SCENE_SIMULATION")
    async def scene_simulation(
        self,
        bundle: ContextBundle,
        rich_characters: List[Dict[str, Any]],
        user_message: str,
    ) -> List[Dict[str, Any]]:
        """Stage 4 - ask each NPC what they'd do this turn."""
        character_decisions: List[Dict[str, Any]] = []
        context_text = bundle.to_string()

        for char_info in rich_characters:
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
                context_text,
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

    @pipeline_stage_method("GENERATION")
    async def generate(
        self,
        bundle: ContextBundle,
        user_message: str,
        character_decisions: List[Dict[str, Any]],
        addendum: Optional[str] = None,
    ) -> str:
        """Stage 6 - the big-model story generation call.

        The prompt template now accepts the typed bundle directly and
        decides how it gets rendered (single source of truth for what
        the model sees).

        `addendum`, when set, is appended to the story prompt; the validator
        uses this for repair regeneration so the model sees what NOT to do.
        """
        story_info = {
            "id": bundle.story.id,
            "title": bundle.story.title,
            "description": bundle.story.description,
        }

        self.logger.ai_decision(
            "Building story generation prompt...",
            "ai",
            {
                "story_title": bundle.story.title,
                "num_character_decisions": len(character_decisions),
                "has_addendum": bool(addendum),
            },
        )

        story_prompt = PromptTemplates.story_generation_prompt(
            bundle,
            user_message,
            character_decisions,
            story_info,
        )
        if addendum:
            story_prompt = f"{story_prompt}\n\n{addendum}"

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

    @pipeline_stage_method("VALIDATION")
    async def validate(
        self,
        bundle: ContextBundle,
        user_message: str,
        character_decisions: List[Dict[str, Any]],
        generated_text: str,
    ) -> ValidationResult:
        """Stage 7 - decide what to do about validator findings.

        Behavior is controlled by `settings.validation_mode`:

        - `warn` (default): log issues with `validation.warned`, return the
          original text. Preserves prior behavior.
        - `block`: raise HTTP 422 with the issues listed (test/strict mode).
        - `repair`: if a `controls_user` issue is present, regenerate once
          with an addendum that quotes the offending text and tells the
          model not to write the user character. Re-validate; if it still
          fails, log `validation.unrepairable` and fall back to the
          original. Other issue types fall through to warn semantics
          until M3 expands the repair strategies.
        """
        validator = ContentValidator(self.db, self.session_id)
        user_character = crud.get_user_character(self.db, self.playthrough_id)
        user_char_id = user_character.id if user_character else None
        user_char_name = user_character.character_name if user_character else None

        is_valid, issues = validator.validate_generated_content(
            generated_text,
            character_decisions,
            user_char_id,
        )

        mode = (settings.validation_mode or "warn").lower()

        if is_valid:
            self.logger.context(
                "validation.passed",
                "validation",
                {"mode": mode, "text_length": len(generated_text)},
            )
            return ValidationResult(
                is_valid=True,
                issues=[],
                final_text=generated_text,
            )

        if mode == "block":
            self.logger.error(
                "validation.blocked",
                "validation",
                {"issues": issues, "content_preview": generated_text[:500]},
            )
            raise HTTPException(
                status_code=422,
                detail={"validation_issues": issues},
            )

        controls_user = self._has_controls_user_issue(issues)

        if mode == "repair" and controls_user and user_char_name:
            return await self._attempt_repair(
                bundle=bundle,
                user_message=user_message,
                character_decisions=character_decisions,
                original_text=generated_text,
                original_issues=issues,
                user_char_id=user_char_id,
                user_char_name=user_char_name,
                validator=validator,
            )

        # `warn` (or `repair` with no repair strategy yet): keep going with
        # the original text and surface the issues in logs.
        self.logger.warning(
            f"validation.warned: {', '.join(issues)}",
            "validation",
            {
                "mode": mode,
                "issues": issues,
                "content_preview": generated_text[:500],
            },
        )
        return ValidationResult(
            is_valid=False,
            issues=issues,
            final_text=generated_text,
        )

    @staticmethod
    def _has_controls_user_issue(issues: List[str]) -> bool:
        """True if any issue is the validator's user-character-control finding."""
        return any("control user character" in i.lower() for i in issues)

    async def _attempt_repair(
        self,
        *,
        bundle: ContextBundle,
        user_message: str,
        character_decisions: List[Dict[str, Any]],
        original_text: str,
        original_issues: List[str],
        user_char_id: int,
        user_char_name: str,
        validator: ContentValidator,
    ) -> ValidationResult:
        """Regenerate once with an anti-control addendum, re-validate, log result."""
        self.logger.notification(
            "validation.repair_attempt",
            "validation",
            {
                "user_character": user_char_name,
                "original_issues": original_issues,
            },
        )

        quoted = original_text[:_REPAIR_QUOTE_CHARS]
        if len(original_text) > _REPAIR_QUOTE_CHARS:
            quoted += "..."

        addendum = (
            f"You previously wrote:\n\"{quoted}\"\n\n"
            f"Do not write or imply what {user_char_name} (the user's character) "
            f"says, thinks, or does. Rewrite the response without that — narrate "
            f"only the NPCs and the environment."
        )

        repaired_text = await self.generate(
            bundle,
            user_message,
            character_decisions,
            addendum=addendum,
        )

        is_valid, issues = validator.validate_generated_content(
            repaired_text,
            character_decisions,
            user_char_id,
        )

        if is_valid:
            self.logger.notification(
                "validation.repaired",
                "validation",
                {
                    "original_issues": original_issues,
                    "repaired_text_preview": repaired_text[:500],
                },
            )
            return ValidationResult(
                is_valid=True,
                issues=[],
                final_text=repaired_text,
                repaired=True,
            )

        # Repair didn't take. Fall back to the original (matches the prior
        # warn-only behavior) and surface the failure loudly.
        self.logger.error(
            "validation.unrepairable",
            "validation",
            {
                "original_issues": original_issues,
                "remaining_issues": issues,
                "falling_back": "original",
                "repaired_text_preview": repaired_text[:500],
            },
        )
        return ValidationResult(
            is_valid=False,
            issues=issues,
            final_text=original_text,
        )

    @pipeline_stage_method("PRESENTATION")
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

    @pipeline_stage_method("STATE_UPDATE")
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

    @pipeline_stage_method("CONTEXT")
    def _gather_rich_characters_in_scene(self) -> List[Dict[str, Any]]:
        """Re-query characters after trigger_detection so simulation sees the post-change set."""
        rich_characters = self.context_builder.get_all_characters_in_scene_info()

        self.logger.context(
            f"Characters in scene: {len(rich_characters)}",
            "character",
            {
                "characters": [
                    c.get("name", "Unknown") for c in rich_characters
                ]
            },
        )

        return rich_characters

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
        rich_characters: List[Dict[str, Any]],
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
            for c in rich_characters
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
