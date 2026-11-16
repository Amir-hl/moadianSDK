"""PEM/DER certificate and RSA private-key loaders.

Supports loading from filesystem paths as well as in-memory strings or raw bytes
(essential for SaaS applications storing keys in database fields).
"""

from __future__ import annotations

from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tax_collect_data.exceptions import CertificateError


def load_certificate_from_string(data: str | bytes) -> x509.Certificate:
    """Load an X.509 certificate from in-memory PEM string, base64 text, or DER bytes."""
    if not data:
        raise ValueError("certificate data cannot be empty")

    if isinstance(data, bytes):
        raw = data
    else:
        raw = data.strip().encode("utf-8")

    if b"-----BEGIN CERTIFICATE-----" in raw:
        try:
            return x509.load_pem_x509_certificate(raw)
        except Exception as exc:
            raise CertificateError("Failed to parse PEM certificate from provided data") from exc

    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data.strip()
    if "-----BEGIN" not in text:
        pem_cert = f"-----BEGIN CERTIFICATE-----\n{text}\n-----END CERTIFICATE-----".encode("utf-8")
        try:
            return x509.load_pem_x509_certificate(pem_cert)
        except Exception:
            pass

    try:
        return x509.load_der_x509_certificate(raw)
    except Exception as exc:
        raise CertificateError("Failed to parse certificate from provided data") from exc


def load_private_key_from_string(
    data: str | bytes, password: bytes | str | None = None
) -> rsa.RSAPrivateKey:
    """Load an RSA private key from in-memory PEM string, base64 text, or DER bytes.

    Automatically handles keys with or without BEGIN/END headers, PKCS#1 and PKCS#8,
    and optional passwords.
    """
    if not data:
        raise ValueError("private key data cannot be empty")

    if isinstance(password, str):
        password = password.encode("utf-8")

    if isinstance(data, bytes):
        raw = data
    else:
        raw = data.strip().encode("utf-8")

    # 1. Try loading directly as standard PEM
    try:
        key = serialization.load_pem_private_key(raw, password=password)
        if isinstance(key, rsa.RSAPrivateKey):
            return key
        raise CertificateError("Private key is not an RSA key")
    except CertificateError:
        raise
    except Exception:
        pass

    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data.strip()

    # 2. If missing PEM headers, wrap as PKCS#8 or PKCS#1
    if "-----BEGIN" not in text:
        # Try PKCS#8 header
        pkcs8_pem = f"-----BEGIN PRIVATE KEY-----\n{text}\n-----END PRIVATE KEY-----".encode("utf-8")
        try:
            key = serialization.load_pem_private_key(pkcs8_pem, password=password)
            if isinstance(key, rsa.RSAPrivateKey):
                return key
        except Exception:
            pass

        # Try PKCS#1 RSA header
        pkcs1_pem = f"-----BEGIN RSA PRIVATE KEY-----\n{text}\n-----END RSA PRIVATE KEY-----".encode("utf-8")
        try:
            key = serialization.load_pem_private_key(pkcs1_pem, password=password)
            if isinstance(key, rsa.RSAPrivateKey):
                return key
        except Exception:
            pass

    # 3. Try DER format
    try:
        key = serialization.load_der_private_key(raw, password=password)
        if isinstance(key, rsa.RSAPrivateKey):
            return key
    except Exception:
        pass

    raise CertificateError("Failed to parse RSA private key from provided data")


def load_certificate(source: str) -> x509.Certificate:
    """Load certificate from either a file path or an in-memory PEM string."""
    if not source or not source.strip():
        raise ValueError("certificate source cannot be empty")

    file_path = Path(source)
    if file_path.is_file():
        return load_certificate_from_string(file_path.read_bytes())

    # If it's not a file on disk, check if it is direct PEM content
    if "-----BEGIN" in source or len(source) > 64:
        return load_certificate_from_string(source)

    raise CertificateError(f"Certificate file not found: {source}")


def load_private_key(source: str, password: bytes | str | None = None) -> rsa.RSAPrivateKey:
    """Load RSA private key from either a file path or an in-memory PEM string."""
    if not source or not source.strip():
        raise ValueError("private key source cannot be empty")

    file_path = Path(source)
    if file_path.is_file():
        return load_private_key_from_string(file_path.read_bytes(), password=password)

    # If it's not a file on disk, check if it is direct PEM/base64 content
    if "-----BEGIN" in source or len(source) > 64:
        return load_private_key_from_string(source, password=password)

    raise CertificateError(f"Private key file not found: {source}")

