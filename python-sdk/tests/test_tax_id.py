from datetime import datetime, timezone

import pytest

from tax_collect_data.providers.tax_id import TaxIdProvider


def test_generation_is_deterministic():
    provider = TaxIdProvider()
    date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    first = provider.generate_tax_id("A111YO", 123456789, date)
    second = provider.generate_tax_id("A111YO", 123456789, date)
    assert first == second
    assert first.startswith("A111YO")


def test_different_serials_produce_different_ids():
    provider = TaxIdProvider()
    date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert provider.generate_tax_id("A111YO", 100, date) != provider.generate_tax_id("A111YO", 200, date)


@pytest.mark.parametrize("client_id, serial", [("", 1), ("A111YO", -1)])
def test_invalid_arguments_are_rejected(client_id, serial):
    with pytest.raises(ValueError):
        TaxIdProvider().generate_tax_id(client_id, serial, datetime.now(timezone.utc))
