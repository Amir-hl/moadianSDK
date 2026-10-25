# Tax Collect Data SDK for Python

This is the initial Python implementation area for the .NET SDK in the repository. The .NET source is intentionally retained as a reference while behavior is ported and tested.

## Status

This is an incremental port, not yet a feature-complete replacement. The initial version contains configuration, domain exceptions, the Verhoeff check-digit algorithm, and tax-ID generation. HTTP authentication, packet submission, JWS/JWE, certificate and PKCS#11 handling, inquiries, taxpayer lookup, and payment registration must be implemented and validated against the original source and official API specifications before production use.

## Install for development

From this directory:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
pytest
```

## Security

Do not commit private keys, certificate PINs, API credentials, or production taxpayer data. Do not use this SDK against production until cryptographic behavior and API payloads have been verified with known test vectors.
