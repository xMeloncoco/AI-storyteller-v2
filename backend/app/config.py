"""
Configuration Management for Dreamwalkers
Loads settings from environment variables with defaults
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    All settings can be overridden via .env file or environment variables
    """

    # Database
    database_url: str = "sqlite:///./data/dreamwalkers.db"

    # ChromaDB for vector memory
    chroma_path: str = "./data/chroma"

    # AI Provider Configuration
    # Options: "local" (Ollama - recommended!), "openrouter", "nebius", "demo"
    # "local" = Uses Ollama for offline, reliable AI (no API keys needed!)
    # "openrouter"/"nebius" = Online APIs (requires API key, subject to rate limits)
    # "demo" = Testing mode without AI
    ai_provider: str = "local"

    # OpenRouter Settings (FREE tier available!)
    # Get free API key from https://openrouter.ai/
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Nebius Settings (alternative provider with free credits)
    # Get API key from https://studio.nebius.ai/
    nebius_api_key: Optional[str] = None
    nebius_base_url: str = "https://api.studio.nebius.ai/v1"

    # DeepSeek Settings (paid, OpenAI-compatible API — good for generation)
    # Get API key from https://platform.deepseek.com/
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # Local Ollama Settings (for future offline support)
    ollama_host: str = "http://localhost:11434"

    # Number of model layers Ollama offloads to the GPU.
    #   None  -> let Ollama decide (default; uses GPU when it can)
    #   0     -> force CPU-only (use on old GPUs that crash on GPU offload,
    #            e.g. a Maxwell GTX 960 hitting "unsupported PTX toolchain")
    ollama_num_gpu: Optional[int] = None

    # Where per-task model assignments are persisted (see ai/model_config.py).
    # Kept alongside the SQLite DB in ./data/. API keys are NOT written here —
    # they stay in this Settings object / .env. (Named ai_* to avoid pydantic's
    # protected `model_` field namespace.)
    ai_model_config_path: str = "./data/model_config.json"

    # Model Configuration
    # For LOCAL (Ollama) - recommended for reliability:
    #   small_model: "llama3.2:3b" (3GB, fast for quick tasks)
    #   large_model: "llama3.2" (4.7GB, better for story generation)
    # For OpenRouter (online, requires API key):
    #   Add ":free" suffix and get key from https://openrouter.ai/

    # Small model: Used for quick analysis tasks (character decisions, event detection)
    small_model: str = "llama3.2:3b"
    # Large model: Used for story generation
    large_model: str = "llama3.2"

    # Application Settings
    log_level: str = "INFO"

    # Context and Memory Settings
    # How many messages to include in background context
    max_context_messages: int = 40  # Increased from 20 to maintain better context

    # How often to save/summarize memory (every N AI responses)
    # Phase 4 feature: UPDATE MEMORY/SAVE BUTTON
    memory_save_interval: int = 5

    # Maximum tokens for AI responses
    max_tokens_small: int = 500
    max_tokens_large: int = 3000  # Increased from 2000 for more detailed responses

    # Token budget for the GENERATE_MORE continuation path. Kept smaller
    # than max_tokens_large because continuations are meant to nudge the
    # story along, not produce a full beat. Raise if continuations feel
    # truncated; lower if they overshoot user agency.
    generate_more_max_tokens: int = 1000

    # =====================================================================
    # CONTEXT_GATHERING tuning (Stage 3)
    # =====================================================================

    # MemoryFlags below this importance score don't get pulled into context.
    # Raising it = tighter context, less drift toward old events. Lowering
    # it = more historical color, but more risk of stale facts crowding the
    # prompt. Scale is 1-10 (see models.MemoryFlag.importance).
    memory_flag_min_importance: int = 7

    # Hard cap on how many MemoryFlags reach the prompt even if more pass
    # the importance threshold. Stops a long playthrough from flooding the
    # context window with old flags.
    memory_flag_top_n: int = 10

    # =====================================================================
    # VALIDATION tuning (Stage 7)
    # =====================================================================

    # Single-character dialogue gets flagged as "too long" past this word
    # count. Raising it = more tolerance for monologues; lowering it =
    # snappier dialogue, but risk of flagging legitimate exposition.
    max_dialogue_words: int = 50

    # =====================================================================
    # STATE_UPDATE tuning (Stage 9)
    # =====================================================================

    # Temperature for the small-model call that estimates relationship
    # trust/affection/familiarity deltas. Lower = more deterministic and
    # repeatable; higher = more variance turn-to-turn.
    relationship_update_temperature: float = 0.3

    # Absolute delta below which we skip writing the relationship row.
    # Stops 0.001 jitter from spamming the DB. Raise if relationship trends
    # feel too twitchy; lower if subtle interactions should accumulate.
    relationship_min_change: float = 0.01

    # Temperature for the small-model call that detects story-flag-worthy
    # events. Lower = more conservative flag detection; higher = more
    # creative interpretation (and false positives).
    story_flag_analysis_temperature: float = 0.3

    # =====================================================================
    # Validation pipeline (Stage 7) - VALIDATION_MODE controls what the
    # validator does when it finds an issue:
    #   warn    - log it and return the text unchanged (current behaviour;
    #             keep as default so M0/R4 doesn't change runtime semantics).
    #   block   - raise 422 to the API caller with the issues listed
    #             (useful in tests / strict mode).
    #   repair  - regenerate once with an addendum prompt when the issue
    #             is `controls_user`; re-validate; fall back to the
    #             original text and log `validation.unrepairable` if the
    #             repair pass still fails.
    # M3 expands the set of repairable issues.
    # =====================================================================
    validation_mode: str = "warn"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()
