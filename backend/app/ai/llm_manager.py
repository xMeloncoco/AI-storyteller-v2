"""
LLM Manager - Handles communication with AI models
Supports multiple providers: OpenRouter, Nebius, Local Ollama

This is the core AI interface that:
1. Sends prompts to the AI
2. Receives and parses responses
3. Handles errors and retries
4. Logs all AI interactions
"""
import httpx
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..config import settings
from ..utils.logger import AppLogger


class LLMManager:
    """
    Manages all LLM (Large Language Model) interactions

    Supports:
    - OpenRouter API (multiple models)
    - Nebius API
    - Local Ollama (for offline use - future feature)
    """

    def __init__(self, db: Session, session_id: Optional[int] = None):
        """
        Initialize the LLM Manager

        Args:
            db: Database session for logging
            session_id: Optional session ID for contextual logging
        """
        self.db = db
        self.logger = AppLogger(db, session_id)
        self.provider = settings.ai_provider

        # Set up API configuration based on provider
        if self.provider == "openrouter":
            self.api_key = settings.openrouter_api_key
            self.base_url = settings.openrouter_base_url
        elif self.provider == "nebius":
            self.api_key = settings.nebius_api_key
            self.base_url = settings.nebius_base_url
        else:
            # Local Ollama - future implementation
            self.api_key = None
            self.base_url = settings.ollama_host

        self.logger.notification(
            f"LLM Manager initialized with provider: {self.provider}",
            "ai"
        )

    async def generate_text(
        self,
        prompt: str,
        model_size: str = "large",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using the configured LLM

        Args:
            prompt: The user/story prompt to send
            model_size: "small" for quick analysis, "large" for story generation
            max_tokens: Maximum tokens in response (uses defaults if None)
            temperature: Creativity level (0.0 = deterministic, 1.0 = creative)
            system_prompt: Optional system instructions for the AI

        Returns:
            Generated text from the AI
        """
        # Select model based on size
        if model_size == "small":
            model = settings.small_model
            default_tokens = settings.max_tokens_small
        else:
            model = settings.large_model
            default_tokens = settings.max_tokens_large

        if max_tokens is None:
            max_tokens = default_tokens

        # Log the request
        self.logger.ai_decision(
            f"Sending request to {model_size} model ({model})",
            "ai",
            {
                "model": model,
                "prompt_length": len(prompt),
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        )

        try:
            if self.provider == "openrouter":
                response = await self._call_openrouter(
                    model, prompt, max_tokens, temperature, system_prompt
                )
            elif self.provider == "nebius":
                response = await self._call_nebius(
                    model, prompt, max_tokens, temperature, system_prompt
                )
            else:
                # Fallback to local - not yet implemented
                self.logger.error(
                    f"Provider {self.provider} not fully implemented",
                    "ai"
                )
                response = "Error: Local provider not yet implemented"

            # Log successful response
            self.logger.notification(
                f"Received response from {model_size} model",
                "ai",
                {"response_length": len(response)}
            )

            return response

        except Exception as e:
            self.logger.error(
                f"Error generating text: {str(e)}",
                "ai",
                {"model": model, "error": str(e)}
            )
            raise

    async def _call_openrouter(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """
        Call OpenRouter API

        OpenRouter provides access to multiple AI models through a single API
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        # Build messages array
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Set headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # Required by OpenRouter
            "X-Title": "Dreamwalkers"
        }

        # Make the API call
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                error_detail = response.text
                self.logger.error(
                    f"OpenRouter API error: {response.status_code}",
                    "ai",
                    {"status": response.status_code, "detail": error_detail}
                )
                raise Exception(f"API error {response.status_code}: {error_detail}")

            result = response.json()

            # Extract the generated text
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception("Invalid response format from OpenRouter")

    async def _call_nebius(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """
        Call Nebius API

        Nebius provides similar interface to OpenRouter
        """
        if not self.api_key:
            raise ValueError("Nebius API key not configured")

        # Build messages array
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Set headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Make the API call
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                error_detail = response.text
                self.logger.error(
                    f"Nebius API error: {response.status_code}",
                    "ai",
                    {"status": response.status_code, "detail": error_detail}
                )
                raise Exception(f"API error {response.status_code}: {error_detail}")

            result = response.json()

            # Extract the generated text
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception("Invalid response format from Nebius")

    async def analyze_character_decision(
        self,
        character_info: Dict[str, Any],
        context: str,
        user_action: str
    ) -> Dict[str, Any]:
        """
        Character Decision Layer - Phase 1.3+

        Ask the AI what the character would realistically do in this situation
        This happens BEFORE generating the actual story text

        Args:
            character_info: Character's traits, personality, history
            context: Current scene context
            user_action: What the user just did/said

        Returns:
            Dictionary with character's decision:
            - action: What they will do
            - dialogue: What they will say (if anything)
            - emotion: Their emotional state
            - refuses: Whether they refuse the user's action
            - reason: Why they made this decision
        """
        from .prompts import PromptTemplates

        prompt = PromptTemplates.character_decision_prompt(
            character_info, context, user_action
        )

        self.logger.ai_decision(
            f"Analyzing character decision for: {character_info.get('name', 'Unknown')}",
            "character",
            {"character": character_info.get("name"), "user_action": user_action[:100]}
        )

        response = await self.generate_text(
            prompt,
            model_size="small",  # Use small model for quick analysis
            temperature=0.5  # More deterministic for character consistency
        )

        # Parse the response - expecting JSON
        try:
            decision = json.loads(response)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract key information
            self.logger.error(
                "Character decision response not valid JSON, attempting to parse",
                "character",
                {"raw_response": response}
            )
            decision = self._parse_decision_text(response)

        self.logger.ai_decision(
            f"Character decision: {decision.get('action', 'unknown')}",
            "character",
            decision
        )

        return decision

    def _parse_decision_text(self, text: str) -> Dict[str, Any]:
        """
        Fallback parser for character decision when JSON parsing fails

        Tries to extract key information from natural language response
        """
        decision = {
            "action": "respond",
            "dialogue": "",
            "emotion": "neutral",
            "refuses": False,
            "reason": "Unable to parse structured response"
        }

        # Simple keyword detection - this is a fallback
        text_lower = text.lower()

        if "refuse" in text_lower or "won't" in text_lower or "wouldn't" in text_lower:
            decision["refuses"] = True

        if "angry" in text_lower or "frustrated" in text_lower:
            decision["emotion"] = "angry"
        elif "happy" in text_lower or "pleased" in text_lower:
            decision["emotion"] = "happy"
        elif "sad" in text_lower or "disappointed" in text_lower:
            decision["emotion"] = "sad"

        # Use the full text as the reason/explanation
        decision["reason"] = text

        return decision

    async def detect_scene_changes(
        self,
        previous_context: str,
        new_message: str
    ) -> Dict[str, Any]:
        """
        Lightweight Model Task - Phase 1.2+

        Detect if there are any scene changes:
        - Location change
        - Time change
        - Characters entering/leaving
        - Significant events

        Uses the small model for quick analysis
        """
        from .prompts import PromptTemplates

        prompt = PromptTemplates.scene_change_detection_prompt(
            previous_context, new_message
        )

        self.logger.context(
            "Analyzing for scene changes",
            "ai"
        )

        response = await self.generate_text(
            prompt,
            model_size="small",
            temperature=0.3  # Very deterministic for detection
        )

        # Parse response
        try:
            changes = json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(
                "Scene change detection response not valid JSON",
                "ai",
                {"raw_response": response}
            )
            changes = {
                "location_changed": False,
                "time_changed": False,
                "characters_entered": [],
                "characters_left": [],
                "significant_event": None
            }

        self.logger.context(
            "Scene change analysis complete",
            "ai",
            changes
        )

        return changes
