# Database Schema Enhancements for Character Depth

This document outlines all schema changes needed to make characters feel like real people with memory, consistency, and depth.

## Design Philosophy

### Pipeline Stages Reference
```
1. INTAKE               → User input received
2. TRIGGER_DETECTION    → Check story flags/conditions
3. CONTEXT_GATHERING    → Retrieve relevant memories/relationships
4. SCENE_SIMULATION     → Background character reactions
5. RESPONSE_PRIORITIZATION → Filter what to include
6. GENERATION           → Create narrative response
7. VALIDATION           → Consistency + content checks
8. PRESENTATION         → Display to user
9. STATE_UPDATE         → Update database records
```

### Importance Scoring System
All retrievable context should have importance (1-10 scale):
- Memories: importance × recency_factor
- Knowledge: importance × relevance_to_scene
- Relationships: closeness × recent_interaction_factor
- Goals: priority × urgency

### Time Skip Handling
- **Baseline state**: Character's default/general emotional state
- **Current state**: What they feel RIGHT NOW in this scene
- **State decay**: Acute emotions (anger, excitement) decay toward baseline
- **State persistence**: Deep emotions (grief, love) persist longer

---

## NEW TABLES

### 1. character_state
Persistent emotional and mental state of characters across playthrough.

```sql
CREATE TABLE character_state (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    playthrough_id INTEGER NOT NULL,

    -- EMOTIONAL STATE
    -- Baseline: their "normal" emotional state when nothing special is happening
    baseline_emotional_state VARCHAR(100),  -- "generally optimistic", "chronically anxious"

    -- Current: what they feel RIGHT NOW (can differ from baseline)
    current_emotional_state VARCHAR(100),   -- "angry", "heartbroken", "excited"

    -- Why they feel this way (critical for decay logic)
    emotion_cause TEXT,                     -- "Just discovered friend's betrayal"
    emotion_intensity FLOAT DEFAULT 0.5,    -- 0.0 to 1.0, how strongly they feel it
    emotion_started_at DATETIME,            -- For time-based decay calculation

    -- MENTAL STATE
    stress_level FLOAT DEFAULT 0.5,         -- 0.0 to 1.0, affects decision-making
    energy_level FLOAT DEFAULT 0.7,         -- 0.0 to 1.0, affects engagement
    mental_clarity FLOAT DEFAULT 0.8,       -- 0.0 to 1.0, affects rationality

    -- CURRENT FOCUS
    primary_concern TEXT,                   -- What's on their mind right now
    secondary_concerns TEXT,                -- JSON array of other worries

    -- TIMESTAMPS
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (playthrough_id) REFERENCES playthroughs(id)
);

CREATE INDEX idx_char_state_character ON character_state(character_id);
CREATE INDEX idx_char_state_playthrough ON character_state(playthrough_id);
```

**Usage in pipeline:**
- **CONTEXT_GATHERING**: Load character's current state
- **SCENE_SIMULATION**: Use stress_level and mental_clarity to determine reactions
- **STATE_UPDATE**: Update emotional state based on what happened

---

### 2. character_goals
What characters want (critical for consistent motivation).

```sql
CREATE TABLE character_goals (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    playthrough_id INTEGER NOT NULL,

    -- GOAL DEFINITION
    goal_type VARCHAR(50) NOT NULL,     -- "short_term", "long_term", "immediate"
    goal_content TEXT NOT NULL,         -- "Get close to the protagonist"

    -- PRIORITY & STATUS
    priority INTEGER DEFAULT 5,         -- 1-10, used for context prioritization
    status VARCHAR(50) DEFAULT 'active', -- "active", "achieved", "abandoned", "blocked"

    -- BLOCKING FACTORS
    blocking_factors TEXT,              -- JSON array: ["protagonist_distrust", "time_constraints"]

    -- MOTIVATION
    underlying_reason TEXT,             -- WHY they want this (links to backstory/values)

    -- PROGRESS
    progress_notes TEXT,                -- How far along they are

    -- TIMESTAMPS
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,

    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (playthrough_id) REFERENCES playthroughs(id)
);

CREATE INDEX idx_goal_character ON character_goals(character_id);
CREATE INDEX idx_goal_playthrough ON character_goals(playthrough_id);
CREATE INDEX idx_goal_status ON character_goals(status);
CREATE INDEX idx_goal_priority ON character_goals(priority);
```

