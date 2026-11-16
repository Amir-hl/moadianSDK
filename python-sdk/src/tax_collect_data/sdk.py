"""Public SDK facade supporting both API v1 (.NET 0.0.30) and API v2 (JWS/JWE)."""

from __future__ import annotations

from typing import Any

from tax_collect_data.config import TaxSdkOptions
from tax_collect_data.crypto.certificate_loader import load_certificate, load_private_key
from tax_collect_data.crypto.encryption_key_repository import EncryptionKeyRepository
from tax_collect_data.crypto.jwe_encryptor import JweEncryptor
from tax_collect_data.crypto.jws_signatory import JwsSignatory
from tax_collect_data.crypto.packet_service import PacketService
from tax_collect_data.crypto.rsa_signatory import RsaSignatory
from tax_collect_data.http.api_client import TaxApiClient
from tax_collect_data.http.client import TaxHttpClient
from tax_collect_data.http.request_provider import RequestProvider
from tax_collect_data.http.url_provider import UrlProvider
from tax_collect_data.http.v1_client import TaxV1Client
from tax_collect_data.models import (
    Article6StatusDto,
    Article6StatusRequestDto,
    FiscalFullInformationDto,
    InquiryByReferenceNumberDto,
    InquiryByTimeRangeDto,
    InquiryByUidDto,
    InvoiceDto,
    InvoiceResponseDto,
    InvoiceStatusDto,
    RegisterPaymentRequestDto,
    TaxpayerInfoDto,
)
from tax_collect_data.serialization import JsonSerializer


