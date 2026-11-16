"""Unit tests for API v1 protocol, in-memory key loading, and v1 transport."""

from __future__ import annotations

import base64
import json
from decimal import Decimal

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from tax_collect_data.config import TaxSdkOptions
from tax_collect_data.crypto.certificate_loader import (
    load_certificate_from_string,
    load_private_key_from_string,
)
from tax_collect_data.crypto.rsa_signatory import RsaSignatory
from tax_collect_data.crypto.v1_encryptor import V1Encryptor, parse_rsa_public_key, xor_bytes
from tax_collect_data.crypto.v1_normalizer import SimpleNormalizer
from tax_collect_data.http.v1_client import TaxV1Client
from tax_collect_data.models import BodyItemDto, HeaderDto, InvoiceDto
from tax_collect_data.sdk import TaxSdk


@pytest.fixture
def test_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()


def test_load_private_key_from_pem_string(test_rsa_key_pair):
    private_key, _ = test_rsa_key_pair
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pem_str = pem_bytes.decode("ascii")

    loaded_key = load_private_key_from_string(pem_str)
    assert isinstance(loaded_key, rsa.RSAPrivateKey)
    assert loaded_key.public_key().public_numbers() == private_key.public_key().public_numbers()


def test_load_private_key_from_raw_base64_string(test_rsa_key_pair):
    private_key, _ = test_rsa_key_pair
    der_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    b64_str = base64.b64encode(der_bytes).decode("ascii")

    # Pass raw base64 without -----BEGIN PRIVATE KEY----- headers
    loaded_key = load_private_key_from_string(b64_str)
    assert isinstance(loaded_key, rsa.RSAPrivateKey)
    assert loaded_key.public_key().public_numbers() == private_key.public_key().public_numbers()


def test_load_private_key_with_password(test_rsa_key_pair):
    private_key, _ = test_rsa_key_pair
    password = "secret_password"
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    loaded_key = load_private_key_from_string(pem_bytes.decode("ascii"), password=password)
    assert isinstance(loaded_key, rsa.RSAPrivateKey)


