"""Ingest financial data and enrich it without inventing missing client preferences."""

import time

from src.agents.base import AgentResponse, BaseAgent


class DataFetcherAgent(BaseAgent):
    name = "DataFetcherAgent"
    role = "Data ingestion and context enrichment"
    description = "Uses registered financial, CRM and benchmark tools."

    def run(self, client_id=None, file_path=None, raw_json_data=None, simulate_crm_error=False):
        started = time.perf_counter()

        def invoke(name, **kwargs):
            self.logger.tool_call(self.name, name, {})
            result = self.tools.get(name).run(**kwargs)
            self.logger.tool_result(self.name, name, result.success, result.execution_time_ms)
            return result

        financial = invoke(
            "financial_data_ingestor", client_id=client_id, file_path=file_path, raw_json_data=raw_json_data
        )
        if not financial.success:
            return AgentResponse(agent_name=self.name, success=False, error=financial.error)
        data = financial.data
        cid = data["client_id"]
        self.blackboard.client_id = cid
        self.blackboard.set("financial_data", data, self.name, "Validated financial snapshot")
        crm = invoke("crm_client_profile_api", client_id=cid, simulate_error=simulate_crm_error)
        self.blackboard.set("crm_degraded", not crm.success, self.name)
        if crm.success:
            profile = crm.data
        else:
            # Identity from the input is retained; preferences and contact details are not invented.
            profile = {
                "client_id": cid,
                "name": data["name"],
                "risk_profile": {},
                "advisor_notes": "DEGRADED STATUS: CRM profile unavailable; target-dependent advice withheld.",
            }
            self.blackboard.set("crm_failure_reason", crm.error, self.name)
            self.log(
                "CRM unavailable; continuing independent checks without target allocation",
                level="WARNING",
                fallback_reason="crm_unavailable",
            )
        self.blackboard.set("crm_profile", profile, self.name, "CRM profile or explicitly degraded context")
        market = invoke("market_benchmark_api")
        self.blackboard.set("market_benchmarks", market.data if market.success else {}, self.name)
        if not market.success:
            self.log(
                "Market benchmarks unavailable; yield estimates omitted",
                level="WARNING",
                fallback_reason="benchmark_unavailable",
            )
        return AgentResponse(
            agent_name=self.name,
            success=True,
            data={"client_id": cid, "crm_status": "DEGRADED" if not crm.success else "ONLINE"},
            execution_time_ms=round((time.perf_counter() - started) * 1000, 2),
        )
