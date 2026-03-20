

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0
**Status:** Normative — all implementations MUST conform
**Authority:** TRD-1 through TRD-12, AGENTS.md, CLAUDE.md, Forge Interface Contracts
**Scope:** Every subsystem, every wire format, every shared data structure, every cross-boundary protocol

---

## Table of Contents

1. [Conventions and Notation](#1-conventions-and-notation)
2. [Architecture Overview](#2-architecture-overview)
3. [CTX-ID — Contextual Identity Token](#3-ctx-id--contextual-identity-token)
4. [VTZ — Virtual Trust Zone](#4-vtz--virtual-trust-zone)
5. [DTL — Data Trust Labels](#5-dtl--data-trust-labels)
6. [TrustFlow — Audit Event Stream](#6-trustflow--audit-event-stream)
7. [CAL — Contextual Authorization Layer](#7-cal--contextual-authorization-layer)
8. [IPC Protocol — Shell ↔ Backend](#8-ipc-protocol--shell--backend)
9. [Consensus Engine](#9-consensus-engine)
10. [Pipeline & PRD Planner](#10-pipeline--prd-planner)
11. [GitHub Operations](#11-github-operations)
12. [Keychain & Secret Management](#12-keychain--secret-management)
13. [Session Lifecycle](#13-session-lifecycle)
14. [UI State Machine](#14-ui-state-machine)
15. [Auto-Update (Sparkle)](#15-auto-update-sparkle)
16. [Enums and Constants](#16-enums-and-constants)
17. [Validation Rules](#17-validation-rules)
18. [Wire Format Examples](#18-wire-format-examples)
19. [Error Contracts](#19-error-contracts)
20. [Audit Contract](#20-audit-contract)
21. [Cross-Reference Matrix](#21-cross-reference-matrix)

---

## 1. Conventions and Notation

| Convention | Meaning |
|---|---|
| `MUST` / `MUST NOT` | Absolute requirement per RFC 2119 |
| `SHOULD` / `SHOULD NOT` | Recommended unless documented reason exists |
| `field: Type` | Field name and its type |
| `Type?` | Nullable / optional field |
| `Type[]` | Array of Type |
| `[K: V]` | Dictionary with key type K, value type V |
| `CSPRNG` | Cryptographically Secure Pseudo-Random Number Generator |
| `LD-JSON` | Line-delimited JSON (one JSON object per `\n`-terminated line) |
| All timestamps | UTC Unix milliseconds unless otherwise stated |
| All hashes | SHA-256, hex-encoded, lowercase |
| All UUIDs | v4, lowercase, hyphenated (`8-4-4-4-12`) |

**Type Aliases Used Throughout:**

```
Timestamp   = Int64          // UTC Unix milliseconds
Hash256     = String         // 64 hex chars, lowercase
UUID4       = String         // 8-4-4-4-12 lowercase
Bytes       = Data / bytes   // raw binary
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    macOS Application Shell               │
│         Swift 5.9+ / SwiftUI / min macOS 13.0           │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Auth/Bio │ │ Keychain │ │ Sparkle  │ │  SwiftUI   │ │
│  │  Gate    │ │ Manager  │ │ Updater  │ │  Frontend  │ │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └─────┬──────┘ │
│       │             │                          │         │
│       └─────────────┼──────────────────────────┘         │
│                     │                                    │
│              ┌──────┴──────┐                             │
│              │  XPC/IPC    │ Authenticated Unix Socket    │
│              │  Bridge     │ Line-Delimited JSON          │
│              └──────┬──────┘                             │
└─────────────────────┼───────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────┐
│              Python Backend (3.12, bundled)               │
│                     │                                    │
│  ┌──────────┐ ┌─────┴─────┐ ┌──────────┐ ┌───────────┐ │
│  │Consensus │ │ Pipeline  │ │ GitHub   │ │ TrustFlow │ │
│  │ Engine   │ │ & Planner │ │   Ops    │ │ & CAL     │ │
│  └──────────┘ └───────────┘ └──────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Invariant:** Neither process ever executes generated code. Generated code is written to files and submitted to CI only.

---

## 3. CTX-ID — Contextual Identity Token

### 3.1 Data Structure

```json
{
  "ctx_id":         "UUID4",
  "session_id":     "UUID4",
  "vtz_id":         "UUID4",
  "principal":      "String",
  "issued_at":      "Timestamp",
  "expires_at":     "Timestamp",
  "trustlock_sig":  "String (base64, Ed25519)",
  "scope":          "CTXScope",
  "metadata":       { }
}
```

| Field | Type | Constraints |
|---|---|---|
| `ctx_id` | UUID4 | MUST be globally unique. Generated via CSPRNG. |
| `session_id` | UUID4 | Session that owns this token. |
| `vtz_id` | UUID4 | The VTZ this token is bound to. Exactly one. |
| `principal` | String | Identity of the agent or user. Max 255 chars. |
| `issued_at` | Timestamp | UTC Unix ms. MUST be ≤ current time + clock_skew_tolerance. |
| `expires_at` | Timestamp | UTC Unix ms. MUST be > `issued_at`. |
| `trustlock_sig` | String | Base64-encoded Ed25519 signature over canonical form. |
| `scope` | CTXScope | Enum: see §16. |
| `metadata` | Object? | Optional. MUST NOT contain secrets. |

### 3.2 Immutability Contract

- CTX-ID tokens are **IMMUTABLE** once issued — no field modification after issuance.
- CTX-ID rotation creates a **new** token; the old one is invalidated **immediately**.
- Expired CTX-ID MUST be rejected. Clock skew tolerance is deployment-configured (default: 30 seconds).
- CTX-ID MUST be validated against TrustLock public key — software-only validation is rejected.
- Missing CTX-ID MUST be treated as **UNTRUSTED** — never infer identity from context.

### 3.3 Canonical Serialization (for signing)

Fields are serialized in this exact order, with no whitespace, no trailing commas:

```
{"ctx_id":"...","session_id":"...","vtz_id":"...","principal":"...","issued_at":...,"expires_at":...,"scope":"..."}
```

The `trustlock_sig` and `metadata` fields are **excluded** from the signed payload.

### 3.4 Validation Sequence

```
1. Parse JSON → reject if malformed
2. Check ctx_id is valid UUID4 → reject if not
3. Check expires_at > now() - clock_skew_tolerance → reject if expired
4. Check issued_at ≤ now() + clock_skew_tolerance → reject if future-dated
5. Retrieve TrustLock public key for principal
6. Verify trustlock_sig over canonical form → reject if invalid
7. Verify vtz_id matches active session VTZ → reject if mismatch
8. Token is VALID
```

---

## 4. VTZ — Virtual Trust Zone

### 4.1 Data Structure

```json
{
  "vtz_id":          "UUID4",
  "name":            "String",
  "policy":          "VTZPolicy",
  "created_at":      "Timestamp",
  "updated_at":      "Timestamp",
  "allowed_tools":   ["String"],
  "denied_tools":    ["String"],
  "cross_vtz_rules": ["CrossVTZRule"],
  "boundary_type":   "VTZBoundaryType"
}
```

| Field | Type | Constraints |
|---|---|---|
| `vtz_id` | UUID4 | CSPRNG-generated. Immutable after creation. |
| `name` | String | Human-readable. 1–128 chars. |
| `policy` | VTZPolicy | See §16 enums. |
| `created_at` | Timestamp | Set at creation. Immutable. |
| `updated_at` | Timestamp | Set on policy change. |
| `allowed_tools` | String[] | Explicit allowlist. Empty = none allowed. |
| `denied_tools` | String[] | Explicit denylist. Evaluated before allowlist. |
| `cross_vtz_rules` | CrossVTZRule[] | Explicit cross-zone authorizations. |
| `boundary_type` | VTZBoundaryType | Enum: `structural`. |

### 4.2 CrossVTZRule

```json
{
  "source_vtz_id":  "UUID4",
  "target_vtz_id":  "UUID4",
  "allowed_tools":  ["String"],
  "requires_audit": true,
  "expires_at":     "Timestamp?"
}
```

### 4.3 Enforcement Contract

- Every agent session is bound to **EXACTLY ONE** VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require **explicit** policy authorization — implicit is **denied**.
- VTZ boundaries are **structural**, not advisory — enforcement cannot be bypassed by application code.
- VTZ policy changes take effect at **NEXT** CTX-ID issuance, not mid-session.
- Denied-tools list is evaluated **before** allowed-tools list (deny wins).

---

## 5. DTL — Data Trust Labels

### 5.1 Data Structure

```json
{
  "dtl_id":           "UUID4",
  "resource_id":      "String",
  "resource_type":    "DTLResourceType",
  "classification":   "DTLClassification",
  "assigned_at":      "Timestamp",
  "assigned_by":      "String",
  "provenance":       "DTLProvenance",
  "source_labels":    ["UUID4"],
  "immutable":        true
}
```

| Field | Type | Constraints |
|---|---|---|
| `dtl_id` | UUID4 | CSPRNG-generated. |
| `resource_id` | String | Identifier of the labeled resource. |
| `resource_type` | DTLResourceType | Enum: see §16. |
| `classification` | DTLClassification | Enum: see §16. Ordered hierarchy. |
| `assigned_at` | Timestamp | Set at data ingestion. Immutable. |
| `assigned_by` | String | Principal or system that assigned. |
| `provenance` | DTLProvenance | Origin tracking. |
| `source_labels` | UUID4[]