"""Packet encryption implementation for API v1 matching .NET DefaultEncryptor."""

from __future__ import annotations

import base64
import os
from typing import Any, Callable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from tax_collect_data.exceptions import CryptographyError
from tax_collect_data.serialization import serialize


def xor_bytes(b1: bytes, b2: bytes) -> bytes:
    """Cyclic XOR matching .NET PacketCodec.Xor / XorBlocks."""
    if not b1 or not b2:
        return b1 if b1 else b2
    if len(b1) < len(b2):
        smaller, bigger = b1, b2
    else:
        smaller, bigger = b2, b1
    smaller_len = len(smaller)
    return bytes(byte ^ smaller[i % smaller_len] for i, byte in enumerate(bigger))


def parse_rsa_public_key(key_b64: str) -> rsa.RSAPublicKey:
    """Parse RSA public key from Base64 DER or PEM string."""
    cleaned = key_b64.strip()
    raw = base64.b64decode(cleaned)

    # 1. Try DER SubjectPublicKeyInfo
    try:
        key = serialization.load_der_public_key(raw)
        if isinstance(key, rsa.RSAPublicKey):
            return key
    except Exception:
        pass

    # 2. Try PEM wrapped
    try:
        pem = f"-----BEGIN PUBLIC KEY-----\n{cleaned}\n-----END PUBLIC KEY-----".encode("ascii")
        key = serialization.load_pem_public_key(pem)
        if isinstance(key, rsa.RSAPublicKey):
            return key
    except Exception:
        pass

    # 3. Try PKCS#1 DER RSAPublicKey
    try:
        key = serialization.load_der_pkcs1_public_key(raw)
        if isinstance(key, rsa.RSAPublicKey):
            return key
    except Exception:
        pass

    raise CryptographyError("Failed to parse tax organization RSA public key")


class V1Encryptor:
    """Encryptor for API v1 matching .NET DefaultEncryptor.

    Uses AES-256-GCM with XOR-scrambled payload and RSA-OAEP-SHA256 encrypted AES key.
    """

    def __init__(
        self,
        key_provider: Callable[[], tuple[str, rsa.RSAPublicKey]],
    ) -> None:
        self._key_provider = key_provider

    def encrypt_data(self, string_to_be_encrypted: str, public_key: rsa.RSAPublicKey) -> str:
        """Encrypt hex AES key using RSA-OAEP-SHA256 matching .NET EncryptData."""
        try:
            encrypted = public_key.encrypt(
                string_to_be_encrypted.encode("utf-8"),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            return base64.b64encode(encrypted).decode("ascii")
        except Exception as exc:
            raise CryptographyError("Failed to encrypt symmetric key with server RSA public key") from exc

    def aes_encrypt(self, payload: bytes, key: bytes, iv: bytes) -> str:
        """AES-256-GCM encryption with 128-bit tag matching .NET AesEncrypt."""
        try:
            aesgcm = AESGCM(key)
            ciphertext_with_tag = aesgcm.encrypt(iv, payload, None)
            return base64.b64encode(ciphertext_with_tag).decode("ascii")
        except Exception as exc:
            raise CryptographyError("AES-GCM encryption failed") from exc

    def encrypt_payload(self, data: Any, aes_key: bytes, iv: bytes) -> str:
        """Serialize data to JSON, XOR with AES key, and encrypt with AES-256-GCM."""
        serialized = serialize(data).encode("utf-8")
        xored = xor_bytes(serialized, aes_key)
        return self.aes_encrypt(xored, aes_key, iv)

    def encrypt_packets(self, packets: list[Any]) -> list[Any]:
        """Encrypt a batch of packets using a shared AES key and IV, matching .NET Encrypt(List)."""
        if not packets:
            return []

        key_id, public_key = self._key_provider()
        aes_key = os.urandom(32)
        iv = os.urandom(16)

        string_to_be_encrypted = aes_key.hex().upper()
        rsa_encrypted_symmetric_key = self.encrypt_data(string_to_be_encrypted, public_key)
        iv_hex = iv.hex().upper()

        encrypted_packets = []
        for packet in packets:
            encrypted_data = self.encrypt_payload(packet.data, aes_key, iv)
            encrypted_packet = packet.model_copy(update={
                "data": encrypted_data,
                "encryptionKeyId": key_id,
                "symmetricKey": rsa_encrypted_symmetric_key,
                "iv": iv_hex,
            })
            encrypted_packets.append(encrypted_packet)

        return encrypted_packets

    def encrypt_single(self, packet: Any) -> Any:
        """Encrypt a single packet matching .NET Encrypt(PacketDto)."""
        key_id, public_key = self._key_provider()
        aes_key = os.urandom(32)
        iv = os.urandom(16)

        string_to_be_encrypted = aes_key.hex().upper()
        rsa_encrypted_symmetric_key = self.encrypt_data(string_to_be_encrypted, public_key)
        iv_hex = iv.hex().upper()

        encrypted_data = self.encrypt_payload(packet.data, aes_key, iv)
        return packet.model_copy(update={
            "data": encrypted_data,
            "encryptionKeyId": key_id,
            "symmetricKey": rsa_encrypted_symmetric_key,
            "iv": iv_hex,
        })
