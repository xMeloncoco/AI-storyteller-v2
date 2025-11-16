"""
Prompt Templates for AI Interactions

All prompts used in the application are centralized here.
This makes it easy to:
1. Modify prompts without changing code logic
2. Maintain consistency across the application
3. Test different prompt strategies

Important: Good prompts are crucial for AI consistency and quality!
"""
from typing import Dict, Any, List


class PromptTemplates:
    """
    Collection of all prompt templates used in the application
    Each method returns a formatted prompt string
    """

    @staticmethod
    def story_generation_prompt(
        context: str,
        user_action: str,
        character_decisions: List[Dict[str, Any]],
        story_info: Dict[str, Any]
    ) -> str:
        """
        Main story generation prompt

        This is used to generate the narrative response after:
        1. Context has been built
        2. Character decisions have been analyzed
        3. Scene state has been updated

        Args:
            context: Full context including scene, history, characters
            user_action: What the user did/said
            character_decisions: Decisions from each character in the scene
            story_info: Information about the story (title, arc, etc.)
        """
        # Build character decision summaries
        decision_text = ""
        for decision in character_decisions:
            char_name = decision.get("character_name", "Character")
            action = decision.get("action", "respond")
            emotion = decision.get("emotion", "neutral")
            dialogue = decision.get("dialogue", "")
            refuses = decision.get("refuses", False)

            decision_text += f"\n{char_name}:\n"
            decision_text += f"  - Emotional state: {emotion}\n"
            decision_text += f"  - Planned action: {action}\n"
            if refuses:
                decision_text += f"  - REFUSES user action: Yes\n"
                decision_text += f"  - Reason: {decision.get('reason', 'Unknown')}\n"
            if dialogue:
                decision_text += f"  - Will say: {dialogue}\n"

        prompt = f"""You are the narrator of an interactive story called "{story_info.get('title', 'Story')}".

CURRENT CONTEXT:
{context}

CHARACTER DECISIONS (what each character has decided to do):
{decision_text}

USER ACTION:
{user_action}

INSTRUCTIONS:
1. Write the next part of the story as a third-person narrative
2. Include both narration and character dialogue
3. Follow the character decisions above - characters should act as they decided
4. If a character refuses the user's action, make this clear in the narrative
5. Maintain consistency with established character personalities
6. Keep the story engaging and immersive
7. Do not break the fourth wall
8. Write 2-4 paragraphs of narrative

IMPORTANT:
- Characters are NOT controlled by the user - they have their own will
- If a character would refuse or react negatively, show this realistically
- Dialogue should match each character's speech patterns
- Show emotions through actions and expressions, not just telling

Write the next part of the story:"""

        return prompt

    @staticmethod
    def character_decision_prompt(
        character_info: Dict[str, Any],
        context: str,
        user_action: str
    ) -> str:
        """
        Character Decision Layer prompt

        This asks the AI what a character would realistically do
        BEFORE generating the actual story text

        Phase 1.3+ feature: Character consistency and refusal system
        """
        traits = character_info.get("personality_traits", "")
        backstory = character_info.get("backstory", "")
        speech = character_info.get("speech_patterns", "")
        name = character_info.get("name", "Character")
        char_type = character_info.get("type", "Main")

        prompt = f"""You are analyzing what a character would do in a story situation.

CHARACTER: {name}
TYPE: {char_type}
PERSONALITY TRAITS: {traits}
BACKSTORY: {backstory}
SPEECH PATTERNS: {speech}

CURRENT CONTEXT:
{context}

USER ACTION/INPUT:
{user_action}

TASK: Determine what {name} would realistically do in response to this situation.

Consider:
1. Is this action consistent with their personality?
2. Would they agree or refuse?
3. What is their emotional reaction?
4. What would they say or do?

Respond in JSON format:
{{
  "action": "brief description of what they do",
  "dialogue": "what they say (empty string if they stay silent)",
  "emotion": "their current emotional state",
  "refuses": true or false (do they refuse or resist the user's action?),
  "reason": "why they made this decision based on their personality"
}}

Important: Characters have their own will. They can refuse, disagree, or react negatively if that's what their personality dictates.

JSON Response:"""

        return prompt

    @staticmethod
    def scene_change_detection_prompt(
        previous_context: str,
        new_message: str
    ) -> str:
        """
        Detect scene changes from user input or story progression

        Used by lightweight model to quickly detect:
        - Location changes
        - Time changes
        - Characters entering/leaving
        - Significant events

        Phase 1.2+ feature
        """
        prompt = f"""Analyze this story interaction for any scene changes.

PREVIOUS CONTEXT:
{previous_context}

NEW MESSAGE/ACTION:
{new_message}

Detect any of the following changes and respond in JSON format:
{{
  "location_changed": true or false,
  "new_location": "location name if changed, null otherwise",
  "time_changed": true or false,
  "new_time": "time description if changed, null otherwise",
  "characters_entered": ["list", "of", "character", "names"],
  "characters_left": ["list", "of", "character", "names"],
  "significant_event": "brief description of important event, or null"
}}

Only include actual changes that are explicitly mentioned or strongly implied.
Do not infer changes that aren't clearly indicated.

JSON Response:"""

        return prompt

    @staticmethod
    def relationship_update_prompt(
        character1: str,
        character2: str,
        current_relationship: Dict[str, Any],
        recent_interaction: str
    ) -> str:
        """
        Determine how an interaction affects the relationship

        Phase 3.1 feature: Dynamic relationship updates
        """
        trust = current_relationship.get("trust", 0.5)
        affection = current_relationship.get("affection", 0.5)
        familiarity = current_relationship.get("familiarity", 0.0)
        relationship_type = current_relationship.get("type", "acquaintances")

        prompt = f"""Analyze how this interaction affects the relationship between two characters.

CHARACTERS: {character1} and {character2}
RELATIONSHIP TYPE: {relationship_type}
CURRENT VALUES (0.0 to 1.0 scale):
  - Trust: {trust}
  - Affection: {affection}
  - Familiarity: {familiarity}

RECENT INTERACTION:
{recent_interaction}

Based on this interaction, determine the change in relationship values.
Values should change by small amounts (-0.1 to +0.1 typically).
Major events might cause larger changes (-0.3 to +0.3).

Respond in JSON format:
{{
  "trust_change": number between -0.3 and 0.3,
  "affection_change": number between -0.3 and 0.3,
  "familiarity_change": number between 0.0 and 0.2 (familiarity only increases),
  "reason": "brief explanation of why these changes occurred"
}}

Note: Familiarity only increases as characters spend time together.

JSON Response:"""

        return prompt

    @staticmethod
    def story_arc_check_prompt(
        current_flags: List[str],
        arc_info: Dict[str, Any],
        recent_events: str
    ) -> str:
        """
        Check if story arc should be activated or completed

        Phase 2.2 feature: Story arc progression
        """
        arc_name = arc_info.get("name", "Arc")
        start_condition = arc_info.get("start_condition", "")
        completion_condition = arc_info.get("completion_condition", "")

        prompt = f"""Check if a story arc should be activated or completed based on current story state.

ARC: {arc_name}
START CONDITION: {start_condition}
COMPLETION CONDITION: {completion_condition}

CURRENT STORY FLAGS:
{', '.join(current_flags) if current_flags else 'None'}

RECENT EVENTS:
{recent_events}

Determine:
1. Should this arc be activated (if not already active)?
2. Should this arc be completed (if currently active)?

Respond in JSON format:
{{
  "should_activate": true or false,
  "activation_reason": "why or why not",
  "should_complete": true or false,
  "completion_reason": "why or why not"
}}

JSON Response:"""

        return prompt

    @staticmethod
    def memory_importance_prompt(
        event_description: str,
        story_context: str
    ) -> str:
        """
        Determine how important an event is for memory storage

        Phase 1.3 feature: Memory flags and importance scoring
        """
        prompt = f"""Rate the importance of this event for story memory.

EVENT:
{event_description}

STORY CONTEXT:
{story_context}

Consider:
1. Is this a key plot point?
2. Does it change relationships significantly?
3. Will characters need to remember this later?
4. Is this a promise, revelation, or turning point?

Respond in JSON format:
{{
  "importance": number from 1 to 10 (10 = extremely important),
  "flag_type": "type of event (e.g., revelation, promise, conflict, achievement)",
  "summary": "brief summary of what happened",
  "should_remember": true or false
}}

JSON Response:"""

        return prompt

    @staticmethod
    def generate_more_prompt(
        context: str,
        last_narrative: str,
        characters_in_scene: List[Dict[str, Any]]
    ) -> str:
        """
        Generate additional narrative without user input

        Phase 3.2 feature: GENERATE MORE option
        """
        char_list = ", ".join([c.get("name", "Character") for c in characters_in_scene])

        prompt = f"""Continue the story narrative without requiring user action.

CURRENT CONTEXT:
{context}

LAST NARRATIVE:
{last_narrative}

CHARACTERS IN SCENE:
{char_list}

INSTRUCTIONS:
1. Continue the story naturally from where it left off
2. Have characters interact with each other or react to the situation
3. Move the story forward slightly
4. Leave room for user interaction (don't resolve everything)
5. Maintain character personalities and story consistency
6. Write 1-2 paragraphs

Continue the story:"""

        return prompt

    @staticmethod
    def coherence_check_prompt(
        generated_text: str,
        context: str,
        character_info: List[Dict[str, Any]]
    ) -> str:
        """
        Check if generated text makes sense and is consistent

        Phase 4 feature: MAKE IT MAKE SENSE
        This is an extra validation step
        """
        char_summary = ""
        for char in character_info:
            char_summary += f"- {char.get('name')}: {char.get('traits', 'unknown')}\n"

        prompt = f"""Check if this generated story text is consistent and makes sense.

CONTEXT:
{context}

CHARACTER INFORMATION:
{char_summary}

GENERATED TEXT TO CHECK:
{generated_text}

Check for:
1. Character consistency - do they act according to their traits?
2. Logic errors - does the narrative make sense?
3. Contradictions - does it contradict established facts?
4. Tone consistency - does it match the story mood?

Respond in JSON format:
{{
  "is_consistent": true or false,
  "issues": ["list of any issues found"],
  "suggestions": ["suggestions for improvement if needed"],
  "severity": "none", "minor", or "major"
}}

JSON Response:"""

        return prompt

    @staticmethod
    def character_knowledge_check_prompt(
        character_name: str,
        known_facts: List[str],
        generated_dialogue: str
    ) -> str:
        """
        Check if character is using knowledge they shouldn't have

        Phase 1.3 feature: Prevent mind-reading
        """
        facts_text = "\n".join([f"- {fact}" for fact in known_facts]) if known_facts else "- Nothing specific"

        prompt = f"""Check if this character's dialogue uses information they shouldn't know.

CHARACTER: {character_name}

WHAT THIS CHARACTER KNOWS:
{facts_text}

DIALOGUE TO CHECK:
{generated_dialogue}

Does this dialogue reference information the character hasn't learned yet?
This is called "mind-reading" and should be avoided.

Respond in JSON format:
{{
  "uses_unknown_info": true or false,
  "problematic_parts": ["specific parts that use unknown information"],
  "suggested_fix": "how to rewrite if needed"
}}

JSON Response:"""

        return prompt
