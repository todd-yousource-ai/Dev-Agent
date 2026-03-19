

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0.0
**Authority:** TRD-1 through TRD-12, CLAUDE.md, AGENTS.md, Forge Component Interface Contracts
**Status:** Normative. All implementations MUST conform to these definitions. Non-conformant components will be rejected at code review.

---

## Table of Contents

1. [Foundational Conventions](#1-foundational-conventions)
2. [CTX-ID — Contextual Identity Token](#2-ctx-id--contextual-identity-token)
3. [VTZ — Virtual Trust Zone](#3-vtz--virtual-trust-zone)
4. [DTL — Data Trust Labels](#4-dtl--data-trust-labels)
5. [TrustFlow — Audit Event Stream](#5-trustflow--audit-event-stream)
6. [CAL — Consensus Arbitration Layer Enforcement](#6-cal--consensus-arbitration-layer-enforcement)
7. [XPC — Swift Shell ↔ Python Backend IPC](#7-xpc--swift-shell--python-backend-ipc)
8. [Consensus Engine — Multi-Model Pipeline](#8-consensus-engine--multi-model-pipeline)
9. [Provider Adapters — LLM Provider Wire Format](#9-provider-adapters--llm-provider-wire-format)
10. [GitHub Operations — PR & Repository Wire Format](#10-github-operations--pr--repository-wire-format)
11. [PRD Planner — Decomposition Structures](#11-prd-planner--decomposition-structures)
12. [Review Cycle — 3-Pass Review Protocol](#12-review-cycle--3-pass-review-protocol)
13. [Session & Authentication](#13-session--authentication)
14. [Process Management](#14-process-management)
15. [Auto-Update — Sparkle Integration](#15-auto-update--sparkle-integration)
16. [SwiftUI View Model Contracts](#16-swiftui-view-model-contracts)
17. [Enums and Constants](#17-enums-and-constants)
18. [Validation Rules](#18-validation-rules)
19. [Cross-Subsystem Protocol Summary](#19-cross-subsystem-protocol-summary)
20. [Wire Format Examples](#20-wire-format-examples)

---

## 1. Foundational Conventions

### 1.1 Wire Format

All inter-process and inter-subsystem messages use **line-delimited JSON** (one JSON object per line, terminated by `\n`). No pretty-printing on the wire.

```
{"msg_type":"request","id":"...","payload":{...}}\n
```

### 1.2 String Encoding

All strings are **UTF-8**. No BOM. No Latin-1 fallback.

### 1.3 Timestamps

All timestamps are **UTC Unix timestamps with millisecond precision**, represented as a JSON number (integer milliseconds) or ISO 8601 string `"2026-03-19T20:51:00.000Z"` where specified. Field-level documentation disambiguates. The canonical form is **integer milliseconds** unless otherwise stated.

### 1.4 Identifiers

All identifiers (event IDs, session IDs, CTX-IDs, message IDs) are generated from a **CSPRNG** and represented as lowercase hex strings or UUID v4 strings. Sequential/auto-increment identifiers are **prohibited** for security-relevant tokens.

### 1.5 Hash Algorithm

All `payload_hash`, `content_hash`, and integrity fields use **SHA-256**, hex-encoded, lowercase, 64 characters.

### 1.6 Size Limits

| Scope | Limit |
|---|---|
| Single JSON message on XPC socket | 16 MiB |
| Single LLM provider response payload | 4 MiB |
| Audit record payload | 1 MiB |
| CTX-ID token (serialized) | 4 KiB |
| DTL label string | 256 bytes |

### 1.7 Byte Order

All binary fields (when present) are **big-endian / network byte order**.

---

## 2. CTX-ID — Contextual Identity Token

### 2.1 Purpose

CTX-ID is the immutable identity token binding an agent session to a verified identity, a VTZ, and a trust anchor. Every enforcement decision begins with CTX-ID validation.

### 2.2 Data Structure

```typescript
interface CTXIDToken {
  ctx_id:           string;    // UUID v4, globally unique, CSPRNG-generated
  session_id:       string;    // UUID v4, session this token belongs to
  vtz_id:           string;    // UUID v4, bound VTZ at issuance
  issued_at:        number;    // UTC Unix ms
  expires_at:       number;    // UTC Unix ms
  issuer:           string;    // Issuing component identifier
  subject:          string;    // Authenticated user or agent identity
  trust_anchor:     string;    // TrustLock public key fingerprint (SHA-256, hex)
  signature:        string;    // Ed25519 signature over canonical form, hex-encoded
  schema_version:   string;    // Semver, currently "1.0.0"
}
```

### 2.3 Canonical Serialization for Signing

The canonical form is the UTF-8 encoding of the following fields concatenated with `|` as separator, in this exact order:

```
ctx_id|session_id|vtz_id|issued_at|expires_at|issuer|subject|trust_anchor|schema_version
```

No trailing separator. No whitespace padding.

### 2.4 Constraints

| Field | Constraint |
|---|---|
| `ctx_id` | UUID v4, immutable after issuance |
| `session_id` | Must reference an active session |
| `vtz_id` | Must reference an existing VTZ definition |
| `issued_at` | Must be ≤ current time (no future issuance) |
| `expires_at` | Must be > `issued_at`; maximum TTL is 86400000 ms (24 hours) |
| `trust_anchor` | Must match a TrustLock public key registered in the local trust store |
| `signature` | Ed25519 over canonical form; MUST be validated against `trust_anchor` |
| `schema_version` | Must be a supported version; unsupported versions are rejected |

### 2.5 Lifecycle Rules

- **Immutability:** No field may be modified after issuance. Any mutation invalidates the token.
- **Rotation:** A new CTX-ID is issued; the old token is immediately invalidated and added to a revocation set.
- **Expiry:** Expired CTX-IDs are rejected. Clock skew tolerance is deployment-defined but defaults to **5000 ms**.
- **Missing CTX-ID:** Any request without a CTX-ID is classified as `UNTRUSTED`. Identity MUST NOT be inferred from ambient context.
- **Revocation:** Revoked CTX-IDs are stored in an append-only revocation log for the duration of the session plus a 1-hour grace period.

### 2.6 JSON Wire Representation

```json
{
  "ctx_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "session_id": "f0e1d2c3-b4a5-4968-8776-554433221100",
  "vtz_id": "11223344-5566-4778-899a-bbccddeeff00",
  "issued_at": 1742413860000,
  "expires_at": 1742500260000,
  "issuer": "forge.shell.auth",
  "subject": "user:biometric:a9f3c1",
  "trust_anchor": "b4d2e6f8a0c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1",
  "signature": "3f7a...c4e1",
  "schema_version": "1.0.0"
}
```

---

## 3. VTZ — Virtual Trust Zone

### 3.1 Purpose

A VTZ defines a structural security boundary constraining what tools, repositories, providers, and data classifications an agent session may access. VTZ boundaries are **structural, not advisory** — enforcement cannot be bypassed by application code.

### 3.2 Data Structure

```typescript
interface VTZDefinition {
  vtz_id:               string;    // UUID v4
  name:                 string;    // Human-readable label, max 128 chars
  created_at:           number;    // UTC Unix ms
  updated_at:           number;    // UTC Unix ms
  allowed_tools:        string[];  // Tool identifiers permitted within this zone
  denied_tools:         string[];  // Explicitly denied tools (takes precedence)
  allowed_repositories: string[];  // Repository identifiers (owner/repo format)
  allowed_providers:    string[];  // LLM provider identifiers
  max_dtl_level:        DTLLevel;  // Maximum data classification allowed
  cross_vtz_policy:     CrossVTZPolicy;
  policy_version:       number;    // Monotonically increasing
}

interface CrossVTZPolicy {
  allow_cross_vtz_calls: boolean;      // Default: false
  authorized_targets:    string[];     // VTZ IDs that may be called into
  requires_elevation:    boolean;      // Whether cross-VTZ requires re-auth
}
```

### 3.3 Constraints

| Field | Constraint |
|---|---|
| `vtz_id` | UUID v4, immutable after creation |
| `name` | 1–128 characters, no control characters |
| `allowed_tools` / `denied_tools` | `denied_tools` ALWAYS takes precedence over `allowed_tools` |
| `max_dtl_level` | One of the DTLLevel enum values |
| `policy_version` | Must be strictly greater than previous version on update |
| `cross_vtz_policy.allow_cross_vtz_calls` | Default `false`. If `false`, `authorized_targets` is ignored |

### 3.4 Enforcement Rules

- Each agent session is bound to **exactly one VTZ** at CTX-ID issuance time.
- Cross-VTZ tool calls require explicit `allow_cross_vtz_calls: true` AND the target VTZ in `authorized_targets`.
- VTZ policy changes take effect at the **next CTX-ID issuance**, not mid-session.
- An active session continues under its bound VTZ policy until the CTX-ID expires or is rotated.

---

## 4. DTL — Data Trust Labels

### 4.1 Purpose

DTL labels classify every piece of data entering, traversing, or leaving the Forge platform. Labels are assigned at ingestion and are **immutable** thereafter.

### 4.2 Data Structure

```typescript
interface DTLLabel {
  label_id:         string;      // UUID v4
  data_ref:         string;      // Reference to the labeled data object
  level:            DTLLevel;    // Classification level
  assigned_at:      number;      // UTC Unix ms
  assigned_by:      string;      // Component that assigned the label
  source_labels:    string[];    // label_ids of source data (for derived data)
  immutable:        true;        // Constant — labels cannot be modified
}
```

### 4.3 Classification Levels

See [Section 17: Enums — DTLLevel](#dtl-levels).

### 4.4 Constraints & Rules

| Rule | Description |
|---|---|
| **Assign at ingestion** | Every data object receives a DTL label at the point it enters any Forge component |
| **Immutability** | Once assigned, a label cannot be modified. Reclassification creates a new label record and is an audited event |
| **Inheritance** | Derived data inherits the