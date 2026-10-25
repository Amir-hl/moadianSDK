from tax_collect_data.models import BodyItemDto, HeaderDto, InvoiceDto, PacketDto, PacketHeaderDto


def test_invoice_payload_uses_expected_api_field_names():
    invoice = InvoiceDto(
        Header=HeaderDto(taxid="TAX-1", indatim=1700000000000, ins=1),
        Body=[BodyItemDto(sstid="123", sstt="sample", am=1, fee=100)],
    )
    payload = invoice.to_api_dict()
    assert "header" in payload
    assert payload["header"]["taxid"] == "TAX-1"
    assert payload["body"][0]["sstid"] == "123"
    assert payload["body"][0]["fee"] == 100
    assert "payments" in payload


def test_packet_header_serializes_camel_case():
    packet = PacketDto(
        Payload="encrypted",
        Header=PacketHeaderDto(RequestTraceId="trace-1", FiscalId="A111YO"),
    )
    payload = packet.to_api_dict()
    assert payload["payload"] == "encrypted"
    assert payload["header"]["requestTraceId"] == "trace-1"
    assert payload["header"]["fiscalId"] == "A111YO"
