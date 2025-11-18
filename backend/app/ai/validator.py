"""
Validation Module for AI-Generated Content

This module implements Stage 7 of the pipeline: VALIDATION
It checks generated content for consistency and character integrity.

Critical checks:
1. Character consistency - do characters act according to their traits?
2. Constraint validation - do characters violate "would_never_do" rules?
3. Goal consistency - do actions make sense given character goals?
4. Dialogue quality - is dialogue appropriate and not repetitive?
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from .. import crud
from ..utils.logger import AppLogger


class ContentValidator:
    """
    Validates AI-generated content for consistency and quality

    This is a crucial layer that prevents nonsensical or contradictory
    narrative from being displayed to the user.
    """

    def __init__(self, db: Session, session_id: int):
        """
        Initialize validator

        Args:
            db: Database session
            session_id: Current session ID
        """
        self.db = db
        self.session_id = session_id
        self.logger = AppLogger(db, session_id)

    def validate_generated_content(
        self,
        generated_text: str,
        character_decisions: List[Dict[str, Any]],
        user_character_id: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate generated content for consistency and quality

        Args:
            generated_text: The AI-generated narrative text
            character_decisions: List of character decision dictionaries
            user_character_id: ID of the user's character (to check for control)

        Returns:
            Tuple of (is_valid, list_of_issues)
            - is_valid: True if content passes validation
            - list_of_issues: List of validation issues found (empty if valid)
        """
        issues = []

        # Validation 1: Check for user character control
        if user_character_id:
            user_control_issues = self._check_user_character_control(
                generated_text,
                user_character_id
            )
            issues.extend(user_control_issues)

        # Validation 2: Check character consistency with decisions
        decision_issues = self._check_character_decision_consistency(
            generated_text,
            character_decisions
        )
        issues.extend(decision_issues)

        # Validation 3: Check for circular/repetitive dialogue
        repetition_issues = self._check_dialogue_repetition(generated_text)
        issues.extend(repetition_issues)

        # Validation 4: Check for contradictory statements
        contradiction_issues = self._check_contradictions(
            generated_text,
            character_decisions
        )
        issues.extend(contradiction_issues)

        # Validation 5: Check dialogue quality
        quality_issues = self._check_dialogue_quality(generated_text)
        issues.extend(quality_issues)

        is_valid = len(issues) == 0

        if not is_valid:
            self.logger.warning(
                f"Content validation failed with {len(issues)} issues",
                "validation",
                {"issues": issues}
            )
        else:
            self.logger.context("Content validation passed", "validation")

        return is_valid, issues

    def _check_user_character_control(
        self,
        text: str,
        user_character_id: int
    ) -> List[str]:
        """
        Check if the generated text controls the user's character

        This is the #1 rule violation - AI should never control user character
        """
        issues = []

        # Get user character name
        user_char = crud.get_character(self.db, user_character_id)
        if not user_char:
            return issues

        user_name = user_char.character_name

        # Check for dialogue attributed to user character
        # Pattern: "Character Name: dialogue" or quotation after character name
        user_dialogue_patterns = [
            rf'{user_name}\s*:\s*["\']',  # "Name: 'dialogue'"
            rf'{user_name}\s+said\s+["\']',  # "Name said 'dialogue'"
            rf'{user_name}\s+replied\s+["\']',  # "Name replied 'dialogue'"
            rf'{user_name}\s+asked\s+["\']',  # "Name asked 'dialogue'"
        ]

        for pattern in user_dialogue_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(
                    f"Generated text appears to control user character '{user_name}' "
                    f"by writing their dialogue"
                )
                break  # Only report once

        return issues

    def _check_character_decision_consistency(
        self,
        text: str,
        character_decisions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Check if generated text matches character decisions

        The character decision layer determines what each character does.
        The narrative MUST follow these decisions.
        """
        issues = []

        for decision in character_decisions:
            char_name = decision.get("character_name", "")
            planned_action = decision.get("action", "")
            planned_dialogue = decision.get("dialogue", "")
            refuses = decision.get("refuses", False)

            if not char_name:
                continue

            # Check if character appears in text
            if char_name.lower() not in text.lower():
                # Character was decided but doesn't appear - that's ok, might be brief
                continue

            # If character refuses, the refusal should be reflected
            if refuses:
                refusal_keywords = ["refuse", "no", "won't", "can't", "shouldn't", "stop"]
                char_section = self._extract_character_section(text, char_name)

                has_refusal_language = any(
                    keyword in char_section.lower()
                    for keyword in refusal_keywords
                )

                if not has_refusal_language:
                    issues.append(
                        f"Character '{char_name}' was decided to refuse user's action, "
                        f"but narrative doesn't show refusal clearly"
                    )

        return issues

    def _check_dialogue_repetition(self, text: str) -> List[str]:
        """
        Check for circular or highly repetitive dialogue patterns

        This is a common failure mode where AI gets stuck in a loop
        """
        issues = []

        # Extract all dialogue from text
        dialogue_pattern = r'["\']([^"\']+)["\']'
        dialogues = re.findall(dialogue_pattern, text)

        if len(dialogues) > 1:
            # Check for exact repetition
            for i, dialogue in enumerate(dialogues):
                for j, other_dialogue in enumerate(dialogues[i+1:], start=i+1):
                    if dialogue.strip() == other_dialogue.strip():
                        issues.append(
                            f"Dialogue repetition detected: '{dialogue[:50]}...'"
                        )
                        break

        # Check for circular conversation patterns (same phrases repeated)
        if len(dialogues) >= 3:
            # Check if dialogue contains repeated phrases
            dialogue_text = " ".join(dialogues).lower()
            words = dialogue_text.split()

            # Look for 3-word phrases that repeat
            phrases = []
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i+3])
                if phrase in phrases:
                    issues.append(
                        f"Circular dialogue pattern detected - repeated phrase: '{phrase}'"
                    )
                    break
                phrases.append(phrase)

        return issues

    def _check_contradictions(
        self,
        text: str,
        character_decisions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Check for contradictory statements in the narrative

        Examples:
        - Character says they'll do X but then does Y
        - Text contradicts character's decision reason
        """
        issues = []

        # Check for common contradiction keywords
        contradiction_patterns = [
            (r'(?:but|however|although|despite).*(?:but|however|although|despite)',
             "Multiple contradictory statements in same sentence"),
            (r'(?:never|won\'t|can\'t).*(?:yes|will|can)',
             "Contradictory acceptance/refusal"),
        ]

        for pattern, issue_desc in contradiction_patterns:
            if re.search(pattern, text.lower()):
                issues.append(issue_desc)

        return issues

    def _check_dialogue_quality(self, text: str) -> List[str]:
        """
        Check basic dialogue quality issues

        - Excessive length
        - Missing variety
        """
        issues = []

        # Extract dialogue
        dialogue_pattern = r'["\']([^"\']+)["\']'
        dialogues = re.findall(dialogue_pattern, text)

        # Check if any single dialogue is excessively long
        for dialogue in dialogues:
            if len(dialogue.split()) > 50:  # More than 50 words
                issues.append(
                    f"Dialogue is too long ({len(dialogue.split())} words). "
                    f"Keep character responses concise."
                )

        return issues

    def _extract_character_section(self, text: str, character_name: str) -> str:
        """
        Extract the section of text related to a specific character

        Returns all sentences mentioning the character
        """
        sentences = text.split('.')
        relevant_sentences = []

        for sentence in sentences:
            if character_name.lower() in sentence.lower():
                relevant_sentences.append(sentence)

        return '. '.join(relevant_sentences)

    def check_character_constraints(
        self,
        character_id: int,
        playthrough_id: int,
        planned_action: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a planned action violates character constraints

        This checks the character's "would_never_do" rules

        Args:
            character_id: ID of the character
            playthrough_id: Current playthrough
            planned_action: What the character is planning to do

        Returns:
            Tuple of (is_valid, violation_reason)
        """
        character = crud.get_character(self.db, character_id)
        if not character:
            return True, None

        # Check would_never_do
        would_never_do = character.would_never_do or ""

        if would_never_do:
            # Simple keyword matching (could be enhanced with AI)
            never_items = [item.strip().lower() for item in would_never_do.split(',')]
            action_lower = planned_action.lower()

            for never_item in never_items:
                if never_item in action_lower:
                    return False, f"Character would never: {never_item}"

        return True, None
