

# INTERFACES.md — Forge Platform Interface Contracts

**Version:** 1.0
**Status:** Normative — Engineering Reference
**Authority:** TRD-1 through TRD-16, AGENTS.md, CLAUDE.md, Forge Component Interface Contracts
**Scope:** Every wire format, data structure, protocol, enum, validation rule, and cross-subsystem contract in the Forge platform.

> **This document is the single source of truth for interface contracts.** If application code disagrees with this document, this document wins. If a TRD disagrees with this document, the TRD wins and this document must be updated.

---

## Table of Contents

1. [Foundational Principles](#1-foundational-principles)
2. [Per-Subsystem Data Structures](#2-per-subsystem-data-structures)
   - 2.1 [CTX-ID (Context Identity Token)](#21-ctx-id-context-identity-token)
   - 2.2 [VTZ (Virtual Trust Zone)](#22-vtz-virtual-trust-zone)
   - 2.3 [DTL (Data Trust Labels)](#23-dtl-data-trust-labels)
   - 2.4 [TrustFlow Events](#24-trustflow-events)
   - 2.5 [VTZ Enforcement Decisions](#25-vtz-enforcement-decisions)
   - 2.6 [CAL (Context-Aware Launcher) Actions](#26-cal-context-aware-launcher-actions)
   - 2.7 [IPC Protocol (Swift ↔ Python)](#27-ipc-protocol-swift--python)
   - 2.8 [Consensus Engine](#28-consensus-engine)
   - 2.9 [Pipeline Execution](#29-pipeline-execution)
   - 2.10 [GitHub Operations](#210-github-operations)
   - 2.11 [Audit Records](#211-audit-records)
   - 2.12 [Session Lifecycle](#212-session-lifecycle)
   - 2.13 [Keychain Entries](#213-keychain-entries)
   - 2.14 [PRD Plan & PR Decomposition](#214-prd-plan--pr-decomposition)
   - 2.15 [UI State (SwiftUI ↔ Backend)](#215-ui-state-swiftui--backend)
3. [Cross-Subsystem Protocols](#3-cross-subsystem-protocols)
   - 3.1 [IPC Wire Protocol](#31-ipc-wire-protocol)
   - 3.2 [CAL Enforcement Flow](#32-cal-enforcement-flow)
   - 3.3 [TrustFlow Emission Flow](#33-trustflow-emission-flow)
   - 3.4 [DTL Boundary Crossing Protocol](#34-dtl-boundary-crossing-protocol)
   - 3.5 [CTX-ID Lifecycle Protocol](#35-ctx-id-lifecycle-protocol)
   - 3.6 [Consensus Protocol](#36-consensus-protocol)
   - 3.7 [Pipeline Execution Protocol](#37-pipeline-execution-protocol)
   - 3.8 [Auto-Update Protocol](#38-auto-update-protocol)
4. [Enums and Constants](#4-enums-and-constants)
5. [Validation Rules](#5-validation-rules)
6. [Wire Format Examples](#6-wire-format-examples)

---

## 1. Foundational Principles

Every interface in Forge follows these non-negotiable rules:

| Principle | Rule |
|---|---|
| **Fail closed** | All trust, identity, policy, and cryptographic failures reject the action, log, and surface to caller. Never silently continue. |
| **No swallowed exceptions** | `try/except/pass` is **banned** in any enforcement path. |
| **Secrets never in messages** | Error messages, logs, and wire payloads MUST NOT contain keys, tokens, secrets, or cleartext credentials. |
| **Audit before execution** | Every security-relevant action generates an audit record BEFORE the action runs. |
| **Append-only audit** | Audit records are never modified or deleted by application code. |
| **Immutable tokens** | CTX-ID, DTL labels, and audit records are immutable once issued/assigned/written. |
| **UTC everywhere** | All timestamps are UTC Unix milliseconds unless explicitly stated otherwise. |
| **Line-delimited JSON** | All IPC is newline-delimited JSON over authenticated Unix socket. No binary framing. |
| **TRD supremacy** | TRDs are authoritative. This document codifies their interface contracts. |

---

## 2. Per-Subsystem Data Structures

### 2.1 CTX-ID (Context Identity Token)

The CTX-ID is the atomic unit of identity in Forge. Every agent action, IPC message, and audit record references a CTX-ID.

#### Structure

```json
{
  "ctx_id": "<string>",
  "session_id": "<string>",
  "vtz_id": "<string>",
  "principal": "<string>",
  "issued_at": "<int64>",
  "expires_at": "<int64>",
  "trust_level": "<TrustLevel>",
  "signature": "<string>",
  "public_key_fingerprint": "<string>"
}
```

#### Field Definitions

| Field | Type | Constraints | Description |
|---|---|---|---|
| `ctx_id` | `string` | 32-byte CSPRNG, hex-encoded (64 chars). Globally unique. | Primary identity token. |
| `session_id` | `string` | 32-byte CSPRNG, hex-encoded (64 chars). | Session this CTX-ID belongs to. |
| `vtz_id` | `string` | 16-byte CSPRNG, hex-encoded (32 chars). | VTZ bound at issuance. Immutable. |
| `principal` | `string` | 1–256 UTF-8 chars. No control characters. | Human-readable principal identifier (user or agent). |
| `issued_at` | `int64` | UTC Unix timestamp, millisecond precision. Must be ≤ current time + 5000ms (clock skew). | Token issuance time. |
| `expires_at` | `int64` | UTC Unix timestamp, millisecond precision. Must be > `issued_at`. Max TTL: 86400000ms (24h). | Token expiration time. |
| `trust_level` | `TrustLevel` | Enum. See §4. | Trust classification at issuance. |
| `signature` | `string` | Base64-encoded Ed25519 signature over canonical form of all other fields. | TrustLock signature. |
| `public_key_fingerprint` | `string` | SHA-256 of the Ed25519 public key, hex-encoded (64 chars). | Identifies the signing key. |

#### Canonical Signing Form

Fields are serialized in **lexicographic key order** as a JSON object with no whitespace, then UTF-8 encoded. The signature is computed over this byte string.

```
{"ctx_id":"...","expires_at":...,"issued_at":...,"principal":"...","public_key_fingerprint":"...","session_id":"...","trust_level":"...","vtz_id":"..."}
```

#### Immutability Contract

- Once issued, **no field may be modified**. Any modification invalidates the signature.
- Rotation creates a **new** CTX-ID; the old one is invalidated immediately.
- Expired CTX-IDs are rejected. Clock skew tolerance: **5000ms** per deployment default.
- Missing CTX-ID ⇒ `UNTRUSTED`. Identity is never inferred from context.

---

### 2.2 VTZ (Virtual Trust Zone)

A VTZ defines a structural enforcement boundary. Every agent session is bound to exactly one VTZ at CTX-ID issuance.

#### Structure

```json
{
  "vtz_id": "<string>",
  "name": "<string>",
  "policy": {
    "allowed_tools": ["<string>"],
    "denied_tools": ["<string>"],
    "allowed_targets": ["<string>"],
    "cross_vtz_authorization": "<CrossVTZPolicy>",
    "max_session_ttl_ms": "<int64>",
    "data_classification_floor": "<DTLClassification>"
  },
  "created_at": "<int64>",
  "updated_at": "<int64>"
}
```

#### Field Definitions

| Field | Type | Constraints | Description |
|---|---|---|---|
| `vtz_id` | `string` | 16-byte CSPRNG, hex-encoded (32 chars). | Unique VTZ identifier. |
| `name` | `string` | 1–128 UTF-8 chars. `[a-zA-Z0-9_-]` only. | Human-readable name. |
| `policy.allowed_tools` | `string[]` | Tool identifiers. If non-empty, only these tools are permitted. | Allowlist (takes precedence over denylist). |
| `policy.denied_tools` | `string[]` | Tool identifiers. | Denylist. Applied only if `allowed_tools` is empty. |
| `policy.allowed_targets` | `string[]` | Repository or path patterns. Glob syntax. | Targets this VTZ may operate on. |
| `policy.cross_vtz_authorization` | `CrossVTZPolicy` | Enum. See §4. | Cross-boundary policy. |
| `policy.max_session_ttl_ms` | `int64` | > 0. Max: 86400000 (24h). | Maximum session lifetime in this VTZ. |
| `policy.data_classification_floor` | `DTLClassification` | Enum. See §4. | Minimum classification for data in this VTZ. |
| `created_at` | `int64` | UTC Unix ms. | Creation time. |
| `updated_at` | `int64` | UTC Unix ms. ≥ `created_at`. | Last policy update. |

#### Enforcement Rules

- Cross-VTZ tool calls require **explicit policy authorization**. Implicit is denied.
- VTZ boundaries are **structural, not advisory** — enforcement cannot be bypassed by application code.
- Policy changes take effect at **next CTX-ID issuance**, not mid-session.

---

### 2.3 DTL (Data Trust Labels)

DTL labels classify data at ingestion and are immutable thereafter.

#### Structure

```json
{
  "dtl_label": {
    "label_id": "<string>",
    "classification": "<DTLClassification>",
    "source": "<string>",
    "assigned_at": "<int64>",
    "assigned_by_ctx_id": "<string>",
    "lineage": ["<string>"]
  }
}
```

#### Field Definitions

| Field | Type | Constraints | Description |
|---|---|---|---|
| `label_id` | `string` | 16-byte CSPRNG, hex-encoded (32 chars). | Unique label identifier. |
| `classification` | `DTLClassification` | Enum. See §4. | Data classification level. |
| `source` | `string` | 1–512 UTF-8 chars. | Origin identifier (file path, API endpoint, user input descriptor). |
| `assigned_at` | `int64` | UTC Unix ms. | Time of assignment. |
| `assigned_by_ctx_id` | `string` | Valid CTX-ID (64 hex chars). | CTX-ID that assigned this label. |
| `lineage` | `string[]` | Array of `label_id` values. May be empty for root data. | Parent labels. Derived data lists all source labels. |

#### Label Rules

- Assigned at **data ingestion**. Immutable after assignment.
- **Inheritance:** Derived data inherits the **highest** classification of any source label.
- **Unlabeled data** is treated as `CONFIDENTIAL` until explicitly reclassified.
- **Label verification** MUST occur before any data crosses a trust boundary.