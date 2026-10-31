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


def test_serialization_preserves_none_values():
    invoice = InvoiceDto(
        Header=HeaderDto(taxid="T1", indatim=123, ins=1)
    )

    value = serialize(invoice)

    assert '"indati2m":null' in value


def test_serialization_uses_string_enum_values():
    request = RegisterPaymentRequestDto(
        TaxId="T1",
        PaidAmount=1000,
        PaymentDate=123456,
        PaymentMethod=PaymentMethod.CASH,
    )

    value = serialize(request)

    assert '"paymentMethod":"CASH"' in value
    assert '"paymentMethod":1' not in value


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