class TaxSdk:
    def __init__(
        self,
        options: TaxSdkOptions,
        api_client: TaxApiClient | None = None,
        http_client: TaxHttpClient | None = None,
        packet_service: PacketService | None = None,
        encryption_keys: EncryptionKeyRepository | None = None,
        v1_client: TaxV1Client | None = None,
    ) -> None:
        self.options = options
        self._api = api_client
        self._http = http_client
        self._packets = packet_service
        self._keys = encryption_keys
        self._v1 = v1_client

    @property
    def v1(self) -> TaxV1Client:
        """Access the underlying v1 client (when configured with api_version='v1')."""
        if self._v1 is None:
            raise ValueError("TaxSdk is not configured for API v1")
        return self._v1

    @property
    def v2(self) -> TaxApiClient:
        """Access the underlying v2 API client (when configured with api_version='v2')."""
        if self._api is None:
            raise ValueError("TaxSdk is not configured for API v2")
        return self._api

    @classmethod
    def configure(cls, options: TaxSdkOptions) -> "TaxSdk":
        options.validate()

        version = options.api_version.strip().lower()

        # --- API v1 Configuration ---
        if version == "v1":
            priv_source = options.private_key or options.private_key_path
            if not priv_source:
                raise ValueError("private_key or private_key_path is required for API v1")

            private_key = load_private_key(priv_source, password=options.private_key_password)
            signatory = RsaSignatory(private_key, key_id=options.signatory_key_id)

            v1_client = TaxV1Client(
                base_url=options.base_url,
                client_id=options.client_id,
                signatory=signatory,
                timeout=options.request_timeout,
                custom_headers=options.custom_headers,
                authorization_header_name=options.authorization_header_name,
            )
            return cls(options=options, v1_client=v1_client)

        # --- API v2 Configuration ---
        has_private_key = bool(
            (options.private_key and options.private_key.strip())
            or (options.private_key_path and options.private_key_path.strip())
        )
        has_cert = bool(
            (options.certificate and options.certificate.strip())
            or (options.certificate_path and options.certificate_path.strip())
        )

        if not (has_private_key and has_cert):
            raise NotImplementedError(
                "PKCS#11 hardware-token signing is not implemented "
                "in this Python port yet"
            )

        cert_source = options.certificate or options.certificate_path
        priv_source = options.private_key or options.private_key_path

        # Load signing credentials from file or in-memory text
        certificate = load_certificate(cert_source)  # type: ignore[arg-type]
        private_key = load_private_key(priv_source, password=options.private_key_password)  # type: ignore[arg-type]

        # Create shared dependencies
        serializer = JsonSerializer()
        signatory_v2 = JwsSignatory(
            certificate,
            private_key,
            serializer=serializer,
        )

        # Create HTTP infrastructure
        url_provider = UrlProvider(
            options.base_url,
            options.api_version,
        )
        request_provider = RequestProvider(url_provider)

        http_client = TaxHttpClient(
            options.client_id,
            signatory_v2,
            timeout=options.request_timeout,
            custom_headers=options.custom_headers,
            authorization_header_name=options.authorization_header_name,
        )

        api_client = TaxApiClient(
            http_client,
            request_provider,
        )

        # Create encryption key repository
        async def get_key_records():
            server_info = await api_client.get_server_information()
            return [
                item.model_dump(by_alias=False)
                for item in server_info.PublicKeys
            ]

        key_repository = EncryptionKeyRepository(get_key_records)
        encryptor = JweEncryptor(key_repository.get_key)

        packet_service = PacketService(
            client_id=options.client_id,
            signatory=signatory_v2,
            encryptor=encryptor,
            serializer=serializer,
        )

        return cls(
            options,
            api_client,
            http_client,
            packet_service,
            key_repository,
        )

    async def send_invoices(self, invoices: list[InvoiceDto]) -> list[InvoiceResponseDto]:
        if not invoices:
            raise ValueError("invoices cannot be empty")

        if self._v1 is not None:
            return await self._v1.send_invoices(invoices)

        assert self._keys is not None
        assert self._packets is not None
        assert self._api is not None

        await self._keys.refresh_if_needed()
        packets = [self._packets.create_invoice_packet(invoice) for invoice in invoices]
        response = await self._api.send_invoices(packets)
        tax_ids_by_trace = {
            packet.Header.RequestTraceId: invoice.Header.taxid
            for packet, invoice in zip(packets, invoices, strict=True)
        }
        return [
            InvoiceResponseDto(
                Data=item.Data,
                Uid=item.Uid,
                ReferenceNumber=item.ReferenceNumber,
                TaxId=tax_ids_by_trace[item.Uid],
            )
            for item in response.Result
        ]

    async def get_invoice_status(self, tax_ids: list[str]) -> list[InvoiceStatusDto]:
        if self._v1 is not None:
            results = await self._v1.inquiry_by_uid(tax_ids)
            if isinstance(results, list):
                return [
                    InvoiceStatusDto(
                        TaxId=getattr(item, "taxId", "") if hasattr(item, "taxId") else item.get("taxId", "") if isinstance(item, dict) else "",
                        InvoiceStatus=getattr(item, "status", "") if hasattr(item, "status") else item.get("status", "") if isinstance(item, dict) else "",
                    )
                    for item in results
                ]
            return []

        assert self._api is not None
        results = await self._api.inquiry_invoice_status(tax_ids)
        return [
            InvoiceStatusDto(
                TaxId=item.TaxId or "",
                InvoiceStatus=item.InvoiceStatus or "",
                Article6Status=item.Article6Status or "",
                Error=item.Error or "",
            )
            for item in results
        ]

    async def inquiry_by_time(self, dto: InquiryByTimeRangeDto) -> Any:
        if self._v1 is not None:
            return await self._v1.inquiry_by_time_range(
                dto.Start.strftime("%Y%m%d"),
                dto.End.strftime("%Y%m%d") if dto.End else dto.Start.strftime("%Y%m%d"),
            )
        assert self._api is not None
        return await self._api.inquiry_by_time(dto)

    async def inquiry_by_uid(self, dto: InquiryByUidDto) -> Any:
        if self._v1 is not None:
            return await self._v1.inquiry_by_uid(dto.UidList, fiscal_id=dto.FiscalId)
        assert self._api is not None
        return await self._api.inquiry_by_uid(dto)

    async def inquiry_by_reference_id(self, dto: InquiryByReferenceNumberDto) -> Any:
        if self._v1 is not None:
            return await self._v1.inquiry_by_reference_id(dto.ReferenceNumbers)
        assert self._api is not None
        return await self._api.inquiry_by_reference_id(dto)

    async def get_fiscal_information(self, memory_id: str) -> FiscalFullInformationDto:
        if self._v1 is not None:
            raw = await self._v1.get_fiscal_information(memory_id)
            if isinstance(raw, dict):
                return FiscalFullInformationDto.model_validate(raw)
            return FiscalFullInformationDto(EconomicCode=memory_id)
        assert self._api is not None
        return await self._api.get_fiscal_information(memory_id)

    async def get_taxpayer_info(self, economic_code: str) -> TaxpayerInfoDto:
        if self._v1 is not None:
            raw = await self._v1.get_economic_code_information(economic_code)
            if isinstance(raw, dict):
                return TaxpayerInfoDto.model_validate(raw)
            return TaxpayerInfoDto(TaxpayerName=economic_code)
        assert self._api is not None
        return await self._api.get_taxpayer_info(economic_code)

    async def get_taxpayer_article6_status(
        self, request: Article6StatusRequestDto
    ) -> Article6StatusDto:
        if self._v1 is not None:
            raise NotImplementedError("Article 6 status check is only available on API v2")
        assert self._api is not None
        return await self._api.get_taxpayer_article6_status(request)

    async def get_taxpayer(self, economic_code: str) -> Any:
        if self._v1 is not None:
            return await self._v1.get_economic_code_information(economic_code)
        assert self._api is not None
        return await self._api.get_taxpayer(economic_code)

    async def register_payment(self, request: RegisterPaymentRequestDto) -> Any:
        if self._v1 is not None:
            raise NotImplementedError("Payment registration is only available on API v2")
        assert self._api is not None
        return await self._api.register_payment(request)

    async def aclose(self) -> None:
        if self._v1 is not None:
            await self._v1.aclose()
        if self._http is not None:
            await self._http.aclose()

    async def __aenter__(self) -> "TaxSdk":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()
