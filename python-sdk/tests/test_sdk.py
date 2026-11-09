import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tax_collect_data.config import TaxSdkOptions
from tax_collect_data.crypto.encryption_key_repository import (
    EncryptionKeyRepository,
)
from tax_collect_data.crypto.packet_service import PacketService
from tax_collect_data.sdk import TaxSdk


def test_configure_builds_sdk_and_wires_dependencies(tmp_path):
    private_key_path = tmp_path / "private.pem"
    certificate_path = tmp_path / "certificate.pem"

    private_key_path.write_text("mock private key")
    certificate_path.write_text("mock certificate")

    options = TaxSdkOptions(
        base_url="https://example.com",
        client_id="A111YO",
        private_key_path=str(private_key_path),
        certificate_path=str(certificate_path),
        request_timeout=30,
        api_version="v2",
        custom_headers={"X-Custom": "test"},
        authorization_header_name="X-Tax-Authorization",
    )

    public_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    ).public_key()

    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    key_record = {
        "Id": "test-key-id",
        "Key": base64.b64encode(public_key_der).decode("ascii"),
    }

    api_client = MagicMock()
    api_client.get_server_information = AsyncMock(
        return_value=SimpleNamespace(
            PublicKeys=[
                SimpleNamespace(
                    model_dump=lambda by_alias=False: key_record
                )
            ]
        )
    )

    http_client = MagicMock()

    with (
        patch("tax_collect_data.sdk.load_certificate", return_value=MagicMock()),
        patch("tax_collect_data.sdk.load_private_key", return_value=MagicMock()),
        patch("tax_collect_data.sdk.JwsSignatory", return_value=MagicMock()),
        patch("tax_collect_data.sdk.UrlProvider"),
        patch("tax_collect_data.sdk.RequestProvider"),
        patch(
            "tax_collect_data.sdk.TaxHttpClient",
            return_value=http_client,
        ) as http_client_factory,
        patch(
            "tax_collect_data.sdk.TaxApiClient",
            return_value=api_client,
        ) as api_client_factory,
    ):
        sdk = TaxSdk.configure(options)

    assert isinstance(sdk, TaxSdk)
    assert sdk.options is options
    assert sdk._api is api_client
    assert sdk._http is http_client
    assert isinstance(sdk._keys, EncryptionKeyRepository)
    assert isinstance(sdk._packets, PacketService)

    http_client_factory.assert_called_once()
    api_client_factory.assert_called_once()

    assert http_client_factory.call_args.kwargs["timeout"] == 30
    assert (
        http_client_factory.call_args.kwargs["custom_headers"]
        == {"X-Custom": "test"}
    )
    assert (
        http_client_factory.call_args.kwargs["authorization_header_name"]
        == "X-Tax-Authorization"
    )

def test_configured_sdk_loads_encryption_key(tmp_path):
    public_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    ).public_key()

    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    key_record = {
        "Id": "test-key-id",
        "Key": base64.b64encode(public_key_der).decode("ascii"),
    }

    api_client = MagicMock()
    api_client.get_server_information = AsyncMock(
        return_value=SimpleNamespace(
            PublicKeys=[
                SimpleNamespace(
                    model_dump=lambda by_alias=False: key_record
                )
            ]
        )
    )

    http_client = MagicMock()
    private_key_path = tmp_path / "private_key.pem"
    certificate_path = tmp_path / "certificate.pem"

    private_key_path.write_text("dummy private key")
    certificate_path.write_text("dummy certificate")
    options = TaxSdkOptions(
        base_url="https://example.com",
        client_id="A111YO",
        private_key_path=str(private_key_path),
        certificate_path=str(certificate_path),
    )

    with (
        patch("tax_collect_data.sdk.load_certificate", return_value=MagicMock()),
        patch("tax_collect_data.sdk.load_private_key", return_value=MagicMock()),
        patch("tax_collect_data.sdk.JwsSignatory", return_value=MagicMock()),
        patch("tax_collect_data.sdk.UrlProvider"),
        patch("tax_collect_data.sdk.RequestProvider"),
        patch("tax_collect_data.sdk.TaxHttpClient", return_value=http_client),
        patch("tax_collect_data.sdk.TaxApiClient", return_value=api_client),
    ):
        sdk = TaxSdk.configure(options)

        asyncio.run(sdk._keys.refresh_if_needed())
        key_id, public_key = sdk._keys.get_key()

    assert key_id == "test-key-id"
    assert isinstance(public_key, rsa.RSAPublicKey)
    api_client.get_server_information.assert_awaited_once()
