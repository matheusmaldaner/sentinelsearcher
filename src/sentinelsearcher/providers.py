"""
Multi-provider support for Sentinel Searcher.

Supports:
- Anthropic Claude with web_search_20250305 tool
- OpenAI GPT with web_search_preview tool (via Responses API)
"""

from abc import ABC, abstractmethod
from typing import Optional, Type
import os


class WebSearchProvider(ABC):
    """Abstract base class for web search providers."""

    @abstractmethod
    def search_and_extract(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 2048,
        max_search_uses: int = 5,
    ) -> str:
        """
        Perform web search and return extracted text response.

        Args:
            system: System prompt
            user: User prompt
            model: Model identifier
            max_tokens: Maximum tokens in response
            max_search_uses: Maximum web searches allowed

        Returns:
            Text response from the model
        """
        pass

    @abstractmethod
    def get_rate_limit_error_class(self) -> Type[Exception]:
        """Return the rate limit exception class for this provider."""
        pass


class AnthropicProvider(WebSearchProvider):
    """Anthropic Claude provider with web search."""

    def __init__(self, api_key: Optional[str] = None):
        import anthropic

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not provided and not found in environment."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self._anthropic = anthropic

    def search_and_extract(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 2048,
        max_search_uses: int = 5,
    ) -> str:
        msg = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_search_uses
            }],
        )
        # Extract text from content blocks
        return "".join(
            getattr(b, "text", "")
            for b in msg.content
            if getattr(b, "type", "") == "text"
        )

    def get_rate_limit_error_class(self) -> Type[Exception]:
        return self._anthropic.RateLimitError


class OpenAIProvider(WebSearchProvider):
    """OpenAI GPT provider with web search via Responses API."""

    def __init__(self, api_key: Optional[str] = None):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OPENAI_API_KEY not provided and not found in environment."
            )
        self.client = openai.OpenAI(api_key=key)
        self._openai = openai

    def search_and_extract(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 2048,
        max_search_uses: int = 5,
    ) -> str:
        # OpenAI Responses API with web search
        # Note: web_search_preview is the OpenAI equivalent
        response = self.client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            tools=[{
                "type": "web_search_preview",
                "search_context_size": "medium",  # low, medium, high
            }],
            max_output_tokens=max_tokens,
        )

        # Extract text from response output
        text_parts = []
        for item in response.output:
            if hasattr(item, 'content'):
                for content in item.content:
                    if hasattr(content, 'text'):
                        text_parts.append(content.text)

        return "".join(text_parts)

    def get_rate_limit_error_class(self) -> Type[Exception]:
        return self._openai.RateLimitError


def create_provider(
    provider_name: str,
    api_key: Optional[str] = None
) -> WebSearchProvider:
    """
    Factory function to create a provider instance.

    Args:
        provider_name: Either 'anthropic' or 'openai'
        api_key: Optional API key (falls back to environment variables)

    Returns:
        WebSearchProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_name = provider_name.lower()

    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    else:
        raise ValueError(
            f"Unsupported provider: {provider_name}. "
            "Supported providers: 'anthropic', 'openai'"
        )
