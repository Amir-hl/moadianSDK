import base64
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from tax_collect_data.crypto.jws_signatory import JwsSignatory
from tax_collect_data.exceptions import CryptographyError
from tax_collect_data.serialization import JsonSerializer


def create_certificate():
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "test")
    ])

    now = datetime.now(timezone.utc)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )

    return cert, key


def decode_part(part: str):
    padded = part + "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def test_jws_signs_json_payload():
    cert, key = create_certificate()

    token = JwsSignatory(cert, key).sign(
        json.dumps({"nonce": "n1", "clientId": "A111YO"})
    )

    parts = token.split(".")

    assert len(parts) == 3
    assert all(parts)

    header = decode_part(parts[0])
    payload = decode_part(parts[1])

    assert header["alg"] == "RS256"
    assert header["crit"] == ["sigT"]
    assert header["typ"] == "jose"
    assert header["cty"] == "text/plain"
    assert payload == {"nonce": "n1", "clientId": "A111YO"}


def test_jws_signature_can_be_verified():
    cert, key = create_certificate()

    token = JwsSignatory(cert, key).sign({"clientId": "A111YO"})
    header_part, payload_part, signature_part = token.split(".")

    signing_input = f"{header_part}.{payload_part}".encode("ascii")

    signature = base64.urlsafe_b64decode(
        signature_part + "=" * (-len(signature_part) % 4)
    )

    cert.public_key().verify(
        signature,
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def test_jws_uses_injected_clock():
    cert, key = create_certificate()

    fixed_time = datetime(
        2026, 1, 2, 3, 4, 5,
        tzinfo=timezone.utc,
    )

    signatory = JwsSignatory(
        cert,
        key,
        clock=lambda: fixed_time,
    )

    token = signatory.sign({"test": True})
    header = decode_part(token.split(".")[0])

    assert header["sigT"] == "2026-01-02T03:04:05Z"


def test_jws_uses_injected_serializer():
    cert, key = create_certificate()
    serializer = JsonSerializer()

    signatory = JwsSignatory(
        cert,
        key,
        serializer=serializer,
    )

    token = signatory.sign({"amount": Decimal("123.45")})
    payload = decode_part(token.split(".")[1])

    assert payload["amount"] == 123.45


def test_jws_rejects_invalid_json_string():
    cert, key = create_certificate()

    with pytest.raises(CryptographyError):
        JwsSignatory(cert, key).sign("{invalid json}")


def test_jws_rejects_empty_or_whitespace_input():
    cert, key = create_certificate()
    signatory = JwsSignatory(cert, key)

    with pytest.raises(ValueError):
        signatory.sign("")

    with pytest.raises(ValueError):
        signatory.sign("   ")

    with pytest.raises(ValueError):
        signatory.sign(None)


def test_jws_rejects_mismatched_private_key():
    cert, _ = create_certificate()

    another_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    with pytest.raises(CryptographyError, match="does not match"):
        JwsSignatory(cert, another_key)


def test_jws_rejects_naive_clock_datetime():
    cert, key = create_certificate()

    signatory = JwsSignatory(
        cert,
        key,
        clock=lambda: datetime(2026, 1, 2, 3, 4, 5),
    )

    with pytest.raises(CryptographyError, match="timezone-aware"):
        signatory.sign({"test": True})