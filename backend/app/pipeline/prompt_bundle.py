"""
PromptBundle - structured per-turn input to the prompt, with a renderer
for the legacy concatenated-string format.

Vocabulary (R8): "prompt" / "bundle" means what we send to the LLM;
"context" means the in-world background (the character's situation,
what they know, their goals). This file owns the prompt input.

R2 introduced the typed bundle without changing what the model sees:
`render_legacy_prompt(bundle)` reproduces the exact format the pre-R2
build_full_context() (now `PromptBuilder.build_prompt_string()`) used to
emit. The promise from REFACTOR_FIRST.md is byte-for-byte (or near) —
assemble the prompt through this renderer until M2.x flips on
per-character filtering.

`CharacterView` is the rich per-character block. M2.3 will populate
`PromptBundle.target_character` and let prompt templates re-inject the
character sheet at the top of every prompt that involves that character
(killing drift). For R2 it's an unused slot.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Views — data the model needs, separated from how it's rendered.
# ---------------------------------------------------------------------------


@dataclass
class StoryView:
    """Static story metadata."""
    id: int
    title: str
    description: Optional[str] = None


@dataclass
class SceneView:
    """Current scene state.

    `is_initial=True` means no `SceneState` row exists yet for this session;
    the renderer emits the legacy "Story beginning" line in that case.
    """
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    emotional_tone: Optional[str] = None
    scene_context: Optional[str] = None
    is_initial: bool = False


@dataclass
class CharacterPresenceView:
    """Lightweight view used in the CHARACTERS PRESENT block."""
    name: str
    character_type: Optional[str] = None
    mood: Optional[str] = None
    intent: Optional[str] = None


@dataclass
class ConversationMessageView:
    """One rendered conversation row (speaker label already resolved)."""
    speaker_label: str
    message: str


@dataclass
class RelationshipView:
    """Relationship between the user character and another character."""
    other_character_name: str
    relationship_type: str
    trust: float
    affection: float
    familiarity: float
    history_summary: Optional[str] = None


@dataclass
class ActiveArcView:
    arc_name: str
    description: Optional[str] = None


@dataclass
class MemoryFlagView:
    flag_type: str
    flag_value: str


@dataclass
class CharacterView:
    """
    Full per-character profile for prompts that involve a specific character.

    The character sheet block (values, fears, would_never_do, etc.) is held
    separately from `state` and `goals` so they can be re-injected fresh
    every turn — drift starts when these dilute (P2.4 / M2.4).

    Slot is unused in R2; M2.3 will populate it via
    `PromptBuilder.build_prompt_bundle_for_character()` plus witness filtering.
    """
    id: int
    name: str
    character_type: str
    sheet: Dict[str, Any] = field(default_factory=dict)
    state: Optional[Dict[str, Any]] = None
    goals: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    mood: Optional[str] = None
    intent: Optional[str] = None
    position: Optional[str] = None


@dataclass
class PromptBundle:
    """Everything PROMPT_BUILD produced for this turn."""
    story: StoryView
    scene: SceneView
    characters_present: List[CharacterPresenceView] = field(default_factory=list)
    history: List[ConversationMessageView] = field(default_factory=list)
    relationships: List[RelationshipView] = field(default_factory=list)
    active_arcs: List[ActiveArcView] = field(default_factory=list)
    memory_flags: List[MemoryFlagView] = field(default_factory=list)
    target_character: Optional[CharacterView] = None

    def to_string(self) -> str:
        """Convenience for the deprecated `build_prompt_string()` alias."""
        return render_legacy_prompt(self)


# ---------------------------------------------------------------------------
# Renderer — byte-for-byte reproduction of the legacy concatenated format.
# ---------------------------------------------------------------------------


def render_legacy_prompt(bundle: PromptBundle) -> str:
    """Reproduce the string pre-R2 build_full_context() (now
    `PromptBuilder.build_prompt_string()`) emitted.

    Order, prefixes and trailing newlines are intentionally identical so the
    LLM input doesn't shift during R2.
    """
    parts: List[str] = [
        f"STORY INFORMATION:\n{_render_story(bundle.story)}",
        f"\nCURRENT SCENE:\n{_render_scene(bundle.scene)}",
        f"\nCHARACTERS PRESENT:\n{_render_characters_present(bundle.characters_present)}",
        f"\nRECENT CONVERSATION:\n{_render_history(bundle.history)}",
    ]

    relationships = _render_relationships(bundle.relationships)
    if relationships:
        parts.append(f"\nRELATIONSHIP STATUS:\n{relationships}")

    arcs = _render_arcs(bundle.active_arcs)
    if arcs:
        parts.append(f"\nACTIVE STORY ARCS:\n{arcs}")

    flags = _render_memory_flags(bundle.memory_flags)
    if flags:
        parts.append(f"\nIMPORTANT MEMORIES:\n{flags}")

    return "\n".join(parts)


def _render_story(story: StoryView) -> str:
    out = f"Title: {story.title}\n"
    if story.description:
        out += f"Description: {story.description}\n"
    return out


def _render_scene(scene: SceneView) -> str:
    if scene.is_initial:
        location = scene.location or "Unknown location"
        time = scene.time_of_day or "Unknown time"
        return f"Location: {location}\nTime: {time}\nScene: Story beginning"

    out = f"Location: {scene.location or 'Unknown'}\n"
    out += f"Time: {scene.time_of_day or 'Unknown'}\n"
    if scene.weather:
        out += f"Weather: {scene.weather}\n"
    if scene.emotional_tone:
        out += f"Mood: {scene.emotional_tone}\n"
    if scene.scene_context:
        out += f"Context: {scene.scene_context}\n"
    return out


def _render_characters_present(characters: List[CharacterPresenceView]) -> str:
    if not characters:
        return "- No characters in scene\n"

    out = ""
    for c in characters:
        out += f"- {c.name}"
        if c.character_type:
            out += f" ({c.character_type})"
        if c.mood:
            out += f" - Mood: {c.mood}"
        if c.intent:
            out += f" - Intent: {c.intent}"
        out += "\n"
    return out


def _render_history(history: List[ConversationMessageView]) -> str:
    if not history:
        return "No conversation yet.\n"

    out = ""
    for msg in history:
        out += f"{msg.speaker_label}: {msg.message}\n\n"
    return out


def _render_relationships(relationships: List[RelationshipView]) -> str:
    if not relationships:
        return ""

    out = ""
    for rel in relationships:
        out += f"{rel.other_character_name}:\n"
        out += f"  Relationship: {rel.relationship_type}\n"
        out += f"  Trust: {rel.trust:.2f}\n"
        out += f"  Affection: {rel.affection:.2f}\n"
        out += f"  Familiarity: {rel.familiarity:.2f}\n"
        if rel.history_summary:
            out += f"  History: {rel.history_summary}\n"
        out += "\n"
    return out


def _render_arcs(arcs: List[ActiveArcView]) -> str:
    if not arcs:
        return ""

    out = ""
    for arc in arcs:
        out += f"- {arc.arc_name}"
        if arc.description:
            out += f": {arc.description}"
        out += "\n"
    return out


def _render_memory_flags(flags: List[MemoryFlagView]) -> str:
    if not flags:
        return ""

    out = ""
    for flag in flags:
        out += f"- [{flag.flag_type}] {flag.flag_value}\n"
    return out
