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
            elif self.provider == "local":
                # Local Ollama
                response = await self._call_ollama(
                    model, prompt, max_tokens, temperature, system_prompt
                )
            elif self.provider == "demo":
                # Demo mode - returns mock responses for testing without API
                response = await self._generate_demo_response(prompt, model_size)
            else:
                # Unknown provider
                self.logger.error(
                    f"Unknown provider: {self.provider}",
                    "ai"
                )
                response = f"Error: Unknown provider {self.provider}"

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

    async def _call_ollama(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """
        Call local Ollama API

        Ollama provides a local LLM server with OpenAI-compatible API
        No API key needed, works offline!
        """
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

        # Prepare request payload (Ollama uses similar format to OpenAI)
        payload = {
            "model": model,
            "messages": messages,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            },
            "stream": False
        }

        # Make the API call (no auth needed for local Ollama)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for local generation
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )

                if response.status_code != 200:
                    error_detail = response.text
                    self.logger.error(
                        f"Ollama API error: {response.status_code}",
                        "ai",
                        {"status": response.status_code, "detail": error_detail}
                    )
                    raise Exception(f"Ollama error {response.status_code}: {error_detail}")

                result = response.json()

                # Extract the generated text from Ollama response format
                if "message" in result and "content" in result["message"]:
                    return result["message"]["content"]
                else:
                    raise Exception("Invalid response format from Ollama")
        except httpx.ConnectError:
            self.logger.error(
                "Cannot connect to Ollama. Is it running?",
                "ai",
                {"base_url": self.base_url}
            )
            raise Exception(
                "Cannot connect to Ollama. Make sure Ollama is installed and running. "
                "Visit https://ollama.com/download"
            )

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

    async def _generate_demo_response(self, prompt: str, model_size: str) -> str:
        """
        Generate demo/mock responses for testing without an API key

        This allows testing the full application flow without incurring API costs
        """
        self.logger.notification(
            f"Generating demo response (model_size: {model_size})",
            "ai"
        )

        # Check what type of prompt this is based on content
        prompt_lower = prompt.lower()

        # Scene change detection
        if "scene changes" in prompt_lower or "location_changed" in prompt_lower:
            return json.dumps({
                "location_changed": False,
                "new_location": None,
                "time_changed": False,
                "new_time": None,
                "characters_entered": [],
                "characters_left": [],
                "significant_event": None
            })

        # Character decision
        if "character would realistically do" in prompt_lower or '"refuses":' in prompt_lower:
            return json.dumps({
                "action": "responds thoughtfully to the situation",
                "dialogue": "I appreciate you sharing that with me.",
                "emotion": "thoughtful",
                "refuses": False,
                "reason": "The character is engaged with the conversation and wants to continue the interaction."
            })

        # Relationship update
        if "trust_change" in prompt_lower or "affection_change" in prompt_lower:
            return json.dumps({
                "trust_change": 0.05,
                "affection_change": 0.03,
                "familiarity_change": 0.02,
                "reason": "Positive interaction that builds trust and connection."
            })

        # Story flags detection
        if "story flags" in prompt_lower or '"flags":' in prompt_lower:
            return json.dumps({
                "flags": []
            })

        # Story generation (default for large model)
        if model_size == "large" or "write the next part" in prompt_lower:
            return self._generate_demo_story()

        # Default response
        return json.dumps({
            "response": "Demo mode active",
            "note": "This is a placeholder response for testing"
        })

    def _generate_demo_story(self) -> str:
        """
        Generate a demo story continuation

        Provides realistic-looking story text for testing the UI
        """
        import random

        responses = [
            """The air between you feels charged with unspoken words. Your visitor shifts their weight slightly, a gesture you remember from countless conversations years ago.

"I know I should have called," they say, their voice carrying a weight of regret. "I know I should have done a lot of things differently."

You feel your heart rate quicken. Part of you wants to slam the door, to protect yourself from the hurt that their absence caused. But another part, the part that remembers late-night conversations and shared dreams, wants to hear what they have to say.

The evening light casts long shadows across the floor, and somewhere in the distance, you can hear the sound of traffic. But in this moment, it feels like the world has shrunk to just this doorway, just this conversation that's been five years in the making.""",

            """They take a tentative step forward, then stop, as if asking permission to enter your space once more.

"I've thought about what to say to you every day since I left," they admit, running a hand through their hair in that familiar nervous gesture. "And now that I'm here, none of those words seem good enough."

You notice the subtle changes in them - the way they carry themselves with more confidence, but also the tiredness around their eyes that suggests the journey hasn't been as smooth as it appeared from the outside.

"Maybe we could talk?" they suggest hopefully. "Really talk. About everything. About what happened, about why I left, about..." they trail off, but their eyes convey what their words cannot.

The weight of this moment settles on your shoulders. This is your choice to make.""",

            """A long moment passes between you, filled with everything that was and everything that could be.

Finally, they speak again, their voice softer now. "I brought something. It's silly, probably, but..." They reach into their pocket and pull out a small, worn object - something that immediately tugs at your memories.

Your breath catches. It's the keychain you gave them years ago, the one with the small star charm. They kept it all this time.

"I never stopped thinking about home," they say quietly. "About you. About all the things I should have said before I left."

The evening breeze carries the scent of rain, and you realize that whatever you decide in this moment will change everything. Do you let the past stay buried, or do you open the door to possibilities you'd long ago given up on?"""
        ]

        return random.choice(responses)
