import pytest

from tax_collect_data.algorithms.verhoeff import VerhoeffAlgorithm


def test_generated_check_digit_validates():
    algorithm = VerhoeffAlgorithm()
    number = "123456"
    full_number = number + algorithm.generate_check_digit(number)
    assert algorithm.validate_check_digit(full_number)


def test_invalid_check_digit_is_rejected():
    algorithm = VerhoeffAlgorithm()
    number = "123456"
    check_digit = algorithm.generate_check_digit(number)
    wrong_digit = str((int(check_digit) + 1) % 10)
    assert not algorithm.validate_check_digit(number + wrong_digit)


@pytest.mark.parametrize("number", ["", "   ", "123ABC", "۱۲۳"])
def test_generate_rejects_invalid_input(number):
    with pytest.raises(ValueError):
        VerhoeffAlgorithm().generate_check_digit(number)
