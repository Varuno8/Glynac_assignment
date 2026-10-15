"""Offline renderer of structured facts; it does not simulate free-form reasoning."""

from src.llm.base import BaseLLMClient
from src.models.advisory import ActionExplanation, AdvisoryContext, AdvisoryNarrative


class MockDeterministicLLM(BaseLLMClient):
    name = "mock"

    def generate(self, prompt, system_prompt=None):
        return self.generate_structured(prompt, AdvisoryNarrative, system_prompt).executive_summary

    def generate_structured(self, prompt, response_model, system_prompt=None):
        if response_model is not AdvisoryNarrative:
            raise ValueError("Offline provider supports AdvisoryNarrative")
        context = AdvisoryContext.model_validate_json(prompt)
        status = (
            "CRM context is incomplete; agreed-target recommendations are withheld. "
            if context.crm_degraded
            else ""
        )
        return AdvisoryNarrative(
            executive_summary=f"Assessment for {context.client_id}: {len(context.analysis.anomalies)} current risk signals and {len(context.actions)} proposed review actions. "
            + status
            + context.history_summary,
            action_explanations=[
                ActionExplanation(action_id=a.action_id, explanation=a.rationale) for a in context.actions
            ],
            meeting_agenda_topics=[a.title for a in context.actions],
        )
