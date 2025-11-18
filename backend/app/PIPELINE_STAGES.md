# AI Processing Pipeline Stages

This document defines the named stages for processing user input through the AI storytelling system. Each stage has specific responsibilities and uses different AI models and tools.

Reference these stage names in code comments to make it clear where each piece of logic fits in the overall flow.

---

## Pipeline Overview

```
User Input → AI Processing → Database Update → User Output
```

---

## Stage Definitions

### 1. INTAKE
**Purpose:** User input received and validated

**Tasks:**
- Receive raw user message
- Basic validation (not empty, within length limits)
- Log the input
- Capture timestamp

**AI Model:** None (simple validation)

**Database Tables Used:**
- `conversations` (insert new user message)
- `sessions` (update last_active)

**Code Location:** Input handlers, API endpoints

---

### 2. TRIGGER_DETECTION
**Purpose:** Check if user input triggers any story events or flags

**Tasks:**
- Small AI checks: "Is event X happening?" (yes/no questions)
- Evaluate story-specific triggers
- Check arc/episode conditions
- Potentially set story flags

**AI Model:** Small/fast model (GPT-3.5 Turbo or Claude Haiku)

**Database Tables Used:**
- `story_flags` (check and set)
- `story_arcs` (check start/completion conditions)
- `story_episodes` (check trigger conditions)
- `memory_flags` (potentially create new flags)

**Important:**
- Triggers are story-specific (each story has different triggers)
- Some triggers may overlap between stories
- This is NOT complex reasoning, just pattern matching
- "Did user mention X?" → Yes/No

**Code Location:** Trigger detection module

---

### 3. CONTEXT_GATHERING
**Purpose:** Retrieve relevant information and memories for AI context

**Tasks:**
- **ChromaDB semantic search:** Find relevant memories similar to current scene
- **Database queries:** Load character states, goals, relationships, knowledge
- **Prioritization:** Rank by importance × recency × relevance
- **Budget management:** Limit total context to ~2000-3000 tokens per character

**AI Model:** Small model for semantic search queries

