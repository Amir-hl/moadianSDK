"""Public SDK facade. This port is under active implementation."""

from __future__ import annotations

from tax_collect_data.config import TaxSdkOptions
from tax_collect_data.crypto.certificate_loader import load_certificate, load_private_key
from tax_collect_data.crypto.encryption_key_repository import EncryptionKeyRepository
from tax_collect_data.crypto.jwe_encryptor import JweEncryptor
from tax_collect_data.crypto.jws_signatory import JwsSignatory
from tax_collect_data.crypto.packet_service import PacketService
from tax_collect_data.http.api_client import TaxApiClient
from tax_collect_data.http.client import TaxHttpClient
from tax_collect_data.http.request_provider import RequestProvider
from tax_collect_data.http.url_provider import UrlProvider
from tax_collect_data.models import (
    InquiryByReferenceNumberDto,
    InquiryByTimeRangeDto,
    InquiryByUidDto,
    InvoiceDto,
    InvoiceResponseDto,
    InvoiceStatusDto,
    PacketDto,
    RegisterPaymentRequestDto,
)
from tax_collect_data.exceptions import CryptographyError


class TaxSdk:
    def __init__(
        self,
        options: TaxSdkOptions,
        api_client: TaxApiClient,
        http_client: TaxHttpClient,
        packet_service: PacketService,
        encryption_keys: EncryptionKeyRepository,
    ) -> None:
        self.options = options
        self._api = api_client
        self._http = http_client
        self._packets = packet_service
        self._keys = encryption_keys

    @classmethod
    def configure(cls, options: TaxSdkOptions) -> "TaxSdk":
        options.validate()
        if not options.private_key_path or not options.certificate_path:
            raise NotImplementedError(
                "PKCS#11 hardware-token signing is not implemented in this Python port yet"
            )
        certificate = load_certificate(options.certificate_path)
        private_key = load_private_key(options.private_key_path)
        signatory = JwsSignatory(certificate, private_key)
        url_provider = UrlProvider(options.base_url, options.api_version)
        request_provider = RequestProvider(url_provider)
        http_client = TaxHttpClient(
            options.client_id,
            signatory,
            timeout=options.request_timeout,
            custom_headers=options.custom_headers,
        )
        api_client = TaxApiClient(http_client, request_provider)

        async def get_key_records():
            server_info = await api_client.get_server_information()
            return [item.model_dump(by_alias=False) for item in server_info.PublicKeys]

        key_repository = EncryptionKeyRepository(get_key_records)
        encryptor = JweEncryptor(key_repository.get_key)
        packet_service = PacketService(options.client_id, signatory, encryptor)
        return cls(options, api_client, http_client, packet_service, key_repository)

    async def send_invoices(self, invoices: list[InvoiceDto]) -> list[InvoiceResponseDto]:
        if not invoices:
            raise ValueError("invoices cannot be empty")
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
                TaxId=tax_ids_by_trace.get(item.Uid, ""),
            )
            for item in response.Result
        ]

    async def get_invoice_status(self, tax_ids: list[str]) -> list[InvoiceStatusDto]:
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

    async def inquiry_by_time(self, dto: InquiryByTimeRangeDto):
        return await self._api.inquiry_by_time(dto)

    async def inquiry_by_uid(self, dto: InquiryByUidDto):
        return await self._api.inquiry_by_uid(dto)

    async def inquiry_by_reference_id(self, dto: InquiryByReferenceNumberDto):
        return await self._api.inquiry_by_reference_id(dto)

    async def get_taxpayer(self, economic_code: str):
        return await self._api.get_taxpayer(economic_code)

    async def register_payment(self, request: RegisterPaymentRequestDto):
        return await self._api.register_payment(request)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "TaxSdk":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
