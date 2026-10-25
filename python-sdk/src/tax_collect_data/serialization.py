"""JSON serialization helpers compatible with the source SDK's camelCase output."""

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.to_api_dict() if hasattr(value, "to_api_dict") else value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def serialize(value: Any) -> str:
    return json.dumps(value, default=_json_default, ensure_ascii=False, separators=(",", ":"))


def deserialize(payload: str) -> Any:
    return json.loads(payload)
