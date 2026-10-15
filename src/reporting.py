"""Human-readable audit reports, with decision state visible before recommendations."""

from src.models.advisory import HITLReviewStatus


def format_evidence(value):
    return f"{value:,.2f}" if isinstance(value, float) else str(value)


def render_markdown(report, plan, status):
    approved = status == "COMPLETED"
    title = "Advisory Review Report" if approved else "ADVISORY AUDIT — NOT APPROVED FOR DISTRIBUTION"
    lines = [
        f"# {title}",
        f"Client: {plan.client_name} ({plan.client_id})",
        f"Generated: {plan.created_at}",
        f"**Workflow outcome: {status} | Review: {plan.hitl_decision.status.value}**",
        "",
        "## Executive summary",
        plan.executive_summary,
        "",
        "## Data quality and provenance",
        f"- Market data: {report.benchmark_source}; as of {report.benchmark_as_of or 'unavailable'}",
        f"- Narrative provider: {plan.narrative_provider}",
    ]
    if plan.fallback_reason:
        lines.append(f"- Provider fallback: {plan.fallback_reason}")
    lines.extend(f"- {warning}" for warning in report.warnings)
    if plan.narrative_provider != "mock":
        lines.append(
            "- AI prose requires factual review; amounts are application-calculated before recorded advisor overrides."
        )
    metrics = report.metrics
    runway = (
        f"{metrics.emergency_fund_months:.2f} months"
        if metrics.emergency_fund_months is not None
        else "Not applicable: zero reported expenses"
    )
    savings = (
        f"{metrics.monthly_savings_rate_pct:.1f}%"
        if metrics.monthly_savings_rate_pct is not None
        else "Not defined: zero reported income"
    )
    lines += [
        "",
        "## Financial snapshot",
        f"- Portfolio assets: ${metrics.total_liquid_net_worth:,.2f}",
        f"- Available emergency cash: ${metrics.total_cash:,.2f}",
        f"- Emergency runway: {runway}",
        f"- Savings rate: {savings}",
        f"- Illustrative health score: {metrics.overall_health_score}/100",
        "",
        "| Asset class | Actual % | Target % | Drift (percentage points) |",
        "|---|---:|---:|---:|",
    ]
    for asset, actual in report.allocation.actual_allocation_pct.items():
        if asset == "UNCLASSIFIED" and actual == 0:
            continue
        target = report.allocation.target_allocation_pct.get(asset)
        drift = report.allocation.drift_pct.get(asset)
        lines.append(
            f"| {asset} | {actual:.2f} | {f'{target:.2f}' if target is not None else 'Unknown'} | {f'{drift:+.2f}' if drift is not None else 'N/A'} |"
        )
    lines += ["", "## Current risk signals"]
    for anomaly in report.anomalies:
        lines += [
            f"### {anomaly.severity.value}: {anomaly.title}",
            f"Evidence ID: `{anomaly.anomaly_id}`",
            anomaly.description,
            "Evidence: " + "; ".join(f"{k}={format_evidence(v)}" for k, v in anomaly.evidence.items()),
            "",
        ]
    if not report.anomalies:
        lines.append("No configured anomaly rules triggered.")
    lines += [
        "",
        "## Reviewed proposals" if approved else "## Draft proposals — audit only",
        "Amounts can overlap across proposals and must not be added together as an execution plan.",
    ]
    if plan.hitl_decision.status == HITLReviewStatus.MODIFIED:
        lines.append(
            "The following reflects the approved edits. Original actions remain in the JSON audit record; the executive summary describes the pre-review assessment."
        )
    if not plan.action_items:
        lines.append("No actions retained after review.")
    for action in plan.action_items:
        amount = (
            f"${action.estimated_dollar_amount:,.2f}" if action.estimated_dollar_amount is not None else "N/A"
        )
        lines += [
            f"### [{action.priority.value}] {action.title}",
            f"- Action ID: `{action.action_id}`",
            f"- Estimated amount: {amount}",
            f"- Sources: {', '.join(action.source_anomaly_ids) or 'Data-quality/monitoring rule'}",
            f"- Rationale: {action.rationale}",
            f"- Expected purpose: {action.impact}",
        ]
        lines.extend(f"- {step}" for step in action.action_steps)
    decision = plan.hitl_decision
    lines += [
        "",
        "## Human review",
        f"- Status: {decision.status.value}",
        f"- Reviewer: {decision.reviewer_name or 'None'}",
        f"- Timestamp: {decision.timestamp or 'None'}",
        f"- Reason: {decision.override_reason or 'None'}",
        "",
        "## Meeting agenda (generated before review)",
    ]
    lines.extend(f"- {topic}" for topic in plan.meeting_agenda_topics)
    lines += ["", "## Historical context and findings"]
    lines.extend(f"- {finding}" for finding in plan.key_findings)
    lines += ["", "## Limitations", plan.compliance_notes, ""]
    return "\n".join(lines)
