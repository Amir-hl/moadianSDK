"""API URL builder ported from the C# implementation."""

from urllib.parse import urlparse


class UrlProvider:
    def __init__(self, base_url: str, api_version: str = "v2") -> None:
        if not base_url or not base_url.strip():
            raise ValueError("base_url cannot be null or empty")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if not api_version or not api_version.strip():
            raise ValueError("api_version cannot be null or empty")
        self._base_url = base_url.rstrip("/")
        self._api_version = api_version.strip("/")

    def get_url(self, endpoint: str) -> str:
        if not endpoint or not endpoint.strip():
            raise ValueError("endpoint cannot be null or empty")
        return f"{self._base_url}/api/{self._api_version}/{endpoint.lstrip('/')}"