**Usage in pipeline:**
- **CONTEXT_GATHERING**: Retrieve top 3-5 active goals by priority
- **SCENE_SIMULATION**: Characters act to advance their goals
- **VALIDATION**: Check if action contradicts their stated goals

---

### 3. character_memories
Episodic memory - what happened to the character.

```sql
CREATE TABLE character_memories (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    playthrough_id INTEGER NOT NULL,

    -- MEMORY CONTENT
    memory_type VARCHAR(50) NOT NULL,   -- "personal_experience", "witnessed", "told_about"
    memory_content TEXT NOT NULL,       -- The actual memory description

    -- EMOTIONAL IMPACT
    emotional_valence VARCHAR(50),      -- "positive", "negative", "neutral", "mixed"
    emotional_intensity FLOAT DEFAULT 0.5, -- 0.0 to 1.0, how emotionally charged

    -- IMPORTANCE & RETRIEVAL
    importance INTEGER DEFAULT 5,       -- 1-10, critical for context selection
    last_recalled_at DATETIME,          -- For recency-based retrieval
    recall_count INTEGER DEFAULT 0,     -- How many times accessed (strengthens memory)

    -- CONTEXT
    related_characters TEXT,            -- JSON array of character IDs involved
    location_id INTEGER,                -- Where this happened
    session_id INTEGER,                 -- When this was formed

    -- ASSOCIATIONS (for semantic search)
    tags TEXT,                          -- JSON array: ["betrayal", "trust_broken", "friendship"]

    -- TIMESTAMPS
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (playthrough_id) REFERENCES playthroughs(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_memory_character ON character_memories(character_id);
CREATE INDEX idx_memory_playthrough ON character_memories(playthrough_id);
CREATE INDEX idx_memory_importance ON character_memories(importance);
CREATE INDEX idx_memory_type ON character_memories(memory_type);
CREATE INDEX idx_memory_emotional ON character_memories(emotional_valence);
```

**Usage in pipeline:**
- **CONTEXT_GATHERING**: ChromaDB semantic search + importance/recency ranking
- **SCENE_SIMULATION**: Characters react based on similar past experiences
- **STATE_UPDATE**: Create new memories after significant events

---

### 4. character_beliefs
Semantic memory - beliefs and worldviews characters hold.

```sql
CREATE TABLE character_beliefs (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    playthrough_id INTEGER NOT NULL,

    -- BELIEF CONTENT
    belief_content TEXT NOT NULL,       -- "Humans cannot be trusted"
    belief_category VARCHAR(100),       -- "worldview", "moral_stance", "factual_belief"

    -- STRENGTH & ORIGIN
    strength FLOAT DEFAULT 0.5,         -- 0.0 to 1.0, how firmly held
    origin TEXT,                        -- WHY they believe this (memory_id or backstory reference)
    origin_memory_id INTEGER,           -- Link to character_memories if applicable

    -- IMPORTANCE
    importance INTEGER DEFAULT 5,       -- 1-10, for context prioritization

    -- CHANGE TRACKING
    is_challenged INTEGER DEFAULT 0,    -- Has this belief been questioned?
    challenged_by TEXT,                 -- JSON array of contradicting evidence/events

    -- TIMESTAMPS
    formed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_reinforced_at DATETIME,        -- Last time evidence supported this
    last_challenged_at DATETIME,        -- Last time evidence contradicted this

    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (playthrough_id) REFERENCES playthroughs(id),
    FOREIGN KEY (origin_memory_id) REFERENCES character_memories(id)
);

CREATE INDEX idx_belief_character ON character_beliefs(character_id);
CREATE INDEX idx_belief_playthrough ON character_beliefs(playthrough_id);
CREATE INDEX idx_belief_importance ON character_beliefs(importance);
```

**Usage in pipeline:**
- **CONTEXT_GATHERING**: Load beliefs relevant to current situation
- **SCENE_SIMULATION**: Beliefs guide character reactions and judgments
- **VALIDATION**: Actions shouldn't contradict strongly-held beliefs without reason

