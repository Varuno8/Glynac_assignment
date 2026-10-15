"""Unit tests for tool abstraction layer."""

import pytest

from src.tools import (
    CRMClientProfileTool,
    FinancialIngestionTool,
    MarketBenchmarkTool,
    create_default_tool_registry,
)


def test_tool_registry_registration_and_lookup():
    registry = create_default_tool_registry()
    assert registry.has_tool("financial_data_ingestor")
    assert registry.has_tool("crm_client_profile_api")
    assert registry.has_tool("market_benchmark_api")
    assert registry.has_tool("anomaly_detection_engine")

    with pytest.raises(KeyError):
        registry.get("non_existent_tool")


def test_financial_ingestion_tool_success():
    tool = FinancialIngestionTool()
    res = tool.run(client_id="101")
    assert res.success is True
    assert res.data["client_id"] == "client_101"
    assert res.data["name"] == "Alex Chen"
    assert len(res.data["accounts"]) >= 3


def test_financial_ingestion_tool_missing_client():
    tool = FinancialIngestionTool()
    res = tool.run(client_id="999999")
    assert res.success is False
    assert "No sample financial file found" in res.error


def test_crm_tool_normal_and_fallback():
    crm_tool = CRMClientProfileTool()

    # Existing client
    res101 = crm_tool.run(client_id="client_101")
    assert res101.success is True
    assert res101.data["name"] == "Alex Chen"
    assert res101.data["risk_profile"]["risk_tolerance"] == "MODERATE_AGGRESSIVE"

    # Non-existing client fallback
    res_unknown = crm_tool.run(client_id="client_unknown_888")
    assert res_unknown.success is False
    assert "not found" in res_unknown.error


def test_crm_tool_simulated_error_resilience():
    crm_tool = CRMClientProfileTool()
    res = crm_tool.run(client_id="client_101", simulate_error=True)
    assert res.success is False
    assert "CRM API 503 Service Unavailable" in res.error


def test_market_benchmark_tool():
    mkt = MarketBenchmarkTool()
    res = mkt.run()
    assert res.success is True
    assert "sp500_ytd_return_pct" in res.data
    assert res.data["high_yield_savings_avg_apy"] > 0
