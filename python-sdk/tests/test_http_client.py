import httpx
import pytest

from tax_collect_data.http.client import TaxHttpClient
from tax_collect_data.models import ServerInformationDto


class FakeSignatory:
    def sign(self, data):
        return "signed-token"


@pytest.mark.asyncio
async def test_transport_fetches_nonce_then_calls_api():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/nonce"):
            return httpx.Response(200, json={"nonce": "nonce-value", "expDate": "later"})
        return httpx.Response(200, json={"serverTime": 123, "publicKeys": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = TaxHttpClient("A111YO", FakeSignatory(), client=client)
        result = await transport.send(
            "GET",
            {"url": "https://api.example.test/api/v2/server-information"},
            ServerInformationDto,
        )

    assert result.ServerTime == 123
    assert calls[0].url.path.endswith("/nonce")
    assert calls[1].headers["Authorization"] == "Bearer signed-token"


from unittest.mock import AsyncMock, Mock

from tax_collect_data.http.api_client import TaxApiClient
from tax_collect_data.models import (
    Article6StatusDto,
    Article6StatusRequestDto,
    FiscalFullInformationDto,
    TaxpayerInfoDto,
)


@pytest.mark.asyncio
async def test_get_fiscal_information():
    expected = FiscalFullInformationDto(
        NameTrade="Test Business",
        FiscalStatus="Active",
    )

    http = Mock()
    http.send = AsyncMock(return_value=expected)

    requests = Mock()
    requests.fiscal_information.return_value = (
        "GET",
        {"url": "https://api.example.test/api/v2/fiscal-information"},
    )

    api = TaxApiClient(http, requests)
    result = await api.get_fiscal_information("MEMORY-123")

    assert result is expected
    requests.fiscal_information.assert_called_once_with("MEMORY-123")
    http.send.assert_awaited_once_with(
        "GET",
        {"url": "https://api.example.test/api/v2/fiscal-information"},
        FiscalFullInformationDto,
    )


@pytest.mark.asyncio
async def test_get_taxpayer_info():
    expected = TaxpayerInfoDto(
        TaxpayerName="Test Taxpayer",
        TaxpayerProfileStatus=1,
    )

    http = Mock()
    http.send = AsyncMock(return_value=expected)

    requests = Mock()
    requests.taxpayer_info.return_value = (
        "GET",
        {"url": "https://api.example.test/api/v2/taxpayer-info"},
    )

    api = TaxApiClient(http, requests)
    result = await api.get_taxpayer_info("1234567890")

    assert result is expected
    requests.taxpayer_info.assert_called_once_with("1234567890")
    http.send.assert_awaited_once_with(
        "GET",
        {"url": "https://api.example.test/api/v2/taxpayer-info"},
        TaxpayerInfoDto,
    )


@pytest.mark.asyncio
async def test_get_taxpayer_article6_status():
    request_dto = Article6StatusRequestDto(
        EconomicCode="1234567890",
        VatValue=100000,
        Period=140501,
    )
    expected = Article6StatusDto(Article6RemainStatus=True)

    http = Mock()
    http.send = AsyncMock(return_value=expected)

    requests = Mock()
    requests.taxpayer_article6_status.return_value = (
        "GET",
        {"url": "https://api.example.test/api/v2/taxpayer-article6-status"},
    )

    api = TaxApiClient(http, requests)
    result = await api.get_taxpayer_article6_status(request_dto)

    assert result is expected
    requests.taxpayer_article6_status.assert_called_once_with(request_dto)
    http.send.assert_awaited_once_with(
        "GET",
        {"url": "https://api.example.test/api/v2/taxpayer-article6-status"},
        Article6StatusDto,
    )