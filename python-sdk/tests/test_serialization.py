from tax_collect_data.models import HeaderDto, InvoiceDto
from tax_collect_data.serialization import serialize


def test_serialization_uses_compact_camel_case_json():
    invoice = InvoiceDto(Header=HeaderDto(taxid="T1", indatim=123, ins=1))
    value = serialize(invoice)
    assert '"header"' in value
    assert '"taxid":"T1"' in value
    assert '"indatim":123' in value
