"""Explicit approval, editable proposals and a safe noninteractive pending outcome."""

import sys

from src.config import DEFAULT_THRESHOLDS
from src.models.advisory import AdvisoryActionItem, HITLDecision
from src.models.advisory import HITLReviewStatus as Status
from src.models.common import utc_now
from src.observability.logger import console


class HITLReviewGate:
    def __init__(
        self,
        logger=None,
        auto_approve=False,
        reviewer_name="Lead Wealth Advisor",
        input_fn=None,
        interactive=None,
        thresholds=None,
    ):
        self.logger = logger
        self.auto_approve = auto_approve
        self.reviewer_name = reviewer_name
        self.input_fn = input_fn
        self.interactive = interactive
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def evaluate_requires_review(self, analysis_report, proposed_actions=None):
        return (
            analysis_report.requires_human_review
            or any(a.severity in {"HIGH", "CRITICAL"} for a in analysis_report.anomalies)
            or any(
                a.category == "PORTFOLIO_REBALANCING"
                and (a.estimated_dollar_amount or 0) > self.thresholds.hitl_rebalance_amount_threshold
                for a in (proposed_actions or [])
            )
        )

    def validate_decision(self, decision, actions):
        decision = HITLDecision.model_validate(
            decision.model_dump() if isinstance(decision, HITLDecision) else decision
        )
        if decision.status == Status.NOT_REQUIRED:
            raise ValueError("A required review cannot be bypassed by a reviewer")
        if decision.status == Status.MODIFIED:
            if decision.modified_actions is None:
                raise ValueError("Modified decision must include revised actions; use [] to remove all")
            original = {a.action_id: a for a in actions}
            ids = [a.action_id for a in decision.modified_actions]
            if len(ids) != len(set(ids)) or not set(ids).issubset(original):
                raise ValueError("Revised actions must have unique existing action IDs")
            for action in decision.modified_actions:
                before = original[action.action_id]
                editable = {"estimated_dollar_amount", "action_steps"}
                if action.model_dump(exclude=editable) != before.model_dump(exclude=editable):
                    raise ValueError(
                        "Review may change amounts and steps, but must preserve action identity and evidence"
                    )
        if (
            decision.status in {Status.MODIFIED, Status.REJECTED}
            and not (decision.override_reason or "").strip()
        ):
            raise ValueError("Modified and rejected decisions require a reason")
        if decision.status != Status.PENDING_APPROVAL and not decision.reviewer_name:
            decision.reviewer_name = self.reviewer_name
        decision.timestamp = decision.timestamp or utc_now()
        return decision

    def request_review(self, analysis_report, proposed_actions, review_callback=None):
        if review_callback:
            copies = [a.model_copy(deep=True) for a in proposed_actions]
            return self.validate_decision(
                review_callback(analysis_report.model_copy(deep=True), copies), proposed_actions
            )
        if self.auto_approve:
            return HITLDecision(
                status=Status.APPROVED,
                reviewer_name=f"{self.reviewer_name} (Auto-Policy)",
                timestamp=utc_now(),
                override_reason="Explicit --auto-approve demo policy; no human review performed.",
            )
        interactive = (
            self.interactive
            if self.interactive is not None
            else (self.input_fn is not None or sys.stdin.isatty())
        )
        if not interactive:
            return self._pending("Interactive input unavailable; approval remains pending.")
        ask = self.input_fn if self.input_fn is not None else input
        console.print(f"Human review required for {analysis_report.client_id}", markup=False)
        for a in proposed_actions:
            amount = (
                f"${a.estimated_dollar_amount:,.2f}" if a.estimated_dollar_amount is not None else "no amount"
            )
            console.print(f"{a.action_id}: {a.title} ({amount})", markup=False)
        try:
            while True:
                choice = ask("[1] Approve [2] Modify [3] Reject [4] Leave pending: ").strip()
                if choice == "1":
                    return HITLDecision(
                        status=Status.APPROVED,
                        reviewer_name=self.reviewer_name,
                        timestamp=utc_now(),
                        override_reason="Explicit advisor approval.",
                    )
                if choice == "4":
                    return self._pending("Advisor left review pending.")
                if choice == "3":
                    reason = self._reason(ask)
                    return HITLDecision(
                        status=Status.REJECTED,
                        reviewer_name=self.reviewer_name,
                        timestamp=utc_now(),
                        override_reason=reason,
                    )
                if choice == "2":
                    revised = self._edit(ask, proposed_actions)
                    if (
                        ask(
                            "Type APPROVE to approve these revised actions (anything else leaves pending): "
                        ).strip()
                        != "APPROVE"
                    ):
                        return self._pending("Modified draft was not approved.")
                    decision = HITLDecision(
                        status=Status.MODIFIED,
                        reviewer_name=self.reviewer_name,
                        timestamp=utc_now(),
                        override_reason=self._reason(ask),
                        modified_actions=revised,
                    )
                    return self.validate_decision(decision, proposed_actions)
                console.print("Choose 1, 2, 3 or 4. Empty input does not approve.")
        except (EOFError, KeyboardInterrupt):
            return self._pending("Input interrupted; approval remains pending.")

    def _reason(self, ask):
        while True:
            reason = ask("Decision rationale (required): ").strip()
            if reason:
                return reason

    def _edit(self, ask, actions):
        revised = []
        for action in actions:
            while True:
                operation = ask(f"{action.action_id}: [k]eep [r]emove [e]dit: ").strip().lower()
                if operation in {"k", "r", "e"}:
                    break
            if operation == "r":
                continue
            data = action.model_dump()
            if operation == "e":
                while True:
                    raw = ask("New amount (blank keeps current; 'none' removes amount): ").strip()
                    try:
                        data["estimated_dollar_amount"] = (
                            None
                            if raw.lower() == "none"
                            else float(raw)
                            if raw
                            else action.estimated_dollar_amount
                        )
                        AdvisoryActionItem.model_validate(data)
                        break
                    except ValueError:
                        console.print("Enter a finite, nonnegative amount.")
                steps = ask("Replacement steps separated by | (blank keeps current): ").strip()
                if steps:
                    data["action_steps"] = [s.strip() for s in steps.split("|") if s.strip()]
            revised.append(AdvisoryActionItem.model_validate(data))
        return revised

    def _pending(self, reason):
        return HITLDecision(status=Status.PENDING_APPROVAL, timestamp=utc_now(), override_reason=reason)
