"""Unit tests for short-term and long-term memory layers."""

import tempfile
from pathlib import Path

from src.memory.long_term import LongTermMemoryStore
from src.memory.short_term import SessionBlackboard


def test_short_term_session_blackboard():
    bb = SessionBlackboard(session_id="test_sess_01")
    bb.client_id = "client_101"

    bb.set("portfolio_val", 1500000.0, "TestAgent", "Initial portfolio balance")
    assert bb.has("portfolio_val") is True
    assert bb.get("portfolio_val") == 1500000.0
    assert bb.get("non_existent", "default_val") == "default_val"

    history = bb.get_history()
    assert len(history) == 1
    assert history[0].step_name == "portfolio_val"
    assert history[0].agent_name == "TestAgent"


def test_long_term_memory_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LongTermMemoryStore(storage_dir=Path(tmpdir))

        # Check empty history
        summary = store.get_trend_summary("client_test")
        assert summary["has_history"] is False

        # Record session 1
        store.record_session_insight(
            client_id="client_test",
            session_id="sess_1",
            overall_health_score=68,
            anomalies_detected=["CASH_DRAG", "CONCENTRATION_RISK"],
            actions_recommended=["Sweep Cash", "Diversify NVDA"],
            hitl_status="APPROVED",
        )

        # Check updated trend summary
        summary1 = store.get_trend_summary("client_test")
        assert summary1["has_history"] is True
        assert summary1["total_past_sessions"] == 1
        assert summary1["previous_health_score"] == 68

        # Record session 2 with recurring cash drag
        store.record_session_insight(
            client_id="client_test",
            session_id="sess_2",
            overall_health_score=75,
            anomalies_detected=["CASH_DRAG"],
            actions_recommended=["Automate sweep"],
            hitl_status="APPROVED",
        )

        summary2 = store.get_trend_summary("client_test")
        assert summary2["total_past_sessions"] == 2
        assert summary2["previous_health_score"] == 75
        assert any("CASH_DRAG (triggered 2x)" in r for r in summary2["recurring_anomalies"])
