"""PEM/DER certificate and RSA private-key loaders."""

from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tax_collect_data.exceptions import CertificateError


def load_certificate(path: str) -> x509.Certificate:
    if not path or not path.strip():
        raise ValueError("certificate path cannot be empty")
    file_path = Path(path)
    if not file_path.is_file():
        raise CertificateError(f"Certificate file not found: {path}")
    data = file_path.read_bytes()
    try:
        if data.lstrip().startswith(b"-----BEGIN CERTIFICATE-----"):
            return x509.load_pem_x509_certificate(data)
        return x509.load_der_x509_certificate(data)
    except Exception as exc:
        raise CertificateError(f"Failed to load certificate from {path}") from exc


def load_private_key(path: str, password: bytes | None = None) -> rsa.RSAPrivateKey:
    if not path or not path.strip():
        raise ValueError("private key path cannot be empty")
    file_path = Path(path)
    if not file_path.is_file():
        raise CertificateError(f"Private key file not found: {path}")
    try:
        key = serialization.load_pem_private_key(file_path.read_bytes(), password=password)
    except Exception as exc:
        raise CertificateError(f"Failed to load private key from {path}") from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise CertificateError("Private key is not an RSA key")
    return key
