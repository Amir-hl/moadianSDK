"""Verhoeff error-detection algorithm ported from the C# implementation."""


class VerhoeffAlgorithm:
    _D = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
    )
    _P = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
    )
    _INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)

    @staticmethod
    def _digits(number: str) -> list[int]:
        if not isinstance(number, str) or not number.strip():
            raise ValueError("number cannot be null or empty")
        if not number.isascii() or not number.isdigit():
            raise ValueError("number must contain ASCII digits only")
        return [int(char) for char in reversed(number)]

    def generate_check_digit(self, number: str) -> str:
        c = 0
        for index, digit in enumerate(self._digits(number)):
            c = self._D[c][self._P[(index + 1) % 8][digit]]
        return str(self._INV[c])

    def validate_check_digit(self, number: str) -> bool:
        if not isinstance(number, str) or not number.strip():
            return False
        digits = self._digits(number)
        c = 0
        for index, digit in enumerate(digits):
            c = self._D[c][self._P[index % 8][digit]]
        return c == 0
