"""
LLM Services for Systematic Review Analysis

This module provides LLM integration for enhanced systematic review auditing,
including PICO extraction, PRISMA validation, risk of bias assessment, and more.

Quick Start:
    from app.services import create_llm_client, get_prompt
    
    # Create OpenRouter client (recommended)
    client = create_llm_client("openrouter", "anthropic/claude-3.5-haiku")
    
    # Get specialized prompt
    pico_prompt = get_prompt("pico_extraction")
    
    # Generate analysis
    result = client.generate_completion_sync(
        prompt=pico_prompt.format(manuscript_text="..."),
        system_prompt=pico_prompt.system_prompt
    )
"""

from .llm_client import (
    LLMClient,
    LLMConfig, 
    LLMProvider,
    create_llm_client,
    get_llm_client
)

from .prompt_templates import (
    PromptTemplate,
    SystemReviewPrompts,
    get_prompt
)

from .llm_config import (
    LLMEnvironment,
    LLMSettings,
    ModelConfig,
    get_llm_environment,
    setup_development_env
)

__all__ = [
    # Core client
    "LLMClient",
    "LLMConfig", 
    "LLMProvider",
    "create_llm_client",
    "get_llm_client",
    
    # Prompts
    "PromptTemplate",
    "SystemReviewPrompts", 
    "get_prompt",
    
    # Configuration
    "LLMEnvironment",
    "LLMSettings",
    "ModelConfig",
    "get_llm_environment",
    "setup_development_env"
]