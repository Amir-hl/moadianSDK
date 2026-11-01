from decimal import Decimal

from tax_collect_data.models import (
    HeaderDto,
    InvoiceDto,
    PaymentMethod,
    RegisterPaymentRequestDto,
)
from tax_collect_data.serialization import serialize, deserialize



def test_serialization_uses_compact_camel_case_json():
    invoice = InvoiceDto(
        Header=HeaderDto(taxid="T1", indatim=123, ins=1)
    )

    value = serialize(invoice)

    assert '"header"' in value
    assert '"taxid":"T1"' in value
    assert '"indatim":123' in value


def test_serialization_omits_none_values_but_preserves_empty_lists():
    invoice = InvoiceDto(
        Header=HeaderDto(taxid="T1", indatim=123, ins=1)
    )

    value = serialize(invoice)

    assert '"indati2m"' not in value
    assert '"body":[]' in value
    assert '"payments":[]' in value
    assert '"extension":[]' in value


def test_serialization_uses_numeric_enum_values():
    request = RegisterPaymentRequestDto(
        TaxId="T1",
        PaidAmount=1000,
        PaymentDate=123456,
        PaymentMethod=PaymentMethod.CASH,
    )

    value = serialize(request)

    assert '"paymentMethod":1' in value
    assert '"paymentMethod":"CASH"' not in value


def test_serialization_preserves_decimal_values_as_json_numbers():
    value = serialize({"amount": Decimal("123.45")})

    assert '"amount":123.45' in value



def test_serialization_preserves_decimal_precision():
    from decimal import Decimal
    from tax_collect_data.serialization import deserialize

    amount = Decimal("12345678901234567890.123456789")

    serialized = serialize({"amount": amount})

    assert serialized == (
        '{"amount":12345678901234567890.123456789}'
    )

    deserialized = deserialize(serialized)

    assert deserialized["amount"] == amount
    assert isinstance(deserialized["amount"], Decimal)