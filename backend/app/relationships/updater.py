"""
Relationship Updater - Phase 3.1

Handles dynamic relationship updates based on interactions.
After each conversation exchange, analyzes how the interaction
affected relationships between characters.

Trust, affection, and familiarity evolve naturally over time.
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..ai.llm_manager import LLMManager
from ..ai.prompts import PromptTemplates
from ..ai.context_builder import ContextBuilder
from ..utils.logger import AppLogger


class RelationshipUpdater:
    """
    Manages relationship updates based on story interactions

    Phase 3.1 feature: Dynamic Relationships
    """

    def __init__(self, db: Session, session_id: int):
        """
        Initialize the relationship updater

        Args:
            db: Database session
            session_id: Current session ID
        """
        self.db = db
        self.session_id = session_id
        self.logger = AppLogger(db, session_id)

        # Get session and playthrough info
        session = crud.get_session(db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        self.playthrough_id = session.playthrough_id

        self.logger.notification(
            "Relationship updater initialized",
            "character"
        )

    async def update_relationships_from_interaction(
        self,
        user_message: str,
        ai_response: str,
        character_decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update relationships based on the current interaction

        Analyzes the user message, AI response, and character decisions
        to determine how relationships should change.

        Args:
            user_message: What the user said/did
            ai_response: The generated story response
            character_decisions: Decisions made by characters

        Returns:
            Dictionary of relationship updates that occurred
        """
        self.logger.notification(
            "Analyzing interaction for relationship updates",
            "character"
        )

        # Get user character
        user_char = crud.get_user_character(self.db, self.playthrough_id)
        if not user_char:
            self.logger.error(
                "No user character found for playthrough",
                "character"
            )
            return {}

        updates = {}

        # For each character that was involved in this interaction
        for decision in character_decisions:
            char_id = decision.get("character_id")
            char_name = decision.get("character_name")

            if not char_id:
                continue

            # Get the relationship between user and this character
            relationship = crud.get_relationship(
                self.db, user_char.id, char_id, self.playthrough_id
            )

            if not relationship:
                # Try the other direction
                relationship = crud.get_relationship(
                    self.db, char_id, user_char.id, self.playthrough_id
                )

            if not relationship:
                self.logger.notification(
                    f"No relationship found between user and {char_name}",
                    "character"
                )
                continue

            # Analyze how this interaction affects the relationship
            update_result = await self._analyze_relationship_change(
                user_char.character_name,
                char_name,
                relationship,
                user_message,
                ai_response,
                decision
            )

            if update_result:
                updates[char_name] = update_result

        self.logger.notification(
            f"Updated {len(updates)} relationships",
            "character",
            updates
        )

        return updates

    async def _analyze_relationship_change(
        self,
        user_name: str,
        character_name: str,
        relationship,
        user_message: str,
        ai_response: str,
        character_decision: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze how a specific interaction affects one relationship

        Uses the small AI model to determine changes in:
        - Trust
        - Affection
        - Familiarity
        """
        self.logger.context(
            f"Analyzing relationship change: {user_name} <-> {character_name}",
            "character",
            {
                "user": user_name,
                "character": character_name,
                "current_trust": relationship.trust,
                "current_affection": relationship.affection,
                "current_familiarity": relationship.familiarity,
                "relationship_type": relationship.relationship_type
            }
        )

        # Build the interaction summary
        interaction_summary = f"""
User ({user_name}) said/did: {user_message}

{character_name}'s reaction:
- Emotion: {character_decision.get('emotion', 'neutral')}
- Action: {character_decision.get('action', 'respond')}
- Dialogue: {character_decision.get('dialogue', '')}
- Refused user: {character_decision.get('refuses', False)}

Story response excerpt: {ai_response[:500]}...
"""

        self.logger.ai_decision(
            f"Building relationship analysis prompt for {character_name}",
            "character",
            {
                "interaction_summary": interaction_summary,
                "character_emotion": character_decision.get('emotion'),
                "character_refused": character_decision.get('refuses', False)
            }
        )

        # Get current relationship state
        current_rel = {
            "trust": relationship.trust,
            "affection": relationship.affection,
            "familiarity": relationship.familiarity,
            "type": relationship.relationship_type
        }

        # Use AI to analyze the change
        llm_manager = LLMManager(self.db, self.session_id)

        prompt = PromptTemplates.relationship_update_prompt(
            user_name,
            character_name,
            current_rel,
            interaction_summary
        )

        self.logger.context(
            f"FULL RELATIONSHIP PROMPT for {character_name}",
            "ai",
            {
                "prompt_length": len(prompt),
                "prompt_content": prompt[:1500] + "..." if len(prompt) > 1500 else prompt
            }
        )

        try:
            response = await llm_manager.generate_text(
                prompt,
                model_size="small",
                temperature=0.3  # More deterministic
            )

            self.logger.ai_decision(
                f"AI relationship analysis response for {character_name}",
                "ai",
                {
                    "raw_response": response,
                    "character": character_name
                }
            )

            # Parse the response
            changes = json.loads(response)

            # Apply changes
            trust_change = changes.get("trust_change", 0)
            affection_change = changes.get("affection_change", 0)
            familiarity_change = changes.get("familiarity_change", 0)

            # Calculate new values (clamped to 0.0-1.0)
            new_trust = max(0.0, min(1.0, relationship.trust + trust_change))
            new_affection = max(0.0, min(1.0, relationship.affection + affection_change))
            new_familiarity = max(0.0, min(1.0, relationship.familiarity + familiarity_change))

            # Only update if there were actual changes
            if (abs(trust_change) > 0.01 or
                abs(affection_change) > 0.01 or
                abs(familiarity_change) > 0.01):

                # Update the relationship in database
                update_data = schemas.RelationshipUpdate(
                    trust=new_trust,
                    affection=new_affection,
                    familiarity=new_familiarity
                )

                crud.update_relationship(self.db, relationship.id, update_data)

                self.logger.edit(
                    f"Updated relationship with {character_name}",
                    "database",
                    {
                        "character": character_name,
                        "trust": f"{relationship.trust:.2f} -> {new_trust:.2f} ({trust_change:+.2f})",
                        "affection": f"{relationship.affection:.2f} -> {new_affection:.2f} ({affection_change:+.2f})",
                        "familiarity": f"{relationship.familiarity:.2f} -> {new_familiarity:.2f} ({familiarity_change:+.2f})",
                        "reason": changes.get("reason", "Unknown")
                    }
                )

                return {
                    "trust_change": trust_change,
                    "affection_change": affection_change,
                    "familiarity_change": familiarity_change,
                    "new_trust": new_trust,
                    "new_affection": new_affection,
                    "new_familiarity": new_familiarity,
                    "reason": changes.get("reason", "")
                }

        except json.JSONDecodeError as e:
            self.logger.error(
                f"Failed to parse relationship update response",
                "character",
                {"error": str(e)}
            )
        except Exception as e:
            self.logger.error(
                f"Error analyzing relationship change: {str(e)}",
                "character",
                {"error": str(e)}
            )

        return None

    async def check_relationship_milestones(
        self,
        character_id: int
    ) -> List[str]:
        """
        Check if any relationship milestones have been reached

        Future feature: Track significant relationship events
        e.g., "First reached 0.8 trust", "Became close friends", etc.
        """
        # TODO: Implement milestone tracking
        # This could trigger special story events or unlock dialogue options
        return []
