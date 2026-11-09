# Moadian SDK v1 — Packet and Transfer Contract (Draft)

**Scope:** ordinary taxpayer direct submission (`NormalProperties` + `SELF_TSP`), API v1. TSP, GSB, and v2 authentication/transport are out of scope for this contract.

**Reference implementation:** local .NET SDK source `tax-collect-data-sdk-dotnet-tax-collect-data-sdk-0.0.30`, especially `DefaultTaxApiClient`, `TransferApi`, `SimpleTransferApi`, `SimpleNormalizer`, `DefaultEncryptor`, `PacketCodec`, `PacketDto`, `AsyncRequestDto`, and `SignedRequest`.

**Status:** contract draft derived from source inspection. It is not yet a golden byte-for-byte fixture. Exact enum wire values, final serializer property order, and response shape must be captured from the same .NET 0.0.30 build before tests assert byte equality.

## 1. Version selection

- v1 uses the simple transfer path (`SimpleNormalizer` + `SimpleTransferApi`) when API version is `v1`.
- v1 uses token acquisition (`RequestToken`) and the token in subsequent request headers.
- v2 nonce/JWS authentication and Compact JWE are a separate protocol and must remain unchanged.
- Current product scope is direct taxpayer submission (`SELF_TSP`) over the normal connection. Do not add TSP or GSB behavior as part of this stage.

## 2. Packet DTO

The .NET v1 `PacketDto<T>` carries these properties:

| Property | JSON name | Meaning / lifecycle |
|---|---|---|
| `Uid` | `uid` | Packet identifier; generated for a normal invoice packet |
| `PacketType` | `packetType` | Packet operation/type; invoice submission uses the SDK's `InvoiceV01` packet type |
| `Retry` | `retry` | Retry flag; builder default is false |
| `Data` | `data` | Invoice DTO before encryption; encrypted Base64 string after encryption |
| `EncryptionKeyId` | `encryptionKeyId` | Server public-key identifier; null before encryption |
| `SymmetricKey` | `symmetricKey` | RSA-OAEP-SHA256-encrypted AES key material, Base64 |
| `Iv` | `iv` | 16-byte IV encoded as uppercase hexadecimal without separators |
| `FiscalId` | `fiscalId` | Taxpayer fiscal identifier; defaults to configured client ID |
| `DataSignature` | `dataSignature` | Signature of packet data, when packet signing is enabled |
| `SignatureKeyId` | `signatureKeyId` | Key identifier associated with packet data signature |

The source serializer uses camelCase property naming, string enum conversion, and default null handling (null properties are not globally omitted). Python's current `exclude_none=True` behavior is therefore not suitable for the v1 signed representation.

## 3. Async transfer envelope

The asynchronous request is an `AsyncRequestDto<T>` derived from `SignedRequest` and contains `Packets`.

Conceptual JSON shape (illustrative; property ordering and exact enum wire value still require a captured .NET golden sample):

```json
{
  "signature": null,
  "signatureKeyId": null,
  "packets": [
    {
      "uid": "<packet-uid>",
      "packetType": "<.NET enum string>",
      "retry": false,
      "data": "<encrypted-data-base64>",
      "encryptionKeyId": "<server-key-id>",
      "symmetricKey": "<encrypted-aes-key-base64>",
      "iv": "<iv-hex>",
      "fiscalId": "<fiscal-id>",
      "dataSignature": "<data-signature-base64>",
      "signatureKeyId": "<signing-key-id>"
    }
  ]
}
```

`SignedRequest.Signature` and `SignedRequest.SignatureKeyId` are null on the ordinary async request construction path; the transfer signature is carried in HTTP headers by `SimpleTransferApi`.

## 4. Packet signing and transfer signing are distinct

### Packet data signature

- The packet data is normalized and signed using the packet/content signatory.
- The resulting signature is stored in `PacketDto.DataSignature`.
- The key ID is stored in `PacketDto.SignatureKeyId`.
- The exact normalized byte/string input must be reproduced from the .NET normalizer before implementing the Python signer.

### HTTP transfer signature

