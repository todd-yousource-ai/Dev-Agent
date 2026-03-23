

# INTERFACES.md — Forge Platform Interface Contracts

**Version:** 1.0
**Status:** Normative — all implementations MUST conform
**Authority:** TRD-1 through TRD-16, AGENTS.md, CLAUDE.md, Forge Component Interface Contracts
**Last Updated:** 2026-03-19

---

## Table of Contents

1. [Overview and Conventions](#1-overview-and-conventions)
2. [Cross-Subsystem Protocols](#2-cross-subsystem-protocols)
3. [CTX-ID — Contextual Identity](#3-ctx-id--contextual-identity)
4. [CAL — Contextual Authorization Layer](#4-cal--contextual-authorization-layer)
5. [VTZ — Virtual Trust Zones](#5-vtz--virtual-trust-zones)
6. [TrustFlow — Audit Event Stream](#6-trustflow--audit-event-stream)
7. [TrustLock — Cryptographic Identity Binding](#7-trustlock--cryptographic-identity-binding)
8. [DTL — Data Trust Labels](#8-dtl--data-trust-labels)
9. [Shell ↔ Backend IPC Protocol](#9-shell--backend-ipc-protocol)
10. [Consensus Engine](#10-consensus-engine)
11. [Provider Adapters](#11-provider-adapters)
12. [Pipeline — PRD / PR Decomposition](#12-pipeline--prd--pr-decomposition)
13. [GitHub Operations](#13-github-operations)
14. [Authentication and Session Lifecycle](#14-authentication-and-session-lifecycle)
15. [Keychain and Secret Storage](#15-keychain-and-secret-storage)
16. [UI State Machine](#16-ui-state-machine)
17. [Error Contract](#17-error-contract)
18. [Enums and Constants](#18-enums-and-constants)
19. [Validation Rules](#19-validation-rules)
20. [Wire Format Examples](#20-wire-format-examples)

---

## 1. Overview and Conventions

### 1.1 Notation

| Convention | Meaning |
|---|---|
| `MUST` / `MUST NOT` | Absolute requirement per RFC 2119 |
| `field: Type` | Field name and its type; all types use JSON-native representations on the wire |
| `[Type]` | Array of Type |
| `Type?` | Nullable / optional field |
| `CSPRNG` | Cryptographically Secure Pseudo-Random Number Generator |
| `LD-JSON` | Line-Delimited JSON — one JSON object per `\n`-terminated line |
| `UTC-ms` | UTC Unix timestamp with millisecond precision (integer, not float) |

### 1.2 Wire Format Baseline

All inter-process and inter-subsystem communication uses **line-delimited JSON (LD-JSON)** over the transport specified per interface. Every JSON line MUST be:

- Valid JSON (RFC 8259)
- Terminated by a single `\n` (0x0A)
- No larger than **1 MiB** per line unless the specific interface states otherwise
- UTF-8 encoded, no BOM

### 1.3 Byte Ordering and Encoding

- All strings: UTF-8
- All hashes: lowercase hex unless stated otherwise
- All timestamps: integer milliseconds since Unix epoch, UTC
- All UUIDs: lowercase RFC 4122 with hyphens (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- All binary blobs on JSON wire: base64url (RFC 4648 §5), no padding

### 1.4 Versioning

Every message envelope includes a `v` field. Receivers MUST reject messages with unknown major versions. Minor version differences MUST be forward-compatible (new fields are ignored by older consumers).

---

## 2. Cross-Subsystem Protocols

### 2.1 Protocol Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     macOS Application Shell (Swift)             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Auth/     │  │ Keychain │  │ UI State  │  │ TrustLock    │  │
│  │ Session   │  │ Store    │  │ Machine   │  │ (Secure      │  │
│  │ Manager   │  │          │  │ (TRD-8)   │  │  Enclave)    │  │
│  └─────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
│        │              │              │               │          │
│        └──────────────┴──────┬───────┴───────────────┘          │
│                              │                                  │
│                    ┌─────────▼──────────┐                       │
│                    │  IPC Socket Server │                       │
│                    │  (Authenticated    │                       │
│                    │   Unix Domain)     │                       │
│                    └─────────┬──────────┘                       │
└──────────────────────────────┼──────────────────────────────────┘
                               │ LD-JSON over UDS
┌──────────────────────────────┼──────────────────────────────────┐
│                     Python Backend                              │
│                    ┌─────────▼──────────┐                       │
│                    │  IPC Socket Client │                       │
│                    └─────────┬──────────┘                       │
│        ┌─────────────┬───────┴────────┬──────────────┐         │
│  ┌─────▼─────┐ ┌─────▼──────┐  ┌─────▼─────┐  ┌─────▼──────┐ │
│  │ Consensus │ │ Pipeline   │  │ GitHub    │  │ CAL / VTZ  │ │
│  │ Engine    │ │ (PRD→PR)   │  │ Ops       │  │ Enforcer   │ │
│  └───────────┘ └────────────┘  └───────────┘  └────────────┘ │
│        │              │              │               │          │
│  ┌─────▼──────────────▼──────────────▼───────────────▼──────┐  │
│  │                    TrustFlow Bus                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Transport Summary

| Interface | Transport | Auth | Direction |
|---|---|---|---|
| Shell ↔ Backend IPC | Unix Domain Socket | CTX-ID in handshake | Bidirectional |
| Backend → LLM Providers | HTTPS | Bearer token (from Keychain via Shell) | Request/Response |
| Backend → GitHub API | HTTPS | PAT or GitHub App JWT (from Keychain) | Request/Response |
| TrustFlow events | In-process bus + append-only file | Session-scoped | Emit-only |
| TrustLock ↔ Secure Enclave | XPC (Apple-internal) | Entitlement-gated | Request/Response |
| Sparkle Updates | HTTPS (appcast) | Ed25519 signature | Pull |

### 2.3 Message Envelope

Every LD-JSON message over IPC MUST use this envelope:

```
MessageEnvelope {
  v:          string        // Protocol version: "<major>.<minor>", e.g. "1.0"
  id:         string        // Message ID — UUID v4, lowercase
  ts:         integer       // UTC-ms timestamp
  ctx_id:     string        // CTX-ID token (opaque string, see §3)
  type:       string        // Message type discriminator (see §9)
  payload:    object        // Type-specific payload
  hmac:       string        // HMAC-SHA256 of canonical payload, hex — keyed by session secret
}
```

**Canonical form for HMAC:** UTF-8 bytes of the `payload` object serialized with keys sorted lexicographically, no whitespace. The HMAC key is the session secret negotiated during IPC handshake (§9.2).

---

## 3. CTX-ID — Contextual Identity

### 3.1 Token Structure

CTX-ID is an opaque bearer token on the wire. Internally it is a signed JWT (RFC 7519) with the following claims:

```
CTXIDClaims {
  jti:        string        // Token ID — CSPRNG, globally unique, 128-bit hex
  sub:        string        // Subject — user identity hash (SHA-256 of Apple ID or local user ID)
  vtz:        string        // VTZ identifier this session is bound to
  iat:        integer       // Issued-at — UTC-ms
  exp:        integer       // Expiry — UTC-ms
  nonce:      string        // CSPRNG 256-bit, hex — replay prevention
  cap:        [string]      // Capabilities granted (see §18.1 for enum)
  tl_kid:     string        // TrustLock key ID used to sign this token
}
```

### 3.2 Signing

- Signed with ES256 (ECDSA P-256) using the TrustLock private key held in Secure Enclave
- Signature is over the standard JWT header + claims
- Public key is retrievable via TrustLock interface (§7)

### 3.3 Lifecycle

| State | Transition | Rule |
|---|---|---|
| `ISSUED` | Created at session start or rotation | Claims are frozen at this point |
| `ACTIVE` | Validated successfully | `iat <= now <= exp` and signature valid |
| `EXPIRED` | `now > exp` | MUST be rejected; no grace period beyond deployment-configured clock skew |
| `REVOKED` | Explicit revocation or rotation | Old token added to revocation set; MUST be rejected |

### 3.4 Constraints

| Constraint | Value |
|---|---|
| Max token lifetime | 3600000 ms (1 hour) |
| Clock skew tolerance | Deployment-configured, default 5000 ms |
| Token size ceiling | 4096 bytes |
| Immutability | No field modification after issuance — any change requires new token |
| Missing CTX-ID | Treated as `UNTRUSTED` — never infer identity from context |

### 3.5 Validation Procedure

```
FUNCTION validate_ctx_id(token: string) -> CTXIDValidationResult:
  1. Decode JWT header — reject if alg != "ES256"
  2. Extract tl_kid from claims
  3. Retrieve public key from TrustLock by tl_kid — reject if key not found
  4. Verify ES256 signature — reject if invalid
  5. Check exp: reject if now_utc_ms > exp + clock_skew_tolerance
  6. Check iat: reject if iat > now_utc_ms + clock_skew_tolerance
  7. Check revocation set: reject if jti is in set
  8. Check nonce uniqueness: reject if nonce was previously seen within exp window
  9. Return CTXIDValidationResult { valid: true, claims: <parsed claims> }
```

```
CTXIDValidationResult {
  valid:      boolean
  claims:     CTXIDClaims?     // Present only when valid=true
  error:      string?          // Present only when valid=false
  checked_at: integer          // UTC-ms of validation
}
```

---

## 4. CAL — Contextual Authorization Layer

### 4.1 Purpose

CAL is the central enforcement point.