"""JWS RS256 signer matching the source SDK's custom protected headers."""

import base64
from datetime import datetime, timezone
from typing import Any, Callable

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes

from tax_collect_data.exceptions import CryptographyError
from tax_collect_data.serialization import JsonSerializer


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class JwsSignatory:
    def __init__(
        self,
        certificate: x509.Certificate,
        private_key: rsa.RSAPrivateKey,
        serializer: JsonSerializer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._certificate = certificate
        self._private_key = private_key
        self._serializer = serializer or JsonSerializer()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

        self._validate_key_pair()

    def _validate_key_pair(self) -> None:
        """Ensure the private key belongs to the supplied certificate."""
        try:
            certificate_public_key = self._certificate.public_key()

            if not isinstance(certificate_public_key, rsa.RSAPublicKey):
                raise CryptographyError(
                    "The certificate must contain an RSA public key"
                )

            if (
                certificate_public_key.public_numbers()
                != self._private_key.public_key().public_numbers()
            ):
                raise CryptographyError(
                    "The private key does not match the certificate"
                )
        except CryptographyError:
            raise
        except Exception as exc:
            raise CryptographyError(
                "Failed to validate certificate and private key"
            ) from exc

    def _timestamp(self) -> str:
        now = self._clock()

        if now.tzinfo is None or now.utcoffset() is None:
            raise CryptographyError("The signing clock must return a timezone-aware datetime")

        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _payload_value(self, data: str | Any) -> Any:
        if isinstance(data, str):
            try:
                # Match the C# Sign(string) overload: parse JSON before signing.
                return self._serializer.deserialize(data)
            except Exception as exc:
                raise CryptographyError(
                    "JWS string input must contain valid JSON"
                ) from exc

        return data

    def sign(self, data: str | Any) -> str:
        if data is None or (isinstance(data, str) and not data.strip()):
            raise ValueError("data cannot be null or empty")

        try:
            payload = self._payload_value(data)

            cert_der = self._certificate.public_bytes(
                serialization.Encoding.DER
            )

            header = {
                "alg": "RS256",
                "x5c": [base64.b64encode(cert_der).decode("ascii")],
                "sigT": self._timestamp(),
                "typ": "jose",
                "crit": ["sigT"],
                "cty": "text/plain",
            }

            header_part = _b64url(
                self._serializer.serialize(header).encode("utf-8")
            )
            payload_part = _b64url(
                self._serializer.serialize(payload).encode("utf-8")
            )

            signing_input = f"{header_part}.{payload_part}".encode("ascii")

            signature = self._private_key.sign(
                signing_input,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )

            return f"{header_part}.{payload_part}.{_b64url(signature)}"

        except (ValueError, CryptographyError):
            raise
        except Exception as exc:
            raise CryptographyError("Failed to create JWS signature") from exc