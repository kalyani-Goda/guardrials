"""
Google Generative AI (Gemini) integration for LLM calls only
Local storage, database, and caching for everything else
"""

import google.generativeai as genai
from typing import Optional
from config.settings import get_settings
from config.logging_config import logger


class GoogleLLMProvider:
    """Wrapper for Google Generative AI (Gemini)"""

    def __init__(self):
        """Initialize Google Generative AI"""
        settings = get_settings()

        if not settings.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not set in environment. "
                "Get it from https://aistudio.google.com/app/apikeys"
            )

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name = settings.GOOGLE_MODEL
        self.model = genai.GenerativeModel(self.model_name)

        logger.info(f"Google Generative AI initialized with model: {self.model_name}")

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate text using Google Gemini API

        Args:
            prompt: Input prompt
            temperature: Creativity level (0-1)
            max_tokens: Max response length

        Returns:
            Generated text
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            logger.debug(f"Google Gemini API response received")
            return response.text

        except Exception as e:
            logger.error(f"Google Gemini API error: {str(e)}")
            raise

    def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate response with system context (for medical advice)

        Args:
            system_prompt: System instructions/context
            user_message: User input
            temperature: Creativity level
            max_tokens: Max response length

        Returns:
            Generated response
        """
        full_prompt = f"""System Instructions:
{system_prompt}

User Message:
{user_message}

Response:"""

        return self.generate_text(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def count_tokens(self, text: str) -> int:
        """Count tokens for rate limiting and cost estimation"""
        try:
            response = self.model.count_tokens(text)
            return response.total_tokens
        except Exception as e:
            logger.warning(f"Token counting error: {str(e)}")
            return len(text.split())  # Fallback to word count


# Global instance
_google_provider: Optional[GoogleLLMProvider] = None


def get_google_llm() -> GoogleLLMProvider:
    """Get or create Google LLM provider"""
    global _google_provider
    if _google_provider is None:
        _google_provider = GoogleLLMProvider()
    return _google_provider
