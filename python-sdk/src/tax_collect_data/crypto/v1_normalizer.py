"""JSON and HTTP header normalizer matching .NET SimpleNormalizer for API v1."""

from __future__ import annotations

from typing import Any, Mapping

from tax_collect_data.serialization import serialize


class SimpleNormalizer:
    """Normalizes JSON payload and HTTP headers for transfer signing in API v1."""

    def __init__(self, token_header_name: str = "Authorization") -> None:
        self._token_header_name = token_header_name

    def normalize_json(self, data: str, headers: Mapping[str, str] | None = None) -> str:
        """Concatenate JSON data with token, requestTraceId, and timestamp headers."""
        if not data or not headers:
            return data or ""

        parts = [data]
        keys = [
            self._token_header_name,
            "requestTraceId",
            "timestamp",
        ]

        # Case-insensitive header lookup
        header_lookup = {k.lower(): v for k, v in headers.items()}
        for key in keys:
            val = header_lookup.get(key.lower())
            if val is not None:
                parts.append(val)

        return "".join(parts)

    def normalize(self, data: Any, headers: Mapping[str, str] | None = None) -> str:
        """Serialize data to JSON and normalize with headers."""
        json_str = serialize(data)
        return self.normalize_json(json_str, headers)
