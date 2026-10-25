"""Tax ID generation ported from the source implementation."""

from datetime import datetime

from tax_collect_data.algorithms.verhoeff import VerhoeffAlgorithm


class TaxIdProvider:
    def __init__(self, error_detection_algorithm: VerhoeffAlgorithm | None = None) -> None:
        self._algorithm = error_detection_algorithm or VerhoeffAlgorithm()

    @staticmethod
    def _to_decimal(memory_id: str) -> str:
        # Mirrors the C# char conversion used by the original implementation.
        return "".join(char if char.isdigit() and char.isascii() else str(ord(char)) for char in memory_id)

    def generate_tax_id(self, client_id: str, serial: int, date: datetime) -> str:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("client_id cannot be null or empty")
        if not isinstance(serial, int) or isinstance(serial, bool) or serial < 0:
            raise ValueError("serial must be a non-negative integer")
        if not isinstance(date, datetime):
            raise TypeError("date must be a datetime")

        # datetime.timestamp() mirrors DateTimeOffset.ToUnixTimeSeconds for normal
        # post-epoch dates; timezone-aware values retain their supplied offset.
        seconds = int(date.timestamp())
        day_range = int(seconds / 86400)
        hex_time = format(day_range, "x")
        hex_serial = format(serial, "x")
        initial = f"{client_id}{hex_time.zfill(5)}{hex_serial.zfill(10)}"
        control_text = (
            f"{self._to_decimal(client_id)}"
            f"{str(day_range).zfill(6)}"
            f"{str(serial).zfill(12)}"
        )
        return f"{initial}{self._algorithm.generate_check_digit(control_text)}".upper()
