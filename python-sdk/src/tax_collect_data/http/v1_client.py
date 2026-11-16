"""API v1 HTTP transport and client matching .NET 0.0.30 (Token + Packet Protocol)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa

from tax_collect_data.crypto.rsa_signatory import RsaSignatory
from tax_collect_data.crypto.v1_encryptor import V1Encryptor, parse_rsa_public_key
from tax_collect_data.crypto.v1_normalizer import SimpleNormalizer
from tax_collect_data.exceptions import TaxApiError, UnknownResponseError
from tax_collect_data.models import (
    AsyncRequestDto,
    ErrorItemDto,
    GetTokenDto,
    InvoiceDto,
    InvoiceResponseDto,
    PublicKeyDto,
    ServerInformationDto,
    SyncRequestDto,
    TokenModel,
    V1AsyncResponseModel,
    V1PacketDto,
    V1SyncResponseModel,
)
from tax_collect_data.serialization import serialize


class TaxV1Client:
    """Complete client for API v1 matching .NET DefaultTaxApiClient and SimpleTransferApi."""

    def __init__(
        self,
        base_url: str,
        client_id: str,
        signatory: RsaSignatory,
        *,
        timeout: float = 600.0,
        custom_headers: Mapping[str, str] | None = None,
        authorization_header_name: str = "Authorization",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._signatory = signatory
        self._timeout = timeout
        self._custom_headers = dict(custom_headers or {})
        self._auth_header_name = authorization_header_name
        self._normalizer = SimpleNormalizer(authorization_header_name)
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

        # Server public key & encryption state
        self._server_key_id: str | None = None
        self._server_public_key: rsa.RSAPublicKey | None = None
        self._encryptor = V1Encryptor(self._get_server_key)

        # Token state
        self._token: TokenModel | None = None

    def _get_server_key(self) -> tuple[str, rsa.RSAPublicKey]:
        if not self._server_key_id or not self._server_public_key:
            raise TaxApiError("Server public key not initialized. Call get_server_information() first.")
        return self._server_key_id, self._server_public_key

    def set_server_key(self, key_id: str, public_key_b64: str) -> None:
        self._server_key_id = key_id
        self._server_public_key = parse_rsa_public_key(public_key_b64)

    def set_token(self, token: TokenModel | str) -> None:
        if isinstance(token, str):
            self._token = TokenModel(token=token)
        else:
            self._token = token

    def get_token(self) -> TokenModel | None:
        return self._token

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _resolve_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        return f"{self._base_url}/{clean_path}"

    async def _send_sync_packet(
        self,
        packet: V1PacketDto,
        path: str,
        *,
        encrypt: bool = False,
        sign_packet: bool = False,
    ) -> V1SyncResponseModel:
        """Send a single packet synchronously via SyncRequestDto matching .NET SendPacketAsync."""
        if sign_packet:
            packet_data_str = serialize(packet.data)
            packet = packet.model_copy(update={
                "dataSignature": self._signatory.sign(packet_data_str),
                "signatureKeyId": self._signatory.get_key_id(),
            })

        if encrypt:
            packet = self._encryptor.encrypt_single(packet)

        request_dto = SyncRequestDto(packet=packet)
        body_dict = request_dto.to_api_dict()
        body_json = serialize(body_dict)

        headers = self._build_headers(body_json)
        url = self._resolve_url(path)

        response = await self._client.post(
            url,
            content=body_json.encode("utf-8"),
            headers=headers,
        )
        return self._parse_sync_response(response)

    async def _send_async_packets(
        self,
        packets: list[V1PacketDto],
        path: str,
        *,
        encrypt: bool = True,
        sign_packets: bool = True,
    ) -> V1AsyncResponseModel:
        """Send a packet batch asynchronously via AsyncRequestDto matching .NET SendPacketsAsync."""
        prepared_packets = []
        for packet in packets:
            if sign_packets:
                packet_data_str = serialize(packet.data)
                packet = packet.model_copy(update={
                    "dataSignature": self._signatory.sign(packet_data_str),
                    "signatureKeyId": self._signatory.get_key_id(),
                })
            prepared_packets.append(packet)

        if encrypt:
            prepared_packets = self._encryptor.encrypt_packets(prepared_packets)

        request_dto = AsyncRequestDto(packets=prepared_packets)
        body_dict = request_dto.to_api_dict()
        body_json = serialize(body_dict)

        headers = self._build_headers(body_json)
        url = self._resolve_url(path)

        response = await self._client.post(
            url,
            content=body_json.encode("utf-8"),
            headers=headers,
        )
        return self._parse_async_response(response)

    def _build_headers(self, body_json: str) -> dict[str, str]:
        """Fill essential headers and compute transfer signature matching .NET SimpleTransferApi."""
        now_ms = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        trace_id = str(uuid4())

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "requestTraceId": trace_id,
            "timestamp": now_ms,
        }

        if self._token and self._token.token:
            prefix = "Bearer " if self._auth_header_name.lower() == "authorization" else ""
            headers[self._auth_header_name] = f"{prefix}{self._token.token}"

        for k, v in self._custom_headers.items():
            headers[k] = v

        # Normalize and compute transfer signature
        normal_text = self._normalizer.normalize_json(body_json, headers)
        signature = self._signatory.sign(normal_text)
        headers["signature"] = signature

        key_id = self._signatory.get_key_id()
        if key_id:
            headers["signatureKeyId"] = key_id

        return headers

    def _parse_sync_response(self, response: httpx.Response) -> V1SyncResponseModel:
        if not response.is_success:
            self._raise_for_status(response)

        try:
            payload = response.json()
            model = V1SyncResponseModel.model_validate(payload)
            if model.errors:
                err_msg = model.errors[0].Message or model.errors[0].Code or "Tax API returned errors"
                raise TaxApiError(err_msg)
            return model
        except TaxApiError:
            raise
        except Exception as exc:
            raise UnknownResponseError(f"Could not parse sync response: {response.text}") from exc

    def _parse_async_response(self, response: httpx.Response) -> V1AsyncResponseModel:
        if not response.is_success:
            self._raise_for_status(response)

        try:
            payload = response.json()
            model = V1AsyncResponseModel.model_validate(payload)
            if model.errors:
                err_msg = model.errors[0].Message or model.errors[0].Code or "Tax API returned errors"
                raise TaxApiError(err_msg)
            return model
        except TaxApiError:
            raise
        except Exception as exc:
            raise UnknownResponseError(f"Could not parse async response: {response.text}") from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            body = response.json()
            errors = body.get("errors") or []
            if errors and isinstance(errors, list):
                first = errors[0]
                msg = first.get("message") or first.get("detail") or first.get("code")
                if msg:
                    raise TaxApiError(f"API Error ({response.status_code}): {msg}")
        except TaxApiError:
            raise
        except Exception:
            pass
        raise TaxApiError(f"HTTP request failed with status {response.status_code}: {response.text}")

    # --- Public High-Level Operations ---

    async def request_token(self) -> TokenModel:
        """Acquire authentication token from /self-tsp/sync/GET_TOKEN."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="GET_TOKEN",
            fiscal_id=self._client_id,
            data={"username": self._client_id},
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/GET_TOKEN",
            encrypt=False,
            sign_packet=False,
        )
        if not response.result or not response.result.data:
            raise TaxApiError("Failed to obtain token from tax authority")

        data = response.result.data
        token = data.get("token") if isinstance(data, dict) else getattr(data, "token", "")
        expires_in = data.get("expiresIn", 0) if isinstance(data, dict) else getattr(data, "expires_in", 0)

        self._token = TokenModel(token=token, expires_in=expires_in)
        return self._token

    async def get_server_information(self) -> ServerInformationDto:
        """Retrieve server public keys and time from /self-tsp/sync/GET_SERVER_INFORMATION."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="GET_SERVER_INFORMATION",
            fiscal_id=self._client_id,
            data=None,
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/GET_SERVER_INFORMATION",
            encrypt=False,
            sign_packet=False,
        )
        if not response.result or not response.result.data:
            raise TaxApiError("Failed to obtain server information")

        data = response.result.data
        server_time = data.get("serverTime", 0) if isinstance(data, dict) else getattr(data, "server_time", 0)
        raw_keys = data.get("publicKeys", []) if isinstance(data, dict) else getattr(data, "public_keys", [])

        keys = []
        for k in raw_keys:
            if isinstance(k, dict):
                keys.append(PublicKeyDto(
                    Id=k.get("id", ""),
                    Key=k.get("key", ""),
                    Algorithm=k.get("algorithm"),
                    Purpose=k.get("purpose"),
                ))
            elif isinstance(k, PublicKeyDto):
                keys.append(k)

        info = ServerInformationDto(ServerTime=server_time, PublicKeys=keys)
        if info.PublicKeys:
            active_key = info.PublicKeys[0]
            self.set_server_key(active_key.Id, active_key.Key)
        return info

    async def ensure_ready(self) -> None:
        """Ensure token and server public keys are acquired."""
        if not self._token:
            await self.request_token()
        if not self._server_public_key:
            await self.get_server_information()

    async def send_invoices(self, invoices: list[InvoiceDto]) -> list[InvoiceResponseDto]:
        """Send invoice batch matching .NET SendInvoices / SendInvoicesAsync."""
        if not invoices:
            raise ValueError("invoices cannot be empty")

        await self.ensure_ready()

        packets = []
        uid_to_taxid: dict[str, str] = {}
        for invoice in invoices:
            uid = str(uuid4())
            tax_id = invoice.Header.taxid
            uid_to_taxid[uid] = tax_id

            packet = V1PacketDto(
                uid=uid,
                packet_type="INVOICE.V01",
                fiscal_id=self._client_id,
                data=invoice.to_api_dict(),
            )
            packets.append(packet)

        response = await self._send_async_packets(
            packets,
            "self-tsp/async/normal-enqueue",
            encrypt=True,
            sign_packets=True,
        )

        results = []
        for item in response.result:
            tax_id = uid_to_taxid.get(item.uid or "", "")
            results.append(InvoiceResponseDto(
                Data=item.error_detail or None,
                Uid=item.uid,
                ReferenceNumber=item.reference_number,
                TaxId=tax_id,
            ))
        return results

    async def inquiry_by_uid(
        self, uid_list: list[str], fiscal_id: str | None = None
    ) -> Any:
        """Inquiry invoice status by UID list."""
        fid = fiscal_id or self._client_id
        items = [{"uid": uid, "fiscalId": fid} for uid in uid_list]
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="INQUIRY_BY_UID",
            fiscal_id=self._client_id,
            data=items,
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/INQUIRY_BY_UID",
            encrypt=False,
            sign_packet=False,
        )
        return response.result.data if response.result else None

    async def inquiry_by_reference_id(self, reference_numbers: list[str]) -> Any:
        """Inquiry invoice status by server reference numbers."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="INQUIRY_BY_REFERENCE_NUMBER",
            fiscal_id=self._client_id,
            data=reference_numbers,
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/INQUIRY_BY_REFERENCE_NUMBER",
            encrypt=False,
            sign_packet=False,
        )
        return response.result.data if response.result else None

    async def inquiry_by_time(self, persian_time: str) -> Any:
        """Inquiry by Persian date string (e.g. '14030825')."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="INQUIRY_BY_TIME",
            fiscal_id=self._client_id,
            data={"time": persian_time},
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/INQUIRY_BY_TIME",
            encrypt=False,
            sign_packet=False,
        )
        return response.result.data if response.result else None

    async def inquiry_by_time_range(
        self, start_date_persian: str, end_date_persian: str
    ) -> Any:
        """Inquiry by Persian date range (e.g. '14030801', '14030830')."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="INQUIRY_BY_TIME_RANGE",
            fiscal_id=self._client_id,
            data={"startDate": start_date_persian, "endDate": end_date_persian},
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/INQUIRY_BY_TIME_RANGE",
            encrypt=False,
            sign_packet=False,
        )
        return response.result.data if response.result else None

    async def get_fiscal_information(self, fiscal_id: str | None = None) -> Any:
        """Get fiscal memory info matching GET_FISCAL_INFORMATION."""
        fid = fiscal_id or self._client_id
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="GET_FISCAL_INFORMATION",
            fiscal_id=fid,
            data=fid,
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/GET_FISCAL_INFORMATION",
            encrypt=False,
            sign_packet=False,
        )
        return response.result.data if response.result else None

    async def get_economic_code_information(self, economic_code: str) -> Any:
        """Get economic code taxpayer info."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="GET_ECONOMIC_CODE_INFORMATION",
            fiscal_id=self._client_id,
            data={"economicCode": economic_code},
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/GET_ECONOMIC_CODE_INFORMATION",
            encrypt=False,
            sign_packet=False,
        )
        return response.result.data if response.result else None

    async def get_service_stuff_list(self, search_dto: dict[str, Any]) -> Any:
        """Query commodity/service stuff codes matching GET_SERVICE_STUFF_LIST."""
        packet = V1PacketDto(
            uid=str(uuid4()),
            packet_type="GET_SERVICE_STUFF_LIST",
            fiscal_id=self._client_id,
            data=search_dto,
        )
        response = await self._send_sync_packet(
            packet,
            "self-tsp/sync/GET_SERVICE_STUFF_LIST",
            encrypt=False,
            sign_packet=True,
        )
        return response.result.data if response.result else None
