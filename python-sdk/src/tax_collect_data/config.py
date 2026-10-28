"""SDK configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass(slots=True)
class TaxSdkOptions:
    base_url: str
    client_id: str
    private_key_path: str | None = None
    certificate_path: str | None = None
    pkcs11_library_path: str | None = None
    pkcs11_token_serial_number: str | None = None
    pkcs11_token_pin: str | None = None
    request_timeout: float = 600.0
    api_version: str = "v2"
    custom_headers: dict[str, str] = field(default_factory=dict)
    authorization_header_name: str = "Authorization"

    def validate(self) -> None:
        if not self.base_url or not self.base_url.strip():
            raise ValueError("base_url is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if not self.client_id or not self.client_id.strip():
            raise ValueError("client_id is required")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be greater than zero")
        if not self.api_version or not self.api_version.strip():
            raise ValueError("api_version is required")
        if (
            not self.authorization_header_name
            or not self.authorization_header_name.strip()
        ):
            raise ValueError("authorization_header_name cannot be empty")

        has_pkcs8 = bool(self.private_key_path and self.certificate_path)
        has_pkcs11 = bool(self.pkcs11_library_path and self.pkcs11_token_serial_number)
        if not (has_pkcs8 or has_pkcs11):
            raise ValueError(
                "Either PKCS#8 (private_key_path + certificate_path) or "
                "PKCS#11 (library path + token serial number) configuration is required"
            )

        if self.private_key_path and not Path(self.private_key_path).is_file():
            raise ValueError(f"Private key file does not exist: {self.private_key_path}")
        if self.certificate_path and not Path(self.certificate_path).is_file():
            raise ValueError(f"Certificate file does not exist: {self.certificate_path}")
