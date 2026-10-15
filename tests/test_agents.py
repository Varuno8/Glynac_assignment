"""Unit and integration tests for multi-agent execution pipeline."""

import tempfile
from pathlib import Path

from src.agents.advisor import AdvisorAgent
from src.agents.analyzer import AnalyzerAgent
from src.agents.data_fetcher import DataFetcherAgent
from src.agents.orchestrator import OrchestratorAgent
from src.memory.long_term import LongTermMemoryStore
from src.memory.short_term import SessionBlackboard
from src.observability.logger import AgentLogger
from src.tools import create_default_tool_registry


def test_data_fetcher_agent_execution():
    tools = create_default_tool_registry()
    logger = AgentLogger(verbose=False)
    blackboard = SessionBlackboard()

    fetcher = DataFetcherAgent(tools, logger, blackboard)
    resp = fetcher.run(client_id="101")

    assert resp.success is True
    assert blackboard.has("financial_data") is True
    assert blackboard.has("crm_profile") is True
    assert blackboard.has("market_benchmarks") is True
    assert blackboard.client_id == "client_101"


def test_data_fetcher_agent_graceful_crm_degradation():
    tools = create_default_tool_registry()
    logger = AgentLogger(verbose=False)
    blackboard = SessionBlackboard()

    fetcher = DataFetcherAgent(tools, logger, blackboard)
    resp = fetcher.run(client_id="101", simulate_crm_error=True)

    assert resp.success is True
    assert blackboard.get("crm_degraded") is True
    # Should contain fallback profile
    crm_profile = blackboard.get("crm_profile")
    assert "DEGRADED STATUS" in crm_profile["advisor_notes"]


def test_analyzer_agent_execution():
    tools = create_default_tool_registry()
    logger = AgentLogger(verbose=False)
    blackboard = SessionBlackboard()

    fetcher = DataFetcherAgent(tools, logger, blackboard)
    fetcher.run(client_id="101")

    analyzer = AnalyzerAgent(tools, logger, blackboard)
    resp = analyzer.run()

    assert resp.success is True
    assert blackboard.has("analysis_report") is True
    report = blackboard.get("analysis_report")
    assert report["metrics"]["overall_health_score"] > 0
    assert len(report["anomalies"]) > 0


def test_advisor_agent_execution():
    tools = create_default_tool_registry()
    logger = AgentLogger(verbose=False)
    blackboard = SessionBlackboard()

    fetcher = DataFetcherAgent(tools, logger, blackboard)
    fetcher.run(client_id="101")

    analyzer = AnalyzerAgent(tools, logger, blackboard)
    analyzer.run()

    advisor = AdvisorAgent(tools, logger, blackboard)
    resp = advisor.run()

    assert resp.success is True
    assert blackboard.has("draft_advisory_plan") is True
    plan = blackboard.get("draft_advisory_plan")
    assert len(plan["action_items"]) > 0
    assert len(plan["meeting_agenda_topics"]) > 0


def test_orchestrator_agent_end_to_end_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_store = LongTermMemoryStore(storage_dir=Path(tmpdir))
        logger = AgentLogger(verbose=False)
        orchestrator = OrchestratorAgent(logger=logger, memory_store=memory_store, auto_approve_hitl=True)

        result = orchestrator.execute_workflow(client_id="101")

        assert result["status"] == "COMPLETED"
        assert result["client_id"] == "client_101"
        assert result["health_score"] > 0
        assert result["anomalies_detected"] >= 2
        assert result["actions_count"] >= 2
        assert result["hitl_status"] == "APPROVED"
        assert Path(result["output_json"]).exists()
        assert Path(result["output_markdown"]).exists()

        # Verify trace metrics
        trace = result["trace"]
        assert trace["total_spans"] >= 5
        assert trace["total_execution_time_ms"] > 0

        # Run again to verify that long-term memory historical insights are loaded
        result2 = orchestrator.execute_workflow(client_id="101")
        assert result2["status"] == "COMPLETED"
        mem = memory_store.load_client_memory("client_101")
        assert mem.total_sessions_run == 2
