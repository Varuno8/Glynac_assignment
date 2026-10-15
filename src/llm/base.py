"""Base LLM interface for pluggable language model providers."""

from abc import ABC, abstractmethod
from typing import Optional, Type

from pydantic import BaseModel


class BaseLLMClient(ABC):
    """Abstract interface for LLM calls."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates raw text response."""
        pass

    @abstractmethod
    def generate_structured(
        self, prompt: str, response_model: Type[BaseModel], system_prompt: Optional[str] = None
    ) -> BaseModel:
        """Generates structured response adhering to a Pydantic schema."""
        pass
