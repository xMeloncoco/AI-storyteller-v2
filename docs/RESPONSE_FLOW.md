# Response Flow Documentation

This document outlines the complete flow when the AI generates a response to user input.

## High-Level Overview

```
User Input → Validation → Context Building → Scene Detection → Character Decisions → Story Generation → Validation → Updates → Response
```

## Detailed Flow

### 1. **Request Reception** (`/chat/send`)
**File:** `backend/app/routers/chat.py:29`

- User sends message via `ChatRequest` with `session_id` and `message`
- Session is validated to ensure it exists
- User message is saved to database as a `Conversation` entry

### 2. **Context Building**
**File:** `backend/app/ai/context_builder.py:66`

The `ContextBuilder` assembles all relevant information:

**2.1. Story Information**
- Story title and description

**2.2. Current Scene State**
- Location (e.g., "Miriam's Apartment - Living Room")
- Time of day
- Weather (if set)
- Emotional tone
- Scene context

**2.3. Characters Present**
- Retrieved from `scene_characters` table
- Includes character type, mood, intent, and physical position

**2.4. Conversation History**
- Last N messages (configurable via `settings.max_context_messages`)
- Formatted as: `SPEAKER: message`

**2.5. Relationship Information**
- For each relationship involving the user character:
  - Relationship type
  - Trust level (0.0 to 1.0)
  - Affection level (0.0 to 1.0)
  - Familiarity level (0.0 to 1.0)
  - History summary

**2.6. Active Story Arcs** (Phase 2.2)
- Arc name and description
- Only arcs with `is_active = true`

**2.7. Important Memory Flags** (Phase 1.3)
- Memory flags with importance ≥ 7
- Limited to top 10 most important

### 3. **Scene Change Detection** (Lightweight Model)
**File:** `backend/app/routers/chat.py:116`
**Prompt:** `backend/app/ai/prompts.py:241`

Uses a lightweight model to detect:
- Location changes
- Time changes
- Characters entering/leaving
- Significant events

**Input:**
- Full context
- User's message

**Output (JSON):**
```json
{
  "location_changed": true/false,
  "new_location": "location name or null",
  "time_changed": true/false,
  "new_time": "time description or null",
  "characters_entered": ["list of names"],
  "characters_left": ["list of names"],
  "significant_event": "description or null"
}
```

If changes detected, scene state is updated in database.

### 4. **Character Decision Layer** (Phase 1.3+)
**File:** `backend/app/routers/chat.py:143-196`
**Prompt:** `backend/app/ai/prompts.py:117`

For each non-user character in the scene:

**Input:**
- Character's complete profile (traits, backstory, speech patterns)
- Character's core values and fears
- Character's "would never do" and "would always do" lists
- Current emotional state (if available)
- Active goals
- Relationships with others present
- Full context
- User's action

**Output (JSON):**
```json
{
  "action": "brief description of what they do",
  "dialogue": "what they say (1-2 sentences max)",
  "emotion": "their current emotional state",
  "refuses": true/false,
  "reason": "why they made this decision"
}
```

This ensures characters:
- Act consistently with their personality
- Can refuse or disagree with the user
- Have their own agency and motivations
- Respond based on their emotional state and goals

### 5. **Story Generation** (Large Model)
**File:** `backend/app/routers/chat.py:198-245`
**Prompt:** `backend/app/ai/prompts.py:22`

**Input:**
- Full context (all assembled information)
- User's action/message
- Character decisions from Step 4
- Story information

**Critical Rules in Prompt:**
1. NEVER control the user's character
2. NEVER write dialogue, thoughts, or actions for user character
3. Keep response to 2-4 short paragraphs MAXIMUM
4. Follow character decisions provided
5. Characters must act consistently with personality
6. Show character emotions through body language, not internal thoughts

**System Prompt:**
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

**Output:**
- Generated narrative text (2-4 paragraphs)

### 6. **Content Validation** (Stage 7)
**File:** `backend/app/routers/chat.py:256-276`
**Validator:** `backend/app/ai/validator.py`

Validates the generated content for:
- User character control (CRITICAL: AI should never control user character)
- Character consistency
- Appropriate length
- Following character decisions

**If validation fails:**
- Issues are logged as warnings
- Content is still returned (doesn't block the story)
- Future enhancement: could trigger regeneration

### 7. **Database Updates**

**7.1. Save AI Response**
- Store generated narrative as `Conversation` entry
- Speaker type: "narrator"

**7.2. Update Relationships** (Phase 3.1)
**File:** `backend/app/relationships/updater.py`

Analyzes interaction and updates relationship values:
- Trust changes (-0.3 to +0.3)
- Affection changes (-0.3 to +0.3)
- Familiarity increases (0.0 to +0.2)

**7.3. Check Story Progression** (Phase 2.2)
**File:** `backend/app/story/progression.py`

Checks if:
- Story arcs should be activated
- Story arcs should be completed
- Story flags should be set

**7.4. Update Session Activity**
- Updates `last_active` timestamp

### 8. **Response Assembly**

**File:** `backend/app/routers/chat.py:347-356`

Returns `ChatResponse` with:
- Generated message
- Session ID
- Conversation ID
- Characters in scene (with mood, intent, position)
- Current location
- Current time
- Relationship updates (if any)
- Story flags set (if any)

## Timeline Estimate

For a typical user message:

1. **Request Reception:** < 10ms
2. **Context Building:** 50-100ms (database queries)
3. **Scene Detection:** 500-1000ms (AI call - lightweight model)
4. **Character Decisions:** 1000-2000ms per character (AI calls - small model)
5. **Story Generation:** 3000-8000ms (AI call - large model)
6. **Validation:** 100-200ms
7. **Database Updates:** 100-200ms
8. **Response Assembly:** < 10ms

**Total:** ~5-12 seconds (depends on number of characters and AI model speed)

## Error Handling

At each step:
- Errors are logged to the `logs` table with context
- Critical errors (session not found) return HTTP 404
- AI errors bubble up as HTTP 500
- Relationship/progression errors are caught and logged but don't block response

## Logging

Throughout the flow, the system logs:
- **Notifications:** Major steps completed
- **Context:** Context building and memory operations
- **AI Decisions:** Character decisions and AI responses
- **Warnings:** Validation issues
- **Errors:** Failures at any step

All logs are stored in database and can be viewed in the Tester panel.
