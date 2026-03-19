

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0
**Status:** Normative — All implementations MUST conform
**Authority:** TRD-1 through TRD-12, CLAUDE.md, AGENTS.md, Forge Interface Contracts
**Last Updated:** 2026-03-19

---

## Table of Contents

1. [Overview & Conventions](#1-overview--conventions)
2. [Transport Layer](#2-transport-layer)
3. [CTX-ID — Context Identity Token](#3-ctx-id--context-identity-token)
4. [VTZ — Virtual Trust Zone](#4-vtz--virtual-trust-zone)
5. [CAL — Context Authority Layer](#5-cal--context-authority-layer)
6. [TrustFlow — Audit Event Stream](#6-trustflow--audit-event-stream)
7. [DTL — Data Trust Labels](#7-dtl--data-trust-labels)
8. [TrustLock — Cryptographic Anchoring](#8-trustlock--cryptographic-anchoring)
9. [Shell ↔ Backend IPC Protocol](#9-shell--backend-ipc-protocol)
10. [Consensus Engine](#10-consensus-engine)
11. [Provider Adapters](#11-provider-adapters)
12. [Pipeline & PR Lifecycle](#12-pipeline--pr-lifecycle)
13. [GitHub Operations](#13-github-operations)
14. [Keychain & Secret Management](#14-keychain--secret-management)
15. [Session Lifecycle](#15-session-lifecycle)
16. [UI Data Contracts (SwiftUI ↔ Backend)](#16-ui-data-contracts-swiftui--backend)
17. [Enums & Constants](#17-enums--constants)
18. [Validation Rules](#18-validation-rules)
19. [Wire Format Examples](#19-wire-format-examples)
20. [Cross-Subsystem Protocol Matrix](#20-cross-subsystem-protocol-matrix)
21. [Error Envelope](#21-error-envelope)
22. [Conformance Checklist](#22-conformance-checklist)

---

## 1. Overview & Conventions

### 1.1 Notation

| Convention | Meaning |
|---|---|
| `REQUIRED` | Field MUST be present; omission is a validation error |
| `OPTIONAL` | Field MAY be absent; absence has defined default semantics |
| `IMMUTABLE` | Value MUST NOT change after initial assignment |
| `string<N>` | UTF-8 string, max N bytes |
| `bytes<N>` | Raw byte sequence, max N bytes |
| `uint64` | Unsigned 64-bit integer |
| `float64` | IEEE 754 double-precision |
| `ts` | UTC Unix timestamp, millisecond precision (uint64) |
| `uuid` | RFC 4122 v4 UUID as lowercase hex with hyphens |
| `sha256` | Lowercase hex-encoded SHA-256 digest (64 chars) |
| `enum[...]` | Value MUST be one of the listed variants |

### 1.2 Wire Format

All inter-process and inter-component messages use **line-delimited JSON (NDJSON)**. Each message is a single UTF-8 line terminated by `\n` (0x0A). No embedded newlines in payloads — use JSON string escaping.

### 1.3 Byte Ordering

All integer fields are serialized in JSON as decimal numbers. Binary fields (keys, signatures) are serialized as base64url (RFC 4648 §5) unless otherwise noted.

### 1.4 Fail-Closed Principle

Every interface in this document operates under fail-closed semantics. If validation fails, parsing fails, or any security-relevant check cannot complete, the operation MUST be rejected. Silent continuation is non-conformant.

---

## 2. Transport Layer

### 2.1 Shell ↔ Backend: Authenticated Unix Domain Socket

```
Path:       $XDG_RUNTIME_DIR/forge-<session_id>.sock
            Fallback: /tmp/forge-<session_id>.sock
Permissions: 0600, owned by launching user
Protocol:   Line-delimited JSON over stream socket
Auth:       Handshake with session_token (see §9.2)
Max message: 16 MiB (16,777,216 bytes)
Encoding:   UTF-8, no BOM
```

### 2.2 Message Envelope

Every message on any Forge transport MUST be wrapped in this envelope:

```
IPCEnvelope {
    msg_id:       uuid              REQUIRED  IMMUTABLE
    msg_type:     string<128>       REQUIRED
    ts:           uint64            REQUIRED  (ms since Unix epoch, UTC)
    session_id:   uuid              REQUIRED
    ctx_id:       string<256>       OPTIONAL  (REQUIRED after handshake)
    version:      string<16>        REQUIRED  (protocol version, e.g. "1.0")
    payload:      object            REQUIRED  (type-specific; see subsystem sections)
    signature:    string<512>       OPTIONAL  (base64url Ed25519 signature)
}
```

**Constraints:**
- `msg_id` is generated via CSPRNG. Sequential IDs are non-conformant.
- `ts` clock skew tolerance: 30 seconds. Messages outside window are rejected.
- `version` MUST match the receiver's supported version or be explicitly negotiated.

---

## 3. CTX-ID — Context Identity Token

### 3.1 Purpose

CTX-ID is the immutable identity token binding an agent session to a user, device, trust zone, and time window. Every enforcement decision references a CTX-ID.

### 3.2 Data Structure

```
CTXIDToken {
    ctx_id:           string<256>     REQUIRED  IMMUTABLE
    session_id:       uuid            REQUIRED  IMMUTABLE
    user_id:          string<128>     REQUIRED  IMMUTABLE
    device_id:        string<128>     REQUIRED  IMMUTABLE
    vtz_id:           string<128>     REQUIRED  IMMUTABLE
    issued_at:        uint64          REQUIRED  IMMUTABLE  (ms timestamp)
    expires_at:       uint64          REQUIRED  IMMUTABLE  (ms timestamp)
    issuer:           string<128>     REQUIRED  IMMUTABLE
    public_key_ref:   string<256>     REQUIRED  IMMUTABLE  (TrustLock key reference)
    signature:        string<512>     REQUIRED  IMMUTABLE  (base64url Ed25519)
    claims:           CTXIDClaims     REQUIRED  IMMUTABLE
}

CTXIDClaims {
    roles:            string[]        REQUIRED  (non-empty)
    max_trust_level:  enum[           REQUIRED
                        "untrusted",
                        "basic",
                        "standard",
                        "elevated",
                        "privileged"
                      ]
    allowed_tools:    string[]        OPTIONAL  (empty = no tool restrictions from CTX)
    scope:            string<512>     OPTIONAL  (freeform scope descriptor)
}
```

### 3.3 Lifecycle

```
                  ┌──────────┐
                  │  ISSUED   │
                  └─────┬────┘
                        │ validate(TrustLock pubkey)
                  ┌─────▼────┐
           ┌──────│  ACTIVE   │──────┐
           │      └─────┬────┘      │
           │ rotate()   │ expire()  │ revoke()
     ┌─────▼────┐ ┌─────▼────┐ ┌───▼──────┐
     │ ROTATED  │ │ EXPIRED  │ │ REVOKED  │
     └──────────┘ └──────────┘ └──────────┘
        (new CTX-ID    (rejected   (rejected
         issued)       on use)     on use)
```

### 3.4 Validation Rules

| Rule | Enforcement |
|---|---|
| Signature MUST verify against `public_key_ref` | Reject if invalid |
| `expires_at` MUST be > current time (within skew tolerance) | Reject if expired |
| `vtz_id` MUST match the requesting session's bound VTZ | Reject if mismatch |
| `issued_at` MUST be ≤ `expires_at` | Reject if inverted |
| Token is IMMUTABLE — any field modification invalidates it | Reject modified tokens |
| Missing CTX-ID = UNTRUSTED | Never infer identity from context |

---

## 4. VTZ — Virtual Trust Zone

### 4.1 Data Structure

```
VTZDefinition {
    vtz_id:             string<128>     REQUIRED  IMMUTABLE
    name:               string<256>     REQUIRED
    created_at:         uint64          REQUIRED  IMMUTABLE
    policy_version:     uint32          REQUIRED
    boundaries:         VTZBoundaries   REQUIRED
    tool_policy:        VTZToolPolicy   REQUIRED
    data_policy:        VTZDataPolicy   REQUIRED
    trust_levels:       TrustLevelMap   REQUIRED
}

VTZBoundaries {
    allowed_repositories:  string[]     REQUIRED  (glob patterns)
    allowed_paths:         string[]     REQUIRED  (glob patterns)
    denied_paths:          string[]     REQUIRED  (glob patterns, takes precedence)
    network_scope:         enum[        REQUIRED
                             "none",
                             "github_only",
                             "allowlisted",
                             "unrestricted"
                           ]
    allowed_hosts:         string[]     OPTIONAL  (when network_scope = "allowlisted")
}

VTZToolPolicy {
    allowed_tools:       ToolPermission[]   REQUIRED
    default_action:      enum["allow", "deny"]  REQUIRED  (MUST be "deny")
    cross_vtz_policy:    enum[              REQUIRED
                           "deny",
                           "explicit_auth_required"
                         ]
}

ToolPermission {
    tool_name:           string<128>     REQUIRED
    action:              enum["allow", "restrict", "deny"]  REQUIRED
    restrictions:        object          OPTIONAL  (tool-specific constraints)
    requires_approval:   bool            REQUIRED
}

VTZDataPolicy {
    max_classification:  enum[           REQUIRED
                           "public",
                           "internal",
                           "confidential",
                           "restricted"
                         ]
    allow_external_data: bool            REQUIRED
    exfiltration_prevention: bool        REQUIRED
}

TrustLevelMap {
    levels: {
        [trust_level: string]: {
            allowed_operations: string[]
            max_file_count:     uint32
            max_diff_lines:     uint32
            requires_review:    bool
        }
    }
}
```

### 4.2 Enforcement Rules

| Rule | Enforcement |
|---|---|
| Every session is bound to EXACTLY ONE VTZ at CTX-ID issuance | No multi-VTZ sessions |
| Cross-VTZ tool calls require explicit policy authorization | Implicit cross-VTZ = deny |
| VTZ boundaries are structural, not advisory | Application code cannot bypass |
| Policy changes take effect at NEXT CTX-ID issuance | No mid-session policy changes |
| `denied_paths` always takes precedence over `allowed_paths` | Deny wins on conflict |
| `default_action` MUST be `"deny"` | Fail-closed by default |

---

## 5. CAL — Context Authority Layer

### 5.1 Enforcement Decision

```
CALEnforcementRequest {
    request_id:      uuid              REQUIRED
    ctx_id:          string<256>       REQUIRED
    action:          CALAction         REQUIRED
    timestamp:       uint64            REQUIRED
}

CALAction {
    tool_name:       string<128>       REQUIRED
    operation:        string