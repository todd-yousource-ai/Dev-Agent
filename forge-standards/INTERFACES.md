

# INTERFACES.md — Forge Platform

## Definitive Wire Format and API Contract Reference

**Version:** 1.0.0
**Status:** Normative
**Authority:** This document is the single source of truth for all inter-component data structures, protocols, wire formats, and validation rules across the Forge platform. Any implementation that contradicts this document is non-conformant.

---

## Table of Contents

1. [Conventions and Notation](#1-conventions-and-notation)
2. [Per-Subsystem Data Structures](#2-per-subsystem-data-structures)
   - 2.1 [CAL — Contextual Authorization Layer](#21-cal--contextual-authorization-layer)
   - 2.2 [CTX-ID — Contextual Identity Tokens](#22-ctx-id--contextual-identity-tokens)
   - 2.3 [VTZ — Virtual Trust Zones](#23-vtz--virtual-trust-zones)
   - 2.4 [TrustFlow — Audit Event Stream](#24-trustflow--audit-event-stream)
   - 2.5 [TrustLock — Cryptographic Verification](#25-trustlock--cryptographic-verification)
   - 2.6 [DTL — Data Trust Labels](#26-dtl--data-trust-labels)
   - 2.7 [macOS Application Shell (TRD-1)](#27-macos-application-shell-trd-1)
   - 2.8 [Document Store and Retrieval Engine (TRD-10)](#28-document-store-and-retrieval-engine-trd-10)
   - 2.9 [Security Threat Model Structures (TRD-11)](#29-security-threat-model-structures-trd-11)
   - 2.10 [Backend Runtime Startup and Version Handshake (TRD-12)](#210-backend-runtime-startup-and-version-handshake-trd-12)
3. [Cross-Subsystem Protocols](#3-cross-subsystem-protocols)
   - 3.1 [XPC Bridge Protocol (Swift ↔ Python)](#31-xpc-bridge-protocol-swift--python)
   - 3.2 [CAL Enforcement Protocol](#32-cal-enforcement-protocol)
   - 3.3 [Document Retrieval Protocol](#33-document-retrieval-protocol)
   - 3.4 [Backend Startup Handshake Protocol](#34-backend-startup-handshake-protocol)
   - 3.5 [Session Lifecycle Protocol](#35-session-lifecycle-protocol)
   - 3.6 [Graceful Shutdown Protocol](#36-graceful-shutdown-protocol)
   - 3.7 [Auto-Update Protocol](#37-auto-update-protocol)
4. [Enums and Constants](#4-enums-and-constants)
5. [Validation Rules](#5-validation-rules)
6. [Wire Format Examples](#6-wire-format-examples)

---

## 1. Conventions and Notation

| Convention | Meaning |
|---|---|
| `MUST` / `MUST NOT` | Absolute requirement per RFC 2119 |
| `SHOULD` / `SHOULD NOT` | Recommended unless compelling reason exists |
| `field: Type` | Field name followed by its type |
| `Type?` | Nullable / optional field |
| `Type[]` | Array of Type |
| `[K: V]` | Dictionary with key type K and value type V |
| `bytes` | Raw byte sequence; encoding specified per field |
| `string` | UTF-8 encoded text |
| `u64` | Unsigned 64-bit integer |
| `i64` | Signed 64-bit integer |
| `f64` | IEEE 754 double-precision float |
| `uuid` | RFC 4122 v4 UUID, lowercase hex with hyphens |
| `timestamp` | UTC Unix timestamp, millisecond precision, u64 |
| `sha256` | Lowercase hex-encoded SHA-256 digest (64 chars) |

**Serialization default:** All wire formats use JSON (RFC 8259) with UTF-8 encoding unless explicitly stated otherwise. Binary payloads use Base64url (RFC 4648 §5) encoding within JSON fields.

**Byte order:** Network byte order (big-endian) for all binary protocols.

**Size limits:** All string fields are capped at 65,536 bytes UTF-8 unless a tighter bound is specified. All JSON messages are capped at 16 MiB unless a tighter bound is specified.

---

## 2. Per-Subsystem Data Structures

### 2.1 CAL — Contextual Authorization Layer

The CAL is the central enforcement gateway. Every agent action transits CAL before execution.

#### 2.1.1 `CALRequest`

Submitted by any component requesting authorization for an agent action.

```json
{
  "request_id": "uuid",
  "ctx_id": "string",
  "session_id": "uuid",
  "action": "ActionDescriptor",
  "timestamp": "timestamp",
  "payload_hash": "sha256",
  "source_component": "string",
  "vtz_id": "string"
}
```

| Field | Type | Constraints | Description |
|---|---|---|---|
| `request_id` | uuid | MUST be globally unique, CSPRNG-generated | Idempotency key for this request |
| `ctx_id` | string | MUST be a valid, non-expired CTX-ID token | Identity context for authorization |
| `session_id` | uuid | MUST match the session bound to `ctx_id` | Session scope |
| `action` | ActionDescriptor | MUST be a valid action descriptor (see §2.1.2) | What the agent wants to do |
| `timestamp` | timestamp | MUST be within 30s of server time | When the request was created |
| `payload_hash` | sha256 | SHA-256 of the serialized action payload | Integrity verification |
| `source_component` | string | Max 128 chars, `[a-zA-Z0-9._-]+` | Component originating the request |
| `vtz_id` | string | MUST match VTZ bound to the session | Trust zone context |

#### 2.1.2 `ActionDescriptor`

```json
{
  "action_type": "ActionType",
  "resource": "string",
  "operation": "OperationType",
  "parameters": "object?",
  "dtl_labels": "DTLLabel[]"
}
```

| Field | Type | Constraints | Description |
|---|---|---|---|
| `action_type` | ActionType | Enum (see §4) | Category of action |
| `resource` | string | Max 1024 chars, URI format | Target resource identifier |
| `operation` | OperationType | Enum (see §4) | Specific operation on resource |
| `parameters` | object? | Max 1 MiB serialized | Action-specific parameters |
| `dtl_labels` | DTLLabel[] | At least one label MUST be present | Data classification of involved data |

#### 2.1.3 `CALDecision`

Returned by CAL after enforcement evaluation.

```json
{
  "request_id": "uuid",
  "decision_id": "uuid",
  "verdict": "Verdict",
  "reason": "string",
  "restrictions": "Restriction[]?",
  "vtz_enforcement": "VTZEnforcementDecision",
  "trustflow_event_id": "uuid",
  "decided_at": "timestamp",
  "expires_at": "timestamp?"
}
```

| Field | Type | Constraints | Description |
|---|---|---|---|
| `request_id` | uuid | MUST match the originating request | Correlation key |
| `decision_id` | uuid | CSPRNG-generated | Unique identifier for this decision |
| `verdict` | Verdict | Enum: `allow`, `restrict`, `block` | Authorization outcome |
| `reason` | string | Max 2048 chars, MUST NOT contain secrets | Human-readable explanation |
| `restrictions` | Restriction[]? | Present when verdict is `restrict` | Conditions imposed on execution |
| `vtz_enforcement` | VTZEnforcementDecision | Always present | VTZ-specific enforcement details |
| `trustflow_event_id` | uuid | MUST match emitted TrustFlow event | Audit trail correlation |
| `decided_at` | timestamp | Server-generated | When the decision was made |
| `expires_at` | timestamp? | If set, decision is invalid after this time | Time-bounded authorization |

#### 2.1.4 `Restriction`

```json
{
  "restriction_type": "RestrictionType",
  "constraint": "string",
  "enforced_by": "string"
}
```

| Field | Type | Constraints | Description |
|---|---|---|---|
| `restriction_type` | RestrictionType | Enum (see §4) | Category of restriction |
| `constraint` | string | Max 2048 chars | Machine-parseable constraint expression |
| `enforced_by` | string | Valid component identifier | Component responsible for enforcement |

---

### 2.2 CTX-ID — Contextual Identity Tokens

CTX-ID tokens are the identity primitive for the entire platform. They are **immutable once issued**.

#### 2.2.1 `CTXIDToken`

```json
{
  "token_id": "uuid",
  "subject": "string",
  "vtz_id": "string",
  "issued_at": "timestamp",
  "expires_at": "timestamp",
  "issuer": "string",
  "public_key_fingerprint": "sha256",
  "signature": "string",
  "claims": "CTXIDClaims",
  "rotation_parent": "uuid?"
}
```

| Field | Type | Constraints | Description |
|---|---|---|---|
| `token_id` | uuid | CSPRNG-generated, globally unique | Immutable token identifier |
| `subject` | string | Max 256 chars | Authenticated principal |
| `vtz_id` | string | Max 128 chars, `[a-zA-Z0-9._-]+` | Bound VTZ at issuance time; immutable |
| `issued_at` | timestamp | MUST be ≤ current time | Issuance moment |
| `expires_at` | timestamp | MUST be > `issued_at`; max lifetime 24h | Expiry moment |
| `issuer` | string | MUST be a recognized issuer identifier | Token issuer |
| `public_key_fingerprint` | sha256 | SHA-256 of the TrustLock public key used | Key binding |
| `signature` | string | Base64url-encoded Ed25519 signature | TrustLock signature over token body |
| `claims` | CTXIDClaims | See §2.2.2 | Authorization claims |
| `rotation_parent` | uuid? | If present, MUST reference an invalidated token | Previous token in rotation chain |

**Immutability contract:** No field of a CTX-ID token may be modified after issuance. Any need for changed claims requires rotation: issue a new token and immediately invalidate the old one.

#### 2.2.2 `CTXIDClaims`

```json
{
  "roles": "string[]",
  "permissions": "string[]",
  "session_id": "uuid",
  "device_id": "string?",
  "biometric_verified": "bool",
  "custom": "[string: string]?"
}
```

| Field | Type | Constraints | Description |
|---|---|---|---|
| `roles` | string[] | Each max 64 chars; at least one | Assigned roles |
| `permissions` | string[] | Each max 128 chars | Granted permissions |
| `session_id` | uuid | MUST match active session | Bound session |
| `device_id` | string? | Max 256 chars | Device binding (macOS hardware UUID) |
| `biometric_verified` | bool | — | Whether biometric authentication succeeded |
| `custom` |