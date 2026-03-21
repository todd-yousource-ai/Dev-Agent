

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0
**Status:** Normative — Engineering Reference
**Authority:** TRD-1 through TRD-12, AGENTS.md, CLAUDE.md, Forge Interface Contracts
**Scope:** Every subsystem, every wire format, every validation rule, every enum. If a byte crosses a boundary, it is defined here.

---

## Table of Contents

1. [Foundational Conventions](#1-foundational-conventions)
2. [CTX-ID — Contextual Identity Tokens](#2-ctx-id--contextual-identity-tokens)
3. [VTZ — Virtual Trust Zones](#3-vtz--virtual-trust-zones)
4. [TrustFlow — Audit Event Stream](#4-trustflow--audit-event-stream)
5. [DTL — Data Trust Labels](#5-dtl--data-trust-labels)
6. [CAL — Consensus Action Layer](#6-cal--consensus-action-layer)
7. [IPC — Shell ↔ Backend Protocol](#7-ipc--shell--backend-protocol)
8. [Consensus Engine](#8-consensus-engine)
9. [Pipeline & PRD Decomposition](#9-pipeline--prd-decomposition)
10. [GitHub Integration](#10-github-integration)
11. [Authentication & Session Lifecycle](#11-authentication--session-lifecycle)
12. [Keychain & Secrets](#12-keychain--secrets)
13. [Auto-Update (Sparkle)](#13-auto-update-sparkle)
14. [UI Events & View Models](#14-ui-events--view-models)
15. [Cross-Subsystem Protocols](#15-cross-subsystem-protocols)
16. [Enums and Constants](#16-enums-and-constants)
17. [Validation Rules](#17-validation-rules)
18. [Wire Format Examples](#18-wire-format-examples)

---

## 1. Foundational Conventions

### 1.1 Serialization

All inter-process and inter-component messages use **line-delimited JSON** (one JSON object per `\n`-terminated line) unless explicitly stated otherwise. No binary framing. No multi-line pretty-printing on the wire.

### 1.2 String Encoding

All strings are UTF-8. No BOM. No Latin-1 fallback.

### 1.3 Timestamps

All timestamps are **UTC Unix timestamps with millisecond precision** expressed as a JSON number (integer milliseconds) or an ISO-8601 string with `Z` suffix. Within a single subsystem, one format must be chosen and used consistently. Cross-subsystem messages use integer milliseconds.

```
1719427200000        ← integer milliseconds (preferred on wire)
"2025-06-27T00:00:00.000Z"  ← ISO-8601 (acceptable in logs and UI)
```

### 1.4 Identifiers

| ID Type | Format | Generation | Example |
|---------|--------|------------|---------|
| `event_id` | 128-bit hex (lowercase) | CSPRNG | `"a3f1c9...d804"` |
| `session_id` | UUIDv4 (lowercase, hyphens) | CSPRNG | `"550e8400-e29b-41d4-a716-446655440000"` |
| `ctx_id` | Opaque base64url token | Issued by TrustLock | `"eyJhbGciOi..."` |
| `request_id` | UUIDv4 (lowercase, hyphens) | Caller-generated | `"7c9e6679-..."` |
| `pr_id` | Integer | GitHub-assigned | `42` |
| `prd_id` | `prd-<UUIDv4>` | Pipeline-generated | `"prd-550e8400-..."` |
| `vtz_id` | `vtz-<UUIDv4>` | Issued at zone creation | `"vtz-9b1deb4d-..."` |

All CSPRNG-generated identifiers MUST use `os.urandom` (Python) or `SecRandomCopyBytes` (Swift). Sequential counters, timestamps, or UUIDv1 are **prohibited** for security-relevant identifiers.

### 1.5 Hash Algorithm

All `payload_hash`, `content_hash`, and integrity fields use **SHA-256**, hex-encoded, lowercase, 64 characters.

### 1.6 Null vs. Absent

A field set to `null` and a field absent from the JSON object have **different semantics**:
- **Absent:** The sender does not provide this field (optional fields only).
- **`null`:** The sender explicitly asserts no value. Required fields MUST NOT be `null`.

---

## 2. CTX-ID — Contextual Identity Tokens

### 2.1 Purpose

CTX-ID is the immutable identity token that binds an agent session to a principal, a VTZ, and a validity window. Every enforcement decision begins with CTX-ID validation.

### 2.2 Token Structure

CTX-ID is an opaque, signed token. Internal structure is not parsed by consuming components — they validate via TrustLock. For issuance and debugging, the logical fields are:

```
CTX-ID Logical Structure
┌──────────────────────────────────────────────────┐
│ Field           │ Type       │ Constraint         │
├──────────────────────────────────────────────────┤
│ ctx_id          │ string     │ base64url, ≤ 2048B │
│ principal_id    │ string     │ UUIDv4             │
│ vtz_id          │ string     │ vtz-<UUIDv4>       │
│ issued_at       │ int64      │ UTC ms             │
│ expires_at      │ int64      │ UTC ms             │
│ scope           │ string[]   │ non-empty          │
│ signature       │ bytes      │ Ed25519 / TrustLock│
└──────────────────────────────────────────────────┘
```

### 2.3 Data Structure (Decoded — Internal Only)

```typescript
interface CTXIDToken {
  ctx_id:        string;       // base64url-encoded opaque token, max 2048 bytes
  principal_id:  string;       // UUIDv4, the authenticated user/agent identity
  vtz_id:        string;       // "vtz-" + UUIDv4, binding to exactly one VTZ
  issued_at:     number;       // UTC Unix ms, set at issuance, immutable
  expires_at:    number;       // UTC Unix ms, must be > issued_at
  scope:         string[];     // non-empty array of permission scopes
  signature:     string;       // base64url-encoded Ed25519 signature
}
```

### 2.4 Validation Rules

| Rule ID | Rule | Failure Action |
|---------|------|----------------|
| CTX-V01 | Token MUST be present on every request | Reject as UNTRUSTED |
| CTX-V02 | Signature MUST verify against TrustLock public key | Reject, log `ctx_signature_failure` |
| CTX-V03 | `expires_at` MUST be > current UTC time (± clock skew tolerance) | Reject as expired |
| CTX-V04 | `vtz_id` MUST match the VTZ of the target resource | Reject as cross-VTZ violation |
| CTX-V05 | Token fields MUST NOT be modified after issuance | Reject, log `ctx_tamper_detected` |
| CTX-V06 | Revoked tokens (post-rotation) MUST be rejected | Reject, log `ctx_revoked` |
| CTX-V07 | Software-only validation (no TrustLock key check) is prohibited | Reject |
| CTX-V08 | Missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from context | Reject |

**Clock skew tolerance:** Configurable per deployment. Default: **5000 ms**. Maximum allowed: **30000 ms**.

### 2.5 Rotation Protocol

```
1. New CTX-ID is issued with new ctx_id value and fresh issued_at/expires_at
2. Old ctx_id is added to revocation set IMMEDIATELY (same atomic operation)
3. Old ctx_id is rejected on all subsequent validation attempts
4. VTZ binding in new token MAY differ (requires explicit policy authorization)
5. Rotation event is emitted to TrustFlow BEFORE the new token is returned to caller
```

### 2.6 CTX-ID on the Wire

CTX-ID is transmitted as an opaque string in the `ctx_id` field of every IPC message and every CAL action envelope. It is never decomposed or partially transmitted.

---

## 3. VTZ — Virtual Trust Zones

### 3.1 Purpose

VTZ defines structural trust boundaries. Every agent session, every resource, and every tool call is bound to exactly one VTZ. Cross-VTZ access requires explicit policy — implicit access is denied.

### 3.2 VTZ Definition Structure

```typescript
interface VTZDefinition {
  vtz_id:          string;     // "vtz-" + UUIDv4
  name:            string;     // human-readable, 1–128 chars, no control chars
  description:     string;     // 0–1024 chars
  created_at:      number;     // UTC Unix ms
  policy_version:  number;     // monotonically increasing integer, starts at 1
  tool_allowlist:  string[];   // tool identifiers permitted in this zone
  resource_scopes: string[];   // resource patterns accessible (glob syntax)
  cross_vtz_policy: CrossVTZPolicy;
}

interface CrossVTZPolicy {
  allow_outbound:  boolean;    // can this VTZ's agents call tools in other VTZs?
  allow_inbound:   boolean;    // can other VTZ agents call tools in this VTZ?
  authorized_vtzs: string[];   // explicit list of vtz_ids for cross-zone access
  requires_escalation: boolean; // must cross-VTZ calls go through approval?
}
```

### 3.3 Enforcement Rules

| Rule ID | Rule |
|---------|------|
| VTZ-E01 | Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance |
| VTZ-E02 | Cross-VTZ tool calls require explicit `cross_vtz_policy` authorization |
| VTZ-E03 | Implicit cross-VTZ access is DENIED — default is deny |
| VTZ-E04 | VTZ boundaries are structural, not advisory — cannot be bypassed by app code |
| VTZ-E05 | Policy changes take effect at NEXT CTX-ID issuance, not mid-session |
| VTZ-E06 | VTZ deletion requires all active CTX-IDs bound to it to be revoked first |

### 3.4 VTZ Enforcement Decision

```typescript
interface VTZEnforcementDecision {
  decision_id:   string;     // 128-bit hex, CSPRNG
  ctx_id:        string;     // the CTX-ID that triggered the check
  vtz_id:        string;     // the VTZ being enforced
  target_vtz_id: string | null; // non-null only for cross-VTZ attempts
  action:        string;     // the action being attempted
  verdict:       "allow" | "restrict" | "block";
  reason:        string;     // human-readable explanation
  policy_version: number;    // the VTZ policy version used for this decision
  ts:            number;     // UTC Unix ms
}
```

---

## 4. TrustFlow — Audit Event Stream

### 4.1 Purpose

TrustFlow is the append-only audit stream. Every security-relevant action emits a TrustFlow event. Emission is synchronous in the enforcement path