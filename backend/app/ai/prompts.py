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

CRITICAL RULES - READ CAREFULLY:
1. The user is playing as a character in the story - you NEVER control their character
2. NEVER write dialogue, thoughts, or actions for the user's character
3. ONLY write about NPCs (non-player characters) and the environment
4. Keep your response to 2-4 short paragraphs MAXIMUM - be concise!
5. Characters MUST act consistently with their established personality, values, and constraints
6. Characters have their own goals and motivations - they don't exist just to agree with the user

CHARACTER CONSISTENCY IS CRITICAL:
- Each character has been analyzed and has made a decision based on their personality, goals, and emotional state
- You MUST follow the character decisions provided above
- If a character refuses or resists the user's action, show this clearly in the narrative
- Characters should speak and act according to their established traits and speech patterns
- Do NOT make characters suddenly change personality or act out of character

WHAT TO WRITE:
- NPC reactions, dialogue, and actions (FOLLOWING the character decisions above)
- Environmental descriptions
- What the user sees/hears happening around them
- How NPCs feel (shown through body language, facial expressions, and tone - not internal thoughts)
- Tension and conflict when characters disagree or have different goals

WHAT NOT TO WRITE:
- What the user character says (they already said it!)
- What the user character thinks or feels
- What the user character does next
- Long descriptive passages (keep it brief!)
- Characters behaving inconsistently with their personality
- Everyone agreeing with the user just because they're the protagonist

STYLE GUIDELINES:
- Write in third-person perspective
- Show NPC emotions through actions and expressions, not just stating them
- Match each character's speech patterns and personality EXACTLY
- If a character refuses the user's action, show this through their response
- Keep the pacing tight - no unnecessary details
- Dialogue should be SHORT (1-2 sentences per character response)
- Focus on meaningful reactions, not filler text

LENGTH: 2-4 SHORT PARAGRAPHS. Not more. This is important.

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

        prompt = f"""Continue the story narrative without requiring user action.

CURRENT CONTEXT:
{context}

LAST NARRATIVE:
{last_narrative}

CHARACTERS IN SCENE:
{char_list}

CRITICAL RULES:
- The user is playing as one of the characters - NEVER control their character
- NEVER write dialogue, thoughts, or actions for the user's character
- ONLY write about NPCs and the environment
- Keep it to 2-3 SHORT paragraphs maximum

INSTRUCTIONS:
1. Continue the story naturally from where it left off
2. Have NPCs interact with each other or react to the situation
3. Move the story forward slightly (but don't resolve major conflicts)
4. Leave room for user interaction - don't make big decisions for them
5. Maintain character personalities and story consistency

LENGTH: 2-3 SHORT PARAGRAPHS. Be concise!

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