---

### 5. character_avoidances
Things characters avoid and WHY (avoidances need underlying reasons).

```sql
CREATE TABLE character_avoidances (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    playthrough_id INTEGER NOT NULL,

    -- AVOIDANCE DEFINITION
    avoidance_type VARCHAR(50),         -- "topic", "location", "person", "activity", "emotion"
    avoidance_target TEXT NOT NULL,     -- "deep water", "talking about father", "showing vulnerability"

    -- UNDERLYING REASON (critical!)
    reason_type VARCHAR(50),            -- "trauma", "fear", "shame", "social_norm", "moral_stance"
    reason_description TEXT NOT NULL,   -- Detailed explanation
    reason_memory_id INTEGER,           -- Link to the memory/trauma that caused this

    -- SEVERITY
    severity INTEGER DEFAULT 5,         -- 1-10, how strongly they avoid it
    importance INTEGER DEFAULT 5,       -- 1-10, for context prioritization

    -- BEHAVIORAL MANIFESTATION
    manifestation TEXT,                 -- "becomes silent, makes excuses to leave"
    override_conditions TEXT,           -- JSON: When would they face this anyway?

    -- TIMESTAMPS
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (playthrough_id) REFERENCES playthroughs(id),
    FOREIGN KEY (reason_memory_id) REFERENCES character_memories(id)
);

CREATE INDEX idx_avoidance_character ON character_avoidances(character_id);
CREATE INDEX idx_avoidance_playthrough ON character_avoidances(playthrough_id);
CREATE INDEX idx_avoidance_severity ON character_avoidances(severity);
```

**Usage in pipeline:**
- **SCENE_SIMULATION**: Check if scene contains avoided elements
- **GENERATION**: Character shows discomfort/avoidance behavior
- **VALIDATION**: Character shouldn't casually engage with avoided topics

---

## MODIFICATIONS TO EXISTING TABLES

### Character Table Additions

Add these columns to the existing `characters` table:

```sql
-- CORE PERSONALITY DEPTH
core_values TEXT,               -- JSON: ["loyalty", "truth", "family", "freedom"]
core_fears TEXT,                -- JSON: ["abandonment", "failure", "loss_of_control"]

-- BEHAVIORAL PATTERNS
would_never_do TEXT,            -- JSON: ["betray_a_friend", "harm_innocent", "lie_to_family"]
would_always_do TEXT,           -- JSON: ["defend_the_weak", "keep_promises"]
comfort_behaviors TEXT,         -- JSON: ["fidgets_with_ring", "paces", "makes_jokes"]

-- SPEECH SPECIFICS (replacing simple speech_patterns)
verbal_patterns TEXT,           -- JSON: {
                                --   "greetings": ["Good day", "Greetings"],
                                --   "agreement": ["Indeed", "Quite so"],
                                --   "exclamations": ["Good heavens"],
                                --   "fillers": ["As it were", "If you will"],
                                --   "avoids": ["yeah", "cool", "awesome"]
                                -- }

sentence_structure TEXT,        -- "complex with subordinate clauses" or "short and direct"
common_phrases TEXT,            -- JSON: ["mark my words", "if you ask me"]

-- DECISION MAKING
decision_style VARCHAR(100),    -- "impulsive", "analytical", "emotional", "cautious"

-- INTERNAL CONFLICT (makes them human!)
internal_contradiction TEXT,    -- "Preaches forgiveness but cannot forgive himself for father's death"

-- SECRETS & HIDDEN LAYERS
secret_kept TEXT,               -- Something they actively hide
vulnerability TEXT,             -- Their deepest weakness
```

**Migration note:** Keep existing `speech_patterns` for backward compatibility, but use `verbal_patterns` going forward.

---

### Relationship Table Additions

Add these columns to the existing `relationships` table:

