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

    # Local Ollama Settings (for future offline support)
    ollama_host: str = "http://localhost:11434"

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
