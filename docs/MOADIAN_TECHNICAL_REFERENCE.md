# Moadian SDK — Technical Documentation Reference

> Purpose: A persistent engineering reference extracted from the two Moadian SDK and technical connection documents reviewed for this project. This document should be consulted before implementation or code review so the original PDFs do not need to be uploaded repeatedly.
>
> Scope: This is a source-derived reference, not a statement that the Python SDK is production-ready. Unclear or undocumented rules are explicitly marked as unresolved.

## 1. Source documents and reliability

### 1.1 .NET SDK usage guide
- Identifies package `TaxCollectData.Library.2.0.31`.
- Dated Farvardin 1405.
- Covers SDK configuration (`TaxApi`, `Signatory`, `Encryptor`), authentication and nonce, TaxId generation, invoice DTO construction, `SendInvoices`, low-level API and packet flow, server information and public keys, invoice inquiries, taxpayer and fiscal information, invoice-status inquiry, payment registration, and PKCS#11/ePass3003.
- It is a .NET SDK usage guide. Its examples are useful implementation references, but do not automatically prove every implementation detail is a universal server-side requirement.
- Documents an `ILowLevelTaxApi` abstraction. The Python SDK must be checked separately for a public equivalent.
- PKCS#8 configuration uses a private key and certificate. PKCS#11 uses a cryptographic token/device.
- The guide does not clearly establish whether a certificate is mandatory for every endpoint or API version.
- It distinguishes sender-generated UID/request identifiers from server-generated `ReferenceNumber`. Neither is the invoice `taxid`.

### 1.2 Technical connection instructions
- Cover identifies `RC_TICS.IS_v1.6`, dated Shahrivar 1404, 49 pages.
- Important inconsistency: many internal page headers from page 9 onward still identify `RC_TICS.IS_v1.5`, dated Ordibehesht 1404.
- Treat the document as version-ambiguous until the authoritative revision or change log is confirmed.
- Covers authentication, nonce, JWT/JWS, JWE, server information and public keys, invoice submission, UID/RequestTraceId, invoice inquiries, taxpayer/workbench status, and payment-related APIs.
- Some PDF table, JSON, and curl extraction order is imperfect. For disputed exact fields, URLs, or payload shapes, inspect the original page or an authoritative current revision.
- Do not silently combine v1.5 and v1.6 rules.

## 2. Important identifiers

These identifiers have different meanings and must remain separate in models, database columns, logs, and API parameters.

- **TaxId / taxid:** Unique tax invoice identifier, generated according to TaxId rules. Not the request UID or server reference number.
- **UID / RequestTraceId:** Sender-generated request tracking identifier. The v2 invoice example contains `requestTraceId` and `fiscalId`. It is a client-side correlation identifier.
- **ReferenceNumber:** Server-generated identifier returned for a submitted invoice. Used for reference-number inquiry.
- **FiscalId:** Fiscal memory/sender identifier used in relevant API payloads and authentication context. Not interchangeable with national ID, economic code, TaxId, or ReferenceNumber.
- **ClientId:** Client identity used in the described authentication payload. The examples associate it with fiscal-identifier context; confirm the exact current contract for each version and sending mode.

## 3. Authentication and nonce — documented v2 flow

The technical connection instructions describe this flow for protected requests:

1. Obtain a fresh nonce.
2. Build an authentication payload containing nonce and client identifier:
   ```json
   {"nonce":"RANDOM_NONCE","clientId":"FISCAL_ID"}
   ```
3. Build a JWS protected header and sign the payload with the configured private key/certificate.
4. Send the resulting token in `Authorization: Bearer ...`.
5. The document describes a nonce lifetime of 30 seconds and single-use behavior. Obtain a fresh nonce for each protected request; do not reuse nonce values or assume tokens can be replayed.

Documented JWS protected-header example:

```json
{
  "alg": "RS256",
  "x5c": ["BASE64_CERTIFICATE"],
  "sigT": "2024-03-06T13:05:50Z",
  "crit": ["sigT"]
}
```

- `alg`: `RS256`, i.e. RSASSA-PKCS1-v1_5 with SHA-256.
- `x5c`: certificate material in the structure/encoding required by the protocol.
- `sigT`: signature timestamp.
- `crit`: identifies `sigT` as a critical protected-header parameter.
- The document says the certificate must be valid, not revoked, and its national identifier must match the owner of the relevant sender/client identity.
- Verify exact validation rules against the authoritative current revision.

