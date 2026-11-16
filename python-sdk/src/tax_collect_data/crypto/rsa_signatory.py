"""RSA PKCS#1 v1.5 signatory matching .NET InMemorySignatory for API v1."""

from __future__ import annotations

import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from tax_collect_data.crypto.certificate_loader import load_private_key


class RsaSignatory:
    """Signatory for API v1 matching .NET InMemorySignatory.

    Signs data with RSA-SHA256 (PKCS#1 v1.5 padding) and outputs Base64.
    """

    def __init__(
        self,
        private_key: rsa.RSAPrivateKey | str,
        password: bytes | str | None = None,
        key_id: str | None = None,
    ) -> None:
        if isinstance(private_key, rsa.RSAPrivateKey):
            self._key = private_key
        else:
            self._key = load_private_key(private_key, password=password)
        self._key_id = key_id or ""

    def sign(self, data: str | bytes) -> str:
        """Sign text or bytes with RSA-SHA256 PKCS#1 v1.5 and return Base64 string."""
        if data is None:
            raise ValueError("data cannot be null")
        if isinstance(data, str):
            payload = data.encode("utf-8")
        else:
            payload = data

        signature = self._key.sign(
            payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def get_key_id(self) -> str:
        return self._key_id