def test_rsa_signatory_signs_and_verifies(test_rsa_key_pair):
    private_key, public_key = test_rsa_key_pair
    signatory = RsaSignatory(private_key, key_id="KEY-123")

    data = "test data to sign for moadian"
    signature_b64 = signatory.sign(data)

    sig_bytes = base64.b64decode(signature_b64)
    public_key.verify(
        sig_bytes,
        data.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    assert signatory.get_key_id() == "KEY-123"


def test_xor_bytes():
    data = b"Hello, World! 1234567890"
    key = b"ABC"  # length 3, cyclical
    xored = xor_bytes(data, key)
    assert len(xored) == len(data)

    # Double XOR restores original
    restored = xor_bytes(xored, key)
    assert restored == data


def test_v1_encryptor_encrypts_and_decrypts(test_rsa_key_pair):
    private_key, public_key = test_rsa_key_pair

    # Mock server public key provider
    server_key_id = "SERVER-KEY-01"
    encryptor = V1Encryptor(lambda: (server_key_id, public_key))

    test_payload = {"hello": "tax_world", "amount": 1000}
    aes_key = b"0123456789abcdef0123456789abcdef"  # 32 bytes
    iv = b"1234567890abcdef"  # 16 bytes

    ciphertext_b64 = encryptor.encrypt_payload(test_payload, aes_key, iv)
    ciphertext_with_tag = base64.b64decode(ciphertext_b64)

    # Decrypt with AES-GCM
    aesgcm = AESGCM(aes_key)
    decrypted_xor = aesgcm.decrypt(iv, ciphertext_with_tag, None)

    # Undo XOR
    decrypted_json_bytes = xor_bytes(decrypted_xor, aes_key)
    recovered = json.loads(decrypted_json_bytes.decode("utf-8"))
    assert recovered == test_payload

    # Test RSA symmetric key wrapping
    hex_key = aes_key.hex().upper()
    rsa_wrapped_b64 = encryptor.encrypt_data(hex_key, public_key)
    rsa_wrapped = base64.b64decode(rsa_wrapped_b64)

    unwrapped_hex = private_key.decrypt(
        rsa_wrapped,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    ).decode("utf-8")
    assert unwrapped_hex == hex_key


def test_simple_normalizer():
    normalizer = SimpleNormalizer(token_header_name="Authorization")
    json_data = '{"packets":[]}'
    headers = {
        "Authorization": "Bearer TEST_TOKEN",
        "requestTraceId": "TRACE-999",
        "timestamp": "1700000000000",
    }
    normalized = normalizer.normalize_json(json_data, headers)
    expected = json_data + "Bearer TEST_TOKEN" + "TRACE-999" + "1700000000000"
    assert normalized == expected


@pytest.mark.asyncio
async def test_v1_client_full_flow(test_rsa_key_pair):
    private_key, public_key = test_rsa_key_pair
    signatory = RsaSignatory(private_key)

    pub_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_b64 = base64.b64encode(pub_der).decode("ascii")

    # Create mock transport
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        assert "signature" in request.headers
        assert "requestTraceId" in request.headers
        assert "timestamp" in request.headers

        if url_str.endswith("GET_TOKEN"):
            return httpx.Response(
                200,
                json={
                    "timestamp": 1700000000000,
                    "result": {
                        "uid": "token-uid",
                        "packetType": "GET_TOKEN",
                        "data": {"token": "MOCK_TOKEN_123", "expiresIn": 3600},
                    },
                    "errors": [],
                },
            )
        elif url_str.endswith("GET_SERVER_INFORMATION"):
            return httpx.Response(
                200,
                json={
                    "timestamp": 1700000000000,
                    "result": {
                        "uid": "server-uid",
                        "packetType": "GET_SERVER_INFORMATION",
                        "data": {
                            "serverTime": 1700000000000,
                            "publicKeys": [
                                {
                                    "id": "TAX-KEY-1",
                                    "key": pub_b64,
                                    "algorithm": "RSA",
                                    "purpose": 1,
                                }
                            ],
                        },
                    },
                    "errors": [],
                },
            )
        elif url_str.endswith("normal-enqueue"):
            assert request.headers.get("Authorization") == "Bearer MOCK_TOKEN_123"
            req_data = json.loads(request.content.decode("utf-8"))
            packets = req_data.get("packets", [])
            assert len(packets) == 1
            pkt = packets[0]
            assert pkt["packetType"] == "INVOICE.V01"
            assert pkt["encryptionKeyId"] == "TAX-KEY-1"
            assert pkt["symmetricKey"] is not None
            assert pkt["iv"] is not None

            return httpx.Response(
                200,
                json={
                    "timestamp": 1700000000000,
                    "result": [
                        {
                            "uid": pkt["uid"],
                            "referenceNumber": "REF-INV-100",
                            "errorCode": None,
                            "errorDetail": None,
                        }
                    ],
                    "errors": [],
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    async_client = httpx.AsyncClient(transport=transport)

    v1_client = TaxV1Client(
        base_url="https://tax.example.com",
        client_id="A11216",
        signatory=signatory,
        client=async_client,
    )

    # 1. Request token
    token = await v1_client.request_token()
    assert token.token == "MOCK_TOKEN_123"

    # 2. Server info
    server_info = await v1_client.get_server_information()
    assert len(server_info.PublicKeys) == 1

    # 3. Send invoice
    invoice = InvoiceDto(
        Header=HeaderDto(
            taxid="A112160000100000000018",
            indatim=1700000000000,
            ins=1,
            inno="1",
        ),
        Body=[
            BodyItemDto(
                sstid="1111111111",
                sstt="کالای آزمایشی",
                mu="164",
                am=Decimal("2"),
                fee=Decimal("100000"),
            )
        ],
    )

    responses = await v1_client.send_invoices([invoice])
    assert len(responses) == 1
    assert responses[0].ReferenceNumber == "REF-INV-100"
    assert responses[0].TaxId == "A112160000100000000018"

    await v1_client.aclose()


@pytest.mark.asyncio
async def test_tax_sdk_configure_v1_with_in_memory_key(test_rsa_key_pair):
    private_key, _ = test_rsa_key_pair
    pem_str = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    options = TaxSdkOptions(
        base_url="https://tax.example.com",
        client_id="A11216",
        api_version="v1",
        private_key=pem_str,  # In-memory text!
    )

    sdk = TaxSdk.configure(options)
    assert sdk._v1 is not None
    assert sdk.v1._client_id == "A11216"
    assert sdk.options.api_version == "v1"
    await sdk.aclose()
