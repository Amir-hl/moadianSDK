import pytest

from tax_collect_data.http.url_provider import UrlProvider


def test_builds_api_url():
    provider = UrlProvider("https://api.example.test/", "v2")
    assert provider.get_url("/invoices") == "https://api.example.test/api/v2/invoices"


def test_rejects_empty_endpoint():
    with pytest.raises(ValueError):
        UrlProvider("https://api.example.test").get_url(" ")
