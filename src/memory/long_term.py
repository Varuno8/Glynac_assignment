"""Sequential CLI history with atomic writes and explicit corruption errors."""

from pathlib import Path

from pydantic import ValidationError

from src.config import STORAGE_DIR
from src.models.common import normalize_client_id, utc_now
from src.models.memory import ClientLongTermMemory, HistoricalInsight
from src.persistence import atomic_write_text


class MemoryCorruptionError(ValueError):
    """A previous memory file could not be read; original bytes are preserved."""


class LongTermMemoryStore:
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = Path(storage_dir if storage_dir is not None else STORAGE_DIR) / "client_memory"

    def _get_client_file(self, client_id):
        return self.storage_dir / f"{normalize_client_id(client_id)}_memory.json"

    def load_client_memory(self, client_id):
        cid = normalize_client_id(client_id)
        path = self._get_client_file(cid)
        if not path.exists():
            return ClientLongTermMemory(client_id=cid, last_updated=utc_now())
        try:
            memory = ClientLongTermMemory.model_validate_json(path.read_text(encoding="utf-8"))
            if memory.client_id != cid:
                raise ValueError("Client identity mismatch")
            return memory
        except (ValidationError, ValueError, UnicodeError) as exc:
            raise MemoryCorruptionError(
                f"Corrupt memory at {path}; file preserved. Restore a valid backup or use --storage-dir with a fresh directory."
            ) from exc

    def record_session_insight(
        self,
        client_id,
        session_id,
        overall_health_score,
        anomalies_detected,
        actions_recommended,
        hitl_status,
        advisor_override_notes=None,
    ):
        memory = self.load_client_memory(client_id)
        if any(s.session_id == session_id for s in memory.historical_sessions):
            return memory
        unique_anomalies = sorted(set(anomalies_detected))
        approved = hitl_status in {"APPROVED", "MODIFIED", "NOT_REQUIRED"}
        memory.historical_sessions.append(
            HistoricalInsight(
                session_id=session_id,
                date=utc_now(),
                overall_health_score=overall_health_score,
                anomalies_detected_count=len(unique_anomalies),
                top_anomaly_types=unique_anomalies,
                actions_recommended=actions_recommended if approved else [],
                hitl_status=hitl_status,
                advisor_override_notes=advisor_override_notes,
            )
        )
        memory.total_sessions_run = len(memory.historical_sessions)
        memory.last_updated = utc_now()
        for kind in unique_anomalies:
            memory.recurring_anomalies[kind] = memory.recurring_anomalies.get(kind, 0) + 1
        atomic_write_text(self._get_client_file(client_id), memory.model_dump_json(indent=2))
        return memory

    def get_trend_summary(self, client_id):
        memory = self.load_client_memory(client_id)
        if not memory.historical_sessions:
            return {"has_history": False, "summary": "First recorded assessment; no historical observations."}
        previous = memory.historical_sessions[-1]
        recurring = [
            f"{kind} (triggered {count}x)"
            for kind, count in sorted(memory.recurring_anomalies.items())
            if count > 1
        ]
        return {
            "has_history": True,
            "total_past_sessions": memory.total_sessions_run,
            "previous_health_score": previous.overall_health_score,
            "previous_session_date": previous.date,
            "recurring_anomalies": recurring,
            "summary": f"{memory.total_sessions_run} earlier assessments; previous health score {previous.overall_health_score}/100. Historical observations do not imply completed actions or current anomalies.",
        }
