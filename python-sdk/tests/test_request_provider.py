from datetime import datetime, timezone

from tax_collect_data.http.request_provider import RequestProvider
from tax_collect_data.http.url_provider import UrlProvider
from tax_collect_data.models import InquiryByUidDto, Pageable, InquiryByTimeRangeDto, RequestStatus


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
    assert ("status", "1") in kwargs["params"]
