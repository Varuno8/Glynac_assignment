"""Analyzer Agent: performs financial health calculations and anomaly detection."""

import time

from src.agents.base import AgentResponse, BaseAgent
from src.models.analysis import AnalysisReport, AnomalySeverity


class AnalyzerAgent(BaseAgent):
    name = "AnalyzerAgent"
    role = "Quantitative Risk & Anomaly Analyst"
    description = "Executes financial health analytics, portfolio drift, cash drag, concentration risk, and transaction anomalies."

    def run(self, **kwargs) -> AgentResponse:
        start_time = time.perf_counter()
        self.log("Beginning quantitative analysis and anomaly detection pass")

        financial_data = self.blackboard.get("financial_data")
        if not financial_data:
            err = "AnalyzerAgent cannot run: missing 'financial_data' on blackboard."
            self.log(err, level="ERROR")
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return AgentResponse(
                agent_name=self.name, success=False, error=err, execution_time_ms=round(elapsed, 2)
            )

        crm_profile = self.blackboard.get("crm_profile", {})
        target_allocation = crm_profile.get("risk_profile", {}).get("target_allocation")

        # Invoke Anomaly Detection Engine Tool
        anom_tool = self.tools.get("anomaly_detection_engine")
        self.logger.tool_call(self.name, anom_tool.name, {"target_allocation": target_allocation})

        tool_res = anom_tool.run(
            financial_data=financial_data,
            target_allocation=target_allocation,
            market_benchmarks=self.blackboard.get("market_benchmarks", {}),
        )
        self.logger.tool_result(self.name, anom_tool.name, tool_res.success, tool_res.execution_time_ms)

        if not tool_res.success:
            err = f"Anomaly detection engine failed: {tool_res.error}"
            self.log(err, level="ERROR")
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return AgentResponse(
                agent_name=self.name, success=False, error=err, execution_time_ms=round(elapsed, 2)
            )

        analysis_data = tool_res.data
        report = AnalysisReport(
            client_id=financial_data.get("client_id", "unknown"),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            metrics=analysis_data["metrics"],
            allocation=analysis_data["allocation"],
            anomalies=analysis_data["anomalies"],
            risk_summary=analysis_data["risk_summary"],
            requires_human_review=analysis_data["requires_human_review"]
            or self.blackboard.get("crm_degraded", False),
            warnings=analysis_data.get("warnings", []),
            benchmark_source=analysis_data.get("benchmark_source", "unavailable"),
            benchmark_as_of=analysis_data.get("benchmark_as_of"),
        )

        self.blackboard.set(
            "analysis_report",
            report.model_dump(),
            self.name,
            f"Computed financial report (Health: {report.metrics.overall_health_score}/100)",
        )

        # Log summary of anomalies detected
        critical_count = sum(1 for a in report.anomalies if a.severity == AnomalySeverity.CRITICAL)
        high_count = sum(1 for a in report.anomalies if a.severity == AnomalySeverity.HIGH)
        med_count = sum(1 for a in report.anomalies if a.severity == AnomalySeverity.MEDIUM)

        self.log(
            f"Analysis complete: Health Score={report.metrics.overall_health_score}/100 | "
            f"Anomalies: {critical_count} Critical, {high_count} High, {med_count} Medium",
            level="WARNING" if (critical_count + high_count) > 0 else "INFO",
        )

        elapsed = (time.perf_counter() - start_time) * 1000.0
        return AgentResponse(
            agent_name=self.name,
            success=True,
            data={
                "health_score": report.metrics.overall_health_score,
                "anomalies_count": len(report.anomalies),
                "requires_human_review": report.requires_human_review,
            },
            execution_time_ms=round(elapsed, 2),
        )
