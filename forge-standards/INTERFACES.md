

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0
**Authority:** This document is the definitive reference for every wire format, data structure, protocol, enum, validation rule, and API contract across the Forge platform. All subsystems MUST conform to these specifications. Non-conformant implementations MUST be rejected at code review.

**Governing Documents:** TRD-1 through TRD-12, CLAUDE.md, AGENTS.md, Forge Component Interface Contracts.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Cross-Subsystem Transport Protocol](#2-cross-subsystem-transport-protocol)
3. [Identity & Trust Subsystem (CTX-ID, TrustLock, CAL)](#3-identity--trust-subsystem)
4. [Virtual Trust Zone (VTZ) Enforcement](#4-virtual-trust-zone-vtz-enforcement)
5. [TrustFlow Event System](#5-trustflow-event-system)
6. [Data Trust Labels (DTL)](#6-data-trust-labels-dtl)
7. [XPC Communication Channel (Swift ↔ Python)](#7-xpc-communication-channel-swift--python)
8. [Consensus Engine Interfaces](#8-consensus-engine-interfaces)
9. [Pipeline & PRD Plan Interfaces](#9-pipeline--prd-plan-interfaces)
10. [GitHub Operations Interfaces](#10-github-operations-interfaces)
11. [Authentication & Session Lifecycle](#11-authentication--session-lifecycle)
12. [Settings, Configuration & Onboarding](#12-settings-configuration--onboarding)
13. [Audit Subsystem](#13-audit-subsystem)
14. [Error Contracts](#14-error-contracts)
15. [Enums and Constants](#15-enums-and-constants)
16. [Validation Rules](#16-validation-rules)
17. [Wire Format Examples](#17-wire-format-examples)

---

## 1. Architecture Overview

```
┌──────────────────────────────────┐     ┌──────────────────────────────────┐
│       Swift Shell (macOS)        │     │        Python Backend            │
│                                  │     │                                  │
│  ┌─────────┐  ┌──────────────┐   │     │  ┌───────────────┐              │
│  │ SwiftUI  │  │  Keychain /  │   │     │  │  Consensus    │              │
│  │  Views   │  │  Auth / Bio  │   │     │  │  Engine       │              │
│  └────┬─────┘  └──────┬───────┘   │     │  └───────┬───────┘              │
│       │               │           │     │          │                      │
│  ┌────┴───────────────┴────────┐  │     │  ┌───────┴───────┐             │
│  │     XPC Manager             │──╋─────╋──│  Socket Server │             │
│  │  (Authenticated Unix Socket)│  │     │  │  (IPC Handler) │             │
│  └─────────────────────────────┘  │     │  └───────┬───────┘             │
│                                  │     │          │                      │
│  ┌─────────────────────────────┐  │     │  ┌───────┴───────┐             │
│  │  CAL Enforcement Layer      │  │     │  │  Pipeline /   │             │
│  │  (CTX-ID, VTZ, TrustFlow)  │  │     │  │  GitHub Ops   │             │
│  └─────────────────────────────┘  │     │  └───────────────┘             │
└──────────────────────────────────┘     └──────────────────────────────────┘
```

**Transport:** Authenticated Unix domain socket. Line-delimited JSON (NDJSON). One JSON object per `\n`-terminated line. Neither process ever executes generated code.

---

## 2. Cross-Subsystem Transport Protocol

### 2.1 Socket Path Convention

```
/tmp/forge-{session_id}.sock
```

- `session_id`: 32-character lowercase hex string (128-bit CSPRNG)
- Socket file permissions: `0600` (owner read/write only)
- Owner: the user running the Forge application

### 2.2 Wire Format: Line-Delimited JSON (NDJSON)

Every message is a single JSON object terminated by `\n` (0x0A). No embedded newlines in the JSON body. UTF-8 encoding. No BOM.

### 2.3 Message Envelope

Every message across the socket MUST conform to this envelope:

```typescript
interface ForgeMessage {
  msg_id: string;         // UUIDv4, globally unique per message
  msg_type: MessageType;  // Enum: "request" | "response" | "event" | "error"
  timestamp: number;      // UTC Unix timestamp, millisecond precision
  ctx_id: string;         // CTX-ID token bound to this session
  version: string;        // Protocol version: "1.0"
  payload: object;        // Subsystem-specific payload
}
```

**Field Constraints:**

| Field | Type | Constraints |
|-------|------|-------------|
| `msg_id` | `string` | UUIDv4 format, MUST be unique per message, generated via CSPRNG |
| `msg_type` | `string` | One of: `"request"`, `"response"`, `"event"`, `"error"` |
| `timestamp` | `number` | UTC Unix epoch in milliseconds. MUST NOT be zero. MUST NOT be in the future beyond clock skew tolerance. |
| `ctx_id` | `string` | Valid CTX-ID token. MUST be validated before payload processing. |
| `version` | `string` | Semantic version. Current: `"1.0"` |
| `payload` | `object` | Non-null JSON object. Schema depends on subsystem and operation. |

### 2.4 Request/Response Correlation

```typescript
interface ForgeRequest extends ForgeMessage {
  msg_type: "request";
  payload: {
    operation: string;      // Subsystem-qualified operation name
    params: object;         // Operation-specific parameters
  };
}

interface ForgeResponse extends ForgeMessage {
  msg_type: "response";
  payload: {
    request_id: string;     // msg_id of the originating request
    status: ResponseStatus; // "ok" | "error" | "partial"
    result: object | null;  // Operation result on success
    error: ForgeError | null; // Error detail on failure
  };
}
```

### 2.5 Maximum Message Size

- Soft limit: 1 MB per message
- Hard limit: 16 MB per message
- Messages exceeding the hard limit MUST be rejected with `ERR_MESSAGE_TOO_LARGE`

### 2.6 Keepalive

- Heartbeat interval: 30 seconds
- Heartbeat is a `ForgeMessage` with `msg_type: "event"` and `payload.event_type: "heartbeat"`
- If no message (including heartbeat) is received within 90 seconds, the connection is considered dead

---

## 3. Identity & Trust Subsystem

### 3.1 CTX-ID Token

The CTX-ID is the foundational identity token for every agent action in the Forge platform.

```typescript
interface CTXIDToken {
  ctx_id: string;              // 64-character hex string (256-bit CSPRNG)
  session_id: string;          // 32-character hex string (128-bit CSPRNG)
  vtz_id: string;              // VTZ identifier this token is bound to
  issued_at: number;           // UTC Unix timestamp (ms) of issuance
  expires_at: number;          // UTC Unix timestamp (ms) of expiration
  issuer: string;              // Issuing component identifier
  trust_level: TrustLevel;     // Enum: trust classification at issuance
  public_key_fingerprint: string; // SHA-256 fingerprint of TrustLock public key
  signature: string;           // Ed25519 signature over canonical form
}
```

**Field Constraints:**

| Field | Type | Size | Constraints |
|-------|------|------|-------------|
| `ctx_id` | `string` | 64 chars | Hex-encoded, CSPRNG-generated, globally unique |
| `session_id` | `string` | 32 chars | Hex-encoded, MUST match active session |
| `vtz_id` | `string` | 1–128 chars | Alphanumeric + hyphens, no leading/trailing hyphen |
| `issued_at` | `number` | 8 bytes | MUST be ≤ current time + clock skew tolerance |
| `expires_at` | `number` | 8 bytes | MUST be > `issued_at`. Max TTL: 3600000 ms (1 hour) |
| `issuer` | `string` | 1–256 chars | Dot-separated component path (e.g., `forge.shell.auth`) |
| `trust_level` | `string` | — | One of TrustLevel enum values |
| `public_key_fingerprint` | `string` | 64 chars | SHA-256 hex digest of TrustLock Ed25519 public key |
| `signature` | `string` | 128 chars | Hex-encoded Ed25519 signature |

**Immutability Contract:** CTX-ID tokens are IMMUTABLE once issued. No field may be modified after issuance. Rotation creates a new token; the old one is invalidated immediately.

**Canonical Form for Signing:**

```
ctx_id|session_id|vtz_id|issued_at|expires_at|issuer|trust_level|public_key_fingerprint
```

Fields concatenated with `|` separator. No trailing separator. UTF-8 encoded. Signature is Ed25519 over SHA-256 of this canonical string.

### 3.2 CTX-ID Validation Procedure

Every entry point that processes an agent action MUST execute this procedure FIRST:

```
1. REQUIRE ctx_id field is present and non-empty
   → Missing: REJECT with ERR_CTX_MISSING, trust_level = UNTRUSTED
2. PARSE token fields
   → Parse failure: REJECT with ERR_CTX_MALFORMED
3. CHECK expires_at > current_time - clock_skew_tolerance
   → Expired: REJECT with ERR_CTX_EXPIRED
4. VERIFY signature against TrustLock public key
   → Invalid signature: REJECT with ERR_CTX_SIGNATURE_INVALID
5. VERIFY session_id matches active session
   → Mismatch: REJECT with ERR_CTX_SESSION_MISMATCH
6. VERIFY vtz_id matches requested VTZ scope
   → Mismatch: REJECT with ERR_CTX_VTZ_MISMATCH
7. ACCEPT — proceed to VTZ policy evaluation
```

Clock skew tolerance: **5000 ms** (5 seconds) default, configurable per deployment.

### 3.3 TrustLock Key Management

```typescript
interface TrustLockKeyPair {
  algorithm: "Ed25519";
  public_key: string;          // Base64-encoded Ed25519 public key (44 chars)
  public_key_fingerprint: string; // SHA-256 hex of raw public key bytes
  created_at: number;          // UTC Unix timestamp (ms)
  storage: "keychain";         // MUST be macOS Keychain, never filesystem
}
```

**Storage Rules:**
- Private key: macOS Keychain ONLY, access control = biometric + device passcode
- Public key: may be stored in UserDefaults for validation caching
- Key rotation: new keypair generated, old public key retained for grace period (