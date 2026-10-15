"""Base tool abstractions and registry for agent tool use."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = "base_tool"
    description: str = "Base tool description"
    args_schema: Optional[Type[BaseModel]] = None

    def run(self, **kwargs) -> ToolResult:
        """Executes the tool with error handling and timing."""
        start_time = time.perf_counter()
        try:
            # Validate args if schema is provided
            if self.args_schema:
                validated_args = self.args_schema(**kwargs)
                result_data = self._execute(**validated_args.model_dump())
            else:
                result_data = self._execute(**kwargs)

            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_name=self.name, success=True, data=result_data, execution_time_ms=round(elapsed, 2)
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            if isinstance(exc, ValidationError):
                detail = "; ".join(
                    f"{'.'.join(map(str, e['loc']))}: {e['msg']}"
                    for e in exc.errors(include_input=False, include_context=False)
                )
            else:
                detail = str(exc)
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Tool '{self.name}' failed: {detail}",
                execution_time_ms=round(elapsed, 2),
            )

    @abstractmethod
    def _execute(self, **kwargs) -> Any:
        """Internal execution method implemented by subclasses."""
        pass


class ToolRegistry:
    """Registry to decouple agents from direct tool instantiation."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in ToolRegistry.")
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> Dict[str, str]:
        return {name: tool.description for name, tool in self._tools.items()}

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        tool = self.get(tool_name)
        return tool.run(**kwargs)
