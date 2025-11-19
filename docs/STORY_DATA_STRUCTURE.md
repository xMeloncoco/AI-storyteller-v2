# Story Data Structure Documentation

This document provides a complete rundown of the story data structure using the Starling Contract as an example.

## Overview

Stories are defined in JSON files located in `backend/test_data/`. Each story file contains:
1. Basic story information
2. Character definitions with deep personality modeling
3. Locations
4. Initial relationships
5. Story arcs with progression

---

## 1. Story Metadata

```json
{
  "title": "Starling Contract",
  "description": "Two childhood friends, separated by tragedy...",
  "initial_message": "The Sterling Enterprises boardroom...",
  "initial_location": "Miriam's Apartment - Living Room",
  "initial_time": "Early evening, 8:00 PM"
}
```

### Fields

| Field | Type | Purpose |
|-------|------|---------|
| `title` | string | Story name shown to users |
| `description` | string | Brief summary of the story premise |
| `initial_message` | string | The opening narrative that starts the story |
| `initial_location` | string | Starting location (must match a location name) |
| `initial_time` | string | Starting time of day |

---

## 2. Character Definitions

Each character has **extensive personality modeling** to ensure consistency and agency.

### Character Structure

```json
{
  "name": "Character Name",
  "type": "User|Main|Support|Antagonist",
  "appearance": "Physical description",
  "age": 28,
  "backstory": "Character's history and trauma",
  "personality_traits": ["trait1", "trait2", ...],
  "speech_patterns": "How they speak",

  // CORE PERSONALITY (Critical for consistency)
  "core_values": ["value1", "value2", ...],
  "core_fears": ["fear1", "fear2", ...],
  "would_never_do": ["action1", "action2", ...],
  "would_always_do": ["action1", "action2", ...],
  "comfort_behaviors": ["behavior1", "behavior2", ...],

  // SPEECH MODELING (Ensures distinct voices)
  "verbal_patterns": {
    "greetings": ["phrase1", "phrase2", ...],
    "agreement": ["phrase1", "phrase2", ...],
    "disagreement": ["phrase1", "phrase2", ...],
    "exclamations": ["phrase1", "phrase2", ...],
    "fillers": ["phrase1", "phrase2", ...]
  },
  "sentence_structure": "Description of how they construct sentences",
  "common_phrases": ["phrase1", "phrase2", ...],

  // DECISION MAKING
  "decision_style": "How they make choices",
  "internal_contradiction": "Their core conflict",
  "secret_kept": "Hidden information",
  "vulnerability": "Their deepest weakness"
}
```

### Character Types

| Type | Purpose | Behavior |
|------|---------|----------|
| `User` | Player-controlled character | AI never generates actions/dialogue for them |
| `Main` | Primary NPCs | Full decision-making, complex interactions |
| `Support` | Supporting cast | Moderate complexity, helpful roles |
| `Antagonist` | Opposition | Complex motivations, create conflict |

### Example: Miriam Cross (User Character)

```json
{
  "name": "Miriam Cross",
  "type": "User",
  "appearance": "A striking woman of 28 with sharp features...",
  "age": 28,
  "backstory": "After losing her mother and brother in a car crash at age 8...",
  "personality_traits": [
    "fiercely independent",
    "workaholic",
    "sharp-tongued",
    "guarded",
    "deeply loyal",
    "intelligent",
    "resilient"
  ],
  "speech_patterns": "Direct and professional with a tendency toward sarcasm...",
  "core_values": ["independence", "truth", "loyalty", "justice", "hard work"],
  "core_fears": ["abandonment", "losing control", "being vulnerable", "failure"],
  "would_never_do": [
    "betray someone who trusts her",
    "give up without a fight",
    "show weakness to enemies",
    "forgive easily without genuine change"
  ],
  "would_always_do": [
    "protect those she cares about",
    "fight for what's right",
    "maintain her independence",
    "honor her commitments"
  ],
  "comfort_behaviors": [
    "working long hours",
    "organizing things",
    "sharp retorts",
    "emotional walls"
  ],
  "verbal_patterns": {
    "greetings": ["Mr. Sterling", "Let's get this over with"],
    "agreement": ["Fine", "If we must", "I suppose"],
    "disagreement": ["Absolutely not", "You can't be serious", "That's ridiculous"],
    "exclamations": ["Unbelievable", "Typical"],
    "fillers": ["Look", "Listen", "Clearly"]
  },
  "sentence_structure": "Direct and concise, sometimes cutting...",
  "common_phrases": [
    "I don't have time for this",
    "Let's be clear about something",
    "Don't patronize me"
  ],
  "decision_style": "analytical but can be impulsive when emotions run high",
  "internal_contradiction": "Craves genuine connection but pushes people away...",
  "secret_kept": "Still has every letter she wrote to Alex but never sent...",
  "vulnerability": "Terrified of being abandoned again..."
}
```

