"""Cached server encryption-key provider."""

import base64
import random
import time
from collections.abc import Awaitable, Callable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tax_collect_data.exceptions import CryptographyError


class EncryptionKeyRepository:
    def __init__(
        self,
        key_list_provider: Callable[[], Awaitable[list[dict[str, object]]]],
        *,
        cache_seconds: int = 3600,
    ) -> None:
        self._provider = key_list_provider
        self._cache_seconds = cache_seconds
        self._expires_at = 0.0
        self._key_id: str | None = None
        self._key: rsa.RSAPublicKey | None = None
        self._lock = __import__("asyncio").Lock()

    async def refresh_if_needed(self) -> None:
        if self._key is not None and time.monotonic() < self._expires_at:
            return
        async with self._lock:
            if self._key is not None and time.monotonic() < self._expires_at:
                return
            records = await self._provider()
            if not records:
                raise CryptographyError("Tax API returned no public encryption keys")
            record = random.choice(records)
            try:
                key_data = base64.b64decode(str(record["Key"]), validate=True)
                public_key = serialization.load_der_public_key(key_data)
                if not isinstance(public_key, rsa.RSAPublicKey):
                    raise TypeError("server key is not RSA")
                key_id = str(record["Id"])
                if not key_id:
                    raise ValueError("server key ID is empty")
            except Exception as exc:
                raise CryptographyError("Could not load server encryption public key") from exc
            self._key_id = key_id
            self._key = public_key
            self._expires_at = time.monotonic() + self._cache_seconds

    def get_key(self) -> tuple[str, rsa.RSAPublicKey]:
        if self._key_id is None or self._key is None:
            raise CryptographyError("Encryption key has not been loaded; call refresh_if_needed first")
        return self._key_id, self._key
