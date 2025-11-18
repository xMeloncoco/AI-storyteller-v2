# AI Storyteller v2 - Narrative & Dialogue Analysis Report

## Executive Summary

I've analyzed the complete codebase for the AI Storyteller application (both frontend and backend). The system has a sophisticated architecture for narrative generation with multiple layers of context building, character decision-making, and story progression. However, there are several areas where issues with dialogue repetition, circular conversations, and narrative inconsistency could arise.

---

## System Architecture Overview

### 1. **Core Processing Pipeline** (9 Stages)
The system uses a multi-stage AI processing pipeline defined in `/PIPELINE_STAGES.md`:

1. **INTAKE** - User input validation
2. **TRIGGER_DETECTION** - Story flag checks
3. **CONTEXT_GATHERING** - Load memories, states, goals
4. **SCENE_SIMULATION** - Character reaction analysis
5. **RESPONSE_PRIORITIZATION** - Filter important actions
6. **GENERATION** - Create narrative (LARGE MODEL)
7. **VALIDATION** - Consistency checks
8. **PRESENTATION** - Format and display
9. **STATE_UPDATE** - Update database

### 2. **AI Model Configuration**
**File:** `/backend/app/config.py`

```
Default Provider: "local" (Ollama)
Small Model: "llama3.2:3b" (3GB, quick tasks)
Large Model: "llama3.2" (4.7GB, story generation)

Token Limits:
- Small: 500 tokens
- Large: 2000 tokens

Context Window: Max 20 messages included
```

**Supported Providers:**
- `local` (Ollama) - Offline, recommended
- `openrouter` - Online API
- `nebius` - Alternative online API
- `demo` - Testing mode

---

## How Narrative & Dialogue Works

### 1. **Context Building Pipeline**
**File:** `/backend/app/ai/context_builder.py`

The system builds comprehensive context from multiple sources:

```
1. Story Information (title, description)
2. Current Scene (location, time, weather, mood)
3. Characters Present (names, types, moods, intents)
4. Conversation History (last 20 messages by default)
5. Relationship Status (trust, affection, familiarity metrics)
6. Active Story Arcs (current narrative threads)
7. Important Memory Flags (anchored key events)
```

**Key Method:** `build_full_context()` - Assembles all above pieces into a single context string passed to AI.

### 2. **Character Decision Layer**
**File:** `/backend/app/ai/llm_manager.py` - `analyze_character_decision()` method

Before generating the narrative, the system asks the AI what each NPC character would do:

```
For each NPC in scene:
  1. Send character_decision_prompt with:
     - Character personality, backstory, speech patterns
     - Current scene context
     - User's action/input
  
  2. AI returns JSON with:
     {
       "action": "What they do",
       "dialogue": "What they say",
       "emotion": "Current emotional state",
       "refuses": true/false (refuse user's action?),
       "reason": "Why they made this decision"
     }
```

This happens BEFORE story generation, ensuring consistency.

### 3. **Story Generation Process**
**File:** `/backend/app/routers/chat.py` - `send_message()` endpoint

**Key Flow:**
```
1. User sends message
2. Save user message to database
3. Build full context (includes conversation history)
4. Detect scene changes (location/time/characters)
5. Get character decisions for all NPCs
6. Generate story response using:
   - Full context
   - User action
   - Character decisions
   - Story information
7. Save AI response
8. Update relationships (async)
9. Check story progression (async)
```

**Critical:** User character is explicitly skipped in decision-making (line 158 in chat.py).

### 4. **The Story Generation Prompt**
**File:** `/backend/app/ai/prompts.py` - `story_generation_prompt()` method

This is the primary prompt that guides the AI. It includes:

```
- CRITICAL RULES section explicitly telling AI:
  ✓ Never write dialogue for the user's character
  ✓ Only write about NPCs and environment
  ✓ Keep response to 2-4 short paragraphs
  ✓ Focus on NPC reactions

- CHARACTER DECISIONS section showing what each NPC decided
  
- STYLE GUIDELINES:
  ✓ Third-person perspective
  ✓ Show emotions through actions, not statements
  ✓ Match character speech patterns
  ✓ Keep pacing tight
```

