"""Tools package providing abstraction layer and default registry factory."""

from src.tools.anomaly_tool import AnomalyDetectionTool
from src.tools.base import BaseTool, ToolRegistry, ToolResult
from src.tools.crm_tool import CRMClientProfileTool
from src.tools.financial_tool import FinancialIngestionTool
from src.tools.market_tool import MarketBenchmarkTool
from src.tools.recommendation_tool import RecommendationTool


def create_default_tool_registry() -> ToolRegistry:
    """Instantiates and registers all system tools into a decoupled registry."""
    registry = ToolRegistry()
    registry.register(FinancialIngestionTool())
    registry.register(CRMClientProfileTool())
    registry.register(MarketBenchmarkTool())
    registry.register(AnomalyDetectionTool())
    registry.register(RecommendationTool())
    return registry


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "FinancialIngestionTool",
    "CRMClientProfileTool",
    "MarketBenchmarkTool",
    "AnomalyDetectionTool",
    "create_default_tool_registry",
]
