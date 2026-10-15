"""Short-term memory subsystem managing live session blackboard and agent scratchpad."""

import time
from copy import deepcopy
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.models.memory import ShortTermMemoryItem


class SessionBlackboard:
    """Working short-term memory shared across agents during a single execution run."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{uuid4().hex}"
        self.client_id: Optional[str] = None
        self._blackboard: Dict[str, Any] = {}
        self._history: List[ShortTermMemoryItem] = []

    def set(self, key: str, value: Any, agent_name: str, summary: str = "") -> None:
        """Stores a key-value pair and records the action in short-term audit history."""
        self._blackboard[key] = deepcopy(value)
        item = ShortTermMemoryItem(
            step_name=key,
            agent_name=agent_name,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            data=deepcopy(value) if isinstance(value, dict) else {"val": str(value)},
            summary=summary or f"Agent '{agent_name}' updated '{key}'",
        )
        self._history.append(item)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a value from the shared blackboard."""
        return deepcopy(self._blackboard.get(key, default))

    def has(self, key: str) -> bool:
        return key in self._blackboard

    def get_history(self) -> List[ShortTermMemoryItem]:
        return list(self._history)

    def dump_session_state(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "keys_present": list(self._blackboard.keys()),
            "total_steps": len(self._history),
        }
