"""Tax ID generation ported from the source implementation."""
from datetime import date as Date, datetime

from tax_collect_data.algorithms.verhoeff import VerhoeffAlgorithm


class TaxIdProvider:
    def __init__(self, error_detection_algorithm: VerhoeffAlgorithm | None = None) -> None:
        self._algorithm = error_detection_algorithm or VerhoeffAlgorithm()

    @staticmethod
    def _to_decimal(memory_id: str) -> str:
        result = []

        for char in memory_id:
            if "0" <= char <= "9":
                result.append(char)
            elif "A" <= char <= "Z":
                result.append(str(ord(char)))
            else:
                raise ValueError(
                    "memory_id must contain only uppercase ASCII letters and digits"
                )

        return "".join(result)


    @staticmethod
    def _get_day_range(value: datetime) -> int:
        invoice_date = value.date()
        epoch_date = Date(1970, 1, 1)

        return (invoice_date - epoch_date).days

    def generate_tax_id(self, client_id: str, serial: int, date: datetime) -> str:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("client_id cannot be null or empty")
        if not isinstance(serial, int) or isinstance(serial, bool) or serial < 0:
            raise ValueError("serial must be a non-negative integer")
        if not isinstance(date, datetime):
            raise TypeError("date must be a datetime")

        # datetime.timestamp() mirrors DateTimeOffset.ToUnixTimeSeconds for normal
        # post-epoch dates; timezone-aware values retain their supplied offset.
        day_range = self._get_day_range(date)
        hex_time = format(day_range, "x")
        hex_serial = format(serial, "x")
        initial = f"{client_id}{hex_time.zfill(5)}{hex_serial.zfill(10)}"
        control_text = (
            f"{self._to_decimal(client_id)}"
            f"{str(day_range).zfill(6)}"
            f"{str(serial).zfill(12)}"
        )
        return f"{initial}{self._algorithm.generate_check_digit(control_text)}".upper()
