"""Behavioral regressions from the assignment review, including failure boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.advisory import HITLDecision
from src.models.advisory import HITLReviewStatus as Review
from src.models.crm import TargetAllocation
from src.models.financial import ClientFinancialData
from src.tools import AnomalyDetectionTool, FinancialIngestionTool
from src.tools.market_tool import MarketBenchmarkTool

TARGET = dict(US_EQUITY=60, INTL_EQUITY=20, FIXED_INCOME=15, CASH=5)


def analyze(data, target=TARGET):
    result = AnomalyDetectionTool().run(
        financial_data=data, target_allocation=target, market_benchmarks=MarketBenchmarkTool().run().data
    )
    assert result.success, result.error
    return result.data


@pytest.mark.parametrize("client", ["101", "102", "103"])
def test_sample_reports_are_specific(make_runner, client):
    result = make_runner(auto_approve_hitl=True).execute_workflow(client_id=client)
    assert result["status"] == "COMPLETED", result["error"]
    report = json.loads(Path(result["output_json"]).read_text())
    assert report["client_id"] == f"client_{client}"
    assert report["schema_version"] == 2
    assert report["advisory_plan"]["client_id"] == report["client_id"]
    assert all(s["status"] == "SUCCESS" for s in result["trace"]["spans"])
    assert (
        json.loads((Path(result["output_json"]).parent / "run_status.json").read_text())["status"]
        == "COMPLETED"
    )


def test_zero_portfolio_stays_zero(sample):
    sample["accounts"] = []
    sample["recent_transactions"] = []
    report = analyze(sample)
    assert report["metrics"]["total_liquid_net_worth"] == 0
    assert all(value == 0 for value in report["allocation"]["actual_allocation_pct"].values())
    assert report["allocation"]["drift_pct"] == {}
    assert report["requires_human_review"]


def test_balance_only_account_is_unclassified(sample):
    account = sample["accounts"][1]
    account["holdings"] = []
    account["balance"] = 10000
    sample["accounts"] = [account]
    sample["recent_transactions"] = []
    report = analyze(sample)
    assert (
        report["metrics"]["total_liquid_net_worth"]
        == ClientFinancialData(**sample).total_liquid_net_worth
        == 10000
    )
    assert report["allocation"]["actual_allocation_pct"]["UNCLASSIFIED"] == 100
    assert report["metrics"]["total_cash"] == 0
    assert report["allocation"]["drift_pct"] == {}


@pytest.mark.parametrize("count", [1, 2])
def test_sparse_bank_flagged_transactions_detected(sample, count):
    flagged = next(tx for tx in sample["recent_transactions"] if tx.get("flagged_by_bank"))
    sample["recent_transactions"] = [flagged]
    if count == 2:
        tx = deepcopy(flagged)
        tx.update(tx_id="other", amount=20, category="GROCERIES", flagged_by_bank=False)
        sample["recent_transactions"].append(tx)
    report = analyze(sample)
    flagged_findings = [a for a in report["anomalies"] if a["evidence"].get("tx_id") == flagged["tx_id"]]
    assert len(flagged_findings) == 1
    assert flagged_findings[0]["severity"] == "CRITICAL"


def test_zero_cashflow_is_explicit(sample):
    sample["monthly_cashflow"].update(average_monthly_expenses=0, average_monthly_net_income=0)
    sample["recent_transactions"] = []
    metrics = analyze(sample)["metrics"]
    assert metrics["emergency_fund_months"] is None
    assert metrics["monthly_savings_rate_pct"] is None


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1])
def test_nonfinite_or_negative_money_rejected(sample, invalid):
    sample["accounts"][0]["balance"] = invalid
    assert not FinancialIngestionTool().run(raw_json_data=sample).success


@pytest.mark.parametrize("identifier", ["../escape", "client_../../escape", "", "x/y", "client_"])
def test_unsafe_client_identifiers_rejected(sample, identifier):
    sample["client_id"] = identifier
    assert not FinancialIngestionTool().run(raw_json_data=sample).success
    assert not FinancialIngestionTool().run(client_id=identifier).success


def test_foreign_currency_and_invalid_allocations_rejected(sample):
    sample["accounts"][0]["currency"] = "EUR"
    assert not FinancialIngestionTool().run(raw_json_data=sample).success
    with pytest.raises(ValidationError, match="100%"):
        TargetAllocation(US_EQUITY=60, INTL_EQUITY=10, FIXED_INCOME=10, CASH=5)


def test_amounts_match_current_evidence(make_runner):
    result = make_runner(auto_approve_hitl=True).execute_workflow(client_id="103")
    actions = result["advisory_plan"]["action_items"]
    reserve = next(a for a in actions if a["category"] == "LIQUIDITY_MANAGEMENT")
    assert reserve["estimated_dollar_amount"] == 10800 * 3 - 3200
    concentration = next(a for a in actions if "TSLA" in a["action_id"])
    total = result["analysis_report"]["metrics"]["total_liquid_net_worth"]
    assert concentration["estimated_dollar_amount"] == pytest.approx(162500 - 0.15 * total)
    assert all(a["source_anomaly_ids"] for a in actions)


def test_cash_yield_and_reserve_use_real_inputs(sample):
    report = analyze(sample)
    evidence = next(a["evidence"] for a in report["anomalies"] if a["anomaly_type"] == "CASH_DRAG")
    retained = max(9200 * 3, report["metrics"]["total_liquid_net_worth"] * 0.05)
    excess = 380000 - retained
    assert evidence["excess_cash_dollars"] == excess
    assert evidence["estimated_annual_opportunity_loss_usd"] == pytest.approx(
        round(excess * (0.0465 - 0.0005), 2)
    )


def test_history_does_not_trigger_resolved_actions(make_runner, sample):
    runner = make_runner(auto_approve_hitl=True)
    runner.memory_store.record_session_insight(
        "101", "old", 60, ["CASH_DRAG"], ["old cash proposal"], "APPROVED"
    )
    sample["accounts"][0]["balance"] = 50000
    sample["recent_transactions"] = []
    result = runner.execute_workflow(raw_json_data=sample)
    assert result["status"] == "COMPLETED"
    assert not any(a["category"] == "CASH_OPTIMIZATION" for a in result["advisory_plan"]["action_items"])


@pytest.mark.parametrize(
    "status,expected", [(Review.REJECTED, "REJECTED"), (Review.PENDING_APPROVAL, "PENDING_REVIEW")]
)
def test_unapproved_runs_export_audit_only(make_runner, status, expected):
    runner = make_runner()
    result = runner.execute_workflow(
        client_id="101",
        hitl_callback=lambda *_: HITLDecision(status=status, override_reason="Review deferred"),
    )
    assert result["status"] == expected
    assert "NOT APPROVED FOR DISTRIBUTION" in Path(result["output_markdown"]).read_text()
    memory = runner.memory_store.load_client_memory("101")
    assert memory.historical_sessions[-1].actions_recommended == []


def test_modified_actions_may_be_empty(make_runner):
    result = make_runner().execute_workflow(
        client_id="101",
        hitl_callback=lambda *_: HITLDecision(
            status=Review.MODIFIED, modified_actions=[], override_reason="Remove all proposals"
        ),
    )
    assert result["status"] == "COMPLETED"
    assert result["actions_count"] == 0
    assert len(result["advisory_plan"]["original_action_items"]) > 0


def test_changed_amount_and_steps_preserve_original(make_runner):
    def reviewer(report, actions):
        chosen = next(a for a in actions if a.estimated_dollar_amount is not None)
        changed = chosen.model_copy(deep=True)
        changed.estimated_dollar_amount = 123
        changed.action_steps = ["Advisor-specific phased implementation"]
        return HITLDecision(
            status=Review.MODIFIED, modified_actions=[changed], override_reason="Phased adjustment"
        )

    result = make_runner().execute_workflow(client_id="101", hitl_callback=reviewer)
    assert result["status"] == "COMPLETED"
    assert result["advisory_plan"]["action_items"][0]["estimated_dollar_amount"] == 123
    original = next(
        a
        for a in result["advisory_plan"]["original_action_items"]
        if a["action_id"] == result["advisory_plan"]["action_items"][0]["action_id"]
    )
    assert original["estimated_dollar_amount"] != 123
    assert "reassess" in result["advisory_plan"]["action_items"][0]["impact"]


@pytest.mark.parametrize("missing", [False, True])
def test_crm_degraded_withholds_target_actions(make_runner, sample, missing):
    if missing:
        sample["client_id"] = "client_missing"
    result = make_runner(auto_approve_hitl=True).execute_workflow(
        raw_json_data=sample, simulate_crm_error=not missing
    )
    assert result["status"] == "COMPLETED"
    assert result["analysis_report"]["requires_human_review"]
    assert result["analysis_report"]["allocation"]["target_allocation_pct"] == {}
    assert not any(
        a["category"] in {"PORTFOLIO_REBALANCING", "CASH_OPTIMIZATION"}
        for a in result["advisory_plan"]["action_items"]
    )
    assert json.loads(Path(result["output_json"]).read_text())["crm_degraded"]


def test_corrupt_memory_preserved(make_runner):
    runner = make_runner(auto_approve_hitl=True)
    path = runner.memory_store._get_client_file("101")
    path.parent.mkdir(parents=True)
    path.write_text("{broken")
    result = runner.execute_workflow(client_id="101")
    assert result["status"] == "FAILED"
    assert result["stage"] == "ADVISORY_SYNTHESIS"
    assert "Corrupt memory" in result["error"]
    assert path.read_text() == "{broken"
    assert all(s["status"] != "RUNNING" for s in result["trace"]["spans"])


def test_unwritable_output_reports_failure(make_runner, tmp_path):
    path = tmp_path / "blocked"
    path.write_text("not a directory")
    runner = make_runner(output_dir=path, auto_approve_hitl=True)
    result = runner.execute_workflow(client_id="101")
    assert result["status"] == "FAILED"
    assert result["stage"] == "EXPORT"
    assert runner.memory_store.load_client_memory("101").total_sessions_run == 0


def test_memory_write_failure_marks_export_failed(make_runner, monkeypatch):
    runner = make_runner(auto_approve_hitl=True)

    def fail(**kwargs):
        raise OSError("storage unavailable")

    monkeypatch.setattr(runner.memory_store, "record_session_insight", fail)
    result = runner.execute_workflow(client_id="101")
    assert result["status"] == "FAILED"
    assert result["stage"] == "PERSIST_MEMORY"
    dossier = next(runner.output_dir.rglob("advisory_dossier.json"))
    assert json.loads(dossier.read_text())["workflow_status"] == "FAILED"


def test_runs_do_not_overwrite_outputs(make_runner):
    runner = make_runner(auto_approve_hitl=True)
    first = runner.execute_workflow(client_id="101")
    second = runner.execute_workflow(client_id="101")
    assert first["session_id"] != second["session_id"]
    assert Path(first["output_json"]).exists() and Path(second["output_json"]).exists()


def test_logs_have_context_without_raw_client_data(make_runner):
    runner = make_runner(auto_approve_hitl=True)
    result = runner.execute_workflow(client_id="101")
    text = runner.logger.log_file.read_text()
    records = [json.loads(line) for line in text.splitlines()]
    assert all(r["session_id"] == result["session_id"] and r["stage"] for r in records)
    assert all(r["client_id"] == "client_101" for r in records if r["stage"] != "DATA_FETCH")
    assert "recent_transactions" not in text and "Alex Chen" not in text and "accounts" not in text


def test_failed_diagnostic_export_does_not_hide_original_error(make_runner, monkeypatch):
    def broken_renderer(*args):
        raise RuntimeError("report renderer failed")

    monkeypatch.setattr("src.agents.orchestrator.render_markdown", broken_renderer)
    result = make_runner(auto_approve_hitl=True).execute_workflow(client_id="101")
    assert result["status"] == "FAILED"
    assert result["stage"] == "EXPORT"
    assert "report renderer failed" in result["error"]
    assert all(span["status"] != "RUNNING" for span in result["trace"]["spans"])
