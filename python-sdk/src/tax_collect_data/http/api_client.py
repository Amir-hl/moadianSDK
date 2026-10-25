"""High-level HTTP endpoint wrapper matching the source SDK."""

from pydantic import TypeAdapter

from tax_collect_data.http.client import TaxHttpClient
from tax_collect_data.http.request_provider import RequestProvider
from tax_collect_data.models import (
    Article6StatusDto,
    Article6StatusRequestDto,
    BatchResponseDto,
    FiscalFullInformationDto,
    InquiryByReferenceNumberDto,
    InquiryByTimeRangeDto,
    InquiryByUidDto,
    InquiryResultDto,
    InvoiceStatusInquiryResponseDto,
    RegisterPaymentRequestDto,
    RegisterPaymentResultDto,
    ServerInformationDto,
    TaxpayerDto,
    TaxpayerInfoDto,
)


class TaxApiClient:
    def __init__(self, http_client: TaxHttpClient, request_provider: RequestProvider) -> None:
        self._http = http_client
        self._requests = request_provider

    async def send_invoices(self, packets):
        method, request = self._requests.invoices(packets)
        return await self._http.send(method, request, BatchResponseDto)

    async def inquiry_by_time(self, dto: InquiryByTimeRangeDto) -> list[InquiryResultDto]:
        method, request = self._requests.inquiry_by_time(dto)
        return await self._http.send(method, request, TypeAdapter(list[InquiryResultDto]))

    async def inquiry_by_uid(self, dto: InquiryByUidDto) -> list[InquiryResultDto]:
        method, request = self._requests.inquiry_by_uid(dto)
        return await self._http.send(method, request, TypeAdapter(list[InquiryResultDto]))

    async def inquiry_by_reference_id(self, dto: InquiryByReferenceNumberDto) -> list[InquiryResultDto]:
        method, request = self._requests.inquiry_by_reference_id(dto)
        return await self._http.send(method, request, TypeAdapter(list[InquiryResultDto]))

    async def inquiry_invoice_status(self, tax_ids: list[str]) -> list[InvoiceStatusInquiryResponseDto]:
        if not tax_ids:
            raise ValueError("tax_ids cannot be empty")
        method, request = self._requests.inquiry_invoice_status(tax_ids)
        return await self._http.send(method, request, TypeAdapter(list[InvoiceStatusInquiryResponseDto]))

    async def get_taxpayer(self, economic_code: str) -> TaxpayerDto:
        method, request = self._requests.taxpayer(economic_code)
        return await self._http.send(method, request, TaxpayerDto)

    async def get_fiscal_information(self, memory_id: str) -> FiscalFullInformationDto:
        method, request = self._requests.fiscal_information(memory_id)
        return await self._http.send(method, request, FiscalFullInformationDto)

    async def get_taxpayer_info(self, economic_code: str) -> TaxpayerInfoDto:
        method, request = self._requests.taxpayer_info(economic_code)
        return await self._http.send(method, request, TaxpayerInfoDto)

    async def get_taxpayer_article6_status(
        self, request_dto: Article6StatusRequestDto
    ) -> Article6StatusDto:
        method, request = self._requests.taxpayer_article6_status(request_dto)
        return await self._http.send(method, request, Article6StatusDto)

    async def get_server_information(self) -> ServerInformationDto:
        method, request = self._requests.server_information()
        return await self._http.send(method, request, ServerInformationDto)

    async def register_payment(self, request_dto: RegisterPaymentRequestDto) -> RegisterPaymentResultDto:
        method, request = self._requests.register_payment(request_dto)
        return await self._http.send(method, request, RegisterPaymentResultDto)