**Database Tables Used:**
- `characters` (core identity: values, fears, would_never_do, etc.)
- `character_state` (current emotional/mental state)
- `character_goals` (top 3-5 active goals by priority)
- `character_memories` (top 5-10 by semantic similarity + importance)
- `character_beliefs` (beliefs relevant to current scene)
- `character_avoidances` (if scene contains avoided elements)
- `character_knowledge` (recent/important knowledge)
- `relationships` (with present characters)
- `scene_state` (current scene info)
- `scene_characters` (who's in the scene)

**Retrieval Priority:**
1. Character core identity (always include)
2. Current state (always include)
3. Active goals (top 3 by priority)
4. Relevant memories (top 5-10 by relevance score)
5. Beliefs relevant to scene (top 3-5)
6. Active avoidances (if triggered)
7. Relationships with present characters
8. Recent knowledge (top 5)

**Context Budget:** ~2000-3000 tokens per character (adjust based on character_type priority)

**Code Location:** Context gathering module, ChromaDB integration

---

### 4. SCENE_SIMULATION
**Purpose:** Background AI processes how each character would react

**Tasks:**
- For each character in scene:
  - Consider their goals, state, memories, beliefs
  - Determine internal reaction to user's action
  - Decide character's intent/what they want to do next
  - Update internal character state (not visible to user yet)
- Track character moods, intentions, positions
- Determine who speaks/acts in response

**AI Model:** Medium model (GPT-4 or Claude Sonnet)

**Database Tables Updated:**
- `scene_characters` (update mood, intent, position)
- Internal state tracking (not immediately visible to user)

**Important:**
- This runs in background
- NOT all character thoughts/actions are narrated
- Some characters may react internally without speaking
- Minor characters may have thoughts that aren't mentioned

**Code Location:** Scene simulation module

---

### 5. RESPONSE_PRIORITIZATION
**Purpose:** Determine what's important enough to mention in the narrative

**Tasks:**
- Filter character actions by importance
- Decide which character reactions to narrate
- Minor character actions may be tracked but not mentioned
- Select top N memories/contexts to include in narrative
- Balance between detail and readability

**AI Model:** Small model (decision logic)

**Logic:**
- Main characters: Always mention significant actions
- Support characters: Mention if relevant to scene
- NPCs: Only mention if directly involved
- Background details: Summarize or omit

**Code Location:** Response prioritization module

---

### 6. GENERATION
**Purpose:** Create the actual narrative response

**Tasks:**
- Use filtered, prioritized context
- Generate narrative response from narrator perspective
- Include character dialogues and actions
- Maintain consistent tone and style
- Follow character voice patterns (verbal_patterns, sentence_structure)

**AI Model:** Large model (GPT-4, Claude Sonnet/Opus)

**Database Tables Used (Read Only):**
- All context gathered in CONTEXT_GATHERING stage
- Character verbal patterns, speech styles
- Scene atmosphere and tone

**Important:**
- This is the most expensive stage (large model + large context)
- Must follow character constraints (would_never_do, avoidances)
- Should reference character beliefs and goals naturally
- Maintain narrative consistency

**Code Location:** Story generation module

---

### 7. VALIDATION
**Purpose:** "Make it make sense" - consistency and content checks

**Tasks:**
- **Consistency checks:**
  - Does action contradict character's `would_never_do`?
  - Does action contradict core `values`?
  - Does dialogue match `verbal_patterns` and `speech_patterns`?
  - Is emotional response consistent with `current_emotional_state`?
  - Does action respect `avoidances` (unless override conditions met)?

- **Content policy checks:**
  - SFW violations (if story is SFW-only)
  - Inappropriate content for story rating
  - Other content policy requirements

- **Context checks:**
  - References things not in scene?
  - Characters know things they shouldn't (violates character_knowledge)?
  - Timeline inconsistencies?

**AI Model:** Medium model (GPT-4 or Claude Sonnet)

**If validation fails:**
- **Critical severity:** Regenerate entire response
- **High severity:** Regenerate with correction notes
- **Medium severity:** Make small adjustments
- **Low severity:** Allow with warning logged

**Database Tables Used (Read Only):**
- `characters` (would_never_do, core_values, verbal_patterns)
- `character_state` (current emotional state)
- `character_avoidances` (check if violated)
- `character_knowledge` (ensure no mind-reading)

**Code Location:** Validation module

---

### 8. PRESENTATION
**Purpose:** Display response to user

**Tasks:**
- Format narrative response
- Apply any styling/formatting
- Display to user interface
- Log the output

**AI Model:** None (formatting only)

**Database Tables Updated:**
- `conversations` (insert narrator response)

**Code Location:** Output handlers, API response

---

### 9. STATE_UPDATE
**Purpose:** Update database records based on what happened

**Tasks (in priority order):**
1. **Relationships:** Update trust/affection/familiarity/closeness changes
2. **Character State:** Update emotional state if changed
3. **New Memories:** Store significant events as character_memories
4. **Character Knowledge:** Record new information learned
5. **Goals:** Update goal progress or status
6. **Memory Flags:** Create flags for important events
7. **Beliefs:** Mark beliefs as challenged or reinforced
8. **Scene State:** Update current scene context

**AI Model:** Small/medium model (decision logic for what changed)

**Database Tables Updated:**
- `relationships` (trust, affection, familiarity, closeness, last_interaction)
- `character_state` (emotional state, stress, energy, concerns)
- `character_memories` (create new memories)
- `character_knowledge` (record new knowledge)
- `character_goals` (update progress/status)
- `memory_flags` (anchor important events)
- `character_beliefs` (challenge or reinforce)
- `scene_state` (update scene context)
- `scene_characters` (update who's present, moods)
- `logs` (log all changes for debugging)

**Important:**
- Runs async/in background (don't block user experience)
- Log all changes to `logs` table
- Update multiple tables in single transaction when possible
- Don't update if nothing significant happened

**Code Location:** State update module (runs after PRESENTATION)

---

## Stage Flow Diagram

```
┌─────────────────────┐
│   1. INTAKE         │  User message received
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. TRIGGER_DETECT   │  Check story flags/conditions
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. CONTEXT_GATHER   │  Load memories, state, goals
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. SCENE_SIMULATION │  Background character reactions
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. PRIORITIZATION   │  Filter what to mention
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 6. GENERATION       │  Create narrative
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 7. VALIDATION       │  Consistency + content checks
└──────────┬──────────┘
           │           If fails → regenerate
           ▼
┌─────────────────────┐
│ 8. PRESENTATION     │  Show to user
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 9. STATE_UPDATE     │  Update database (async)
└─────────────────────┘
```

---

## Usage in Code Comments

When writing code, reference these stages explicitly:

```python
# CONTEXT_GATHERING stage: Load character's active goals
def get_character_active_goals(character_id, playthrough_id, limit=3):
    """
    Retrieve character's top active goals by priority.
    Used in CONTEXT_GATHERING stage.
    """
    ...

# VALIDATION stage: Check if action contradicts character values
def validate_character_action(character_id, proposed_action):
    """
    Verify action is consistent with character.
    Used in VALIDATION stage.
    """
    ...

# STATE_UPDATE stage: Update relationship metrics after interaction
def update_relationship_metrics(relationship_id, trust_delta, affection_delta):
    """
    Update trust/affection after character interaction.
    Used in STATE_UPDATE stage.
    """
    ...
```

This makes it immediately clear where each function fits in the pipeline.

---

## Performance Considerations

- **CONTEXT_GATHERING:** Use indexes heavily, cache where possible
- **SCENE_SIMULATION:** Can be parallelized for multiple characters
- **GENERATION:** Most expensive - minimize retries
- **VALIDATION:** Fast checks first, expensive checks only if needed
- **STATE_UPDATE:** Async, don't block user response

---

## Future Enhancements

Potential additions to pipeline:
- **Content moderation stage** (between GENERATION and VALIDATION)
- **User preference adaptation** (learn user preferences over time)
- **Dynamic difficulty adjustment** (adjust story complexity)
- **Multi-path branching** (generate multiple possible responses)
