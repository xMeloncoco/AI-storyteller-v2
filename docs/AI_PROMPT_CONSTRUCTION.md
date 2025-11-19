# AI Prompt Construction Documentation

This document details exactly what information is fed to the AI at each stage of story generation.

## Overview

The system uses **three different prompts** for different purposes:
1. **Scene Change Detection** - Lightweight model, analyzes user input
2. **Character Decision** - Small model, one prompt per character
3. **Story Generation** - Large model, generates the narrative

---

## 1. Scene Change Detection Prompt

**File:** `backend/app/ai/prompts.py:241`
**Model:** Lightweight (fast, inexpensive)
**When:** Every user message
**Purpose:** Detect location/time changes and character movements

### Prompt Structure

```
Analyze this story interaction for any scene changes.

PREVIOUS CONTEXT:
{full_context from context_builder}

NEW MESSAGE/ACTION:
{user_message}

Detect any of the following changes and respond in JSON format:
{
  "location_changed": true or false,
  "new_location": "location name if changed, null otherwise",
  "time_changed": true or false,
  "new_time": "time description if changed, null otherwise",
  "characters_entered": ["list", "of", "character", "names"],
  "characters_left": ["list", "of", "character", "names"],
  "significant_event": "brief description of important event, or null"
}

Only include actual changes that are explicitly mentioned or strongly implied.
Do not infer changes that aren't clearly indicated.

JSON Response:
```

### Example Input

```
PREVIOUS CONTEXT:
STORY INFORMATION:
Title: Starling Contract
Description: Two childhood friends, separated by tragedy...

CURRENT SCENE:
Location: Miriam's Apartment - Living Room
Time: Early evening, 8:00 PM

CHARACTERS PRESENT:
- Miriam Cross (User character)

RECENT CONVERSATION:
Narrator: The doorbell rang at exactly eight o'clock...

NEW MESSAGE/ACTION:
"I take a deep breath and open the door, keeping my expression neutral."
```

---

## 2. Character Decision Prompt

**File:** `backend/app/ai/prompts.py:117`
**Model:** Small/Medium
**When:** For each non-user character in the scene
**Purpose:** Determine what each character would realistically do

### Prompt Structure

```
You are analyzing what a character would do in a story situation.

CHARACTER: {character_name}
TYPE: {character_type}
PERSONALITY TRAITS: {personality_traits}
BACKSTORY: {backstory}
SPEECH PATTERNS: {speech_patterns}
CORE VALUES: {core_values}
CORE FEARS: {core_fears}
WOULD NEVER DO: {would_never_do}
WOULD ALWAYS DO: {would_always_do}

CURRENT EMOTIONAL STATE: {emotional_state}
EMOTION CAUSE: {emotion_cause}
STRESS LEVEL: {stress_level}/1.0 (higher = more impulsive, less rational)
MENTAL CLARITY: {mental_clarity}/1.0 (higher = more rational thinking)
PRIMARY CONCERN: {primary_concern}

ACTIVE GOALS (what they're trying to achieve):
  [{goal_type}] (priority {priority}/10): {goal_content}
  [{goal_type}] (priority {priority}/10): {goal_content}
  ...

RELATIONSHIPS:
  {other_character}: Trust={trust}, Affection={affection}
  {other_character}: Trust={trust}, Affection={affection}
  ...

CURRENT CONTEXT:
{full_context}

USER ACTION/INPUT:
{user_message}

TASK: Determine what {character_name} would realistically do in response.

Consider:
1. Their personality traits and values
2. Their current emotional state and stress level
3. Their active goals
4. Their relationships with others present
5. What they WOULD NEVER DO and WOULD ALWAYS DO
6. Their fears and what they care about

CRITICAL: This character MUST remain consistent with their established traits.
- If the situation conflicts with "WOULD NEVER DO", they WILL refuse/resist
- If their goals are threatened, they will act to protect them
- Emotional state and stress affect HOW they respond

Respond in JSON format:
{
  "action": "brief description of what they do",
  "dialogue": "what they say (1-2 sentences max, empty string if silent)",
  "emotion": "their current emotional state",
  "refuses": true or false (do they refuse or resist the user's action?),
  "reason": "why they made this decision based on personality, goals, state"
}

Important: Characters have their own will. They can refuse, disagree, or react
negatively if that's what their personality dictates.

JSON Response:
```

### Example Input for Alexander Sterling

