import json

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, timezone

from tax_collect_data.crypto.jws_signatory import JwsSignatory


def test_jws_signs_json_payload():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    token = JwsSignatory(cert, key).sign(json.dumps({"nonce": "n1", "clientId": "A111YO"}))
    parts = token.split(".")
    assert len(parts) == 3
    assert all(parts)
    header = json.loads(__import__("base64").urlsafe_b64decode(parts[0] + "=="))
    assert header["alg"] == "RS256"
    assert header["crit"] == ["sigT"]
