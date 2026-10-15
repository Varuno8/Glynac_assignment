"""Select providers explicitly; offline execution never needs credentials."""

import os

from src.llm.base import BaseLLMClient
from src.llm.mock_llm import MockDeterministicLLM


def get_llm_client(provider: str = "mock") -> BaseLLMClient:
    if provider == "mock":
        return MockDeterministicLLM()
    if provider == "openai":
        from src.llm.openai_client import OpenAIClient

        return OpenAIClient(model=os.environ.get("OPENAI_MODEL"), api_key=os.environ.get("OPENAI_API_KEY"))
    raise ValueError(f"Unknown LLM provider: {provider}")


__all__ = ["BaseLLMClient", "MockDeterministicLLM", "get_llm_client"]