```
CHARACTER: Alexander Sterling
TYPE: Main
PERSONALITY TRAITS: dominant, short-tempered, arrogant, ruthless, protective, surprisingly vulnerable, secretive
BACKSTORY: Heir to Sterling Enterprises, sent to boarding school at 13 to separate him from Miriam, which broke something fundamental in him. Spent his teens and twenties as a notorious playboy...
SPEECH PATTERNS: Commanding and confident, uses his voice like a weapon. Can be charming or intimidating depending on his goal. Deflects with humor when uncomfortable.
CORE VALUES: protection, redemption, justice (hidden), loyalty
CORE FEARS: losing Miriam again, becoming his parents, his secrets being discovered, being truly seen
WOULD NEVER DO: abandon Miriam again, hurt innocents, let his parents destroy more lives
WOULD ALWAYS DO: protect those he cares about, honor his hidden commitments, maintain his facade

CURRENT EMOTIONAL STATE: tense and guarded
EMOTION CAUSE: seeing Miriam again after 15 years
STRESS LEVEL: 0.7/1.0
MENTAL CLARITY: 0.6/1.0
PRIMARY CONCERN: not revealing his guilt over leaving her

ACTIVE GOALS:
  [SHORT_TERM] (priority 8/10): Get through this dinner without a scene
  [LONG_TERM] (priority 9/10): Protect Miriam from his parents
  [HIDDEN] (priority 7/10): Find a way to explain why he left

RELATIONSHIPS:
  Miriam Cross: Trust=0.2, Affection=0.3

CURRENT CONTEXT:
[Full context from context builder...]

USER ACTION/INPUT:
"Fine. Let's just get this over with." *I grab my coat*
```

### Example Output

```json
{
  "action": "steps inside, maintaining distance but his eyes track her every movement",
  "dialogue": "The car is downstairs. We should leave now if we want to avoid the worst of the photographers.",
  "emotion": "tense with underlying guilt",
  "refuses": false,
  "reason": "Alex wants to protect Miriam from media scrutiny. His protective instinct overrides his discomfort. He keeps it professional to maintain emotional distance, which aligns with his 'maintain facade' behavior."
}
```

---

## 3. Story Generation Prompt

**File:** `backend/app/ai/prompts.py:22`
**Model:** Large (most capable, most expensive)
**When:** After all character decisions are made
**Purpose:** Generate the actual narrative response

### Prompt Structure

```
You are the narrator of an interactive story called "{story_title}".

CURRENT CONTEXT:
{full_context from context_builder}

CHARACTER DECISIONS (what each character has decided to do):

{character_name}:
  - Emotional state: {emotion}
  - Planned action: {action}
  - REFUSES user action: {refuses} (Yes/No)
  - Reason: {reason}
  - Will say: {dialogue}

{character_name}:
  - Emotional state: {emotion}
  - Planned action: {action}
  ...

USER ACTION:
{user_message}

CRITICAL RULES - READ CAREFULLY:
1. The user is playing as a character - you NEVER control their character
2. NEVER write dialogue, thoughts, or actions for the user's character
3. ONLY write about NPCs and the environment
4. Keep your response to 2-4 short paragraphs MAXIMUM - be concise!
5. Characters MUST act consistently with established personality, values, constraints
6. Characters have their own goals - they don't exist just to agree with the user

CHARACTER CONSISTENCY IS CRITICAL:
- Each character has been analyzed and made a decision based on personality/goals
- You MUST follow the character decisions provided above
- If a character refuses/resists the user's action, show this clearly
- Characters should speak/act according to their established traits/patterns
- Do NOT make characters suddenly change personality

WHAT TO WRITE:
- NPC reactions, dialogue, and actions (FOLLOWING the character decisions above)
- Environmental descriptions
- What the user sees/hears happening around them
- How NPCs feel (shown through body language/expressions, not internal thoughts)
- Tension and conflict when characters disagree

WHAT NOT TO WRITE:
- What the user character says (they already said it!)
- What the user character thinks or feels
- What the user character does next
- Long descriptive passages (keep it brief!)
- Characters behaving inconsistently
- Everyone agreeing with the user just because they're the protagonist

STYLE GUIDELINES:
- Write in third-person perspective
- Show NPC emotions through actions/expressions, not just stating them
- Match each character's speech patterns and personality EXACTLY
- If a character refuses the user's action, show this through their response
- Keep the pacing tight - no unnecessary details
- Dialogue should be SHORT (1-2 sentences per character response)
- Focus on meaningful reactions, not filler text

LENGTH: 2-4 SHORT PARAGRAPHS. Not more. This is important.

Write the next part of the story:
```

### System Prompt (Sent Separately)

```
You are the narrator of an interactive story. Write engaging, immersive
narrative text that:
1. Follows character personalities consistently
2. Respects character decisions (they can refuse or disagree)
3. Uses third-person perspective
4. Includes both narration and dialogue
5. Maintains story continuity
6. Is appropriate for the story's tone
```

### Example Full Input

