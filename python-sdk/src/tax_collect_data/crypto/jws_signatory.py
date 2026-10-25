"""JWS RS256 signer matching the source SDK's custom protected headers."""

import base64
import json
from datetime import datetime, timezone
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from tax_collect_data.exceptions import CryptographyError


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class JwsSignatory:
    def __init__(
        self,
        certificate: x509.Certificate,
        private_key: rsa.RSAPrivateKey,
    ) -> None:
        self._certificate = certificate
        self._private_key = private_key

    @staticmethod
    def _payload_value(data: str | Any) -> Any:
        if isinstance(data, str):
            try:
                # The C# implementation parses string input as JSON before signing.
                return json.loads(data)
            except json.JSONDecodeError as exc:
                raise CryptographyError("JWS string input must contain valid JSON") from exc
        return data

    def sign(self, data: str | Any) -> str:
        if data is None or data == "":
            raise ValueError("data cannot be null or empty")
        payload = self._payload_value(data)
        cert_der = self._certificate.public_bytes(__import__(
            "cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]
        ).Encoding.DER)
        header = {
            "alg": "RS256",
            "x5c": [base64.b64encode(cert_der).decode("ascii")],
            "sigT": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "typ": "jose",
            "crit": ["sigT"],
            "cty": "text/plain",
        }
        try:
            header_part = _b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
            payload_part = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
            signing_input = f"{header_part}.{payload_part}".encode("ascii")
            signature = self._private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            return f"{header_part}.{payload_part}.{_b64url(signature)}"
        except Exception as exc:
            raise CryptographyError("Failed to create JWS signature") from exc