### 3.1 Certificate and sending modes

The document describes three sending modes:

1. Taxpayer sends using the taxpayer's own key.
2. Trusted company sends using the taxpayer's key.
3. Trusted company sends using the trusted company's own key.

In mode 3, the taxpayer does not need to upload their own key/certificate for that arrangement; the trusted company uses its own certificate.

Do not confuse:
- Certificate included in API authentication JWS (`x5c`).
- Taxpayer certificate registration/upload in the workbench.
- Which entity's certificate is used for a particular sending mode.
- API-version-specific authentication requirements.

The reviewed document describes certificate-based JWS authentication for v2. It does not justify saying certificates are universally optional for v2, or that every taxpayer must personally upload a certificate in every sending mode.

The document says the previous API version remains usable until notice, but exact v1 authentication and certificate rules must be verified from the applicable v1 documentation.

## 4. JWE packet encryption — documented v2 flow

The technical instructions describe:

- Key management algorithm: `RSA-OAEP-256`
- Content encryption algorithm: `A256GCM`
- `kid`: identifier of the selected server public key.

Conceptual process:

1. Generate a fresh symmetric content-encryption key (AES-256).
2. Wrap/encrypt that key using the server RSA public key with RSA-OAEP-256.
3. Generate an initialization vector (IV).
4. Encrypt the JWS content using AES-256-GCM.
5. Include the authentication tag and required protected-header fields.
6. Serialize as compact JWE.

Implementation cautions:
- Preserve exact compact-serialization segment ordering and base64url rules.
- Use the server-provided key identifier as `kid`; never invent it.
- Generate per-message cryptographic values as required by the JWE contract.
- Tests using a fake encryptor do not prove real RSA-OAEP/AES-GCM interoperability.
- The document describes the v2 flow. Do not assume v1 requires the same packet encryption without checking its contract.

## 5. Server information and public keys — v2

Documented endpoint:

```http
GET /api/v2/server-information
```

Response includes `serverTime` and a `publicKeys` collection. Example fields:

- `key`: public-key material.
- `id`: key identifier; used as JWE `kid`.
- `algorithm`: algorithm label (RSA in the example).
- `purpose`: purpose code (example shows 1).

Implementation implications:
- Fetch server information from the correct environment/base URL.
- Retain key identifier with public-key material.
- Select a key matching the required algorithm, purpose, and any validity/status rules actually documented.
- Do not guess undocumented purpose codes or validity fields.
- Key caching, refresh, rotation, and stale-key handling need explicit design and tests.

## 6. Invoice packet and submission

- The .NET usage guide describes invoice DTO construction, packet preparation, and `SendInvoices`.
- The technical instructions show the v2 endpoint:

  ```http
  POST /api/v2/invoice
  ```

- The v2 example body is a packet collection. The packet contains encrypted `payload` and a `header` containing at least `requestTraceId` and `fiscalId` in the example.
- Keep invoice serialization, packet creation, signing, encryption, and HTTP transmission independently testable.
- TaxId generation/validation is its own concern. The usage guide describes TaxId generation, but exact bit layout, serial conversion, date encoding, and check-digit algorithm must be verified using the dedicated authoritative TaxId specification or known-good test vectors.
- Invoice DTO field names, types, requiredness, conditional rules, and enums must come from the latest invoice technical/business rules. Do not infer them from C# property names alone.

Project decision: implement v1 first while keeping shared invoice/business logic independent from version-specific protocol behavior.

## 7. Ordinary invoice-processing inquiries

The documents describe inquiries by:
- Reference number / reference ID.
- UID.
- Time range.

The .NET request-provider excerpt shows these query concepts:
- `referenceIds` (repeated for a list).
- `uidList` (repeated for a list).
- `fiscalId` for UID inquiry.
- `start`, `end`.
- `status`.
- `pageNumber`, `pageSize`.

The technical instructions show v2 route names:
- `inquiry-by-reference-id`
- `inquiry-by-uid`
- `inquiry` (time-based inquiry)