```
You are the narrator of an interactive story called "Starling Contract".

CURRENT CONTEXT:
STORY INFORMATION:
Title: Starling Contract
Description: Two childhood friends, separated by tragedy and family interference...

CURRENT SCENE:
Location: Miriam's Apartment - Living Room
Time: Early evening, 8:00 PM
Mood: tense

CHARACTERS PRESENT:
- Miriam Cross (User character)
- Alexander Sterling (Main)

RECENT CONVERSATION:
Narrator: The doorbell rang at exactly eight o'clock...
User: "Fine. Let's just get this over with." *I grab my coat*

RELATIONSHIP STATUS:
Alexander Sterling:
  Relationship: childhood friends turned bitter strangers
  Trust: 0.20
  Affection: 0.30
  Familiarity: 0.60
  History: Were best friends from age 5-13...

CHARACTER DECISIONS (what each character has decided to do):

Alexander Sterling:
  - Emotional state: tense with underlying guilt
  - Planned action: steps inside, maintaining distance but his eyes track her every movement
  - REFUSES user action: No
  - Reason: Alex wants to protect Miriam from media scrutiny. His protective instinct overrides his discomfort.
  - Will say: The car is downstairs. We should leave now if we want to avoid the worst of the photographers.

USER ACTION:
"Fine. Let's just get this over with." *I grab my coat*

[CRITICAL RULES section...]

Write the next part of the story:
```

### Example Output

```
Alex stepped inside, and the apartment suddenly felt smaller. He maintained
a careful distance, but his steel-gray eyes tracked Miriam's every movement
as she reached for her coat. Fifteen years had changed them both, but the
tension between them felt achingly familiar.

"The car is downstairs," he said, his voice carefully controlled. "We should
leave now if we want to avoid the worst of the photographers." He didn't
mention that he'd already paid building security to clear the side entrance,
or that he'd been planning this extraction for days. Some protective instincts
never died, even when buried under years of resentment.

His hand moved toward her coat as if to help, then stopped mid-reach. The
gesture was automatic, a ghost of the boy who used to walk her home from
school. But that boy was gone, and the woman before him had made it clear
she didn't need his help with anything. Alex dropped his hand and stepped
back, jaw tight.

"After you," he said, gesturing toward the door with formal courtesy that
felt like a wall between them.
```

---

## Full Context Structure

The `full_context` variable that appears in all prompts is built by `ContextBuilder` and contains:

```
STORY INFORMATION:
Title: {story.title}
Description: {story.description}

CURRENT SCENE:
Location: {scene.location}
Time: {scene.time_of_day}
Weather: {scene.weather}
Mood: {scene.emotional_tone}
Context: {scene.scene_context}

CHARACTERS PRESENT:
- {character_name} ({character_type})
  - Mood: {mood}
  - Intent: {intent}
- {character_name} ({character_type})
  ...

RECENT CONVERSATION:
{speaker}: {message}

{speaker}: {message}
...

RELATIONSHIP STATUS:
{other_character}:
  Relationship: {relationship_type}
  Trust: {trust}
  Affection: {affection}
  Familiarity: {familiarity}
  History: {history_summary}

ACTIVE STORY ARCS:
- {arc_name}: {arc_description}
- {arc_name}: {arc_description}

IMPORTANT MEMORIES:
- [{flag_type}] {flag_value}
- [{flag_type}] {flag_value}
```

## Key Design Principles

1. **Separation of Concerns:** Character logic (decisions) is separate from narrative generation
2. **Consistency Enforcement:** Character decisions are made BEFORE narrative, then narrative MUST follow them
3. **Explicit Constraints:** The prompts explicitly tell the AI what NOT to do (control user character)
4. **Conciseness:** Multiple reminders to keep responses short (2-4 paragraphs)
5. **Character Agency:** Characters can refuse, disagree, and have their own goals
6. **Context Richness:** Full context includes relationships, history, arcs, and memories
7. **Validation:** Generated content is validated against character decisions

## Placeholders Guide

When reviewing prompts, you'll see these placeholders:

- `{story_title}` - Story name from database
- `{full_context}` - Complete context built by ContextBuilder
- `{user_message}` - The user's input/action
- `{character_name}` - Character's name
- `{character_type}` - User, Main, Support, or Antagonist
- `{personality_traits}` - Comma-separated list
- `{backstory}` - Character's background story
- `{speech_patterns}` - How character speaks
- `{core_values}` - What character values most
- `{core_fears}` - What character fears most
- `{would_never_do}` - Hard boundaries for character
- `{would_always_do}` - Character's consistent behaviors
- `{emotional_state}` - Current emotion (if tracked)
- `{stress_level}` - 0.0 to 1.0, affects impulsiveness
- `{mental_clarity}` - 0.0 to 1.0, affects rationality
- `{goal_type}` - short_term, long_term, hidden, etc.
- `{goal_content}` - Description of the goal
- `{priority}` - 1-10 importance rating
- `{trust}` - 0.0 to 1.0
- `{affection}` - 0.0 to 1.0
- `{familiarity}` - 0.0 to 1.0

All placeholders are filled by the respective builder/manager classes before sending to AI.
