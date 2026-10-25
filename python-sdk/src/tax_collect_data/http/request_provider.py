"""Build HTTP requests using endpoints and query parameter names from the .NET SDK."""

from datetime import datetime
from urllib.parse import urlencode

from tax_collect_data.models import (
    InquiryByReferenceNumberDto,
    InquiryByTimeRangeDto,
    InquiryByUidDto,
    PacketDto,
    RegisterPaymentRequestDto,
    Article6StatusRequestDto,
)
from tax_collect_data.http.url_provider import UrlProvider
from tax_collect_data.serialization import serialize


def _format_datetime(value: datetime) -> str:
    # ISO 8601 with timezone when present. Confirm exact wire format against
    # official API/test fixtures before production use.
    return value.isoformat(timespec="microseconds")


class RequestProvider:
    def __init__(self, url_provider: UrlProvider) -> None:
        self._urls = url_provider

    def nonce(self) -> tuple[str, dict[str, str]]:
        return "GET", {"url": self._urls.get_url("nonce")}

    def server_information(self) -> tuple[str, dict[str, str]]:
        return "GET", {"url": self._urls.get_url("server-information")}

    def invoices(self, packets: list[PacketDto]) -> tuple[str, dict[str, object]]:
        return "POST", {
            "url": self._urls.get_url("invoice"),
            "json": [packet.to_api_dict() for packet in packets],
        }

    def inquiry_by_time(self, dto: InquiryByTimeRangeDto) -> tuple[str, dict[str, object]]:
        query: list[tuple[str, str]] = [("start", _format_datetime(dto.Start))]
        if dto.End is not None:
            query.append(("end", _format_datetime(dto.End)))
        if dto.Status is not None:
            query.append(("status", dto.Status.name))
        if dto.Pageable is not None:
            query.extend([
                ("pageNumber", str(dto.Pageable.PageNumber)),
                ("pageSize", str(dto.Pageable.PageSize)),
            ])
        return "GET", {"url": self._urls.get_url("inquiry"), "params": query}

    def inquiry_by_uid(self, dto: InquiryByUidDto) -> tuple[str, dict[str, object]]:
        query: list[tuple[str, str]] = [("fiscalId", dto.FiscalId)]
        query.extend(("uidList", uid) for uid in dto.UidList)
        if dto.Start is not None:
            query.append(("start", _format_datetime(dto.Start)))
        if dto.End is not None:
            query.append(("end", _format_datetime(dto.End)))
        return "GET", {"url": self._urls.get_url("inquiry-by-uid"), "params": query}

    def inquiry_by_reference_id(self, dto: InquiryByReferenceNumberDto) -> tuple[str, dict[str, object]]:
        query: list[tuple[str, str]] = [("referenceIds", ref) for ref in dto.ReferenceNumbers]
        if dto.Start is not None:
            query.append(("start", _format_datetime(dto.Start)))
        if dto.End is not None:
            query.append(("end", _format_datetime(dto.End)))
        return "GET", {"url": self._urls.get_url("inquiry-by-reference-id"), "params": query}

    def inquiry_invoice_status(self, tax_ids: list[str]) -> tuple[str, dict[str, object]]:
        return "GET", {
            "url": self._urls.get_url("inquiry-invoice-status"),
            "params": [("taxIds", tax_id) for tax_id in tax_ids],
        }

    def taxpayer(self, economic_code: str) -> tuple[str, dict[str, object]]:
        return "GET", {
            "url": self._urls.get_url("taxpayer"),
            "params": {"economicCode": economic_code},
        }

    def fiscal_information(self, memory_id: str) -> tuple[str, dict[str, object]]:
        return "GET", {
            "url": self._urls.get_url("fiscal-information"),
            "params": {"memoryId": memory_id},
        }

    def taxpayer_info(self, economic_code: str) -> tuple[str, dict[str, object]]:
        return "GET", {
            "url": self._urls.get_url("taxpayer-info"),
            "params": {"economicCode": economic_code},
        }

    def taxpayer_article6_status(
        self, request: Article6StatusRequestDto
    ) -> tuple[str, dict[str, object]]:
        return "GET", {
            "url": self._urls.get_url("taxpayer-article6-status"),
            "params": {
                "economicCode": request.EconomicCode,
                "vatValue": str(request.VatValue),
                "period": str(request.Period),
            },
        }

    def register_payment(self, request: RegisterPaymentRequestDto) -> tuple[str, dict[str, object]]:
        return "POST", {
            "url": self._urls.get_url("invoice-payment"),
            "content": serialize(request),
            "headers": {"Content-Type": "application/json; charset=utf-8"},
        }
