"""Optional OpenAI Responses adapter. SDK retries transient errors once."""

from src.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    name = "openai"

    def __init__(self, model, api_key=None, client=None):
        if not model:
            raise ValueError("Set OPENAI_MODEL to a model supporting Responses structured outputs")
        self.model = model
        if client is None:
            if not api_key:
                raise ValueError("Set OPENAI_API_KEY for --llm-provider openai, or use mock")
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ValueError("Install requirements-openai.txt for --llm-provider openai") from exc
            client = OpenAI(api_key=api_key, timeout=15.0, max_retries=1)
        self.client = client

    def generate(self, prompt, system_prompt=None):
        response = self.client.responses.create(
            model=self.model, instructions=system_prompt, input=prompt, store=False, max_output_tokens=2500
        )
        if response.status != "completed" or not response.output_text:
            raise ValueError("Provider response was incomplete or refused")
        return response.output_text

    def generate_structured(self, prompt, response_model, system_prompt=None):
        response = self.client.responses.parse(
            model=self.model,
            instructions=system_prompt,
            input=prompt,
            text_format=response_model,
            store=False,
            max_output_tokens=2500,
        )
        if response.status != "completed" or response.output_parsed is None:
            raise ValueError("Provider response was incomplete or refused")
        return response_model.model_validate(response.output_parsed)