Confirm exact query casing, date-time formatting, optionality, and route prefix against the applicable version's API contract.

Ordinary processing statuses described in the technical document:
- `SUCCESS`
- `FAILED`
- `IN_PROGRESS`
- `NOT_FOUND`

The response may include a server-signed JWS. Determine whether response-signature verification is required and implement it if the current contract requires it. Decoding a response is not the same as verifying its signature.

A successful submission/processing inquiry does not necessarily mean final workbench approval.

## 8. Workbench invoice-status inquiry — separate lifecycle

Documented v2 endpoint:

```http
GET /api/v2/inquiry-invoice-status
```

The .NET request-provider excerpt constructs repeated `taxIds` query parameters.

This endpoint concerns invoice status in the taxpayer workbench. It is not the same status model as ordinary submission-processing inquiries.

Status examples:
- `APPROVED`
- `REJECTED`
- `SYSTEMIC_APPROVED`
- `AWAITING_REACTION`
- `NO_NEED_REACTION`
- `CANCELED`

The document also describes Article 6 status separately.

Keep workbench approval status separate from transmission/processing status in response models and business logic. Do not collapse them into one enum or field unless the official contract explicitly defines the mapping.

## 9. Taxpayer and fiscal information

The .NET guide includes:
- `GetTaxpayer` / taxpayer information, with economic code in the shown request-provider example.
- `GetFiscalInformation` / fiscal-memory information.

The technical instructions show v2 routes:

```http
GET /api/v2/taxpayer?economicCode=...
GET /api/v2/fiscal-information?memoryId=...
```

Example response concepts include trade name, taxpayer status, national ID, fiscal status, and economic code. These are examples, not an exhaustive schema. Confirm exact fields, nullability, enums, and response structure from the authoritative contract.

## 10. Payment registration

- The .NET guide includes `RegisterPaymentRequest` / payment registration.
- The .NET request-provider excerpt sends JSON to the `invoice-payment` route under the configured base URL.
- Confirm exact versioned route, payload, field rules, and response schema from the applicable technical instructions.
- Do not infer payment semantics or validation rules from the method name alone.

## 11. PKCS#8 and PKCS#11

- PKCS#8 configuration in the .NET guide uses private key and certificate.
- PKCS#11 uses a cryptographic token/hardware device; the guide includes an ePass3003 example.
- These are different key-access mechanisms. They are not the same thing as API version selection or workbench certificate upload.
- Earlier Python SDK inspection found PKCS#11 configuration incomplete: options existed, but the configuration path raised a not-implemented error. This is a historical code-review finding, not a statement from the PDFs; re-check the current branch.
- A future design should isolate private-key operations behind a signing interface so file-based PKCS#8 and token-backed PKCS#11 can share higher-level authentication logic where compatible.

## 12. Transport, errors, timeouts, and security

The reviewed documents do not fully specify a complete retry, timeout, or idempotency policy.

Engineering requirements to validate:
- Distinguish transport errors, HTTP errors, authentication errors, server validation errors, and business-status results.
- Preserve server error codes/messages in structured exceptions or response objects.
- Use bounded timeouts.
- Retry only when safe under endpoint semantics.
- Never blindly replay a one-use nonce or a request whose idempotency is unknown.
- Log correlation IDs (UID/RequestTraceId and ReferenceNumber when available).
- Never log private keys, bearer tokens, nonce secrets, token PINs, or sensitive invoice payloads.
- Test connection failures, read timeouts, malformed JSON, non-success HTTP responses, and transient server errors.

These are engineering quality requirements; not all are explicit protocol mandates in the PDFs.

## 13. API v1-first, v2-ready architecture decision

Project decision:
- Implement and validate API v1 first because certificate use is expected to be uncommon among intended users at this stage.
- Design the SDK so v2 can be added soon without disrupting v1 or rewriting invoice/business logic.
- Do not assume v1 and v2 differ only in authentication. That remains an unverified hypothesis until endpoints, packet structure, encryption, responses, and certificate requirements are compared.