---

## Potential Issues & Root Causes

### **ISSUE 1: Dialogue Becomes Repetitive and Circular**

**Likely Causes:**

#### A. **Limited Context Window**
- **File:** `config.py` line 63
- **Setting:** `max_context_messages: int = 20`
- **Problem:** Only last 20 messages included in context
- **Impact:** AI loses broader conversation context, repeats itself
- **Symptom:** Same dialogue patterns repeat, AI forgets earlier plot points

**Evidence in Code:**
```python
# context_builder.py lines 182-187
history = crud.get_conversation_history(
    self.db,
    self.session_id,
    limit=settings.max_context_messages  # ONLY 20!
)
```

#### B. **Token Limits Too Low**
- **File:** `config.py` lines 70-71
- **Settings:**
  - `max_tokens_small: 500`
  - `max_tokens_large: 2000`
- **Problem:** 2000 tokens may be too short for maintaining coherence with large context
- **Issue:** AI response gets cut off mid-sentence, feels incomplete

#### C. **Missing Memory Integration**
- **File:** `context_builder.py` line 249-262 - `_get_memory_flags_context()`
- **Problem:** Only loads top 10 memory flags with `min_importance=7`
- **Issue:** Important story beats might be lost if not marked with high importance
- **Symptom:** AI forgets character development points, repeats old plot threads

#### D. **Character Decision Parsing Fallback**
- **File:** `llm_manager.py` lines 402-412
- **Problem:** When character decision JSON parsing fails, falls back to keyword matching
- **Code:**
```python
try:
    decision = json.loads(response)
except json.JSONDecodeError:
    # Falls back to brittle keyword-based parsing
    decision = self._parse_decision_text(response)  # LINE 412
```
- **Issue:** Fallback parser (lines 422-452) uses simple keyword detection - very unreliable
- **Symptom:** Character decisions misinterpreted, leading to nonsensical dialogue

---

### **ISSUE 2: Multiple "User:" Labels Appear Incorrectly**

**Likely Causes:**

#### A. **Backend Saving Wrong Speaker Type**
- **File:** `/backend/app/routers/chat.py` lines 73-81
- **Code:**
```python
user_conversation = crud.create_conversation(
    db,
    schemas.ConversationCreate(
        session_id=request.session_id,
        playthrough_id=session.playthrough_id,
        speaker_type="user",  # Saved as "user"
        speaker_name="User",   # But name is "User"
        message=request.message
    )
)
```
- **Problem:** Backend saves speaker_name as "User" but frontend might display it differently
- **Impact:** Inconsistent labeling between frontend display and database

#### B. **Frontend Display Logic**
- **File:** `/frontend/src/components/chat.js` lines 66-85
- **Code:**
```javascript
addMessage(type, speaker, content) {
    const header = document.createElement('div');
    header.textContent = speaker;  // Displays whatever speaker name is passed
}
```
- **Issue:** If backend sends "User" instead of expected name, it might appear redundantly
- **Possible:** Multiple messages with same speaker triggers duplication in display

#### C. **Conversation History Loading**
- **File:** `/frontend/src/components/chat.js` lines 44-47
- **Code:**
```javascript
for (const msg of history) {
    this.addMessage(msg.speaker_type, msg.speaker_name || msg.speaker_type, msg.message);
}
```
- **Problem:** Falls back to speaker_type if speaker_name is null
- **Issue:** DB might return NULL speaker_name for user messages, causing "user" labels

---

### **ISSUE 3: Characters Contradict Established Narrative Setup**

**Likely Causes:**

#### A. **Weak Character Constraint Prompts**
- **File:** `prompts.py` lines 71-97
- **Problem:** Story generation prompt says "NEVER control user character" but gives minimal constraints for NPCs
- **Issue:** No constraints on character values, fears, or behavioral rules
- **Code:** Missing explicit `would_never_do`, `would_always_do` validation

