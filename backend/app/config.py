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
    # Options: "openrouter", "nebius", "local" (for Ollama), "demo" (for testing without API)
    # IMPORTANT: Set to "demo" for testing without AI, or "openrouter"/"nebius" with API key
    ai_provider: str = "demo"

    # OpenRouter Settings (FREE tier available!)
    # Get free API key from https://openrouter.ai/
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Nebius Settings (alternative provider with free credits)
    # Get API key from https://studio.nebius.ai/
    nebius_api_key: Optional[str] = None
    nebius_base_url: str = "https://api.studio.nebius.ai/v1"

    # Local Ollama Settings (for future offline support)
    ollama_host: str = "http://localhost:11434"

    # Model Configuration
    # Small model: Used for quick analysis tasks (character decisions, event detection)
    # For FREE OpenRouter: add :free suffix to model name!
    # Updated: Phi-3 Mini is typically more available and faster for quick tasks
    small_model: str = "microsoft/phi-3-mini-128k-instruct:free"
    # Large model: Used for story generation
    # For FREE OpenRouter: add :free suffix to model name!
    # Updated: Gemma 2 9B is currently available and works well for story generation
    large_model: str = "google/gemma-2-9b-it:free"

    # NOTE: Free tier models may be rate-limited during peak usage
    # For better reliability, get a free API key from https://openrouter.ai/
    # and set it in your .env file: OPENROUTER_API_KEY=your_key_here

    # Application Settings
    log_level: str = "INFO"

    # Context and Memory Settings
    # How many messages to include in background context
    max_context_messages: int = 20

    # How often to save/summarize memory (every N AI responses)
    # Phase 4 feature: UPDATE MEMORY/SAVE BUTTON
    memory_save_interval: int = 5

    # Maximum tokens for AI responses
    max_tokens_small: int = 500
    max_tokens_large: int = 2000

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()
