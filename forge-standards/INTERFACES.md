

# INTERFACES.md — Forge Platform Interface Contracts

**Version:** 1.0
**Status:** Normative — All implementations MUST conform
**Authority:** TRDs 1–16 (forge-docs/), Forge Component Interface Contracts
**Last Updated:** 2026-03-19

---

## Table of Contents

1. [Overview and Conventions](#1-overview-and-conventions)
2. [Transport Layer](#2-transport-layer)
3. [CTX-ID — Context Identity Token](#3-ctx-id--context-identity-token)
4. [VTZ — Virtual Trust Zone](#4-vtz--virtual-trust-zone)
5. [CAL — Contextual Action Layer](#5-cal--contextual-action-layer)
6. [TrustFlow — Audit Event Stream](#6-trustflow--audit-event-stream)
7. [DTL — Data Trust Labels](#7-dtl--data-trust-labels)
8. [TrustLock — Cryptographic Identity Binding](#8-trustlock--cryptographic-identity-binding)
9. [Shell ↔ Backend IPC Protocol](#9-shell--backend-ipc-protocol)
10. [Consensus Engine Interfaces](#10-consensus-engine-interfaces)
11. [Provider Adapter Interfaces](#11-provider-adapter-interfaces)
12. [Pipeline Interfaces](#12-pipeline-interfaces)
13. [GitHub Operations Interfaces](#13-github-operations-interfaces)
14. [Authentication and Session Lifecycle](#14-authentication-and-session-lifecycle)
15. [UI Event Contracts (Swift ↔ SwiftUI)](#15-ui-event-contracts-swift--swiftui)
16. [Enums and Constants](#16-enums-and-constants)
17. [Validation Rules](#17-validation-rules)
18. [Wire Format Examples](#18-wire-format-examples)
19. [Error Contract](#19-error-contract)
20. [Audit Contract](#20-audit-contract)

---

## 1. Overview and Conventions

### 1.1 Notation

| Convention | Meaning |
|---|---|
| `MUST` / `MUST NOT` | Absolute requirement per RFC 2119 |
| `field: Type` | Field name with its type; all types are JSON-representable |
| `field: Type?` | Nullable / optional field |
| `field: Type = value` | Field with default value |
| `[Type]` | Array of Type |
| `{K: V}` | Dictionary / object with key type K, value type V |
| `CSPRNG` | Cryptographically Secure Pseudo-Random Number Generator |
| `UTC-ms` | UTC Unix timestamp, millisecond precision (int64) |

### 1.2 Wire Format

All inter-process messages are **line-delimited JSON** (one JSON object per `\n`-terminated line) over an **authenticated Unix domain socket**. Each line MUST be valid UTF-8. Maximum line length: **4 MiB** (4,194,304 bytes). Lines exceeding this limit MUST be rejected.

### 1.3 Byte Encoding

- All strings: UTF-8, NFC normalized
- All hashes: lowercase hexadecimal unless noted
- All binary blobs in JSON: base64url (RFC 4648 §5), no padding
- All timestamps: integer, UTC Unix milliseconds

### 1.4 Versioning

Every message envelope includes a `v` field. This document defines **v1**. Receivers MUST reject messages with unrecognized major versions. Minor versions (e.g., `1.1`) add optional fields only; receivers MUST ignore unknown fields.

---

## 2. Transport Layer

### 2.1 Unix Domain Socket

| Property | Value |
|---|---|
| Socket path | `$XDG_RUNTIME_DIR/crafted/ipc.sock` or `~/Library/Caches/Crafted/ipc.sock` |
| Socket type | `SOCK_STREAM` |
| Permissions | `0600` — owner-only read/write |
| Owner | The macOS user running Crafted.app |
| Authentication | Handshake message with session token (see §14) |
| Keepalive | Application-level ping every 30s; timeout after 90s of silence |
| Reconnect | Backend retries 3× with exponential backoff (1s, 2s, 4s), then surfaces error |

### 2.2 Message Envelope

Every message on the socket uses this envelope:

```jsonc
{
  "v": 1,                          // int — protocol major version
  "id": "<message-id>",            // string — UUIDv4, unique per message
  "ts": 1711036800000,             // int — UTC-ms, sender's wall clock
  "type": "<message-type>",        // string — see per-subsystem types
  "ref": "<message-id>?",          // string? — id of message this replies to
  "ctx_id": "<ctx-id-token>",      // string — current CTX-ID (required after handshake)
  "payload": { }                   // object — type-specific payload
}
```

| Field | Required | Constraints |
|---|---|---|
| `v` | MUST | Integer. Currently `1`. |
| `id` | MUST | UUIDv4, CSPRNG-generated. MUST be globally unique. |
| `ts` | MUST | UTC-ms. MUST be within ±5000ms of receiver's clock or message is rejected. |
| `type` | MUST | One of the registered message types in this document. |
| `ref` | Conditional | MUST be present on response messages. MUST match a previously sent `id`. |
| `ctx_id` | Conditional | MUST be present on all messages after the handshake phase. |
| `payload` | MUST | Object. Schema depends on `type`. Empty object `{}` is valid for types with no payload. |

---

## 3. CTX-ID — Context Identity Token

### 3.1 Purpose

A CTX-ID is an immutable, cryptographically signed token that binds an agent session to an identity, a VTZ, and a time window. It is the primary credential for all intra-platform authorization.

### 3.2 Structure

```jsonc
{
  "token_id": "<csprng-hex-32>",       // string — 32 hex chars (128-bit), globally unique
  "session_id": "<uuid>",              // string — UUIDv4 of the enclosing session
  "principal": "<principal-uri>",      // string — e.g., "user:alice@crafted.local"
  "vtz_id": "<vtz-identifier>",       // string — VTZ this token is scoped to
  "issued_at": 1711036800000,          // int — UTC-ms
  "expires_at": 1711040400000,         // int — UTC-ms
  "trustlock_key_id": "<key-id>",      // string — ID of TrustLock public key used for signing
  "signature": "<base64url-sig>"       // string — Ed25519 signature over canonical payload
}
```

| Field | Type | Constraints |
|---|---|---|
| `token_id` | string | 32 lowercase hex characters. CSPRNG. Immutable after issuance. |
| `session_id` | string | UUIDv4. References the session that requested issuance. |
| `principal` | string | URI format: `<type>:<identifier>`. Types: `user`, `agent`, `service`. Max 256 chars. |
| `vtz_id` | string | 1–128 chars, `[a-zA-Z0-9._-]`. Must reference an existing VTZ definition. |
| `issued_at` | int | UTC-ms. MUST be ≤ current time. |
| `expires_at` | int | UTC-ms. MUST be > `issued_at`. Maximum lifetime: 3,600,000ms (1 hour). |
| `trustlock_key_id` | string | References the public key in the TrustLock keyring. |
| `signature` | string | Ed25519 signature, base64url-encoded, over the canonical JSON of all other fields (sorted keys, no whitespace). |

### 3.3 Lifecycle Rules

1. **Issuance:** Created by the Shell process after successful authentication. One CTX-ID per session per VTZ.
2. **Immutability:** No field may be modified after issuance. Any mutation invalidates the signature.
3. **Validation:** Every subsystem MUST validate `signature` against the TrustLock public key AND check `expires_at > now`. Software-only validation (skipping TrustLock) is rejected.
4. **Rotation:** Creates a new CTX-ID with a new `token_id`. The old token is added to the revocation set immediately.
5. **Expiry:** Expired tokens MUST be rejected. Clock skew tolerance is deployment-configured, default ±5000ms.
6. **Missing CTX-ID:** MUST be treated as `UNTRUSTED`. Identity MUST NOT be inferred from connection state, IP, or process context.

### 3.4 Canonical Serialization

For signature computation:

1. Collect all fields except `signature`.
2. Sort keys lexicographically (byte-order).
3. Serialize as JSON with no whitespace (compact form).
4. Sign the resulting UTF-8 byte string with Ed25519.

---

## 4. VTZ — Virtual Trust Zone

### 4.1 Purpose

A VTZ is a structural boundary that constrains what resources, tools, and data an agent session may access. VTZ boundaries are enforced, not advisory.

### 4.2 VTZ Definition

```jsonc
{
  "vtz_id": "<vtz-identifier>",
  "display_name": "Production Repository Scope",
  "owner": "<principal-uri>",
  "created_at": 1711036800000,
  "policy": {
    "allowed_tools": ["github.pr.create", "github.pr.read", "file.read", "file.write"],
    "denied_tools": ["shell.exec", "network.arbitrary"],
    "allowed_data_labels": ["PUBLIC", "INTERNAL"],
    "denied_data_labels": ["RESTRICTED"],
    "cross_vtz_policy": "DENY",
    "max_session_duration_ms": 3600000,
    "max_concurrent_sessions": 5
  },
  "resource_bindings": [
    {
      "resource_type": "repository",
      "resource_id": "github.com/org/repo",
      "permissions": ["read", "write", "pr.create"]
    }
  ]
}
```

| Field | Type | Constraints |
|---|---|---|
| `vtz_id` | string | 1–128 chars, `[a-zA-Z0-9._-]`. Unique per deployment. |
| `display_name` | string | 1–256 chars. Human-readable. |
| `owner` | string | Principal URI. Must be a valid principal. |
| `created_at` | int | UTC-ms. |
| `policy.allowed_tools` | [string] | Tool identifiers that are permitted. Empty = deny all. |
| `policy.denied_tools` | [string] | Explicit denials. Deny takes precedence over allow. |
| `policy.allowed_data_labels` | [string] | DTL labels permitted for processing. |
| `policy.denied_data_labels` | [string] | DTL labels denied. Deny precedence. |
| `policy.cross_vtz_policy` | string | One of: `DENY`, `AUTHORIZE_EXPLICIT`. Default `DENY`. |
| `policy.max_session_duration_ms` | int | Maximum session lifetime. 0 = use system default. |
| `policy.max_concurrent_sessions` | int | ≥ 1. |
| `resource_bindings` | [ResourceBinding] | Resources accessible within this VTZ. |

### 4.3 ResourceBinding

```jsonc
{
  "resource_type": "repository",       // string