Recommended boundaries:
- Shared domain models and invoice business rules where contracts are genuinely identical.
- Version-specific authentication strategy.
- Version-specific packet protection/encryption where required.
- Version-aware endpoint and request construction.
- Version-specific response adapters only where response contracts differ.
- Keep high-level public SDK methods stable where possible (for example, same invoice-send method), with version selected through configuration.
- Certificate configuration must not be a mandatory global dependency for v1 if the v1 contract does not require it.
- Do not remove certificate support from the architecture because v2 requires it.
- Prefer explicit version selection such as `api_version="v1"` over scattered version checks throughout business logic.

## 14. Historical Python SDK review findings

These findings came from earlier code inspection and must be re-verified against the current branch:

| Area | Earlier finding | Follow-up |
|---|---|---|
| Nonce/authentication | `TaxHttpClient.send` obtained nonce and generated a token for protected requests. | Verify exact v1 flow and per-request behavior. |
| JWS | Signing implementation existed. | Verify header, x5c, timestamp, certificate handling, and version rules. |
| TaxId | Provider implementation existed. | Compare with official specification and test vectors. |
| UID/RequestTraceId | UUID generation existed. | Verify every submission path and field mapping. |
| JWE | Encryption implementation existed. | Test real RSA public key and AES-GCM; earlier packet tests used a fake encryptor. |
| Server keys | Retrieval/repository existed. | Verify selection by ID, algorithm, purpose, rotation, and environment. |
| Invoice send | Implementation existed. | Verify packet schema, versioned endpoint, and live behavior. |
| Inquiries | Reference, UID, and time inquiries existed. | Verify query names, response parsing, and status semantics. |
| Workbench status | Invoice-status inquiry existed. | Keep separate from ordinary processing inquiry. |
| Taxpayer/fiscal info | Operations existed. | Verify DTOs and endpoint contracts. |
| Payment | Registration operation existed. | Verify exact request and response schema. |
| PKCS#11 | Earlier inspection found configuration incomplete/not implemented. | Re-check and implement if required by product scope. |
| Low-level API | .NET guide exposed `ILowLevelTaxApi`; public Python equivalent was not confirmed. | Decide whether Python SDK needs a public low-level interface. |
| Response JWS verification | Potential gap / not confirmed. | Inspect contract and current implementation. |

Historical test status: Python SDK tests were reported as **55 passed** in a prior run. This is unit-test evidence only. It does not prove live Moadian connectivity, real certificate interoperability, complete endpoint coverage, or production readiness.

## 15. Outstanding questions

1. Obtain/identify the authoritative current v1 technical connection specification, including authentication and certificate requirements.
2. Resolve whether the technical connection PDF is officially v1.6 throughout; obtain its change log or a clean copy because cover and internal page headers disagree.
3. Compare v1 and v2 endpoint by endpoint: authentication, nonce, JWS, JWE, packet envelope, headers, query parameters, response DTOs, error codes, and status lifecycle.
4. Confirm whether v1 requires packet encryption and, if so, the exact algorithm and public-key discovery process.
5. Confirm TaxId format/generation with official rules and known-good test vectors.
6. Confirm invoice header/body fields, types, requiredness, conditional rules, enums, and business validation from the latest invoice specification.
7. Confirm response JWS verification requirements and verification keys/trust model.
8. Confirm taxpayer/fiscal information and payment schemas.
9. Confirm PKCS#11 support requirements and token behavior for the intended product.
10. Run real-environment tests with authorized credentials and test invoices. Unit tests and fake crypto are insufficient.
11. Define secure multi-tenant key and credential isolation for SaaS. Never share one tenant's private key, token, fiscal identity, or authentication context with another tenant.

## 16. Implementation guardrails

- Current official documentation takes precedence over assumptions and incidental behavior in a sample SDK.
- Treat the .NET SDK as an implementation reference, not the final authority when it conflicts with official protocol documentation.
- Label v1 and v2 rules explicitly in code, tests, and docs.
- Do not infer missing protocol rules from naming conventions.
- Preserve raw server error details and correlation IDs for diagnosis while redacting secrets.
- Keep private keys, certificates, token PINs, bearer tokens, and nonce values out of source control and logs.
- Do not call the SDK production-ready until real-environment tests, cryptographic interoperability tests, endpoint coverage, and multi-tenant security review are complete.

---
Last reviewed from the two uploaded documents and the Python SDK review context available on 2026-11-09. Update this reference when a newer official specification is supplied or a disputed rule is confirmed.