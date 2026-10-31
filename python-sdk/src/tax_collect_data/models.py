"""Typed API models based on the source SDK DTOs.

Field names used by the tax API are retained. PascalCase C# properties are
serialized using lowerCamelCase aliases to match System.Text.Json defaults.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _camel_case(name: str) -> str:
    if "_" in name:
        first, *rest = name.split("_")
        return first + "".join(part[:1].upper() + part[1:] for part in rest)
    return name[:1].lower() + name[1:]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="ignore",
        validate_assignment=True,
    )

    def to_api_dict(self, *, exclude_none: bool = False) -> dict[str, Any]:
        return self.model_dump(
            by_alias=True,
            exclude_none=exclude_none,
        )


class PaymentMethod(IntEnum):
    CASH = 1
    CHEQUE = 2
    CREDIT_CARD = 3
    BANK_TRANSFER = 4
    OTHER = 5


class RequestStatus(IntEnum):
    SUCCESS = 1
    FAILED = 2
    PENDING = 3
_RequestStatus = RequestStatus

class ShippingGoodDto(ApiModel):
    sgid: str | None = None
    sgt: str | None = None


class HeaderDto(ApiModel):
    taxid: str = ""
    indatim: int
    ins: int
    indati2m: int | None = None
    inty: int | None = None
    ft: int | None = None
    inno: str | None = None
    irtaxid: str | None = None
    scln: str | None = None
    setm: int | None = None
    tins: str | None = None
    cap: int | None = None
    bid: str | None = None
    insp: int | None = None
    tvop: int | None = None
    bpc: str = ""
    tax17: int | None = None
    inp: int | None = None
    scc: str | None = None
    billid: str | None = None
    tprdis: int | None = None
    tdis: int | None = None
    tadis: int | None = None
    tvam: int | None = None
    todam: int | None = None
    tbill: int | None = None
    tob: int | None = None
    tinb: str | None = None
    sbc: str | None = None
    bbc: str | None = None
    bpn: str | None = None
    crn: str | None = None
    cdcn: str | None = None
    cdcd: int | None = None
    tonw: Decimal | None = None
    torv: int | None = None
    tocv: Decimal | None = None
    tinc: str | None = None
    lno: str | None = None
    lrno: str | None = None
    ocu: str | None = None
    oci: str | None = None
    dco: str | None = None
    dci: str | None = None
    tid: str | None = None
    rid: str | None = None
    lt: int | None = None
    cno: str | None = None
    did: str | None = None
    sg: list[ShippingGoodDto] = Field(default_factory=list)
    asn: str | None = None
    asd: int | None = None
    In: str | None = None
    an: str | None = None


class BodyItemDto(ApiModel):
    sstid: str = ""
    sstt: str = ""
    mu: str = ""
    am: Decimal | None = None
    fee: Decimal | None = None
    cfee: Decimal | None = None
    cut: str = ""
    exr: int | None = None
    prdis: int | None = None
    dis: int | None = None
    adis: int | None = None
    vra: Decimal | None = None
    vam: int | None = None
    odt: str = ""
    odr: Decimal | None = None
    odam: int | None = None
    olt: str = ""
    olr: Decimal | None = None
    olam: int | None = None
    consfee: int | None = None
    spro: int | None = None
    bros: int | None = None
    tcpbs: int | None = None
    cop: int | None = None
    bsrn: str = ""
    vop: int | None = None
    tsstam: int | None = None
    nw: Decimal | None = None
    ssrv: int | None = None
    sscv: Decimal | None = None
    cui: Decimal | None = None
    hs: str = ""
    cpr: Decimal | None = None
    sovat: int | None = None


class PaymentItemDto(ApiModel):
    iinn: str = ""
    acn: str = ""
    trmn: str = ""
    trn: str = ""
    pcn: str = ""
    pid: str = ""
    vatpid: str = ""
    vatbid: str = ""
    pdt: int | None = None
    pmt: int | None = None
    pv: int | None = None


class ExtensionItemDto(ApiModel):
    pass


class InvoiceDto(ApiModel):
    Header: HeaderDto
    Body: list[BodyItemDto] = Field(default_factory=list)
    Payments: list[PaymentItemDto] = Field(default_factory=list)
    Extension: list[ExtensionItemDto] = Field(default_factory=list)


class PacketHeaderDto(ApiModel):
    RequestTraceId: str
    FiscalId: str


class PacketDto(ApiModel):
    Payload: str
    Header: PacketHeaderDto


class Pageable(ApiModel):
    PageNumber: int = 0
    PageSize: int = 10

_Pageable = Pageable



class InquiryByTimeRangeDto(ApiModel):
    Start: datetime
    End: datetime | None = None
    Pageable: _Pageable | None = None
    Status: _RequestStatus | None = None


class InquiryByUidDto(ApiModel):
    UidList: list[str]
    FiscalId: str
    Start: datetime | None = None
    End: datetime | None = None


class InquiryByReferenceNumberDto(ApiModel):
    ReferenceNumbers: list[str]
    Start: datetime | None = None
    End: datetime | None = None


class RegisterPaymentRequestDto(ApiModel):
    TaxId: str
    PaidAmount: int
    PaymentDate: int
    PaymentMethod: PaymentMethod
    TerminalNumber: str = ""
    ReferenceNumber: str = ""


class ErrorItemDto(ApiModel):
    Code: str | None = None
    Message: str | None = None


class ErrorResponseDto(ApiModel):
    Timestamp: int | None = None
    RequestTraceId: str | None = None
    Errors: list[ErrorItemDto] = Field(default_factory=list)


class InvoiceStatusInquiryResponseDto(ApiModel):
    TaxId: str | None = None
    InvoiceStatus: str | None = None
    Article6Status: str | None = None
    Error: str | None = None


class InvoiceResponseDto(ApiModel):
    Data: Any = None
    Uid: str | None = None
    ReferenceNumber: str | None = None
    TaxId: str | None = None


class InvoiceStatusDto(ApiModel):
    TaxId: str | None = None
    InvoiceStatus: str | None = None
    Article6Status: str | None = None
    Error: str | None = None


class InquiryResultDto(ApiModel):
    ReferenceNumber: str | None = None
    Uid: str | None = None
    Status: Any = None
    Data: Any = None


class BatchResponseDto(ApiModel):
    Result: list[InvoiceResponseDto] = Field(default_factory=list)


class RegisterPaymentResultDto(ApiModel):
    RequestStatus: _RequestStatus | None = None
    Error: list[ErrorItemDto] = Field(default_factory=list)


class PublicKeyDto(ApiModel):
    Id: str = ""
    Key: str = ""
    Algorithm: str | None = None
    Purpose: int | None = None


class ServerInformationDto(ApiModel):
    ServerTime: int = 0
    PublicKeys: list[PublicKeyDto] = Field(default_factory=list)


class TaxpayerDto(ApiModel):
    NameTrade: str = ""
    TaxpayerStatus: str = ""
    TaxpayerType: str = ""
    PostalcodeTaxpayer: str = ""
    AddressTaxpayer: str = ""
    NationalId: str = ""


class FiscalFullInformationDto(ApiModel):
    NameTrade: str = ""
    FiscalStatus: str = ""
    SaleThreshold: str = ""
    EconomicCode: str = ""
    NationalId: str = ""


class TaxpayerInfoDto(ApiModel):
    TaxpayerName: str = ""
    TaxpayerProfileStatus: int = 0
    TaxpayerCallStatus: bool = False
    TaxpayerArticle2Status: bool = False


class Article6StatusRequestDto(ApiModel):
    EconomicCode: str
    VatValue: int
    Period: int


class Article6StatusDto(ApiModel):
    Article6RemainStatus: bool = False
