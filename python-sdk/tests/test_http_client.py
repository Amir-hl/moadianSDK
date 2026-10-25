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
