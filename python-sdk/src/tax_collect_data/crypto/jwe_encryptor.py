"""Compact JWE encryption using RSA-OAEP-256 and A256GCM.

The caller supplies the active server public key and its key ID. Key retrieval and
rotation are intentionally separated from encryption.
"""

from typing import Callable

from cryptography.hazmat.primitives.asymmetric import rsa
from jwcrypto import jwk, jwe

from tax_collect_data.exceptions import CryptographyError


class JweEncryptor:
    def __init__(self, key_provider: Callable[[], tuple[str, rsa.RSAPublicKey]]) -> None:
        self._key_provider = key_provider

    def encrypt(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            raise ValueError("text cannot be null or empty")
        try:
            key_id, public_key = self._key_provider()
            public_jwk = jwk.JWK.from_pyca(public_key)
            protected = {
                "alg": "RSA-OAEP-256",
                "enc": "A256GCM",
                "kid": key_id,
            }
            token = jwe.JWE(
                plaintext=text.encode("utf-8"),
                protected=protected,
            )
            token.add_recipient(public_jwk)
            return token.serialize(compact=True)
        except Exception as exc:
            raise CryptographyError("Failed to encrypt payload as JWE") from exc
