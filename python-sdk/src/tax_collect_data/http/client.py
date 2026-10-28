"""Authenticated async HTTP transport for the tax API."""

from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter

from tax_collect_data.crypto.jws_signatory import JwsSignatory
from tax_collect_data.exceptions import TaxApiError, UnknownResponseError
from tax_collect_data.serialization import serialize

T = TypeVar("T")


class TaxHttpClient:
    def __init__(
        self,
        client_id: str,
        signatory: JwsSignatory,
        *,
        timeout: float = 600.0,
        custom_headers: dict[str, str] | None = None,
        authorization_header_name: str = "Authorization",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not client_id or not client_id.strip():
            raise ValueError("client_id cannot be empty")
        if not authorization_header_name or not authorization_header_name.strip():
            raise ValueError("authorization_header_name cannot be empty")
        self._client_id = client_id
        self._signatory = signatory
        self._timeout = timeout
        self._custom_headers = dict(custom_headers or {})
        self._authorization_header_name = authorization_header_name.strip()
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def send(
        self,
        method: str,
        request_kwargs: dict[str, Any],
        response_type: type[T] | TypeAdapter,
    ) -> T:
        url = request_kwargs.get("url")
        if not url:
            raise ValueError("request_kwargs must include url")

        # The source SDK obtains a fresh nonce and signs { nonce, clientId }
        # before each protected API request. Custom headers also apply to nonce.
        nonce_response = await self._client.get(
            url.rsplit("/", 1)[0] + "/nonce",
            headers=self._custom_headers,
        )
        self._raise_for_api_error(nonce_response)
        nonce_body = nonce_response.json()
        nonce = nonce_body.get("nonce")
        if not nonce:
            raise UnknownResponseError("Nonce response did not include a nonce")
        authorization = self._signatory.sign(serialize({"nonce": nonce, "clientId": self._client_id}))

        kwargs = {key: value for key, value in request_kwargs.items() if key != "url"}
        headers = dict(self._custom_headers)
        headers.update(kwargs.pop("headers", {}) or {})
        headers.update({
            self._authorization_header_name: f"Bearer {authorization}",
            "Accept": "application/json",
            "Accept-Charset": "utf-8",
        })
        response = await self._client.request(method, url, headers=headers, **kwargs)
        self._raise_for_api_error(response)
        try:
            payload = response.json()
            if isinstance(response_type, TypeAdapter):
                return response_type.validate_python(payload)
            if isinstance(response_type, type) and issubclass(response_type, BaseModel):
                return response_type.model_validate(payload)
            return payload
        except Exception as exc:
            raise UnknownResponseError("Could not parse tax API response") from exc

    @staticmethod
    def _raise_for_api_error(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            body = response.json()
        except ValueError:
            body = {}
        errors = body.get("errors") or []
        first_error = errors[0] if errors else {}
        message = first_error.get("message") or body.get("message") or response.text
        raise TaxApiError(
            f"Tax API request failed: {message}",
            status_code=response.status_code,
            error_code=first_error.get("code"),
            error_message=message,
        )
