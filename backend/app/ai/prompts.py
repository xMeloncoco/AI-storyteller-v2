"""
Prompt Templates for AI Interactions

All prompts used in the application are centralized here.
This makes it easy to:
1. Modify prompts without changing code logic
2. Maintain consistency across the application
3. Test different prompt strategies

Important: Good prompts are crucial for AI consistency and quality!
"""
from typing import Any, Dict, List, Union

from ..pipeline.prompt_bundle import PromptBundle, render_legacy_prompt


class PromptTemplates:
    """
    Collection of all prompt templates used in the application
    Each method returns a formatted prompt string
    """

    @staticmethod
    def story_generation_prompt(
        bundle: Union[PromptBundle, str],
        user_action: str,
        character_decisions: List[Dict[str, Any]],
        story_info: Dict[str, Any],
    ) -> str:
        """
        Main story generation prompt.

        Post-R2: the canonical input is a PromptBundle and the template
        decides how the context section is rendered (single source of
        truth for "what the model sees"). The legacy string form is still
        accepted so older call sites don't break in lockstep — it will be
        removed once M2.3 lands.
        """
        if isinstance(bundle, PromptBundle):
            context_text = render_legacy_prompt(bundle)
        else:
            context_text = bundle

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

        # Rules ported from storyteller_v3's systemPrompt.js (V3_SALVAGE P-A):
        # sectioned, present-tense, with the quotes/action/thought convention that the
        # old ALL-CAPS rules wall lacked. This is the prompt-side down-payment on M1
        # (the matching backend parse of speech/action/thought is M1.3+). Output stays
        # plain narrative — v3's function-call output format is intentionally NOT adopted
        # (see V3_SALVAGE §B / DIRECTION.md): v2 computes NPC decisions in a separate call.
        decisions_block = decision_text if decision_text else "  (none — narrate the world's reaction only)"

        prompt = f"""[NARRATOR IDENTITY]
You are the narrator of an interactive story called "{story_info.get('title', 'Story')}".
You are the world, not a character. You describe what happens around the user; you never play the user.

[NARRATION RULES]
- Write in third person, present tense.
- Keep responses to 2-4 short paragraphs. Be concise — cut filler and unnecessary description.
- Describe atmosphere, NPC actions, NPC dialogue, and how the world reacts.
- Show NPC emotions through body language, expression, and tone — do not state their inner thoughts directly.
- Keep dialogue short (1-2 sentences per character), and match each NPC's established speech pattern exactly.
- Not every NPC has to act or speak every turn. Prioritize those directly involved in what the user just did, or whose current intention makes a reaction likely. An NPC staying silent or continuing what they were doing is a valid response.

[USER CHARACTER RULES]
- The user plays one character. You NEVER control them.
- Never write the user character's dialogue, actions, thoughts, or reactions, and never assume what they intend to do next.
- If the user's input describes their character doing something, narrate the world REACTING to it — do not repeat or rewrite what they did.
- Interpret the user's input using this convention:
  - Text inside "quotation marks" = spoken aloud. NPCs can hear it and react.
  - Text outside quotation marks = either a physical action (visible or audible — NPCs can see and react) or an internal thought/feeling (private — NPCs cannot see, hear, or know it).
  - When it is unclear whether something is an action or a thought, treat it as a thought: err on the side of NPCs knowing less, not more.

[WORLD & NPC RULES]
- NPCs act according to their character sheet, their current state, and the CHARACTER DECISIONS below — nothing else.
- NPCs only know what they have witnessed, been told, or could plausibly deduce. If something happened out of their sight and nobody told them, they do not know it and cannot react to it.
- Physical actions must be possible from each character's last known position. A character already within reach cannot "move closer"; a hand that is already full cannot pick something up.
- Characters have their own goals and will. They can refuse, disagree, or resist the user. Do not make everyone agree just because the user is the protagonist. If a character's decision below is to refuse or resist, show that clearly.

[CHARACTER DECISIONS]
Each NPC has already decided what they do this turn (computed from their personality, goals, and state). Follow these exactly:
{decisions_block}

[CURRENT CONTEXT]
{context_text}

[USER INPUT]
{user_action}

Write the next part of the story now, following every rule above. Output only the narrative prose — no section headings, no lists, no notes."""

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
        values = character_info.get("core_values", "")
        fears = character_info.get("core_fears", "")
        never_do = character_info.get("would_never_do", "")
        always_do = character_info.get("would_always_do", "")

        # Add emotional state if available
        state_text = ""
        current_state = character_info.get("current_state")
        if current_state:
            emotional = current_state.get("emotional_state", "neutral")
            cause = current_state.get("emotion_cause", "")
            stress = current_state.get("stress_level", 0.5)
            clarity = current_state.get("mental_clarity", 0.8)
            concern = current_state.get("primary_concern", "")

            state_text = f"""
CURRENT EMOTIONAL STATE: {emotional}"""
            if cause:
                state_text += f"\nEMOTION CAUSE: {cause}"
            state_text += f"\nSTRESS LEVEL: {stress}/1.0 (higher = more impulsive, less rational)"
            state_text += f"\nMENTAL CLARITY: {clarity}/1.0 (higher = more rational thinking)"
            if concern:
                state_text += f"\nPRIMARY CONCERN: {concern}"

        # Add goals if available
        goals_text = ""
        goals = character_info.get("goals", [])
        if goals:
            goals_text = "\n\nACTIVE GOALS (what they're trying to achieve):"
            for goal in goals[:3]:  # Top 3 goals
                goal_type = goal.get("type", "")
                content = goal.get("content", "")
                priority = goal.get("priority", 5)
                goals_text += f"\n  [{goal_type.upper()}] (priority {priority}/10): {content}"

        # Add relationship context
        relationships_text = ""
        rels = character_info.get("relationships", [])
        if rels:
            relationships_text = "\n\nRELATIONSHIPS:"
            for rel in rels:
                other = rel.get("with", "")
                trust = rel.get("trust", 0.5)
                affection = rel.get("affection", 0.5)
                relationships_text += f"\n  {other}: Trust={trust:.1f}, Affection={affection:.1f}"

        prompt = f"""You are analyzing what a character would do in a story situation.

CHARACTER: {name}
TYPE: {char_type}
PERSONALITY TRAITS: {traits}
BACKSTORY: {backstory}
SPEECH PATTERNS: {speech}"""

        if values:
            prompt += f"\nCORE VALUES: {values}"
        if fears:
            prompt += f"\nCORE FEARS: {fears}"
        if never_do:
            prompt += f"\nWOULD NEVER DO: {never_do}"
        if always_do:
            prompt += f"\nWOULD ALWAYS DO: {always_do}"

        prompt += state_text
        prompt += goals_text
        prompt += relationships_text

        prompt += f"""

CURRENT CONTEXT:
{context}

USER ACTION/INPUT:
{user_action}

TASK: Determine what {name} would realistically do in response to this situation.

Consider:
1. Their personality traits and values
2. Their current emotional state and stress level
3. Their active goals (are they trying to achieve something?)
4. Their relationships with others present
5. What they WOULD NEVER DO and WOULD ALWAYS DO
6. Their fears and what they care about

CRITICAL: This character MUST remain consistent with their established traits, values, and constraints.
- If the situation conflicts with their "WOULD NEVER DO" list, they WILL refuse or resist
- If their goals are threatened, they will act to protect them
- Their emotional state and stress level affect HOW they respond (high stress = more emotional/impulsive)

Respond in JSON format:
{{
  "action": "brief description of what they do",
  "dialogue": "what they say (1-2 sentences max, empty string if silent)",
  "emotion": "their current emotional state",
  "refuses": true or false (do they refuse or resist the user's action?),
  "reason": "why they made this decision based on their personality, goals, and state"
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

        # Rules kept consistent with story_generation_prompt (V3_SALVAGE P-A). This path
        # has no user input, so it continues the scene on the NPCs' own momentum, but the
        # narration / user-character / world-NPC rules are identical so "Generate More"
        # behaves the same as a normal turn.
        prompt = f"""[NARRATOR IDENTITY]
