

# INTERFACES.md — Forge Platform Wire Format and API Contract Reference

**Version:** 1.0
**Status:** Normative — all implementations MUST conform
**Authority:** TRD-1 through TRD-12, AGENTS.md, CLAUDE.md, Forge Interface Contracts
**Scope:** Every subsystem, every wire format, every data structure, every protocol boundary

---

## Table of Contents

1. [Overview and Conventions](#1-overview-and-conventions)
2. [CTX-ID — Contextual Identity Tokens](#2-ctx-id--contextual-identity-tokens)
3. [VTZ — Virtual Trust Zones](#3-vtz--virtual-trust-zones)
4. [CAL — Contextual Action Layer](#4-cal--contextual-action-layer)
5. [TrustFlow — Audit Event Stream](#5-trustflow--audit-event-stream)
6. [DTL — Data Trust Labels](#6-dtl--data-trust-labels)
7. [TrustLock — Cryptographic Identity Binding](#7-trustlock--cryptographic-identity-binding)
8. [IPC Protocol — Shell ↔ Backend](#8-ipc-protocol--shell--backend)
9. [Consensus Engine Protocol](#9-consensus-engine-protocol)
10. [GitHub Operations Interface](#10-github-operations-interface)
11. [Pipeline & PRD Decomposition](#11-pipeline--prd-decomposition)
12. [Keychain & Credential Interface](#12-keychain--credential-interface)
13. [UI State Machine & View Contracts](#13-ui-state-machine--view-contracts)
14. [Auto-Update (Sparkle) Interface](#14-auto-update-sparkle-interface)
15. [Cross-Subsystem Protocols](#15-cross-subsystem-protocols)
16. [Enums and Constants](#16-enums-and-constants)
17. [Validation Rules](#17-validation-rules)
18. [Wire Format Examples](#18-wire-format-examples)
19. [Error Contract Reference](#19-error-contract-reference)
20. [Conformance Checklist](#20-conformance-checklist)

---

## 1. Overview and Conventions

### 1.1 Notation

| Convention | Meaning |
|---|---|
| `MUST` / `MUST NOT` | Absolute requirement per RFC 2119 |
| `SHOULD` / `SHOULD NOT` | Recommended unless justified deviation |
| `field: Type` | Field name followed by its type |
| `Type?` | Nullable / optional field |
| `Type[]` | Array of Type |
| `[K: V]` | Dictionary / map with key type K and value type V |
| `CSPRNG` | Cryptographically Secure Pseudo-Random Number Generator |
| `LDJ` | Line-Delimited JSON (one JSON object per `\n`-terminated line) |

### 1.2 Serialization

All wire formats use **UTF-8 encoded JSON** unless explicitly stated otherwise. Timestamps are **UTC Unix milliseconds** (int64). UUIDs are **lowercase hyphenated** (`8-4-4-4-12`). Binary data is **base64url** encoded (RFC 4648 §5, no padding).

### 1.3 Hash Algorithm

All `payload_hash`, `content_hash`, and integrity fields use **SHA-256**, hex-encoded lowercase, 64 characters.

### 1.4 Architectural Boundary

```
┌──────────────────────────────────────────────────┐
│                macOS Application Shell            │
│          (Swift 5.9+ / SwiftUI / TRD-1)          │
│                                                    │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────┐ │
│  │ Keychain │ │ TrustLock│ │   UI State Machine│ │
│  │ (TRD-11) │ │ (§7)     │ │   (TRD-8)        │ │
│  └────┬─────┘ └────┬─────┘ └────────┬──────────┘ │
│       │             │                │             │
│       └─────────────┼────────────────┘             │
│                     │                              │
│              ┌──────┴──────┐                       │
│              │ IPC Socket  │  Unix domain socket   │
│              │ (LDJ/JSON)  │  authenticated         │
│              └──────┬──────┘                       │
└─────────────────────┼──────────────────────────────┘
                      │
┌─────────────────────┼──────────────────────────────┐
│              Python Backend (3.12)                   │
│                                                      │
│  ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌───────┐ │
│  │ Consensus │ │Pipeline │ │ GitHub   │ │  CAL  │ │
│  │ Engine    │ │ & PRD   │ │ Ops      │ │       │ │
│  │ (TRD-2)  │ │(TRD-3/5)│ │(TRD-4)  │ │(§4)   │ │
│  └───────────┘ └─────────┘ └──────────┘ └───────┘ │
│                                                      │
│  ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌───────┐ │
│  │ TrustFlow │ │  DTL    │ │  VTZ     │ │CTX-ID │ │
│  │ (§5)      │ │ (§6)    │ │ (§3)     │ │(§2)   │ │
│  └───────────┘ └─────────┘ └──────────┘ └───────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 2. CTX-ID — Contextual Identity Tokens

### 2.1 Purpose

CTX-ID tokens provide cryptographically bound, immutable identity for every agent session. Every subsystem MUST validate CTX-ID before processing any action.

### 2.2 Data Structure

```typescript
CTXIDToken {
  ctx_id:          string       // UUIDv4, globally unique, lowercase hyphenated
  session_id:      string       // UUIDv4, binds to the originating session
  vtz_id:          string       // UUIDv4, the VTZ this token is bound to
  principal_type:  PrincipalType // enum: "human" | "agent" | "service"
  principal_id:    string       // identifier of the acting principal
  issued_at:       int64        // UTC Unix timestamp, millisecond precision
  expires_at:      int64        // UTC Unix timestamp, millisecond precision
  trust_level:     TrustLevel   // enum: see §16.2
  signature:       string       // base64url, Ed25519 signature over canonical form
  public_key_id:   string       // identifier of the TrustLock key used to sign
  nonce:           string       // 32 bytes, CSPRNG, base64url encoded
  metadata:        [string: string]? // optional key-value pairs, max 16 entries
}
```

### 2.3 Canonical Serialization for Signing

The signature covers the following fields concatenated with `|` (pipe) separator, UTF-8 encoded:

```
ctx_id|session_id|vtz_id|principal_type|principal_id|issued_at|expires_at|trust_level|public_key_id|nonce
```

No trailing separator. No whitespace padding. Fields are serialized as their string representations.

### 2.4 Constraints

| Constraint | Requirement |
|---|---|
| Immutability | CTX-ID tokens are IMMUTABLE once issued. No field modification after issuance. |
| Rotation | Rotation creates a NEW token. The old token is invalidated immediately. |
| Expiration | Expired CTX-ID MUST be rejected. Clock skew tolerance: **±5000ms** (configurable per deployment). |
| Validation | MUST be validated against TrustLock public key. Software-only validation is rejected. |
| Missing CTX-ID | MUST be treated as UNTRUSTED. Never infer identity from context. |
| Nonce | MUST be generated via CSPRNG. MUST NOT be reused across tokens. |
| Metadata | Keys: max 64 bytes. Values: max 256 bytes. Total entries: max 16. |

### 2.5 Lifecycle

```
  ┌─────────┐    issue()     ┌────────┐   validate()   ┌───────────┐
  │ ABSENT  │───────────────►│ ACTIVE │───────────────►│ VALIDATED │
  └─────────┘                └────┬───┘                └───────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │ expire()    │ rotate()     │ revoke()
                    ▼             ▼              ▼
              ┌──────────┐ ┌──────────┐  ┌──────────┐
              │ EXPIRED  │ │ ROTATED  │  │ REVOKED  │
              └──────────┘ └──────────┘  └──────────┘
```

All terminal states (EXPIRED, ROTATED, REVOKED) are irreversible. Tokens in terminal states MUST be rejected on any validation attempt.

---

## 3. VTZ — Virtual Trust Zones

### 3.1 Purpose

VTZ defines structural isolation boundaries for agent sessions. Every session is bound to exactly one VTZ. Cross-VTZ operations require explicit policy authorization.

### 3.2 Data Structure

```typescript
VTZDefinition {
  vtz_id:             string              // UUIDv4
  name:               string              // human-readable, max 128 chars
  created_at:         int64               // UTC Unix ms
  policy:             VTZPolicy           // see below
  allowed_tools:      string[]            // tool identifiers permitted in this zone
  allowed_resources:  ResourcePattern[]   // resource patterns accessible
  cross_vtz_policy:   CrossVTZPolicy      // see below
  trust_floor:        TrustLevel          // minimum trust level for entry
  metadata:           [string: string]?   // max 16 entries
}

VTZPolicy {
  max_session_duration_ms:  int64         // 0 = unlimited (NOT RECOMMENDED)
  max_concurrent_sessions:  int32         // 0 = unlimited (NOT RECOMMENDED)
  require_biometric:        bool          // require biometric auth for session
  allow_network:            bool          // allow outbound network from zone
  allow_filesystem_write:   bool          // allow filesystem mutations
  allowed_github_scopes:    string[]      // GitHub permission scopes
  code_execution_policy:    CodeExecPolicy // enum: see §16.4
}

CrossVTZPolicy {
  allow_cross_vtz:    bool                // master switch
  allowed_targets:    string[]            // VTZ IDs this zone may call into
  require_elevation:  bool                // require trust level elevation for cross-VTZ
  audit_cross_vtz:    bool                // MUST be true if allow_cross_vtz is true
}

ResourcePattern {
  pattern:     string                     // glob pattern, e.g., "repo:owner/name/*"
  permissions: Permission[]               // enum array: see §16.5
}
```

### 3.3 Constraints

| Constraint | Requirement |
|---|---|
| Binding | Every agent session is bound to