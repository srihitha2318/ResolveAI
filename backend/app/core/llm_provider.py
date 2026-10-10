from abc import ABC, abstractmethod
from typing import Optional
import httpx
from app.core.config import settings
from app.core.logging_config import logger


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and ready."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the provider name identifier."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Generates text from the provider or returns None if unavailable or failed."""
        pass


class NullLLMProvider(BaseLLMProvider):
    """Fallback provider when no AI provider credentials are configured."""

    def is_available(self) -> bool:
        return False

    def get_provider_name(self) -> str:
        return "none"

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        return None


class HTTPLLMProvider(BaseLLMProvider):
    """
    Lightweight HTTP-based LLM provider supporting hosted APIs (e.g. Gemini, Groq)
    using the existing httpx library without heavy vendor-specific SDK dependencies.
    """

    def __init__(self, provider_type: str = "none"):
        self.provider_type = provider_type.lower()

    def is_available(self) -> bool:
        if self.provider_type == "gemini":
            return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
        elif self.provider_type == "groq":
            return bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
        return False

    def get_provider_name(self) -> str:
        return self.provider_type

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        if not self.is_available():
            logger.info("AI provider %s is not configured or unavailable.", self.provider_type)
            return None

        try:
            if self.provider_type == "gemini":
                # Google Gemini REST endpoint
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt + chr(10) if system_prompt else ''}{prompt}"}]}]
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]

            elif self.provider_type == "groq":
                # Groq OpenAI-compatible chat completions endpoint
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                payload = {
                    "model": settings.LLM_MODEL,
                    "messages": messages,
                    "temperature": 0.2,
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.warning("LLM generation request failed on %s: %s", self.provider_type, e)
            return None

        return None


def get_llm_provider() -> BaseLLMProvider:
    """Factory to return the active configured LLM provider."""
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name in ("gemini", "groq"):
        provider = HTTPLLMProvider(provider_type=provider_name)
        if provider.is_available():
            return provider
    return NullLLMProvider()
