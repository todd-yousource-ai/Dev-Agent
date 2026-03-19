

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0
**Status:** Normative — all implementations MUST conform
**Authority:** TRD-1 through TRD-12, CLAUDE.md, AGENTS.md, Forge Interface Contracts
**Last Updated:** 2026-03-19

---

## Table of Contents

1. [Conventions and Notation](#1-conventions-and-notation)
2. [Transport Layer](#2-transport-layer)
3. [CTX-ID — Contextual Identity Token](#3-ctx-id--contextual-identity-token)
4. [VTZ — Virtual Trust Zone](#4-vtz--virtual-trust-zone)
5. [CAL — Consensus Action Layer](#5-cal--consensus-action-layer)
6. [TrustFlow — Audit Event Stream](#6-trustflow--audit-event-stream)
7. [DTL — Data Trust Labels](#7-dtl--data-trust-labels)
8. [TrustLock — Cryptographic Identity](#8-trustlock--cryptographic-identity)
9. [Shell ↔ Backend IPC Protocol](#9-shell--backend-ipc-protocol)
10. [Consensus Engine](#10-consensus-engine)
11. [Pipeline & PRD Subsystem](#11-pipeline--prd-subsystem)
12. [GitHub Integration](#12-github-integration)
13. [Provider Adapter Interface](#13-provider-adapter-interface)
14. [Keychain & Secrets](#14-keychain--secrets)
15. [Auto-Update (Sparkle)](#15-auto-update-sparkle)
16. [UI State Machine](#16-ui-state-machine)
17. [Cross-Subsystem Protocols](#17-cross-subsystem-protocols)
18. [Enums and Constants](#18-enums-and-constants)
19. [Validation Rules](#19-validation-rules)
20. [Wire Format Examples](#20-wire-format-examples)

---

## 1. Conventions and Notation

| Convention | Meaning |
|---|---|
| `MUST` / `MUST NOT` | Absolute requirement per RFC 2119 |
| `REQUIRED` | Field is non-optional; absence is a validation error |
| `OPTIONAL` | Field may be absent; consumers MUST handle absence |
| `CSPRNG` | Cryptographically Secure Pseudo-Random Number Generator |
| `⊥` | Bottom / undefined — indicates the value MUST NOT exist |
| `snake_case` | All wire-format field names |
| `UPPER_SNAKE` | All enum values |
| `ISO-8601` | Date-time strings unless otherwise specified |
| `SHA-256` | Default hash algorithm unless otherwise specified |
| All sizes | Bytes unless otherwise specified |
| All timestamps | UTC Unix milliseconds unless otherwise specified |

### Type Aliases

```
type Identifier   = string          # 32-byte hex-encoded CSPRNG output (64 chars)
type Timestamp     = uint64          # UTC Unix time in milliseconds
type Hash          = string          # Hex-encoded SHA-256 (64 chars)
type PEM           = string          # PEM-encoded key material
type SessionId     = Identifier
type EventId       = Identifier
type CtxId         = Identifier
type VtzId         = Identifier
type ActionId      = Identifier
type PrId          = Identifier
type PrdId         = Identifier
```

---

## 2. Transport Layer

### 2.1 Shell ↔ Backend: Authenticated Unix Domain Socket

| Property | Value |
|---|---|
| Socket type | `AF_UNIX`, `SOCK_STREAM` |
| Path | `$XDG_RUNTIME_DIR/forge/ipc.sock` or `~/Library/Application Support/Forge/ipc.sock` |
| Permissions | `0600` — owner read/write only |
| Framing | Newline-delimited JSON (`\n` terminator, U+000A) |
| Encoding | UTF-8, no BOM |
| Max message size | 16 MiB per frame |
| Authentication | Session token exchanged at connection handshake (see §9.2) |
| Keepalive | Heartbeat every 30 seconds; 3 missed = connection dead |

### 2.2 Backend ↔ LLM Providers: HTTPS

| Property | Value |
|---|---|
| Protocol | HTTPS/1.1 minimum, HTTP/2 preferred |
| TLS | TLS 1.3 required; TLS 1.2 accepted with AEAD ciphers only |
| Certificate pinning | Not required; system trust store is authoritative |
| Timeouts | Connect: 10s, Read: 120s, Write: 30s |
| Retries | 3 attempts with exponential backoff (1s, 2s, 4s) + jitter |

### 2.3 Backend ↔ GitHub: HTTPS REST/GraphQL

| Property | Value |
|---|---|
| Auth | `Authorization: Bearer <PAT>` or GitHub App installation token |
| API version | `2022-11-28` (Accept header) |
| Rate limit | Respect `X-RateLimit-Remaining`; back off at ≤ 100 remaining |

---

## 3. CTX-ID — Contextual Identity Token

### 3.1 Data Structure

```json
{
  "ctx_id":          "<Identifier>",
  "session_id":      "<SessionId>",
  "vtz_id":          "<VtzId>",
  "principal":       "<string>",
  "issued_at":       "<Timestamp>",
  "expires_at":      "<Timestamp>",
  "trustlock_key_id":"<Identifier>",
  "signature":       "<base64>",
  "claims": {
    "roles":         ["<string>"],
    "scopes":        ["<string>"],
    "device_id":     "<Identifier>"
  }
}
```

### 3.2 Field Specifications

| Field | Type | Required | Constraints |
|---|---|---|---|
| `ctx_id` | Identifier | REQUIRED | 64 hex chars, CSPRNG-generated, globally unique |
| `session_id` | SessionId | REQUIRED | References active session |
| `vtz_id` | VtzId | REQUIRED | Binds token to exactly one VTZ |
| `principal` | string | REQUIRED | 1–256 chars, UTF-8, no control characters |
| `issued_at` | Timestamp | REQUIRED | MUST be ≤ current time |
| `expires_at` | Timestamp | REQUIRED | MUST be > `issued_at`; max TTL = 86400000 ms (24h) |
| `trustlock_key_id` | Identifier | REQUIRED | References the TrustLock signing key |
| `signature` | string | REQUIRED | Base64-encoded Ed25519 or ECDSA-P256 signature over canonical form |
| `claims.roles` | string[] | REQUIRED | At least one role; values from `RoleEnum` |
| `claims.scopes` | string[] | REQUIRED | At least one scope; values from `ScopeEnum` |
| `claims.device_id` | Identifier | OPTIONAL | Hardware-bound device identifier |

### 3.3 Immutability Contract

- CTX-ID tokens are **IMMUTABLE** once issued — no field modification after issuance.
- CTX-ID rotation creates a **new** token; the old one is invalidated **immediately**.
- Expired CTX-ID MUST be rejected — clock skew tolerance: **5000 ms**.
- CTX-ID MUST be validated against TrustLock public key — software-only validation is **rejected**.
- Missing CTX-ID MUST be treated as **UNTRUSTED** — never infer identity from context.

### 3.4 Canonical Serialization (for Signing)

Fields are serialized in lexicographic key order, with no whitespace, using canonical JSON (RFC 8785). The `signature` field is excluded from the signing input.

```
signing_input = canonical_json(ctx_id_object \ {signature})
signature = sign(private_key, SHA-256(signing_input))
```

---

## 4. VTZ — Virtual Trust Zone

### 4.1 Data Structure

```json
{
  "vtz_id":          "<VtzId>",
  "name":            "<string>",
  "created_at":      "<Timestamp>",
  "policy": {
    "allowed_tools":   ["<string>"],
    "denied_tools":    ["<string>"],
    "max_file_ops":    "<uint32>",
    "max_net_ops":     "<uint32>",
    "allowed_hosts":   ["<string>"],
    "data_ceiling":    "<DTLClassification>",
    "cross_vtz":       "<CrossVtzPolicy>"
  },
  "boundaries": {
    "paths":           ["<string>"],
    "repos":           ["<string>"],
    "environments":    ["<string>"]
  }
}
```

### 4.2 Field Specifications

| Field | Type | Required | Constraints |
|---|---|---|---|
| `vtz_id` | VtzId | REQUIRED | 64 hex chars, CSPRNG-generated |
| `name` | string | REQUIRED | 1–128 chars, `[a-zA-Z0-9_-]` |
| `created_at` | Timestamp | REQUIRED | Immutable after creation |
| `policy.allowed_tools` | string[] | REQUIRED | Whitelist; empty = deny all |
| `policy.denied_tools` | string[] | OPTIONAL | Blacklist; takes precedence over allowed |
| `policy.max_file_ops` | uint32 | REQUIRED | Per-session limit; 0 = no file ops |
| `policy.max_net_ops` | uint32 | REQUIRED | Per-session limit; 0 = no network ops |
| `policy.allowed_hosts` | string[] | OPTIONAL | FQDN list; empty = deny all outbound |
| `policy.data_ceiling` | DTLClassification | REQUIRED | Maximum DTL label allowed in zone |
| `policy.cross_vtz` | CrossVtzPolicy | REQUIRED | `DENY`, `EXPLICIT_GRANT`, or `AUDIT_ONLY` |
| `boundaries.paths` | string[] | REQUIRED | Filesystem path prefixes this VTZ may access |
| `boundaries.repos` | string[] | OPTIONAL | GitHub `owner/repo` patterns |
| `boundaries.environments` | string[] | OPTIONAL | CI environment names |

### 4.3 Enforcement Contract

- Every agent session is bound to **EXACTLY ONE** VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require **explicit policy authorization** — implicit is denied.
- VTZ boundaries are **structural, not advisory** — enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at **NEXT CTX-ID issuance**, not mid-session.

---

## 5. CAL — Consensus Action Layer

### 5.1 Action Request

```json
{
  "action_id":       "<ActionId>",
  "ctx_id":          "<CtxId>",
  "session_id":      "<SessionId>",
  "action_type":     "<ActionType>",
  "tool":            "<string>",
  "parameters":      {},
  "payload":         "<base64>",
  "payload_hash":    "<Hash>",
  "requested_at":    "<Timestamp>"
}
```

### 5.2 Field Specifications

| Field | Type | Required | Constraints |
|---|---|---|---|
| `action_id` | ActionId | REQUIRED | CSPRNG, globally unique |
| `ctx_id` | CtxId | REQUIRED | MUST reference valid, non-expired CTX-ID |
| `session_id` | SessionId | REQUIRED | MUST match CTX-ID's session |
| `action_type` | ActionType | REQUIRED