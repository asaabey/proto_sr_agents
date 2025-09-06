"""
LLM client wrapper for systematic review agents.

Supports multiple LLM providers with consistent interface for
PICO extraction, PRISMA validation, and specialized assessments.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
import os
from dataclasses import dataclass
import asyncio
from pathlib import Path


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.1  # Low temperature for consistent medical analysis
    timeout: int = 30


class LLMClient:
    """Unified client for LLM API calls across all systematic review agents."""

    def __init__(self, config: LLMConfig):
        # Load environment variables from .env.llm if it exists
        env_file = Path(".env.llm")
        if env_file.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_file)
            except ImportError:
                # dotenv not available, try manual loading
                self._load_env_file(env_file)

        self.config = config
        self._client = None
        self._initialize_client()

    def _load_env_file(self, env_file: Path):
        """Manual loading of .env file if dotenv is not available."""
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    def _initialize_client(self):
        """Initialize the appropriate LLM client based on provider."""
        if self.config.provider == LLMProvider.OPENAI:
            try:
                import openai

                self._client = openai.AsyncOpenAI(
                    api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
                    base_url=self.config.base_url,
                )
            except ImportError:
                raise ImportError(
                    "OpenAI client not available. Install with: pip install openai"
                )

        elif self.config.provider == LLMProvider.OPENROUTER:
            try:
                import openai

                self._client = openai.AsyncOpenAI(
                    api_key=self.config.api_key or os.getenv("OPENROUTER_API_KEY"),
                    base_url=self.config.base_url or "https://openrouter.ai/api/v1",
                )
            except ImportError:
                raise ImportError(
                    "OpenAI client required for OpenRouter. Install with: pip install openai"
                )

        elif self.config.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(
                    api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
                )
            except ImportError:
                raise ImportError(
                    "Anthropic client not available. Install with: pip install anthropic"
                )

        elif self.config.provider == LLMProvider.OLLAMA:
            # For local Ollama deployment
            self.config.base_url = self.config.base_url or "http://localhost:11434"

        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    async def generate_completion(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """Generate completion from LLM with provider-specific handling."""

        if self.config.provider in [LLMProvider.OPENAI, LLMProvider.OPENROUTER]:
            return await self._openai_completion(prompt, system_prompt, **kwargs)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            return await self._anthropic_completion(prompt, system_prompt, **kwargs)
        elif self.config.provider == LLMProvider.OLLAMA:
            return await self._ollama_completion(prompt, system_prompt, **kwargs)
        else:
            raise NotImplementedError(
                f"Provider {self.config.provider} not implemented"
            )

    async def _openai_completion(
        self, prompt: str, system_prompt: Optional[str], **kwargs
    ) -> str:
        """OpenAI API completion."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **kwargs,
        )
        return response.choices[0].message.content

    async def _anthropic_completion(
        self, prompt: str, system_prompt: Optional[str], **kwargs
    ) -> str:
        """Anthropic Claude API completion."""
        response = await self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt or "You are a systematic review analysis assistant.",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.content[0].text

    async def _ollama_completion(
        self, prompt: str, system_prompt: Optional[str], **kwargs
    ) -> str:
        """Ollama local completion (requires aiohttp)."""
        try:
            import aiohttp
            import json

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens,
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    result = await response.json()
                    return result["response"]

        except ImportError:
            raise ImportError(
                "aiohttp required for Ollama client. Install with: pip install aiohttp"
            )

    def generate_completion_sync(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """Synchronous wrapper for completion generation."""
        try:
            # Check if we're already in an event loop
            asyncio.get_running_loop()
            # If we get here, there's already a running loop
            # We need to run this in a separate thread with its own event loop
            import concurrent.futures
            import threading

            def run_async():
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.generate_completion(prompt, system_prompt, **kwargs)
                    )
                finally:
                    loop.close()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async)
                return future.result(timeout=60)  # 60 second timeout

        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(
                self.generate_completion(prompt, system_prompt, **kwargs)
            )


# Factory function for easy client creation
def create_llm_client(
    provider: str = "openrouter", model: str = "anthropic/claude-3.5-haiku"
) -> LLMClient:
    """Create LLM client with default configurations for systematic review analysis."""

    configs = {
        "openai": LLMConfig(
            provider=LLMProvider.OPENAI,
            model=model if "gpt" in model else "gpt-4o-mini",
            max_tokens=2000,
            temperature=0.1,
        ),
        "openrouter": LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model=model,
            max_tokens=2000,
            temperature=0.1,
        ),
        "anthropic": LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-haiku-20240307",
            max_tokens=2000,
            temperature=0.1,
        ),
        "ollama": LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama2:7b",
            max_tokens=2000,
            temperature=0.1,
        ),
    }

    if provider not in configs:
        raise ValueError(
            f"Unknown provider: {provider}. Available: {list(configs.keys())}"
        )

    return LLMClient(configs[provider])


# Global client instance (initialized lazily)
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create default LLM client."""
    global _default_client
    if _default_client is None:
        # Default to OpenRouter with Claude 3.5 Haiku for cost-effective analysis
        _default_client = create_llm_client("openrouter", "anthropic/claude-3.5-haiku")
    return _default_client
