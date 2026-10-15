"""Sequential orchestrator with explicit outcomes and stage-level failure boundaries."""

import json
from pathlib import Path
from uuid import uuid4

from src.agents.advisor import AdvisorAgent
from src.agents.analyzer import AnalyzerAgent
from src.agents.data_fetcher import DataFetcherAgent
from src.config import OUTPUT_DIR
from src.hitl.checkpoint import HITLReviewGate
from src.llm import get_llm_client
from src.memory.long_term import LongTermMemoryStore
from src.memory.short_term import SessionBlackboard
from src.models.advisory import AdvisoryPlan, HITLDecision
from src.models.advisory import HITLReviewStatus as Review
from src.models.analysis import AnalysisReport
from src.models.common import utc_now
from src.models.workflow import WorkflowResult
from src.observability.logger import AgentLogger
from src.observability.tracer import ExecutionTracer
from src.persistence import atomic_write_text
from src.reporting import render_markdown
from src.tools import create_default_tool_registry


class OrchestratorAgent:
    def __init__(
        self,
        tools=None,
        logger=None,
        memory_store=None,
        hitl_gate=None,
        auto_approve_hitl=False,
        llm=None,
        output_dir=None,
    ):
        self.name = "OrchestratorAgent"
        self.tools = tools if tools is not None else create_default_tool_registry()
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.logger = logger if logger is not None else AgentLogger(self.output_dir / "agent_execution.jsonl")
        self.memory_store = memory_store if memory_store is not None else LongTermMemoryStore()
        self.hitl_gate = (
            hitl_gate if hitl_gate is not None else HITLReviewGate(auto_approve=auto_approve_hitl)
        )
        self.llm = llm if llm is not None else get_llm_client()

    def execute_workflow(
        self, client_id=None, file_path=None, raw_json_data=None, simulate_crm_error=False, hitl_callback=None
    ):
        session_id = f"session_{uuid4().hex}"
        tracer = ExecutionTracer(session_id)
        board = SessionBlackboard(session_id)
        logger = self.logger.bind(session_id=session_id)
        current_stage = "START"
        report = plan = None
        output_files = {}

        def stage(name, agent, operation):
            nonlocal current_stage
            current_stage = name
            span = tracer.start_span(name, agent)
            scoped = logger.bind(stage=name, client_id=board.client_id)
            try:
                scoped.info(agent, "Stage started", outcome="STARTED")
                value = operation(scoped)
                if hasattr(value, "success") and not value.success:
                    raise ValueError(value.error)
                scoped.info(agent, "Stage finished", outcome="SUCCESS")
            except Exception:
                tracer.end_span(span, status="FAILED")
                raise
            tracer.end_span(span, status="SUCCESS")
            return value

        try:
            stage(
                "DATA_FETCH",
                "DataFetcherAgent",
                lambda log: DataFetcherAgent(self.tools, log, board).run(
                    client_id=client_id,
                    file_path=file_path,
                    raw_json_data=raw_json_data,
                    simulate_crm_error=simulate_crm_error,
                ),
            )
            logger = logger.bind(client_id=board.client_id)
            stage("ANALYSIS", "AnalyzerAgent", lambda log: AnalyzerAgent(self.tools, log, board).run())
            report = AnalysisReport.model_validate(board.get("analysis_report"))
            stage(
                "ADVISORY_SYNTHESIS",
                "AdvisorAgent",
                lambda log: AdvisorAgent(self.tools, log, board, self.memory_store, self.llm).run(),
            )
            plan = AdvisoryPlan.model_validate(board.get("draft_advisory_plan"))

            def review(log):
                required = self.hitl_gate.evaluate_requires_review(report, plan.action_items)
                if required:
                    decision = self.hitl_gate.request_review(report, plan.action_items, hitl_callback)
                    # Custom gates must obey the same contract as the interactive gate.
                    decision = self.hitl_gate.validate_decision(decision, plan.action_items)
                else:
                    decision = HITLDecision(
                        status=Review.NOT_REQUIRED,
                        reviewer_name="Rule evaluation",
                        timestamp=utc_now(),
                        override_reason="No configured review trigger; no human approval implied.",
                    )
                plan.hitl_decision = decision
                if decision.status == Review.MODIFIED:
                    plan.action_items = decision.modified_actions
                    original = {action.action_id: action for action in plan.original_action_items}
                    for action in plan.action_items:
                        if (
                            action.estimated_dollar_amount
                            != original[action.action_id].estimated_dollar_amount
                        ):
                            action.impact = "Advisor changed the proposed amount; reassess the original impact estimate before implementation."
                log.info("HITLReviewGate", "Review decision recorded", outcome=decision.status.value)

            stage("HITL_REVIEW", "HITLReviewGate", review)
            outcome = {Review.REJECTED: "REJECTED", Review.PENDING_APPROVAL: "PENDING_REVIEW"}.get(
                plan.hitl_decision.status, "COMPLETED"
            )
            # Export first. Failed exports do not become new history entries.
            output_files = stage(
                "EXPORT",
                self.name,
                lambda log: self._export_deliverables(
                    board.client_id, session_id, report, plan, board, outcome
                ),
            )
            stage(
                "PERSIST_MEMORY",
                "LongTermMemoryStore",
                lambda log: self.memory_store.record_session_insight(
                    client_id=board.client_id,
                    session_id=session_id,
                    overall_health_score=report.metrics.overall_health_score,
                    anomalies_detected=[a.anomaly_type.value for a in report.anomalies],
                    actions_recommended=[a.title for a in plan.action_items],
                    hitl_status=plan.hitl_decision.status.value,
                    advisor_override_notes=plan.hitl_decision.override_reason,
                ),
            )
            result = WorkflowResult(
                status=outcome,
                session_id=session_id,
                client_id=board.client_id,
                health_score=report.metrics.overall_health_score,
                anomalies_detected=len(report.anomalies),
                actions_count=len(plan.action_items),
                hitl_status=plan.hitl_decision.status.value,
                output_json=str(output_files["json_path"]),
                output_markdown=str(output_files["md_path"]),
                analysis_report=report,
                advisory_plan=plan,
                trace=tracer.get_summary(),
            )
            current_stage = "FINALIZE"
            atomic_write_text(
                self.output_dir / board.client_id / session_id / "run_status.json",
                json.dumps({"status": outcome, "session_id": session_id, "trace": result.trace}, indent=2),
            )
            logger.bind(stage="FINALIZE").info(self.name, "Workflow finished", outcome=outcome)
            return result.model_dump(mode="json")
        except Exception as exc:
            try:
                logger.bind(stage=current_stage).error(
                    self.name, "Workflow failed", outcome="FAILED", error_type=type(exc).__name__
                )
            except Exception:
                pass  # A broken log destination must not hide the original failure.
            failure = WorkflowResult(
                status="FAILED",
                session_id=session_id,
                client_id=board.client_id,
                stage=current_stage,
                error=f"{type(exc).__name__}: {exc}",
                trace=tracer.get_summary(),
            )
            if board.client_id:
                try:
                    # Correct any partially exported success labels after persistence failure.
                    if report is not None and plan is not None:
                        self._export_deliverables(board.client_id, session_id, report, plan, board, "FAILED")
                    atomic_write_text(
                        self.output_dir / board.client_id / session_id / "run_status.json",
                        json.dumps(failure.model_dump(mode="json"), indent=2),
                    )
                except Exception:
                    pass
            return failure.model_dump(mode="json")

    def _export_deliverables(self, client_id, session_id, report, advisory_plan, blackboard, status):
        directory = self.output_dir / client_id / session_id
        json_path = directory / "advisory_dossier.json"
        md_path = directory / "advisory_report.md"
        data = {
            "schema_version": 2,
            "workflow_status": status,
            "client_id": client_id,
            "session_id": session_id,
            "crm_degraded": blackboard.get("crm_degraded", False),
            "analysis_report": report.model_dump(mode="json"),
            "advisory_plan": advisory_plan.model_dump(mode="json"),
            "session_history": [
                {
                    "step_name": item.step_name,
                    "agent_name": item.agent_name,
                    "timestamp": item.timestamp,
                    "summary": item.summary,
                }
                for item in blackboard.get_history()
            ],
        }
        atomic_write_text(json_path, json.dumps(data, indent=2, allow_nan=False))
        atomic_write_text(md_path, render_markdown(report, advisory_plan, status))
        return {"json_path": json_path, "md_path": md_path}
