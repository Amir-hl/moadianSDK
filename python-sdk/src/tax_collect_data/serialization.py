
"""JSON serialization helpers compatible with the source C# SDK."""

import simplejson as json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel


def _normalize(value: Any) -> Any:
    """Convert Python values to JSON-compatible values."""

    # IntEnum must be checked before primitive types.
    if isinstance(value, Enum):
        return value.name

    if isinstance(value, BaseModel):
        if hasattr(value, "to_api_dict"):
            value = value.to_api_dict(exclude_none=False)
        else:
            value = value.model_dump(
                by_alias=True,
                exclude_none=False,
            )

    if isinstance(value, dict):
        return {
            key: _normalize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def serialize(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        use_decimal=True,
        allow_nan=False,
    )


def deserialize(payload: str) -> Any:
    return json.loads(payload, use_decimal=True)