#### B. **Character Decision Layer Gaps**
- **File:** `llm_manager.py` lines 359-420
- **Problem:** Character decision prompt (lines 104-158 in prompts.py) only returns JSON
- **Issue:** No validation that decisions are consistent with character's `would_never_do`
- **No validation step:** The returned decision is used directly without checking

#### C. **Missing Validation Stage**
- **File:** `PIPELINE_STAGES.md` Stage 7 - VALIDATION
- **Problem:** Validation stage described but **NOT IMPLEMENTED** in actual code
- **Evidence:** Stage 7 is documented but has no corresponding code module
- **Impact:** No system to catch character inconsistencies before displaying

#### D. **Incomplete Character Knowledge System**
- **File:** `context_builder.py` lines 308-311
- **Code:**
```python
# Future: Add character knowledge (Phase 1.3+)
# This prevents "mind-reading"
info["known_facts"] = []  # To be implemented
```
- **Problem:** Character knowledge tracking **NOT IMPLEMENTED**
- **Issue:** AI has no mechanism to prevent "mind-reading" (characters knowing things they shouldn't)
- **Symptom:** Characters reference events they weren't present for

---

### **ISSUE 4: AI Loses Context & Generates Nonsensical Conversation**

**Likely Causes:**

#### A. **Conversation History Not Including User Character Actions**
- **File:** `context_builder.py` lines 180-197
- **Problem:** Conversation history shows speaker names but might not clearly identify the USER
- **Issue:** AI might confuse who did what
- **Code:**
```python
def _get_conversation_history(self) -> str:
    # ...
    for msg in history:
        speaker = msg.speaker_name or msg.speaker_type.upper()
        context += f"{speaker}: {msg.message}\n\n"
```
- **Issue:** If speaker_name is "User", context becomes confusing ("User: I look around")

#### B. **Scene Change Detection Not Updating Context**
- **File:** `chat.py` lines 116-141
- **Problem:** Scene changes detected but context builder has already built context
- **Issue:** Location/time changes applied AFTER context built
- **Timing:** Scene context might be stale

#### C. **Large Model Receiving Incomplete Prompt Structure**
- **File:** `chat.py` lines 210-214
- **Problem:** Story generation prompt passes raw context without formatting
- **Issue:** Large model receives unstructured, verbose context string
- **Code:**
```python
story_prompt = PromptTemplates.story_generation_prompt(
    full_context,  # Raw, potentially huge string
    request.message,
    character_decisions,
    story_info
)
```
- **Issue:** No context prioritization or summarization before sending to LLM

#### D. **Model Size Mismatch**
- **File:** `config.py` & `llm_manager.py`
- **Problem:** Using `llama3.2` for large model - may have limited reasoning
- **Issue:** Smaller language models struggle with maintaining conversation coherence
- **Evidence:** llama3.2 is relatively small compared to Claude/GPT-4

#### E. **Character Decision Prompt Too Simple for Complex Scenes**
- **File:** `prompts.py` lines 104-158
- **Problem:** Character decision prompt doesn't include:
  - Character's current emotional state
  - Character's goals
  - Character's memories
  - Relationship with user
- **Missing Context:** Only personality + scene + user action
- **Result:** Shallow character decisions → inconsistent narrative

---

## Critical Implementation Gaps

### **1. Missing VALIDATION Stage**
**Severity:** HIGH

The system describes a VALIDATION stage in documentation but doesn't implement it:
- No code module for consistency checking
- No regeneration on contradiction detection
- No `would_never_do` enforcement
- No `would_always_do` enforcement

**File Locations to Add:**
- New module: `backend/app/ai/validator.py`
- Called from: `chat.py` after story generation

### **2. Incomplete Character Knowledge System**
**Severity:** MEDIUM

The `CharacterKnowledge` model exists but isn't used:
- Table defined in `models.py` (lines 507-551)
- Not populated anywhere
- Not used in `context_builder.py`
- Prevents "mind-reading" validation

**Files Involved:**
- `models.py` - CharacterKnowledge table
- `context_builder.py` - Should load known_facts
- `chat.py` - Should update after interactions

### **3. Prompt Engineering Issues**
**Severity:** MEDIUM

Story generation prompt has problems:
- Doesn't include character's **current emotional state**
- Doesn't include character's **active goals**
- Doesn't include character's **relevant memories**
- Doesn't include character's **beliefs/values** explicitly

These exist in database but aren't in context!

---

## Message Flow & Data Structures

### **How User Input Becomes Story Output**

```
1. FRONTEND (chat.js)
   └─> addMessage('user', 'You', user_text)
   └─> sendMessage(session_id, message)

2. BACKEND API (routers/chat.py - send_message)
   └─> Validate session
   └─> Save user message to Conversation table
   └─> BUILD CONTEXT via ContextBuilder
       ├─ Story info
       ├─ Scene state
       ├─ Characters in scene
       ├─ Conversation history (ONLY 20 messages!)
       ├─ Relationships
       ├─ Story arcs
       └─ Memory flags
   
   └─> DETECT SCENE CHANGES
   
   └─> GET CHARACTER DECISIONS
       For each NPC:
       └─> llm_manager.analyze_character_decision()
           └─> Send to AI with character_decision_prompt
           └─> Parse JSON response
           └─> Return decision (action, dialogue, emotion, refuses, reason)
   
   └─> GENERATE STORY
       └─> llm_manager.generate_text()
           └─> Build story_generation_prompt with:
               ├─ Full context
               ├─ User action
               ├─ Character decisions
               └─ Story info
           └─> Send to LARGE MODEL
           └─> Return narrative text
   
   └─> SAVE RESPONSE
       └─> Save to Conversation table (speaker_type='narrator')
   
   └─> UPDATE RELATIONSHIPS (async)
   
   └─> CHECK STORY PROGRESSION (async)
   
   └─> RETURN ChatResponse with message, session_id, conversation_id

3. FRONTEND (chat.js)
   └─> Receive response
   └─> addMessage('narrator', 'Narrator', response.message)
   └─> Display to user
```

### **Speaker Types & Names in Database**

**Conversation Table Fields:**
```
speaker_type: 'user' | 'narrator'
speaker_name: String (optional)
message: Text
```

**Current Implementation:**
- User messages: speaker_type="user", speaker_name="User"
- Narrator: speaker_type="narrator", speaker_name="Narrator"
- NPCs: Should be included in narrator message, not separate entries

---

## Prompt Engineering Analysis

### **Story Generation Prompt Issues**

**File:** `prompts.py` lines 22-101

**What's Good:**
```python
✓ Explicitly tells AI not to control user character
✓ Specifies 2-4 paragraph limit
✓ Requests third-person perspective
✓ Includes character decision summaries
✓ Has style guidelines
```

**What's Missing:**
```python
✗ No system prompt context about character goals
✗ No explicit mention of character fears/values
✗ No instruction to check consistency
✗ No mechanism to prevent contradictions
✗ No emphasis on maintaining relationship dynamics
✗ Doesn't show character emotional history
✗ Missing timestamp/session context
```

### **Character Decision Prompt Issues**

**File:** `prompts.py` lines 104-158

**Current Input:**
```python
- Character name, type, personality traits, backstory, speech patterns
- Current context (but formatted oddly)
- User action/input
```

**Missing Context for Better Decisions:**
```python
- Character's current emotional state
- Character's goals (short-term, long-term, immediate)
- Character's recent experiences/memories
- Character's relationship with the user
- Character's values and fears
- What character is worried/focused on right now
```

---

## Database Context - Key Tables

### **Conversation History**
```sql
speaker_type: 'user' | 'narrator'
speaker_name: String (optional)
message: Text
timestamp: DateTime
-- Limited to 20 most recent messages in context
```

### **Scene State**
```sql
location: String
time_of_day: String
weather: String
scene_context: Text
emotional_tone: String
-- Tracks current state of the scene
```

### **Character Information**
```sql
-- Basic
character_name, appearance, age, backstory
personality_traits, speech_patterns

-- Depth (not always used in context!)
core_values, core_fears
would_never_do, would_always_do
comfort_behaviors
verbal_patterns (JSON)
sentence_structure, common_phrases
decision_style
internal_contradiction
secret_kept, vulnerability
```

### **Relationships**
```sql
trust: float (0-1)
affection: float (0-1)
familiarity: float (0-1)
-- Updated in STATE_UPDATE stage
```

### **Character State** (exists but rarely used)
```sql
baseline_emotional_state
current_emotional_state
emotion_cause, emotion_intensity
stress_level, energy_level, mental_clarity
primary_concern, secondary_concerns
-- Should be loaded in CONTEXT_GATHERING!
```

### **Character Goals** (exists but not in context)
```sql
goal_type: 'short_term' | 'long_term' | 'immediate'
goal_content: Text
priority: 1-10
status: 'active' | 'achieved' | 'abandoned' | 'blocked'
-- Should be loaded in CONTEXT_GATHERING!
```

---

## Configuration & Models

### **AI Provider Configuration**
**File:** `config.py`

```python
ai_provider: str = "local"  # Can be: local, openrouter, nebius, demo
small_model: str = "llama3.2:3b"
large_model: str = "llama3.2"
```

### **Token Budgets**
```python
max_tokens_small: 500
max_tokens_large: 2000
max_context_messages: 20
```

### **Model-Specific Implementations**

**LLMManager.generate_text()** (lines 59-143)
- Selects model based on size parameter
- Calls appropriate provider API
- Supports: OpenRouter, Nebius, Ollama, Demo mode

**Available Providers:**
1. **OpenRouter** (`_call_openrouter`)
   - Supports multiple models
   - Requires API key
   - URL: `https://openrouter.ai/api/v1`

2. **Nebius** (`_call_nebius`)
   - Alternative provider
   - Requires API key
   - URL: `https://api.studio.nebius.ai/v1`

3. **Ollama** (`_call_ollama`)
   - Local, offline
   - No API key needed
   - URL: `http://localhost:11434`
   - Longer timeout (120s)

4. **Demo** (`_generate_demo_response`)
   - Mock responses for testing
   - Returns JSON or story text depending on prompt

---

## Summary of Key Files & Their Roles

| File | Purpose | Issues |
|------|---------|--------|
| `config.py` | Settings and model config | Token limits may be too low, context window too small |
| `prompts.py` | All AI prompts | Missing character depth in decision & story prompts |
| `llm_manager.py` | AI communication | Fallback JSON parsing is fragile |
| `context_builder.py` | Context assembly | Doesn't include character state/goals/emotional info |
| `chat.py` | Main API endpoint | No validation stage, scene updates late |
| `models.py` | Database schemas | CharacterState/CharacterGoal/CharacterKnowledge not used |
| `schemas.py` | Request/Response formats | Speaker name/type consistency issues |
| `chat.js` | Frontend display | May not handle speaker names consistently |

---

## Recommendations for Investigation

### **High Priority:**
1. **Implement Validation Stage** - Add consistency checking before returning responses
2. **Load Character Goals & State** - Include in context builder and prompts
3. **Increase Context Window** - Test with 30-50 messages instead of 20
4. **Better Prompt Engineering** - Include character depth in decision prompts
5. **Character Knowledge System** - Implement tracking of what characters know

### **Medium Priority:**
6. **Fix Character Decision Parsing** - Improve JSON fallback or use structured output
7. **Add Character Voice Matching** - Ensure dialogue follows verbal_patterns
8. **Scene Update Timing** - Update context after scene detection
9. **Memory System** - Better importance scoring and retrieval

### **Lower Priority:**
10. **Larger Language Model** - Consider Claude/GPT-4 for better reasoning
11. **Token Budget Optimization** - Prioritize context over verbosity
12. **Token usage monitoring** - Track and optimize token consumption

