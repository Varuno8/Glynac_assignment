"""Shared input validation; identifiers are safe to use as file names."""

import re
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict


def normalize_client_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Client ID must be a string")
    suffix = value.removeprefix("client_")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", suffix):
        raise ValueError("Client ID must contain only letters, numbers, underscores or hyphens")
    return f"client_{suffix}"


ClientId = Annotated[str, BeforeValidator(normalize_client_id)]


class ValidatedModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
