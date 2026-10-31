from datetime import datetime, timezone, timedelta

from tax_collect_data.http.request_provider import _format_datetime
from tax_collect_data.http.request_provider import RequestProvider
from tax_collect_data.http.url_provider import UrlProvider

from tax_collect_data.models import (
    Article6StatusRequestDto,
    InquiryByUidDto,
    Pageable,
    InquiryByTimeRangeDto,
    RequestStatus,
)


def test_inquiry_by_uid_preserves_repeated_uid_parameters():
    provider = RequestProvider(UrlProvider("https://api.example.test"))
    method, kwargs = provider.inquiry_by_uid(
        InquiryByUidDto(UidList=["uid-1", "uid-2"], FiscalId="A111YO")
    )
    assert method == "GET"
    assert kwargs["url"].endswith("/api/v2/inquiry-by-uid")
    assert kwargs["params"][:3] == [
        ("fiscalId", "A111YO"),
        ("uidList", "uid-1"),
        ("uidList", "uid-2"),
    ]


def test_inquiry_by_time_includes_pagination_and_status():
    provider = RequestProvider(UrlProvider("https://api.example.test"))
    method, kwargs = provider.inquiry_by_time(
        InquiryByTimeRangeDto(
            Start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            Pageable=Pageable(PageNumber=2, PageSize=25),
            Status=RequestStatus.SUCCESS,
        )
    )
    assert method == "GET"
    assert ("pageNumber", "2") in kwargs["params"]
    assert ("pageSize", "25") in kwargs["params"]
    assert ("status", "SUCCESS") in kwargs["params"]



def test_fiscal_information_request_uses_memory_id():
    provider = RequestProvider(UrlProvider("https://api.example.test"))
    method, kwargs = provider.fiscal_information("MEMORY-123")
    assert method == "GET"
    assert kwargs["url"].endswith("/api/v2/fiscal-information")
    assert kwargs["params"] == {"memoryId": "MEMORY-123"}


def test_taxpayer_info_request_uses_economic_code():
    provider = RequestProvider(UrlProvider("https://api.example.test"))
    method, kwargs = provider.taxpayer_info("1234567890")
    assert method == "GET"
    assert kwargs["url"].endswith("/api/v2/taxpayer-info")
    assert kwargs["params"] == {"economicCode": "1234567890"}


def test_taxpayer_article6_status_request_includes_all_query_fields():
    provider = RequestProvider(UrlProvider("https://api.example.test"))
    method, kwargs = provider.taxpayer_article6_status(
        Article6StatusRequestDto(
            EconomicCode="1234567890",
            VatValue=250000,
            Period=1405,
        )
    )
    assert method == "GET"
    assert kwargs["url"].endswith("/api/v2/taxpayer-article6-status")
    assert kwargs["params"] == {
        "economicCode": "1234567890",
        "vatValue": "250000",
        "period": "1405",
    }

def test_format_datetime_matches_dotnet_format_without_timezone():
    value = datetime(2026, 10, 31, 12, 30, 45, 123456)

    assert _format_datetime(value) == "2026-10-31T12:30:45.123456000"


def test_format_datetime_matches_dotnet_format_with_utc_timezone():
    value = datetime(
        2026, 10, 31, 12, 30, 45, 123456,
        tzinfo=timezone.utc,
    )

    assert _format_datetime(value) == "2026-10-31T12:30:45.123456000Z"


def test_format_datetime_matches_dotnet_format_with_positive_offset():
    value = datetime(
        2026, 10, 31, 12, 30, 45, 123456,
        tzinfo=timezone(timedelta(hours=3, minutes=30)),
    )

    assert _format_datetime(value) == "2026-10-31T12:30:45.123456000+03:30"