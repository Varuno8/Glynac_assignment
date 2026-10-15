"""Tool for ingesting and validating client financial data."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator

from src.config import SAMPLE_CLIENTS_DIR
from src.models.common import ClientId, normalize_client_id
from src.models.financial import ClientFinancialData
from src.tools.base import BaseTool


class FinancialIngestionArgs(BaseModel):
    client_id: Optional[ClientId] = Field(default=None, description="Client ID (e.g., client_101 or 101)")
    file_path: Optional[str] = Field(default=None, description="Explicit path to client financial JSON file")
    raw_json_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Direct in-memory dictionary data"
    )

    @model_validator(mode="after")
    def one_source(self):
        if sum(value is not None for value in (self.client_id, self.file_path, self.raw_json_data)) != 1:
            raise ValueError("Provide exactly one of client_id, file_path or raw_json_data")
        return self


class FinancialIngestionTool(BaseTool):
    name = "financial_data_ingestor"
    description = "Ingests, parses, and validates client financial profile, accounts, and transactions."
    args_schema = FinancialIngestionArgs

    def _execute(
        self,
        client_id: Optional[str] = None,
        file_path: Optional[str] = None,
        raw_json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        if raw_json_data is not None:
            data = raw_json_data
        elif file_path:
            p = Path(file_path)
            if not p.exists():
                raise FileNotFoundError(f"Financial data file not found: {file_path}")
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif client_id:
            # Normalize client_id
            norm_id = normalize_client_id(client_id)
            # Look for matching file in SAMPLE_CLIENTS_DIR
            matches = sorted(SAMPLE_CLIENTS_DIR.glob(f"{norm_id}_*.json"))
            exact = SAMPLE_CLIENTS_DIR / f"{norm_id}.json"
            if exact.exists():
                matches.append(exact)
            if not matches:
                raise FileNotFoundError(
                    f"No sample financial file found for {norm_id} in {SAMPLE_CLIENTS_DIR}"
                )
            if len(matches) != 1:
                raise ValueError(f"Ambiguous financial input for {norm_id}; use file_path")
            with open(matches[0], "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError("Must provide either client_id, file_path, or raw_json_data.")

        # Validate with Pydantic
        client_obj = ClientFinancialData(**data)
        if client_id is not None and client_obj.client_id != normalize_client_id(client_id):
            raise ValueError("Client ID does not match financial input")
        return client_obj.model_dump()
