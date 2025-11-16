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
    ai_provider: str = "demo"

    # OpenRouter Settings
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Nebius Settings (alternative provider)
    nebius_api_key: Optional[str] = None
    nebius_base_url: str = "https://api.studio.nebius.ai/v1"

    # Local Ollama Settings
    ollama_host: str = "http://localhost:11434"

    # Model Configuration
    # Small model: Used for quick analysis tasks (character decisions, event detection)
    small_model: str = "meta-llama/llama-3.2-3b-instruct"
    # Large model: Used for story generation
    large_model: str = "meta-llama/llama-3.1-8b-instruct"

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
