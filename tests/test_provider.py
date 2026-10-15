"""No-network provider contract tests, including the real SDK parser."""

import json
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI

from src.llm import get_llm_client
from src.llm.mock_llm import MockDeterministicLLM
from src.llm.openai_client import OpenAIClient
from src.models.advisory import AdvisoryNarrative


class BrokenProvider:
    name = "broken"

    def generate_structured(self, *args):
        raise TimeoutError("secret-key-must-never-be-logged")


def test_provider_failure_falls_back_and_redacts(make_runner):
    runner = make_runner(llm=BrokenProvider(), auto_approve_hitl=True)
    result = runner.execute_workflow(client_id="101")
    assert result["status"] == "COMPLETED"
    plan = result["advisory_plan"]
    assert plan["narrative_provider"] == "mock"
    assert "TimeoutError" in plan["fallback_reason"]
    assert "secret-key" not in json.dumps(result)
    assert "secret-key" not in runner.logger.log_file.read_text()


def test_unknown_narrative_action_ids_fall_back(make_runner):
    class InventedActions(MockDeterministicLLM):
        name = "invented"

        def generate_structured(self, *args):
            narrative = super().generate_structured(*args)
            narrative.action_explanations[0].action_id = "invented-action"
            return narrative

    result = make_runner(llm=InventedActions(), auto_approve_hitl=True).execute_workflow(client_id="101")
    assert result["advisory_plan"]["narrative_provider"] == "mock"
    assert result["advisory_plan"]["fallback_reason"]


def test_live_configuration_is_required(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert isinstance(get_llm_client(), MockDeterministicLLM)
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        get_llm_client("openai")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_llm_client("openai")


def test_adapter_configures_timeout_and_retry(monkeypatch):
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("openai.OpenAI", factory)
    OpenAIClient(model="test-model", api_key="dummy")
    assert captured["timeout"] == 15.0
    assert captured["max_retries"] == 1


@pytest.mark.parametrize("mode", ["valid", "refused", "incomplete", "invalid"])
def test_sdk_structured_response_contract(mode):
    captured = []
    narrative = dict(
        executive_summary="A bounded summary.",
        action_explanations=[],
        meeting_agenda_topics=["Review supplied findings"],
    )

    def respond(request):
        body = json.loads(request.content)
        captured.append(body)
        text = json.dumps(narrative if mode != "invalid" else {"unexpected": 1})
        content = (
            [{"type": "refusal", "refusal": "Unable to comply"}]
            if mode == "refused"
            else [{"type": "output_text", "text": text, "annotations": []}]
        )
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "incomplete" if mode == "incomplete" else "completed",
                "model": "test-model",
                "incomplete_details": {"reason": "max_output_tokens"} if mode == "incomplete" else None,
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": content,
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        sdk = OpenAI(api_key="dummy", http_client=transport, max_retries=1, timeout=15)
        adapter = OpenAIClient(model="test-model", client=sdk)
        if mode == "valid":
            assert (
                adapter.generate_structured("{}", AdvisoryNarrative).executive_summary
                == narrative["executive_summary"]
            )
        else:
            with pytest.raises(Exception):
                adapter.generate_structured("{}", AdvisoryNarrative)
    assert captured[0]["store"] is False
    assert captured[0]["text"]["format"]["type"] == "json_schema"
    assert captured[0]["text"]["format"]["strict"] is True


def test_transient_sdk_errors_retry_once():
    attempts = []

    def respond(request):
        attempts.append(request)
        return httpx.Response(503, json={"error": {"message": "mock unavailable", "type": "server_error"}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        adapter = OpenAIClient(
            model="test-model",
            client=OpenAI(api_key="dummy", http_client=transport, max_retries=1, timeout=15),
        )
        with pytest.raises(Exception):
            adapter.generate_structured("{}", AdvisoryNarrative)
    assert len(attempts) == 2
