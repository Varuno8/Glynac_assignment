"""Mock CRM API; missing records are failures, never fabricated risk profiles."""

import json
import time
from pathlib import Path

from pydantic import BaseModel

from src.config import CRM_DB_PATH
from src.models.common import ClientId
from src.models.crm import CRMClientProfile
from src.tools.base import BaseTool


class CRMQueryArgs(BaseModel):
    client_id: ClientId
    simulate_network_delay: bool = False
    simulate_error: bool = False


class CRMClientProfileTool(BaseTool):
    name = "crm_client_profile_api"
    description = "Retrieves a validated client profile from a simulated CRM."
    args_schema = CRMQueryArgs

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or CRM_DB_PATH

    def _execute(self, client_id, simulate_network_delay=False, simulate_error=False):
        if simulate_network_delay:
            time.sleep(0.05)
        if simulate_error:
            raise ConnectionError("CRM API 503 Service Unavailable: simulated outage")
        records = json.loads(self.db_path.read_text(encoding="utf-8"))
        if client_id not in records:
            raise LookupError(f"CRM profile not found for {client_id}")
        profile = CRMClientProfile.model_validate(records[client_id])
        if profile.client_id != client_id:
            raise ValueError("CRM identity does not match requested client")
        return profile.model_dump()