```sql
-- RELATIONSHIP DEPTH
shared_memories TEXT,           -- JSON array of important shared experiences
inside_jokes TEXT,              -- JSON: ["the coffee incident", "Tuesday's disaster"]

-- CONFLICTS & PROMISES
unresolved_conflicts TEXT,      -- JSON array of ongoing tensions
promises_made TEXT,             -- JSON: [{who: "entity1", promise: "will always be there", date: "..."}]
last_conflict TEXT,             -- Description of most recent conflict
last_conflict_at DATETIME,      -- When it happened

-- RELATIONSHIP QUALITY
closeness FLOAT DEFAULT 0.5,    -- 0.0 to 1.0, overall relationship strength
importance INTEGER DEFAULT 5,   -- 1-10, for context prioritization (major vs minor relationships)

-- INTERACTION PATTERNS
typical_interaction_tone VARCHAR(100),  -- "playful_banter", "professional", "tense", "warm"
conversational_dynamics TEXT,   -- "entity1 teases, entity2 plays along"
```

---

### CharacterKnowledge Table Additions

Add importance scoring to existing table:

```sql
-- IMPORTANCE & RETRIEVAL
importance INTEGER DEFAULT 5,   -- 1-10, for context prioritization
last_accessed_at DATETIME,      -- For recency tracking
access_count INTEGER DEFAULT 0, -- How often this knowledge is referenced
```

---

### MemoryFlags Table - ALREADY HAS IMPORTANCE
Current `memory_flags` table already has:
- `importance` field (1-10)
- `flag_type` field
- Perfect as-is!

---

## CONTEXT GATHERING ALGORITHM

For **Stage 3: CONTEXT_GATHERING**, retrieve context in this priority order:

### 1. Character Core Identity (always include)
```sql
SELECT core_values, core_fears, would_never_do, internal_contradiction, decision_style
FROM characters WHERE id = ?
```

### 2. Current State (always include)
```sql
SELECT * FROM character_state
WHERE character_id = ? AND playthrough_id = ?
```

### 3. Active Goals (top 3 by priority)
```sql
SELECT * FROM character_goals
WHERE character_id = ? AND playthrough_id = ? AND status = 'active'
ORDER BY priority DESC
LIMIT 3
```

### 4. Relevant Memories (top 5-10 by relevance score)
```sql
-- Combine:
-- - ChromaDB semantic similarity to current scene
-- - importance score (1-10)
-- - recency factor (time decay)
-- - emotional intensity

SELECT * FROM character_memories
WHERE character_id = ? AND playthrough_id = ?
ORDER BY (importance * recency_factor * relevance_score) DESC
LIMIT 10
```

### 5. Beliefs Relevant to Scene (top 3-5)
```sql
-- Filter by scene context/topics
SELECT * FROM character_beliefs
WHERE character_id = ? AND playthrough_id = ?
  AND (belief_category = ? OR belief_content LIKE ?)
ORDER BY (strength * importance) DESC
LIMIT 5
```

### 6. Active Avoidances (if scene triggers them)
```sql
SELECT * FROM character_avoidances
WHERE character_id = ? AND playthrough_id = ?
  AND avoidance_target IN (scene_elements)
ORDER BY severity DESC
```

### 7. Relationships (present characters + high importance)
```sql
SELECT * FROM relationships
WHERE playthrough_id = ?
  AND (entity1_id IN (scene_character_ids) OR entity2_id IN (scene_character_ids))
ORDER BY importance DESC, closeness DESC
```

### 8. Recent Knowledge (relevant to scene)
```sql
SELECT * FROM character_knowledge
WHERE character_id = ? AND playthrough_id = ?
ORDER BY (importance * recency) DESC
LIMIT 5
```

**Total context budget:** ~2000-3000 tokens per character (adjust based on character_type priority).

---

## VALIDATION STAGE CHECKS

For **Stage 7: VALIDATION**, verify:

### Consistency Checks
```python
def validate_character_action(character_id, proposed_action, context):
    """Check if action is consistent with character."""

    # Load character core traits
    char = get_character(character_id)

    # Check 1: Would never do
    if action_matches_any(proposed_action, char.would_never_do):
        return ValidationError("Character would never do this", severity="critical")

    # Check 2: Contradicts core values
    if contradicts_values(proposed_action, char.core_values):
        return ValidationError("Action contradicts core values", severity="high")

    # Check 3: Verbal patterns
    if has_dialogue(proposed_action):
        if violates_speech_patterns(dialogue, char.verbal_patterns):
            return ValidationError("Speech doesn't match character voice", severity="medium")

    # Check 4: Current emotional state
    state = get_character_state(character_id)
    if action_incompatible_with_mood(proposed_action, state.current_emotional_state):
        return ValidationError("Action doesn't match current emotional state", severity="medium")

    # Check 5: Active avoidances
    avoidances = get_active_avoidances(character_id)
    if triggers_avoidance(proposed_action, avoidances):
        if not override_conditions_met(proposed_action, avoidances):
            return ValidationError("Character avoiding this situation", severity="high")

    return ValidationSuccess()
```

