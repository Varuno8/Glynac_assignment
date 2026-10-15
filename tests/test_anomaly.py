"""Unit tests for anomaly detection algorithms and thresholds."""

import json

from src.config import SAMPLE_CLIENTS_DIR
from src.tools.anomaly_tool import AnomalyDetectionTool


def load_client_data(client_file: str):
    with open(SAMPLE_CLIENTS_DIR / client_file, "r", encoding="utf-8") as f:
        return json.load(f)


def test_anomaly_detection_client_101_alex_chen():
    data = load_client_data("client_101_alex_chen.json")
    tool = AnomalyDetectionTool()

    target_alloc = {"US_EQUITY": 60.0, "INTL_EQUITY": 20.0, "FIXED_INCOME": 15.0, "CASH": 5.0}

    res = tool.run(financial_data=data, target_allocation=target_alloc)
    assert res.success is True

    anomalies = res.data["anomalies"]
    types = [a["anomaly_type"] for a in anomalies]

    # Client 101 should trigger:
    # 1. CASH_DRAG (holding $380,000 in checking vs 5% target)
    # 2. CONCENTRATION_RISK (NVDA is over 15% of portfolio)
    # 3. HIGH_VALUE_WIRE_TRANSFER ($45,000 outbound wire transfer)
    assert "CASH_DRAG" in types
    assert "CONCENTRATION_RISK" in types
    assert "HIGH_VALUE_WIRE_TRANSFER" in types

    assert res.data["requires_human_review"] is True
    assert res.data["metrics"]["overall_health_score"] < 80


def test_anomaly_detection_client_102_sarah_connor():
    data = load_client_data("client_102_sarah_connor.json")
    tool = AnomalyDetectionTool()

    # Conservative target: 30% US_EQUITY, 10% INTL, 50% FIXED_INCOME, 10% CASH
    target_alloc = {"US_EQUITY": 30.0, "INTL_EQUITY": 10.0, "FIXED_INCOME": 50.0, "CASH": 10.0}

    res = tool.run(financial_data=data, target_allocation=target_alloc)
    assert res.success is True

    types = [a["anomaly_type"] for a in res.data["anomalies"]]

    # Client 102 should trigger ASSET_ALLOCATION_DRIFT (heavy equity overweight)
    assert "ASSET_ALLOCATION_DRIFT" in types
    assert res.data["requires_human_review"] is True


def test_anomaly_detection_client_103_marcus_vance():
    data = load_client_data("client_103_marcus_vance.json")
    tool = AnomalyDetectionTool()

    res = tool.run(financial_data=data)
    assert res.success is True

    types = [a["anomaly_type"] for a in res.data["anomalies"]]
    # Client 103 has only $3,200 cash vs $10,800 monthly burn -> EMERGENCY_RESERVE_DEFICIT
    assert "EMERGENCY_RESERVE_DEFICIT" in types
    assert res.data["requires_human_review"] is True
