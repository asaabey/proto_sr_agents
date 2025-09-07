"""
Configuration and environment management for LLM integration.

Handles API keys, model selection, retry logic, and cost optimization
for systematic review analysis workflows.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""

    name: str
    provider: str
    max_tokens: int = 2000
    temperature: float = 0.1
    cost_per_1k_tokens: float = 0.001  # Rough estimate for budgeting
    recommended_use: str = "general"


@dataclass
class LLMSettings:
    """Global LLM settings and preferences."""

    default_provider: str = "openai"
    default_model: str = "gpt-4o-mini"
    max_retries: int = 3
    timeout_seconds: int = 30
    enable_caching: bool = True
    cost_limit_per_day: float = 10.0  # USD
    log_api_calls: bool = True
    models: Dict[str, ModelConfig] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default model configurations."""
        if not self.models:
            self.models = get_default_models()


def get_default_models() -> Dict[str, ModelConfig]:
    """Get default model configurations optimized for systematic review tasks."""
    return {
        # OpenRouter Models (Primary provider)
        "claude-3.5-haiku-openrouter": ModelConfig(
            name="anthropic/claude-3.5-haiku",
            provider="openrouter",
            max_tokens=4000,
            temperature=0.1,
            cost_per_1k_tokens=0.0001,
            recommended_use="cost-effective analysis, PICO extraction, PRISMA checking",
        ),
        "claude-3.5-sonnet-openrouter": ModelConfig(
            name="anthropic/claude-3.5-sonnet",
            provider="openrouter",
            max_tokens=4000,
            temperature=0.1,
            cost_per_1k_tokens=0.003,
            recommended_use="detailed analysis, risk of bias assessment, GRADE evaluation",
        ),
        "gpt-4o-mini-openrouter": ModelConfig(
            name="openai/gpt-4o-mini",
            provider="openrouter",
            max_tokens=4000,
            temperature=0.1,
            cost_per_1k_tokens=0.00015,
            recommended_use="balanced cost/performance, general systematic review tasks",
        ),
        "deepseek-v3-openrouter": ModelConfig(
            name="deepseek/deepseek-chat",
            provider="openrouter",
            max_tokens=4000,
            temperature=0.1,
            cost_per_1k_tokens=0.00002,
            recommended_use="ultra-low cost analysis, bulk processing",
        ),
        # Local Models (Ollama fallback)
        "llama2-7b": ModelConfig(
            name="llama2:7b",
            provider="ollama",
            max_tokens=2000,
            temperature=0.1,
            cost_per_1k_tokens=0.0,  # Local inference
            recommended_use="privacy-sensitive analysis, offline use",
        ),
        "mistral-7b": ModelConfig(
            name="mistral:7b",
            provider="ollama",
            max_tokens=2000,
            temperature=0.1,
            cost_per_1k_tokens=0.0,
            recommended_use="local medical text analysis",
        ),
    }


