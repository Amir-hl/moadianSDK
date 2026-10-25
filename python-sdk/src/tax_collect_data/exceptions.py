"""Domain and API exceptions."""


class DomainException(Exception):
    """Base exception for SDK domain errors."""


class NotInitializedError(DomainException):
    """Raised when the SDK is used before configuration."""


class CertificateError(DomainException):
    """Raised for certificate loading or validation failures."""


class CryptographyError(DomainException):
    """Raised when signing or encryption fails."""


class InvalidTaxIdError(DomainException, ValueError):
    """Raised when a tax ID is invalid."""


class TaxApiError(DomainException):
    """Error returned by the tax API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message


class UnknownResponseError(DomainException):
    """Raised when an API response cannot be interpreted."""