### Example: Alexander Sterling (Main NPC)

```json
{
  "name": "Alexander Sterling",
  "type": "Main",
  "appearance": "Tall at 6'3\" with black hair and steel-gray eyes...",
  "age": 29,
  "backstory": "Heir to Sterling Enterprises, sent to boarding school at 13...",
  "personality_traits": [
    "dominant",
    "short-tempered",
    "arrogant",
    "ruthless",
    "protective",
    "surprisingly vulnerable",
    "secretive"
  ],
  "speech_patterns": "Commanding and confident, uses his voice like a weapon...",
  "core_values": ["protection", "redemption", "justice (hidden)", "loyalty"],
  "core_fears": [
    "losing Miriam again",
    "becoming his parents",
    "his secrets being discovered",
    "being truly seen"
  ],
  "would_never_do": [
    "abandon Miriam again",
    "hurt innocents",
    "let his parents destroy more lives"
  ],
  "would_always_do": [
    "protect those he cares about",
    "honor his hidden commitments",
    "maintain his facade"
  ],
  "comfort_behaviors": [
    "intimidation",
    "reckless behavior",
    "expensive purchases",
    "late night drives"
  ],
  "verbal_patterns": {
    "greetings": ["Miriam", "Miss Cross", "We need to talk"],
    "agreement": ["Agreed", "Very well", "As you wish"],
    "disagreement": ["That's not happening", "Try again", "Unacceptable"],
    "exclamations": ["Christ", "Damn it"],
    "fillers": ["Look", "Listen to me"]
  },
  "sentence_structure": "Authoritative and direct, but can become softer...",
  "common_phrases": [
    "This isn't negotiable",
    "I won't let that happen",
    "You don't understand"
  ],
  "decision_style": "impulsive when emotional, strategic when calm",
  "internal_contradiction": "Projects ruthless arrogance but secretly works to help...",
  "secret_kept": "Has been anonymously donating to charities...",
  "vulnerability": "Believes he doesn't deserve forgiveness..."
}
```

### Why This Level of Detail Matters

This extensive character modeling ensures:
1. **Consistency:** Characters behave predictably based on values/fears
2. **Agency:** Characters can refuse user requests that violate their values
3. **Distinct Voices:** Each character sounds different in dialogue
4. **Meaningful Conflict:** Characters have real reasons to disagree
5. **Character Growth:** Secrets and vulnerabilities create development opportunities

---

## 3. Locations

```json
{
  "locations": [
    {
      "name": "Miriam's Apartment - Living Room",
      "description": "A luxury downtown apartment with floor-to-ceiling windows...",
      "type": "indoor|outdoor",
      "scope": "room|floor|building|landmark|neighborhood|city"
    }
  ]
}
```

### Fields

| Field | Type | Options | Purpose |
|-------|------|---------|---------|
| `name` | string | - | Unique identifier for the location |
| `description` | string | - | Visual details and atmosphere |
| `type` | string | indoor, outdoor | Affects weather/lighting considerations |
| `scope` | string | room, floor, building, landmark, neighborhood, city | Scale of the location |

### Example Locations

**Intimate Space:**
```json
{
  "name": "Miriam's Apartment - Living Room",
  "description": "A luxury downtown apartment with floor-to-ceiling windows...",
  "type": "indoor",
  "scope": "room"
}
```

**Multi-Level Space:**
```json
{
  "name": "Sterling Penthouse - Upper Floor",
  "description": "Master bedroom suite with walk-in closets...",
  "type": "indoor",
  "scope": "floor"
}
```

**Public Space:**
```json
{
  "name": "The Metropolitan Club",
  "description": "An exclusive restaurant where New York's elite gather...",
  "type": "indoor",
  "scope": "building"
}
```

**Landmark:**
```json
{
  "name": "The Old Oak Tree",
  "description": "An ancient oak tree between the Cross and Sterling family estates...",
  "type": "outdoor",
  "scope": "landmark"
}
```

---

## 4. Relationships

Relationships define the initial state of connections between characters.

```json
{
  "relationships": [
    {
      "entity1": "Character Name 1",
      "entity2": "Character Name 2",
      "type": "relationship description",
      "first_meeting": "When and how they first met",
      "trust": 0.2,
      "affection": 0.3,
      "familiarity": 0.6,
      "history": "Detailed shared history"
    }
  ]
}
```

### Fields