class LLMEnvironment:
    """Manages environment variables and API keys for LLM providers."""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path(".env")
        self.settings = LLMSettings()
        self._load_config()

    def _load_config(self):
        """Load configuration from environment and config file."""
        # Load from environment variables
        env_mappings = {
            "LLM_DEFAULT_PROVIDER": "default_provider",
            "LLM_DEFAULT_MODEL": "default_model",
            "LLM_MAX_RETRIES": "max_retries",
            "LLM_TIMEOUT": "timeout_seconds",
            "LLM_DAILY_COST_LIMIT": "cost_limit_per_day",
            "LLM_ENABLE_CACHING": "enable_caching",
            "LLM_LOG_CALLS": "log_api_calls",
        }

        for env_var, setting in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                if setting in ["max_retries", "timeout_seconds"]:
                    value = int(value)
                elif setting == "cost_limit_per_day":
                    value = float(value)
                elif setting in ["enable_caching", "log_api_calls"]:
                    value = value.lower() in ("true", "1", "yes")

                setattr(self.settings, setting, value)

        # Load from config file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            os.environ[key] = value
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for specified provider."""
        if provider == "openrouter":
            return os.getenv("OPENROUTER_API_KEY")
        return None

    def validate_setup(self) -> Dict[str, Any]:
        """Validate LLM environment setup and return status."""
        status = {
            "configured": True,
            "providers": {},
            "warnings": [],
            "recommendations": [],
        }

        # Check API keys for configured providers
        for model_name, model_config in self.settings.models.items():
            provider = model_config.provider
            if provider not in status["providers"]:
                api_key = self.get_api_key(provider)
                status["providers"][provider] = {
                    "api_key_available": api_key is not None,
                    "models": [],
                }

            status["providers"][provider]["models"].append(model_name)

        # Generate warnings and recommendations
        for provider, info in status["providers"].items():
            if not info["api_key_available"] and provider not in ["ollama"]:
                status["warnings"].append(f"No API key found for {provider}")
                status["recommendations"].append(
                    f"Set {provider.upper()}_API_KEY environment variable"
                )

        if not any(p["api_key_available"] for p in status["providers"].values()):
            status["configured"] = False
            status["recommendations"].append(
                "Install Ollama for local inference: https://ollama.ai"
            )

        return status

    def save_config(self):
        """Save current settings to config file."""
        config_lines = [
            "# LLM Configuration for Systematic Review Auditor",
            "# Auto-generated configuration file",
            "",
            "# LLM Settings",
            f"LLM_DEFAULT_PROVIDER={self.settings.default_provider}",
            f"LLM_DEFAULT_MODEL={self.settings.default_model}",
            f"LLM_MAX_RETRIES={self.settings.max_retries}",
            f"LLM_TIMEOUT={self.settings.timeout_seconds}",
            f"LLM_DAILY_COST_LIMIT={self.settings.cost_limit_per_day}",
            f"LLM_ENABLE_CACHING={self.settings.enable_caching}",
            f"LLM_LOG_CALLS={self.settings.log_api_calls}",
        ]

        with open(self.config_file, "w") as f:
            f.write("\n".join(config_lines))


# Global environment instance
_env: Optional[LLMEnvironment] = None


def get_llm_environment() -> LLMEnvironment:
    """Get or create the global LLM environment."""
    global _env
    if _env is None:
        _env = LLMEnvironment()
    return _env


def setup_development_env():
    """Quick setup for development with sensible defaults."""
    env_content = """# LLM Configuration for Systematic Review Auditor
# Copy to .env and add your API keys

# OpenRouter Configuration (Primary and only provider)
OPENROUTER_API_KEY=your_openrouter_key_here

# LLM Settings
LLM_DEFAULT_PROVIDER=openrouter
LLM_DEFAULT_MODEL=anthropic/claude-3.5-haiku
LLM_MAX_RETRIES=3
LLM_TIMEOUT=30
LLM_DAILY_COST_LIMIT=10.0
LLM_ENABLE_CACHING=true
LLM_LOG_CALLS=true

# OpenRouter gives you access to:
# - anthropic/claude-3.5-haiku (fast, cost-effective)
# - anthropic/claude-3.5-sonnet (detailed analysis)
# - openai/gpt-4o-mini (balanced performance)
# - deepseek/deepseek-chat (ultra low cost)
# - Many other models from different providers
"""

    env_file = Path(".env.llm.example")
    env_file.write_text(env_content)
    print(f"Created example environment file: {env_file}")
    print("Copy to .env and add your OpenRouter API key")
    print("Get your OpenRouter API key at: https://openrouter.ai/keys")


if __name__ == "__main__":
    # Setup development environment
    setup_development_env()

    # Validate current setup
    env = get_llm_environment()
    status = env.validate_setup()

    print("LLM Environment Status:")
    print(f"  Configured: {status['configured']}")
    print(f"  Providers: {list(status['providers'].keys())}")

    if status["warnings"]:
        print("  Warnings:")
        for warning in status["warnings"]:
            print(f"    - {warning}")

    if status["recommendations"]:
        print("  Recommendations:")
        for rec in status["recommendations"]:
            print(f"    - {rec}")
