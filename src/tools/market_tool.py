"""Tool for fetching market indicators and macroeconomic benchmarks."""

from typing import Any, Dict

from pydantic import BaseModel, Field

from src.tools.base import BaseTool


class MarketBenchmarkArgs(BaseModel):
    benchmark_scope: str = Field(default="US_CORE", description="Scope of benchmarks: US_CORE or GLOBAL")


class MarketBenchmarkTool(BaseTool):
    name = "market_benchmark_api"
    description = "Provides explicitly simulated market benchmarks for the assignment demo."
    args_schema = MarketBenchmarkArgs

    def _execute(self, benchmark_scope: str = "US_CORE") -> Dict[str, Any]:
        # Realistic macroeconomic context benchmark figures
        return {
            "source": "simulated fixture (not live market data)",
            "sp500_ytd_return_pct": 14.2,
            "us_10y_treasury_yield_pct": 4.15,
            "high_yield_savings_avg_apy": 4.65,
            "traditional_checking_avg_apy": 0.07,
            "core_cpi_inflation_pct": 2.8,
            "last_updated": "2026-10-15",
        }