| Field | Type | Range | Purpose |
|-------|------|-------|---------|
| `entity1` | string | - | First character name (must match character.name) |
| `entity2` | string | - | Second character name (must match character.name) |
| `type` | string | - | Freeform description of relationship |
| `first_meeting` | string | - | Context of how they met |
| `trust` | float | 0.0-1.0 | How much they trust each other |
| `affection` | float | 0.0-1.0 | Emotional warmth/liking |
| `familiarity` | float | 0.0-1.0 | How well they know each other |
| `history` | string | - | Detailed backstory of their relationship |

### Relationship Value Meanings

**Trust (0.0 to 1.0):**
- 0.0-0.2: Actively distrustful, suspicious
- 0.2-0.4: Low trust, wary
- 0.4-0.6: Neutral, no strong opinion
- 0.6-0.8: Trustworthy, reliable
- 0.8-1.0: Complete trust

**Affection (0.0 to 1.0):**
- 0.0-0.2: Dislike, hostility
- 0.2-0.4: Cold, distant
- 0.4-0.6: Neutral feelings
- 0.6-0.8: Warm, friendly
- 0.8-1.0: Deep love/care

**Familiarity (0.0 to 1.0):**
- 0.0-0.2: Strangers or just met
- 0.2-0.4: Acquaintances
- 0.4-0.6: Know each other moderately
- 0.6-0.8: Know each other well
- 0.8-1.0: Know each other intimately

### Example: Complex Relationship

```json
{
  "entity1": "Miriam Cross",
  "entity2": "Alexander Sterling",
  "type": "childhood friends turned bitter strangers forced into marriage",
  "first_meeting": "Met at age 5 when their parents signed the marriage contract...",
  "trust": 0.2,
  "affection": 0.3,
  "familiarity": 0.6,
  "history": "Were best friends from age 5-13. Alex was there for Miriam after her mother and brother died when she was 8, providing comfort through her darkest years. At 13, Alex was sent to boarding school without warning, never saying goodbye. Miriam waited by their oak tree for three days. They haven't seen each other in 15 years. Both harbor deep hurt, resentment, and buried feelings. The contract forces them back together when neither has a choice."
}
```

**Why these values?**
- **Trust: 0.2** - Very low due to abandonment and betrayal
- **Affection: 0.3** - Slightly higher because of childhood bond (still there, buried)
- **Familiarity: 0.6** - Moderately high because they were best friends for 8 years

### Example: Not Yet Met

```json
{
  "entity1": "Miriam Cross",
  "entity2": "Margaret Chen",
  "type": "future housekeeper relationship, initially wary",
  "first_meeting": "Will meet when Miriam moves into the Sterling penthouse",
  "trust": 0.0,
  "affection": 0.0,
  "familiarity": 0.0,
  "history": "Not yet met, but Margaret will become protective of Miriam"
}
```

---

## 5. Story Arcs

Story arcs define the major plot progression beats and track completion.

```json
{
  "story_arcs": [
    {
      "name": "Arc Name",
      "description": "What happens in this arc",
      "order": 1,
      "is_active": 1,
      "start_condition": {
        "flags": ["flag_name"]
      },
      "completion_condition": {
        "flags": ["flag_name"]
      },
      "episodes": [
        {
          "name": "Episode Name",
          "description": "What happens in this episode",
          "order": 1,
          "trigger_flags": ["flag_name"],
          "completion_flags": ["flag_name"]
        }
      ]
    }
  ]
}
```

### Fields

| Field | Type | Purpose |
|-------|------|---------|
| `name` | string | Arc name |
| `description` | string | What the arc is about |
| `order` | int | Sequence number (1, 2, 3, ...) |
| `is_active` | int | 0 or 1, whether arc is currently active |
| `start_condition` | object | Flags required to activate this arc |
| `completion_condition` | object | Flags required to complete this arc |
| `episodes` | array | Sub-sections within the arc (optional) |

### Example: First Arc

```json
{
  "name": "Forced Reunion",
  "description": "Miriam and Alex's first encounters after 15 years, filled with anger, hurt, and forced cooperation. They must prepare for their public debut as an engaged couple.",
  "order": 1,
  "is_active": 1,
  "start_condition": {},
  "completion_condition": {
    "flags": ["first_public_appearance_complete"]
  },
  "episodes": [
    {
      "name": "The Doorstep",
      "description": "Alex arrives to pick up Miriam for their first public appearance. The tension is explosive.",
      "order": 1,
      "trigger_flags": [],
      "completion_flags": ["alex_arrived_at_apartment"]
    },
    {
      "name": "The Metropolitan Club",
      "description": "Their first public appearance as an engaged couple. They must convince New York's elite while barely able to stand each other.",
      "order": 2,
      "trigger_flags": ["alex_arrived_at_apartment"],
      "completion_flags": ["first_public_appearance_complete"]
    }
  ]
}
```