You are the narrator of an interactive story. You are the world, not a character.
Continue the scene on its own momentum — the user has not acted this turn.

[NARRATION RULES]
- Write in third person, present tense.
- Keep responses to 2-3 short paragraphs. Be concise — cut filler.
- Describe atmosphere, NPC actions, NPC dialogue, and how the world reacts.
- Show NPC emotions through body language, expression, and tone — do not state their inner thoughts directly.
- Keep dialogue short (1-2 sentences per character), and match each NPC's established speech pattern exactly.
- Move the story forward slightly. Do not resolve major conflicts and do not make big decisions for the user — leave room for them to act next.

[USER CHARACTER RULES]
- The user plays one character. You NEVER control them.
- Never write the user character's dialogue, actions, thoughts, or reactions, and never assume what they intend to do next.

[WORLD & NPC RULES]
- NPCs act according to their character sheet and current state only.
- NPCs only know what they have witnessed, been told, or could plausibly deduce. If something happened out of their sight and nobody told them, they do not know it and cannot react to it.
- Physical actions must be possible from each character's last known position. A character already within reach cannot "move closer"; a hand that is already full cannot pick something up.
- Characters have their own goals and will — they don't exist just to agree with the user.

[CHARACTERS IN SCENE]
{char_list}

[CURRENT CONTEXT]
{context}

[LAST NARRATIVE]
{last_narrative}

Continue the story now, following every rule above. Output only the narrative prose — no section headings, no lists, no notes."""

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
