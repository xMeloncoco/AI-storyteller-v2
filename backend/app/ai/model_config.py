"""
Per-task model assignment registry (BUILD_INSTRUCTIONS.md M12.2).

Each pipeline LLM call site is a named *task*. Every task is assigned a
``(provider, model, max_tokens)`` independently, so e.g. the analysis/critic
tasks can run on local Ollama while story generation runs on paid DeepSeek.

Two concerns are kept separate on purpose:

* **Task assignments** — which provider+model each task uses. These are the
  mutable, user-facing choices. They are persisted to
  ``settings.ai_model_config_path`` (JSON) so they survive restarts.
* **Provider connections** — base URLs and API keys. These live in
  ``config.Settings`` / ``.env`` and are *never* written to the JSON file, so
  secrets stay out of the persisted config.
"""
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import settings

# ---------------------------------------------------------------------------
# Tasks — one stable key per live LLM call site in the pipeline.
# ---------------------------------------------------------------------------

# Ordered so the settings UI lists them grouped narrative-first then utility.
TASKS = [
    "story_generation",
    "generate_more",
    "scene_detection",
    "character_decision",
    "relationship_update",
    "story_flag",
]

TASK_LABELS = {
    "story_generation": "Story generation",
    "generate_more": "Generate more (continuation)",
    "scene_detection": "Scene change detection",
    "character_decision": "Character decisions",
    "relationship_update": "Relationship updates",
    "story_flag": "Story flag detection",
}

# Tasks that produce narrative prose (the "large"/quality tier). Everything
# else is fast analysis/critic work (the "small" tier). Used only to pick a
# sensible default model the first time, before the user reassigns.
_NARRATIVE_TASKS = {"story_generation", "generate_more"}

# Per-task default token budgets, mapped from the legacy size-based settings so
# behavior is unchanged until the user edits anything.
_DEFAULT_MAX_TOKENS = {
    "story_generation": settings.max_tokens_large,
    "generate_more": settings.generate_more_max_tokens,
    "scene_detection": settings.max_tokens_small,
    "character_decision": settings.max_tokens_small,
    "relationship_update": settings.max_tokens_small,
    "story_flag": settings.max_tokens_small,
}


def _normalize_provider(provider: str) -> str:
    """Map the legacy provider name 'local' to its current name 'ollama'."""
    return "ollama" if provider == "local" else provider


def _default_task_config(task: str) -> Dict[str, Any]:
    """Legacy-equivalent default: old global provider + old small/large model."""
    narrative = task in _NARRATIVE_TASKS
    return {
        "provider": _normalize_provider(settings.ai_provider),
        "model": settings.large_model if narrative else settings.small_model,
        "max_tokens": _DEFAULT_MAX_TOKENS.get(task, settings.max_tokens_small),
    }


# ---------------------------------------------------------------------------
# Providers — connection info resolved from settings/.env (never persisted).
# ---------------------------------------------------------------------------

# type drives which LLMManager call path is used:
#   "openai" -> OpenAI-compatible /chat/completions (deepseek/openrouter/nebius)
#   "ollama" -> local Ollama /api/chat
#   "demo"   -> built-in mock responses, no network
PROVIDER_TYPES = {
    "deepseek": "openai",
    "openrouter": "openai",
    "nebius": "openai",
    "ollama": "ollama",
    "demo": "demo",
}


def provider_connection(provider: str) -> Dict[str, Any]:
    """Resolve a provider name to ``{type, base_url, api_key}`` from settings."""
    provider = _normalize_provider(provider)
    ptype = PROVIDER_TYPES.get(provider, "unknown")

    if provider == "deepseek":
        return {"type": ptype, "base_url": settings.deepseek_base_url, "api_key": settings.deepseek_api_key}
    if provider == "openrouter":
        return {"type": ptype, "base_url": settings.openrouter_base_url, "api_key": settings.openrouter_api_key}
    if provider == "nebius":
        return {"type": ptype, "base_url": settings.nebius_base_url, "api_key": settings.nebius_api_key}
    if provider == "ollama":
        return {"type": ptype, "base_url": settings.ollama_host, "api_key": None}
    if provider == "demo":
        return {"type": ptype, "base_url": None, "api_key": None}
    return {"type": "unknown", "base_url": None, "api_key": None}


def provider_status() -> Dict[str, Dict[str, Any]]:
    """For the settings UI: each provider's type, base_url, and availability."""
    out: Dict[str, Dict[str, Any]] = {}
    for name, ptype in PROVIDER_TYPES.items():
        conn = provider_connection(name)
        if ptype == "openai":
            available = bool(conn["api_key"])
            reason = None if available else "API key not set in .env"
        else:
            available = True
            reason = None
        out[name] = {
            "type": ptype,
            "base_url": conn["base_url"],
            "available": available,
            "reason": reason,
        }
    return out


# ---------------------------------------------------------------------------
# Registry — loads/saves task assignments, thread-safe.
# ---------------------------------------------------------------------------


class ModelRegistry:
    """Holds the per-task assignments and persists them to a JSON file."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = Path(settings.ai_model_config_path)
        self._tasks: Dict[str, Dict[str, Any]] = {
            t: _default_task_config(t) for t in TASKS
        }
        self._load()

    def _load(self) -> None:
        """Merge persisted assignments over the defaults. Never crashes startup."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return  # corrupt/unreadable -> keep defaults
        for task, cfg in (data.get("tasks") or {}).items():
            if task in self._tasks and isinstance(cfg, dict):
                for key in ("provider", "model", "max_tokens"):
                    if key in cfg and cfg[key] is not None:
                        self._tasks[task][key] = cfg[key]

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"tasks": self._tasks}, indent=2), encoding="utf-8"
            )
        except Exception:
            # Persistence is best-effort; in-memory change still applies.
            pass

    def get_task(self, task: str) -> Dict[str, Any]:
        """Resolved config for a task (falls back to defaults for unknown keys)."""
        return dict(self._tasks.get(task) or _default_task_config(task))

    def set_task(
        self,
        task: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update one task's assignment and persist. Returns the new config."""
        with self._lock:
            cfg = self._tasks.setdefault(task, _default_task_config(task))
            if provider is not None:
                cfg["provider"] = provider
            if model is not None:
                cfg["model"] = model
            if max_tokens is not None:
                cfg["max_tokens"] = int(max_tokens)
            self._save()
            return dict(cfg)

    def all_tasks(self) -> Dict[str, Dict[str, Any]]:
        return {t: self.get_task(t) for t in TASKS}


# Module-level singleton, loaded once at import.
model_registry = ModelRegistry()
