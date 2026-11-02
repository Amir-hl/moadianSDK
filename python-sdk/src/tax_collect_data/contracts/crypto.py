from typing import Any, Protocol


class Serializer(Protocol):
    def serialize(self, value: Any) -> str:
        ...


class Signatory(Protocol):
    def sign(self, text: str) -> str:
        ...


class Encryptor(Protocol):
    def encrypt(self, text: str) -> str:
        ...