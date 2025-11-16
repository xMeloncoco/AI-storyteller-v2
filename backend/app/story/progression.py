"""
Story Progression Manager - Phase 2.2

Handles story arc progression, episode triggers, and story flags.
Ensures the story stays on track while allowing player freedom.

Key responsibilities:
1. Track story flags (events that happened)
2. Check arc activation conditions
3. Monitor episode completion
4. Prevent story from straying too far
"""
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..ai.llm_manager import LLMManager
from ..ai.prompts import PromptTemplates
from ..utils.logger import AppLogger


class StoryProgressionManager:
    """
    Manages story progression and arc tracking

    Phase 2.2 feature: Story Arcs & Episodes
    """

    def __init__(self, db: Session, playthrough_id: int):
        """
        Initialize the story progression manager

        Args:
            db: Database session
            playthrough_id: Current playthrough ID
        """
        self.db = db
        self.playthrough_id = playthrough_id
        self.logger = AppLogger(db, None)

        self.logger.notification(
            f"Story progression manager initialized for playthrough {playthrough_id}",
            "story"
        )

    async def check_progression(
        self,
        user_message: str,
        ai_response: str,
        character_decisions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Check for story progression after an interaction

        This method:
        1. Analyzes the interaction for important events
        2. Sets story flags if needed
        3. Checks if arcs should be activated/completed
        4. Returns list of new flags set

        Args:
            user_message: What the user said/did
            ai_response: The generated story response
            character_decisions: Character decision data

        Returns:
            List of story flag names that were set
        """
        self.logger.notification(
            "Checking story progression",
            "story"
        )

        new_flags = []

        # Step 1: Check for important events and set flags
        event_flags = await self._analyze_for_story_flags(
            user_message,
            ai_response,
            character_decisions
        )

        for flag in event_flags:
            self._set_story_flag(flag["name"], flag["value"], "ai_analysis")
            new_flags.append(flag["name"])

        # Step 2: Check if any arcs should be activated
        await self._check_arc_activation()

        # Step 3: Check if any active arcs should be completed
        await self._check_arc_completion()

        # Step 4: Check if story is straying too far (future feature)
        # await self._check_story_coherence()

        if new_flags:
            self.logger.notification(
                f"Set {len(new_flags)} story flags",
                "story",
                {"flags": new_flags}
            )

        return new_flags

    async def _analyze_for_story_flags(
        self,
        user_message: str,
        ai_response: str,
        character_decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Analyze the interaction for important events that should be flagged

        Uses AI to detect:
        - First meetings
        - Major reveals
        - Promises made
        - Conflicts started/resolved
        - Relationship milestones
        """
        # Build context for analysis
        decisions_summary = ""
        for decision in character_decisions:
            char_name = decision.get("character_name", "Unknown")
            action = decision.get("action", "unknown")
            emotion = decision.get("emotion", "neutral")
            decisions_summary += f"- {char_name}: {action} (feeling {emotion})\n"

        interaction_text = f"""
User action: {user_message}

Character reactions:
{decisions_summary}

Story response: {ai_response[:500]}
"""

        # Get current flags for context
        current_flags = crud.get_story_flags(self.db, self.playthrough_id)
        current_flag_names = [f.flag_name for f in current_flags]

        # Use AI to detect important events
        llm_manager = LLMManager(self.db, None)

        prompt = f"""Analyze this story interaction for important events that should be tracked as story flags.

CURRENT STORY FLAGS (already set):
{', '.join(current_flag_names) if current_flag_names else 'None'}

CURRENT INTERACTION:
{interaction_text}

Identify any NEW important events such as:
- First time meeting a character
- Major revelations or secrets discovered
- Promises made
- Conflicts started or resolved
- Important locations visited
- Key items obtained
- Emotional breakthroughs

Respond in JSON format with a list of flags to set:
{{
  "flags": [
    {{"name": "flag_name_in_snake_case", "value": "true_or_description"}},
    ...
  ]
}}

Only include truly significant events. Don't set flags for minor interactions.
If no important events occurred, return an empty list.

JSON Response:"""

        try:
            response = await llm_manager.generate_text(
                prompt,
                model_size="small",
                temperature=0.3
            )

            result = json.loads(response)
            flags = result.get("flags", [])

            # Filter out flags that are already set
            new_flags = [
                f for f in flags
                if f.get("name") not in current_flag_names
            ]

            return new_flags

        except json.JSONDecodeError:
            self.logger.error(
                "Failed to parse story flag analysis",
                "story"
            )
            return []
        except Exception as e:
            self.logger.error(
                f"Error analyzing story flags: {str(e)}",
                "story"
            )
            return []

    def _set_story_flag(self, flag_name: str, flag_value: str, set_by: str) -> None:
        """
        Set a story flag in the database
        """
        # Check if flag already exists
        existing = crud.check_story_flag(self.db, self.playthrough_id, flag_name)
        if existing:
            self.logger.notification(
                f"Story flag {flag_name} already set",
                "story"
            )
            return

        flag_data = schemas.StoryFlagCreate(
            playthrough_id=self.playthrough_id,
            flag_name=flag_name,
            flag_value=flag_value,
            set_by=set_by
        )

        crud.create_story_flag(self.db, flag_data)

        self.logger.edit(
            f"Set story flag: {flag_name}",
            "story",
            {"flag_name": flag_name, "flag_value": flag_value}
        )

    async def _check_arc_activation(self) -> None:
        """
        Check if any story arcs should be activated based on current flags
        """
        # Get all inactive arcs for this playthrough
        inactive_arcs = self.db.query(models.StoryArc).filter(
            models.StoryArc.playthrough_id == self.playthrough_id,
            models.StoryArc.is_active == 0,
            models.StoryArc.is_completed == 0
        ).all()

        if not inactive_arcs:
            return

        # Get current flags
        current_flags = crud.get_story_flags(self.db, self.playthrough_id)
        flag_names = [f.flag_name for f in current_flags]

        for arc in inactive_arcs:
            if arc.start_condition:
                try:
                    # Parse start condition (expecting JSON)
                    condition = json.loads(arc.start_condition)

                    # Check if all required flags are set
                    required_flags = condition.get("flags", [])
                    if all(flag in flag_names for flag in required_flags):
                        # Activate the arc
                        crud.activate_story_arc(self.db, arc.id)

                        self.logger.notification(
                            f"Activated story arc: {arc.arc_name}",
                            "story",
                            {"arc_id": arc.id, "condition_met": condition}
                        )

                except json.JSONDecodeError:
                    # If not JSON, treat as simple string condition
                    if arc.start_condition in flag_names:
                        crud.activate_story_arc(self.db, arc.id)
                except Exception as e:
                    self.logger.error(
                        f"Error checking arc activation: {str(e)}",
                        "story"
                    )

    async def _check_arc_completion(self) -> None:
        """
        Check if any active arcs should be marked as completed
        """
        active_arcs = crud.get_active_story_arcs(self.db, self.playthrough_id)

        if not active_arcs:
            return

        # Get current flags
        current_flags = crud.get_story_flags(self.db, self.playthrough_id)
        flag_names = [f.flag_name for f in current_flags]

        for arc in active_arcs:
            if arc.completion_condition:
                try:
                    # Parse completion condition
                    condition = json.loads(arc.completion_condition)

                    # Check if all required flags are set
                    required_flags = condition.get("flags", [])
                    if all(flag in flag_names for flag in required_flags):
                        # Complete the arc
                        crud.complete_story_arc(self.db, arc.id)

                        self.logger.notification(
                            f"Completed story arc: {arc.arc_name}",
                            "story",
                            {"arc_id": arc.id}
                        )

                except json.JSONDecodeError:
                    # If not JSON, treat as simple string condition
                    if arc.completion_condition in flag_names:
                        crud.complete_story_arc(self.db, arc.id)
                except Exception as e:
                    self.logger.error(
                        f"Error checking arc completion: {str(e)}",
                        "story"
                    )

    async def ensure_story_coherence(
        self,
        generated_text: str,
        context: str
    ) -> str:
        """
        Ensure the story doesn't stray too far from intended path

        Future feature: MAKE SURE AI DOESN'T STRAY TOO FAR FROM STORY
        Could reject or modify responses that are too off-track
        """
        # TODO: Implement coherence checking
        # This would check if the generated text stays within story bounds
        return generated_text

    def get_current_story_state(self) -> Dict[str, Any]:
        """
        Get a summary of current story progression

        Useful for debugging and showing to users
        """
        flags = crud.get_story_flags(self.db, self.playthrough_id)
        active_arcs = crud.get_active_story_arcs(self.db, self.playthrough_id)

        return {
            "flags": [{"name": f.flag_name, "value": f.flag_value} for f in flags],
            "active_arcs": [{"name": a.arc_name, "description": a.description} for a in active_arcs],
            "total_flags": len(flags),
            "active_arc_count": len(active_arcs)
        }