### Example: Conditional Arc

```json
{
  "name": "Under One Roof",
  "description": "Miriam moves into the Sterling penthouse. Living together forces daily interactions and slowly breaks down their walls.",
  "order": 2,
  "is_active": 0,
  "start_condition": {
    "flags": ["first_public_appearance_complete"]
  },
  "completion_condition": {
    "flags": ["settled_into_penthouse", "established_boundaries"]
  },
  "episodes": []
}
```

**How it works:**
1. Arc starts inactive (`is_active: 0`)
2. When `first_public_appearance_complete` flag is set, arc activates
3. Arc completes when BOTH `settled_into_penthouse` AND `established_boundaries` are set

---

## 6. How Data Flows into the System

### Import Process

1. **JSON File** → `load_story_from_json()` in `backend/app/routers/admin.py:180`
2. Creates database records with `playthrough_id = NULL` (templates)
3. When user starts a new playthrough:
   - Copies template data
   - Sets `playthrough_id` to the new playthrough
   - Characters, relationships, locations, arcs are now playthrough-specific

### Character Usage

**In Character Decision Prompt:**
```python
character_info = context_builder.get_character_info(character_id)
# Returns all fields: name, type, traits, backstory, values, fears, etc.

prompt = PromptTemplates.character_decision_prompt(
    character_info,
    context,
    user_action
)
```

**In Story Generation:**
```python
# Character decisions are already made
character_decisions = [
    {
        "character_name": "Alexander Sterling",
        "action": "...",
        "dialogue": "...",
        "emotion": "...",
        "refuses": False,
        "reason": "..."
    }
]

# Passed into story generation prompt
prompt = PromptTemplates.story_generation_prompt(
    context,
    user_action,
    character_decisions,  # AI MUST follow these
    story_info
)
```

### Relationship Usage

**In Context:**
```
RELATIONSHIP STATUS:
Alexander Sterling:
  Relationship: childhood friends turned bitter strangers
  Trust: 0.20
  Affection: 0.30
  Familiarity: 0.60
  History: Were best friends from age 5-13...
```

**Dynamic Updates:**
After each interaction, relationships can change:
- Trust: ±0.1 to ±0.3
- Affection: ±0.1 to ±0.3
- Familiarity: +0.0 to +0.2 (only increases)

### Story Arc Usage

**In Context:**
```
ACTIVE STORY ARCS:
- Forced Reunion: Miriam and Alex's first encounters after 15 years...
```

**Progression:**
System checks after each response whether flags should be set to advance arcs.

---

## 7. Design Principles

### Why Deep Character Modeling?

1. **Prevents "Yes-Man" NPCs:** Characters with values/fears can refuse user
2. **Creates Believable Conflict:** Characters have real reasons to disagree
3. **Enables Character Growth:** Secrets/vulnerabilities create arcs
4. **Ensures Consistency:** Values guide decisions across all interactions
5. **Supports Long-Form Stories:** Characters remain recognizable over time

### Why Relationship Tracking?

1. **Dynamic Interactions:** Relationships evolve based on player choices
2. **Meaningful Consequences:** Poor choices damage relationships
3. **Emergent Storytelling:** Relationship values affect character decisions
4. **Player Agency:** Players see the impact of their choices

### Why Story Arcs with Flags?

1. **Structured Progression:** Ensures story moves forward
2. **Flexible Pacing:** Player actions determine when arcs advance
3. **Multiple Paths:** Different flags can lead to different arcs
4. **Tracking Progress:** System knows what has/hasn't happened

---

## 8. Creating Your Own Story

To create a new story, copy `backend/test_data/TEMPLATE_story.json` and fill in:

**Minimum Required:**
- Story title, description, initial_message
- At least 1 User character
- At least 1 Main or Support character
- At least 1 location
- At least 1 relationship (between user and main character)
- At least 1 story arc

**Recommended:**
- 3-5 detailed characters (1 User, 2-3 Main, 1-2 Support)
- 5-10 locations spanning different scopes
- All relationships between characters who know each other
- 3-5 story arcs for major plot beats

**Character Detail Checklist:**
- [ ] Name, type, age, appearance
- [ ] Backstory with specific events
- [ ] 5-7 personality traits
- [ ] Speech patterns description
- [ ] Core values (3-5)
- [ ] Core fears (3-5)
- [ ] Would never do (3-5 actions)
- [ ] Would always do (3-5 actions)
- [ ] Verbal patterns (greetings, agreement, disagreement, etc.)
- [ ] Decision style
- [ ] Internal contradiction
- [ ] Secret kept
- [ ] Vulnerability

The more detail you provide, the more consistent and engaging characters will be!
