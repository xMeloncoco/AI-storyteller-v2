# AI Storyteller - Quick Reference Guide

## Key Files Involved in Narrative Generation

### Backend Core Files
- **config.py** - AI model settings (llama3.2, token limits, context size)
- **prompts.py** - All AI prompts (story_generation, character_decision, etc.)
- **llm_manager.py** - Communicates with AI models
- **context_builder.py** - Assembles context from database
- **chat.py** - Main API endpoint handling user input/AI response
- **models.py** - Database schemas (Character, Conversation, Scene, etc.)

### Frontend Files
- **chat.js** - Displays messages and sends user input

## Critical Data Flow

```
User Message
    ↓
[chat.py] Save to Conversation table
    ↓
[context_builder.py] Build full context from:
  - Story info
  - Scene state
  - Characters in scene
  - Last 20 messages (CONFIGURABLE: max_context_messages)
  - Relationships
  - Story arcs
  - Memory flags
    ↓
[chat.py] Detect scene changes (location/time)
    ↓
[llm_manager.py] Get character decisions (for each NPC):
  - Send character_decision_prompt to AI
  - Parse JSON response
    ↓
[llm_manager.py] Generate narrative:
  - Send story_generation_prompt to AI
  - Receive narrative text
    ↓
[chat.py] Save AI response to Conversation table
    ↓
[frontend] Display to user
```

## 4 Main Issues Identified

### 1. Dialogue Repetition & Circular Conversations
- **Root Cause:** Limited context window (only 20 messages!)
- **Files:** config.py (line 63), context_builder.py (lines 182-187)
- **Solutions:**
  - Increase max_context_messages from 20 to 30-50
  - Improve memory flag importance scoring
  - Better JSON parsing fallback for character decisions

### 2. Multiple "User:" Labels
- **Root Cause:** Inconsistent speaker_name handling
- **Files:** chat.py (lines 73-81), chat.js (lines 44-47)
- **Solution:** Ensure speaker_name is never NULL, use consistent display logic

### 3. Characters Contradict Narrative
- **Root Cause:** Missing validation stage + weak character constraints
- **Files:** prompts.py (no validation), llm_manager.py (no checks)
- **Solutions:**
  - **CRITICAL:** Implement validation stage (doesn't exist!)
  - Add character goals/state to decision prompts
  - Enforce would_never_do/would_always_do constraints

### 4. AI Loses Context
- **Root Cause:** Incomplete context, small model, simple prompts
- **Files:** context_builder.py (missing character state/goals), config.py (model size)
- **Solutions:**
  - Load CharacterState (emotional state, stress, clarity)
  - Load CharacterGoal (what character wants right now)
  - Include in both decision AND story generation prompts

## Configuration Settings

### Currently Applied
```python
ai_provider = "local"           # Ollama (offline)
small_model = "llama3.2:3b"     # For quick tasks
large_model = "llama3.2"        # For story generation
max_tokens_small = 500
max_tokens_large = 2000
max_context_messages = 20       # ← LIMITING FACTOR!
```

### Key Settings to Tune
- `max_context_messages` - Increase from 20 to 30+ for better context
- `max_tokens_large` - May need 2000-3000 for coherent stories
- `large_model` - llama3.2 is relatively small; consider larger model

## Database Tables Used in Context

### Always Loaded
- Story (title, description)
- SceneState (location, time, weather, mood)
- SceneCharacter (who's in scene, their mood/intent)
- Conversation (last N messages)

### Sometimes Loaded
- Relationship (trust/affection/familiarity)
- StoryArc (current story arcs)
- MemoryFlag (top 10 by importance)

### NEVER Loaded (But Should Be!)
- **CharacterState** - Current emotional/mental state
- **CharacterGoal** - What character wants/trying to achieve
- **CharacterMemory** - Relevant past experiences
- **CharacterKnowledge** - What character knows (prevents mind-reading)
- **CharacterBelief** - Character's worldview

## The Missing VALIDATION Stage

**Status:** DOCUMENTED (PIPELINE_STAGES.md) but NOT IMPLEMENTED

Should check:
- Does action contradict character's `would_never_do`?
- Does dialogue match character's verbal patterns?
- Does character reference information they don't know?
- Is emotional response consistent with current state?
- Are relationships respected?

**Location:** Should be in `/backend/app/ai/validator.py` (DOESN'T EXIST)

## Prompt Issues Summary

### Story Generation Prompt (prompts.py lines 22-101)
**Good:** Tells AI not to control user character, specifies length limit
**Bad:** Doesn't include character goals, emotional state, or values

### Character Decision Prompt (prompts.py lines 104-158)
**Good:** Asks for structured JSON response
**Bad:** 
- Missing character's current emotional state
- Missing character's goals
- Missing character's relationship with user
- Fallback parser is too simple (lines 422-452)

## Character Information Flow

### What's in Database
```
Character table has:
- Basic: name, appearance, age, backstory
- Personality: traits, speech patterns
- Depth: core_values, core_fears, would_never_do, would_always_do
- Behavior: comfort_behaviors, verbal_patterns, sentence_structure
- Psychology: internal_contradiction, secret_kept, vulnerability
```

### What Actually Gets to AI
Character decision prompt includes:
- Name, type, traits, backstory, speech patterns
- (Missing) Goals, emotional state, relationship with user

Story generation prompt includes:
- Character decisions (action, dialogue, emotion, refusals)
- (Missing) Character's values, goals, emotional baseline

### Gap Analysis
Raw character data in DB → Not loaded into context → Can't constrain AI → Character contradictions

## Quick Fixes (High Impact)

### 1. Increase Context Window (5 min)
**File:** config.py line 63
```python
max_context_messages: int = 30  # was 20
```

### 2. Load Character State (15 min)
**File:** context_builder.py
Add method to load CharacterState and include in context

### 3. Better Speaker Name Handling (10 min)
**File:** chat.py line 79 + chat.js line 46
Ensure speaker_name is never NULL

### 4. Enhanced Character Decision Prompt (20 min)
**File:** prompts.py character_decision_prompt()
Add character's goals, emotional state, relationship info

## Files by Frequency of Use

**Used Every Turn:**
- chat.py (chat endpoint)
- context_builder.py (builds context)
- llm_manager.py (communicates with AI)
- prompts.py (provides prompts)
- models.py (database schemas)

**Used Sometimes:**
- relationships/updater.py (relationship changes)
- story/progression.py (story flags/arcs)
- schemas.py (request validation)

**Used on Start/Init:**
- main.py (API setup)
- database.py (DB connection)

## Testing the Issues

### To Debug Repetitive Dialogue
1. Check database: `conversations` table for message content
2. Watch logs for character decision parsing errors
3. Test with `max_context_messages = 30` to see if improves

### To Debug "User:" Labels
1. Check database: `conversations.speaker_name` column
2. Check frontend console: What does API return?
3. Verify speaker_name is "User" or actual character name, not NULL

### To Debug Character Contradictions
1. Check character's `would_never_do` in database
2. See if violated in generated text
3. Implement validation stage to catch

### To Debug Context Loss
1. Check logs: "FULL CONTEXT BUILT" message
2. Look at context_length in logs
3. See if CharacterState/CharacterGoal are missing
