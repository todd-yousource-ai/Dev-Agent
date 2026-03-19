

# INTERFACES.md — Forge Platform

## Definitive Wire Format and API Contract Reference

**Version:** 1.0
**Authority:** This document is the canonical reference for every interface contract, wire format, data structure, enum, validation rule, and cross-subsystem protocol in the Forge platform. All implementations MUST conform to these specifications. Conflicts with code are resolved in favor of this document.

**Scope:** All subsystems — macOS Application Shell, Consensus Engine, Pipeline, IPC, Trust/Identity (CAL, CTX-ID, VTZ, TrustFlow, TrustLock, DTL), Audit, GitHub Operations, UI, Settings, and Logging.

---

## Table of Contents

1. [Foundational Conventions](#1-foundational-conventions)
2. [CTX-ID — Context Identity Tokens](#2-ctx-id--context-identity-tokens)
3. [VTZ — Virtual Trust Zones](#3-vtz--virtual-trust-zones)
4. [TrustFlow — Security Event Stream](#4-trustflow--security-event-stream)
5. [TrustLock — Cryptographic Validation](#5-trustlock--cryptographic-validation)
6. [DTL — Data Trust Labels](#6-dtl--data-trust-labels)
7. [CAL — Contextual Authorization Layer](#7-cal--contextual-authorization-layer)
8. [IPC — Inter-Process Communication](#8-ipc--inter-process-communication)
9. [Consensus Engine](#9-consensus-engine)
10. [Pipeline — PRD / PR Decomposition and Execution](#10-pipeline--prd--pr-decomposition-and-execution)
11. [GitHub Operations](#11-github-operations)
12. [Audit Subsystem](#12-audit-subsystem)
13. [macOS Application Shell](#13-macos-application-shell)
14. [Settings and Configuration](#14-settings-and-configuration)
15. [UI View Models and State](#15-ui-view-models-and-state)
16. [Logging](#16-logging)
17. [Enums and Constants — Master Reference](#17-enums-and-constants--master-reference)
18. [Validation Rules — Master Reference](#18-validation-rules--master-reference)
19. [Wire Format Examples — Master Reference](#19-wire-format-examples--master-reference)
20. [Cross-Subsystem Protocol Matrix](#20-cross-subsystem-protocol-matrix)

---

## 1. Foundational Conventions

### 1.1 Serialization

| Property | Requirement |
|---|---|
| Wire format | Line-delimited JSON (LDJSON). One JSON object per line. No pretty-printing on the wire. |
| Encoding | UTF-8. No BOM. |
| Line terminator | `\n` (0x0A). |
| Max message size | 16 MiB per line. Messages exceeding this MUST be rejected. |
| Numeric precision | Integers: signed 64-bit. Floats: IEEE 754 double. |
| Timestamps | UTC Unix timestamp, millisecond precision, represented as integer (not float). Field name: `ts`. |
| Identifiers | Unless otherwise noted, all IDs are hex-encoded strings from 128-bit CSPRNG output (32 hex chars). |
| Hashing | SHA-256. Represented as lowercase hex string (64 chars). |
| Null handling | Explicit `null` in JSON. Missing keys and `null` are semantically distinct — missing keys are protocol errors. |
| Boolean representation | JSON `true`/`false`. Never `0`/`1`, `"yes"`/`"no"`. |
| String constraints | No control characters (U+0000–U+001F) except `\n` in designated freetext fields. |

### 1.2 Versioning

Every top-level message on IPC and every persisted data structure includes a `v` field:

```
"v": 1
```

Receivers MUST reject messages with unknown major versions. Minor version negotiation is not supported — the version integer is the major version.

### 1.3 Error Representation (Universal)

All subsystems use this error envelope when returning errors:

```json
{
  "error": {
    "code": "STRING_ERROR_CODE",
    "component": "subsystem_name",
    "operation": "operation_name",
    "reason": "Human-readable failure description",
    "ctx_id": "hex_string_or_null",
    "ts": 1719000000000
  }
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `code` | string | YES | Must be a value from `ErrorCode` enum (§17). |
| `component` | string | YES | Originating subsystem identifier. |
| `operation` | string | YES | Operation that failed. |
| `reason` | string | YES | MUST NOT contain keys, tokens, secrets, or cleartext payloads. |
| `ctx_id` | string \| null | YES | The CTX-ID in scope when the error occurred, or `null` if unavailable. |
| `ts` | integer | YES | UTC Unix ms. |

### 1.4 Fail-Closed Semantics

All trust, identity, policy, and cryptographic failures MUST fail closed:

1. **Reject** the action.
2. **Log** the event (audit record BEFORE execution — see §12).
3. **Surface** the error to the caller via the error envelope.
4. **Never** silently continue.

`try/except/pass` (or equivalent) is **BANNED** in all enforcement code paths.

---

## 2. CTX-ID — Context Identity Tokens

### 2.1 Purpose

A CTX-ID is an immutable, cryptographically signed token that binds an agent session to an identity, a VTZ, and a time window. Every action in the system requires a valid CTX-ID.

### 2.2 Data Structure

```json
{
  "ctx_id": "a1b2c3d4e5f6...",
  "session_id": "f6e5d4c3b2a1...",
  "vtz_id": "zone_repo_main",
  "principal": "user@example.com",
  "issued_at": 1719000000000,
  "expires_at": 1719003600000,
  "scope": ["repo:read", "repo:write", "pr:create"],
  "trustlock_key_id": "key_abc123...",
  "signature": "hex_encoded_ed25519_signature",
  "v": 1
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `ctx_id` | string | YES | 32 hex chars. CSPRNG-generated. Globally unique. |
| `session_id` | string | YES | 32 hex chars. Binds to the session that requested issuance. |
| `vtz_id` | string | YES | Must match an active VTZ definition. Format: `zone_{scope}_{qualifier}`. |
| `principal` | string | YES | Authenticated identity. Email or service account URI. Max 256 chars. |
| `issued_at` | integer | YES | UTC Unix ms. Must be ≤ current time + clock_skew_tolerance. |
| `expires_at` | integer | YES | UTC Unix ms. Must be > `issued_at`. Max lifetime: 3600000 ms (1 hour). |
| `scope` | array[string] | YES | Non-empty. Each element must be a value from `Scope` enum (§17). |
| `trustlock_key_id` | string | YES | Identifies the TrustLock key pair used to sign this token. |
| `signature` | string | YES | Ed25519 signature over the canonical serialization of all other fields. Hex-encoded. 128 hex chars. |
| `v` | integer | YES | Must be `1`. |

### 2.3 Lifecycle Rules

| Rule | Specification |
|---|---|
| **Immutability** | Once issued, no field may be modified. Any modification invalidates the token. |
| **Rotation** | Creates a new CTX-ID with a new `ctx_id` value. The old token is invalidated immediately and added to the revocation set. |
| **Expiry** | Expired CTX-IDs MUST be rejected. Clock skew tolerance: configurable per deployment, default 5000 ms. |
| **Validation** | MUST be validated against TrustLock public key. Software-only validation (skipping signature check) is rejected. |
| **Missing CTX-ID** | MUST be treated as UNTRUSTED. Never infer identity from context (IP, process ID, etc.). |
| **Revocation** | Revoked tokens are stored in an in-memory set with periodic persistence. Revocation checks happen before signature verification (fast-path rejection). |

### 2.4 Canonical Serialization for Signing

Fields are serialized in deterministic order for signature computation:

```
ctx_id|session_id|vtz_id|principal|issued_at|expires_at|scope_csv|trustlock_key_id|v
```

- `scope_csv`: scope values sorted lexicographically, joined by `,`.
- All fields are UTF-8 string representations.
- Separator: `|` (U+007C).
- No trailing separator.

### 2.5 Validation Procedure

```
1. Parse JSON. Reject if malformed or missing required fields.
2. Check v == 1. Reject if unknown version.
3. Check ctx_id is in valid format (32 hex chars). Reject otherwise.
4. Check ctx_id is NOT in revocation set. Reject if revoked.
5. Check expires_at > now() - clock_skew_tolerance. Reject if expired.
6. Check issued_at <= now() + clock_skew_tolerance. Reject if issued in future.
7. Check expires_at - issued_at <= 3600000. Reject if lifetime exceeds maximum.
8. Resolve trustlock_key_id to a public key. Reject if key is unknown or revoked.
9. Compute canonical serialization (§2.4).
10. Verify Ed25519 signature. Reject if invalid.
11. Validate vtz_id references an active VTZ. Reject if VTZ is unknown or suspended.
12. Validate each scope value is a known Scope enum member. Reject if any unknown.
13. Return validated CTX-ID for use in enforcement.
```

Every rejection produces an error envelope (§1.3) with `component: "ctx_id"` and the appropriate `ErrorCode`.

---

## 3. VTZ — Virtual Trust Zones

### 3.1 Purpose

A VTZ defines a structural security boundary. Every agent session is bound to exactly one VTZ at CTX-ID issuance. VTZ boundaries are **structural, not advisory** — enforcement cannot be bypassed by application code.

### 3.2 Data Structure

```json
{
  "vtz_id": "zone_repo_main",
  "display_name": "Main Repository Zone",
  "status": "active",
  "policy": {
    "allowed_scopes": ["repo:read", "repo:write", "pr:create", "pr:merge"],
    "allowed_tools": ["git_clone", "git_push", "file_read", "file_write", "gh_api"],
    "cross_vtz_policy": "deny",
    "max_session_lifetime_ms": 3600000,
    "require_biometric": true,
    "data_classification_floor": "internal"
  },
  "resource_bindings": [
    {
      "resource_type": "repository",
      "resource_id": "org/repo-name",
      "access": "read_write"
    }
  ],
  "created_at": 1719000000000,
  "updated_at": 1719000000000,
  "v": 1
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `vtz_id` | string | YES | Format: `zone_{scope}_{qualifier}`. Max 128 chars. Alphanumeric, underscores, hyphens. |