### Content Policy Checks
```python
def validate_content_policy(response, story_settings):
    """Check if response meets content requirements (SFW, etc.)"""

    # Check against story-level content settings
    if story_settings.sfw_only:
        if contains_nsfw_content(response):
            return ValidationError("NSFW content in SFW story", severity="critical")

    # Check for other policy violations
    # ...

    return ValidationSuccess()
```

---

## STATE UPDATE PRIORITIES

For **Stage 9: STATE_UPDATE**, update in this order:

1. **Relationships** (trust/affection/familiarity changes)
2. **Character State** (new emotional state if changed)
3. **New Memories** (significant events)
4. **Character Knowledge** (new information learned)
5. **Goals** (progress or new goals)
6. **Memory Flags** (anchor important events)
7. **Beliefs** (challenged or reinforced)

Run async/background to not block user experience.

---

## IMPLEMENTATION PRIORITY

Suggested implementation order:

**Phase 1: Core Character Depth**
1. Add new columns to `characters` table ✓
2. Add new columns to `relationships` table ✓
3. Create `character_state` table ✓
4. Create `character_goals` table ✓

**Phase 2: Memory Systems**
5. Create `character_memories` table ✓
6. Create `character_beliefs` table ✓
7. Add importance to `character_knowledge` ✓

**Phase 3: Behavioral Constraints**
8. Create `character_avoidances` table ✓
9. Implement context gathering algorithm
10. Implement validation checks

**Phase 4: Integration**
11. Connect to ChromaDB for semantic memory search
12. Build memory retrieval system
13. Implement state update logic
14. Add decay algorithms for time skips

---

## TIME SKIP HANDLING LOGIC

When a time skip occurs (hours, days, weeks):

```python
def handle_time_skip(character_id, playthrough_id, time_elapsed_hours):
    """Adjust character state after time skip."""

    state = get_character_state(character_id)
    baseline = state.baseline_emotional_state
    current = state.current_emotional_state

    # Calculate decay rate based on emotion type
    if current in ACUTE_EMOTIONS:  # anger, excitement, surprise
        decay_rate = 0.1 * time_elapsed_hours  # fast decay
    elif current in DEEP_EMOTIONS:  # grief, love, deep betrayal
        decay_rate = 0.01 * time_elapsed_hours  # slow decay
    else:
        decay_rate = 0.05 * time_elapsed_hours  # medium decay

    # Decay toward baseline
    if decay_rate >= 1.0:
        # Fully returned to baseline
        state.current_emotional_state = baseline
        state.emotion_cause = None
        state.emotion_intensity = 0.3
    else:
        # Partial decay - blend current and baseline
        state.emotion_intensity *= (1.0 - decay_rate)
        if state.emotion_intensity < 0.3:
            state.current_emotional_state = baseline

    # Reset stress/energy toward normal levels
    state.stress_level = trend_toward(state.stress_level, 0.3, decay_rate)
    state.energy_level = trend_toward(state.energy_level, 0.7, decay_rate)

    update_character_state(state)
```

---

## SUMMARY OF CHANGES

### New Tables (5)
- `character_state` - Emotional and mental state
- `character_goals` - Character motivations
- `character_memories` - Episodic memory
- `character_beliefs` - Worldviews and beliefs
- `character_avoidances` - Things they avoid + WHY

### Modified Tables (3)
- `characters` - Added 11 new columns for depth
- `relationships` - Added 9 new columns for relationship quality
- `character_knowledge` - Added 3 columns for importance tracking

### Total New Columns: ~50+
### Total New Indexes: 15+

This gives you a complete memory and personality system for characters that feel like real people!
