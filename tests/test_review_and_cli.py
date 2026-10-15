import json

import pytest

from src.hitl.checkpoint import HITLReviewGate
from src.main import main
from src.memory.long_term import LongTermMemoryStore
from src.models.advisory import AdvisoryActionItem, HITLDecision, HITLReviewStatus
from src.persistence import atomic_write_text
from tests.test_hitl import build_mock_report


def proposal():
    return AdvisoryActionItem(
        action_id="act",
        priority="HIGH",
        category="PORTFOLIO_REBALANCING",
        title="Rebalance",
        rationale="Evidence",
        impact="Review allocation",
        estimated_dollar_amount=60000,
        action_steps=["Verify"],
    )


def test_turnover_triggers_review_without_high_anomaly():
    report = build_mock_report(False)
    assert HITLReviewGate().evaluate_requires_review(report, [proposal()])


def test_empty_or_invalid_input_never_approves():
    answers = iter(["", "wrong", "4"])
    gate = HITLReviewGate(input_fn=lambda _: next(answers))
    assert gate.request_review(build_mock_report(), [proposal()]).status == HITLReviewStatus.PENDING_APPROVAL


def test_eof_and_noninteractive_remain_pending():
    def eof(_):
        raise EOFError()

    assert (
        HITLReviewGate(input_fn=eof).request_review(build_mock_report(), []).status
        == HITLReviewStatus.PENDING_APPROVAL
    )
    assert (
        HITLReviewGate(interactive=False).request_review(build_mock_report(), []).status
        == HITLReviewStatus.PENDING_APPROVAL
    )


def test_interactive_edit_applies_amount_and_steps():
    answers = iter(["2", "e", "nan", "125", "First | Second", "APPROVE", "Phased review"])
    decision = HITLReviewGate(input_fn=lambda _: next(answers)).request_review(
        build_mock_report(), [proposal()]
    )
    assert decision.status == HITLReviewStatus.MODIFIED
    assert decision.modified_actions[0].estimated_dollar_amount == 125
    assert decision.modified_actions[0].action_steps == ["First", "Second"]


def test_interactive_remove_every_action():
    answers = iter(["2", "r", "APPROVE", "Remove all"])
    decision = HITLReviewGate(input_fn=lambda _: next(answers)).request_review(
        build_mock_report(), [proposal()]
    )
    assert decision.modified_actions == []


def test_invalid_callback_mutation_cannot_bypass_validation(make_runner):
    def callback(report, actions):
        actions[0].estimated_dollar_amount = float("nan")
        return HITLDecision(status="MODIFIED", override_reason="invalid", modified_actions=actions)

    result = make_runner().execute_workflow(client_id="101", hitl_callback=callback)
    assert result["status"] == "FAILED"
    assert result["stage"] == "HITL_REVIEW"


def test_memory_counts_types_once_per_session(tmp_path):
    store = LongTermMemoryStore(tmp_path)
    args = dict(
        client_id="101",
        session_id="one",
        overall_health_score=50,
        anomalies_detected=["CASH_DRAG", "CASH_DRAG"],
        actions_recommended=[],
        hitl_status="APPROVED",
    )
    store.record_session_insight(**args)
    store.record_session_insight(**args)
    memory = store.load_client_memory("101")
    assert memory.recurring_anomalies["CASH_DRAG"] == 1
    assert memory.total_sessions_run == 1


def test_atomic_replacement_failure_preserves_previous_file(tmp_path, monkeypatch):
    path = tmp_path / "memory.json"
    path.write_text("original")

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr("src.persistence.os.replace", fail)
    with pytest.raises(OSError):
        atomic_write_text(path, "replacement")
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_batch_honors_flags_and_quiet(tmp_path, capsys):
    args = [
        "--batch",
        "--auto-approve",
        "--simulate-crm-error",
        "--quiet",
        "--output-dir",
        str(tmp_path / "out"),
        "--storage-dir",
        str(tmp_path / "mem"),
    ]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "Stage started" not in output
    dossiers = list((tmp_path / "out").rglob("advisory_dossier.json"))
    assert len(dossiers) == 3
    assert all(json.loads(p.read_text())["crm_degraded"] for p in dossiers)


def test_batch_does_not_implicitly_approve(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert (
        main(
            [
                "--batch",
                "--quiet",
                "--output-dir",
                str(tmp_path / "out"),
                "--storage-dir",
                str(tmp_path / "mem"),
            ]
        )
        == 2
    )
    assert all(
        json.loads(p.read_text())["workflow_status"] == "PENDING_REVIEW"
        for p in (tmp_path / "out").rglob("advisory_dossier.json")
    )


def test_cli_invalid_json_returns_failure(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{")
    assert (
        main(
            [
                "--input",
                str(path),
                "--quiet",
                "--output-dir",
                str(tmp_path / "out"),
                "--storage-dir",
                str(tmp_path / "mem"),
            ]
        )
        == 1
    )


def test_explicit_file_input(tmp_path, sample):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(sample))
    assert (
        main(
            [
                "--input",
                str(path),
                "--auto-approve",
                "--quiet",
                "--output-dir",
                str(tmp_path / "out"),
                "--storage-dir",
                str(tmp_path / "mem"),
            ]
        )
        == 0
    )