- `SimpleTransferApi` serializes the `AsyncRequestDto` JSON.
- `SimpleNormalizer.NormalizeJson` appends, in this order, the configured token header value, `RequestTraceId`, and `Timestamp`, with no separators, when those headers exist.
- The transfer signatory signs that normalized text.
- The result is sent in HTTP header `Signature`; the transfer key ID is sent in `Signature-Key-Id` when non-empty.
- These signature headers are not included in the normalized input.
- Other custom headers are not included by the inspected `SimpleNormalizer` implementation.

## 5. v1 encryption contract

For an encrypted packet batch, the inspected .NET implementation:

1. Generates one 32-byte AES key and one 16-byte IV for the batch.
2. Converts AES key bytes to uppercase hexadecimal text (64 characters) without separators.
3. Encrypts the UTF-8 bytes of that hex text using the tax organization's RSA public key with OAEP-SHA256; result is Base64 `symmetricKey`.
4. Serializes each packet's `Data` using the configured .NET JSON serializer.
5. XORs the serialized JSON bytes with the 32-byte AES key repeated cyclically to the length of the longer input.
6. Encrypts the XOR output with AES-256-GCM, 128-bit authentication tag, and the generated IV.
7. Stores Base64 ciphertext+tag in `data`, the server key ID in `encryptionKeyId`, and IV hex in `iv`.

**Important source behavior to preserve/explicitly review:** batch encryption reuses the same AES key and IV for every packet in that batch. This is cryptographically unsafe for GCM nonce reuse, but changing it may break protocol compatibility. Do not silently alter this behavior; verify with official protocol requirements and integration tests.

The C# RSA helper catches every exception and returns the literal string `"error"`; this is a source SDK error-handling defect and should not be copied into Python. Python should fail closed with a typed cryptography exception before sending malformed packets.

## 6. HTTP lifecycle for direct SELF_TSP v1

1. Obtain server information through the v1 packet transfer mechanism (`GET_SERVER_INFORMATION` packet; not the v2-style direct GET route).
2. Configure the encryption key from the returned public-key information. The inspected .NET source selects the first returned public key; Python key selection must be checked against the official key `purpose`/`algorithm` contract before finalizing.
3. Request an access token with `GET_TOKEN` packet, with encryption disabled and packet/transfer signing disabled for this token request according to the inspected `DefaultTaxApiClient` call.
4. Cache/use the returned token and include it in subsequent request headers.
5. For invoice submission, create invoice packet(s), sign packet data, encrypt packet(s), wrap them in `AsyncRequestDto`, sign the transfer, then POST to the v1 invoice endpoint.

## 7. Python implementation gaps to close

The current Python implementation is v2-oriented and does not implement this v1 contract:

- `PacketDto` currently has `Payload` + `Header`, not the .NET v1 packet fields.
- `PacketService` currently signs the invoice JSON as JWS and encrypts it as Compact JWE.
- `RequestProvider.invoices()` currently sends a top-level JSON array rather than an `AsyncRequestDto` envelope.
- `TaxHttpClient` currently obtains a nonce and sends a JWS Authorization value rather than acquiring/caching the v1 access token and applying the v1 transfer signature headers.
- The current serializer omits nulls and emits Python enum `.value`; v1 requires .NET-compatible null and string-enum behavior.
- Current response mapping appears to conflate `Uid` with `RequestTraceId`; those are separate identifiers and must be mapped independently.

## 8. Golden fixture requirements before byte-for-byte assertions

Capture from the exact local .NET 0.0.30 source/build using deterministic test inputs:

- A representative invoice DTO JSON before signing.
- Packet JSON immediately before encryption.
- Packet JSON after encryption (use deterministic/injectable test key, IV, and RSA public key in a test harness, not production randomness).
- `AsyncRequestDto` JSON including null base properties and exact property order.
- Exact packet-signature input string and signature output.
- Exact transfer-signature input string and signature output for fixed token, RequestTraceId, and Timestamp.
- Exact request headers and final POST body.

The fixture must not contain production taxpayer credentials or production private keys. The approved test-only private key may be used only in local test fixtures.

## 9. Acceptance criteria for Stage 1

- This document is reviewed against the exact local 0.0.30 source.
- A deterministic .NET golden fixture is captured for one invoice and one packet.
- Python tests can load the fixture and validate field names, null handling, enum representation, envelope shape, and signing-input construction.
- No v2 behavior is changed in Stage 1.
- No TSP or GSB support is introduced in Stage 1.
