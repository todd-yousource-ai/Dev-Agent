# CLAUDE.md — Forge Platform

Forge is a security-first, two-process enforcement platform that cryptographically binds every agent action to a verified machine identity (CTX-ID), enforces session-bound policy isolation (VTZ), classifies all data at ingestion (DTL), and records every control decision through synchronous TrustFlow audit streams — every decision is explainable, observable, and reproducible.

---

## Critical Rules — Read Before Writing Any Code

1. Validate CTX-ID **first** at every enforcement entry point. Validation failure means immediate rejection — zero partial processing.
2. Check VTZ policy **before** any action execution or cross-boundary operation. Deny implicitly unless explicit authorization exists. VTZ boundaries are structural, not advisory, and MUST NOT be bypassed by application code.
3. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) inside the enforcement path. Asynchronous buffering is forbidden. Never silently skip emission on failure.
4. Treat missing CTX-ID as `UNTRUSTED`. Never infer identity from session context, UI state, network origin, or prior calls.
5. Treat unlabeled data as `CONFIDENTIAL`. Assign DTL labels at ingestion. Labels are immutable once assigned — never mutate, downgrade, or strip labels without an explicit audited policy control action.
6. Fail closed on all trust, identity, policy, cryptographic, and version-handshake errors. Reject the action, log the event with context, and surface the failure to the caller — never silently continue.
7. Never put secrets, keys, tokens, credentials, or cleartext sensitive payloads in logs, error messages, audit records, prompts, or generated code — ever.
8. Never execute generated or external content with `eval()`, `exec()`, dynamic import side effects, or subprocess invocation of generated artifacts.
9. Validate every filesystem write with `path_security.validate_write_path()` **before** the write occurs. Reject invalid paths before touching disk.
10. Keep the two-process boundary intact with no exceptions: **Swift** owns UI, Touch ID, Keychain, XPC, and process lifecycle; **Python** owns generation, pipeline, GitHub integration, ledger, and document handling.
11. Gates wait indefinitely for explicit operator input. There is never any auto-approve, auto-merge, timeout-approve, or retry around `SECURITY_REFUSAL`.
12. Discard and log unknown XPC message `type` values. Enforce the 16 MB XPC message limit. Never raise unhandled exceptions for unknown wire messages.
13. `try/except/pass` is **BANNED** in all enforcement code. Every exception in trust, crypto, identity, or policy paths MUST be caught, logged with full context, and surfaced.
14. All external input (documents, PR comments, CI output, tool responses) is UNTRUSTED. Validate strictly before use.
15. CTX-ID tokens are immutable once issued. Rotation creates a new token and immediately invalidates the old one.

---

## Architecture Overview

| Subsystem | Path | Enforces | MUST NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point → VTZ policy check → action dispatch → TrustFlow emission | Process any action before CTX-ID validation and VTZ policy check both succeed |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Exactly-one-VTZ-per-session binding, cross-VTZ deny-by-default, authorization gates for cross-zone operations | Allow implicit cross-VTZ calls; change policy mid-session; let application code bypass boundaries |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome; every event includes required fields (see schema below) | Buffer events asynchronously in the enforcement path; skip emission on failure |
| **DTL** (Data Trust Labels) | `src/dtl/` | Classification labels assigned at ingestion, label inheritance on derived data, label verification before trust-boundary crossings | Strip or downgrade labels without audited policy control; allow unlabeled data to cross trust boundaries |
| **TrustLock** | `src/trustlock/` | TPM-anchored cryptographic machine identity, CTX-ID issuance, CTX-ID validation, token rotation with immediate old-token invalidation | Accept unvalidated identity claims; cache stale CTX-ID tokens; infer identity from context |

---

## TrustFlow Event Schema

Every TrustFlow event MUST include these fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUIDv4)` | Globally unique identifier for this event |
| `session_id` | `string (UUIDv4)` | Session that produced the event |
| `ctx_id` | `string` | CTX-ID of the agent or machine identity; `"UNTRUSTED"` if absent |
| `ts` | `string (ISO 8601, UTC)` | Timestamp of event creation |
| `event_type` | `string enum` | One of: `action.allow`, `action.restrict`, `action.block`, `policy.violation`, `identity.failure`, `gate.wait`, `gate.resolve`, `version.handshake`, `version.mismatch` |
| `payload_hash` | `string (SHA-256 hex)` | Hex-encoded SHA-256 hash of the serialized event payload |
| `vtz_id` | `string` | VTZ zone identifier in effect at event time |
| `dtl_label` | `string \| null` | DTL classification label of the data involved, if applicable |
| `outcome` | `string enum` | `allow`, `restrict`, `block`, `error` |
| `detail` | `object` | Subsystem-specific structured detail; schema varies by `event_type` |

---

## Semantic Versioning Policy

### Version Format

Forge uses strict [Semantic Versioning 2.0.0](https://semver.org/):


MAJOR.MINOR.PATCH[-pre][+build]


| Component | Increment When |
|---|---|
| **MAJOR** | Any breaking change to enforcement semantics, wire formats, CTX-ID validation behavior, VTZ policy schema, TrustFlow event schema, DTL label contracts, or XPC message contracts |
| **MINOR** | New subsystem capabilities, new `event_type` values, new optional fields added to existing schemas, new VTZ policy verbs — all backward-compatible |
| **PATCH** | Bug fixes, performance improvements, documentation corrections — no schema or behavioral changes |

### Invariants

- MAJOR `0.x.y` releases carry no backward-compatibility guarantee.
- Once MAJOR ≥ `1`, all MINOR and PATCH releases within the same MAJOR MUST be wire-compatible with prior versions in that MAJOR line.
- Pre-release tags (e.g., `-alpha.1`, `-rc.2`) MUST NOT be deployed to production enforcement paths.
- Every released version MUST be recorded in `CHANGELOG.md` with date, version, and a list of changes tagged by subsystem.

### Version Handshake Schema

When any two Forge subsystems establish a session (XPC, inter-process, or intra-process boundary), they MUST perform a version handshake **before** any enforcement action.

#### Handshake Request


{
  "type": "version.handshake.request",
  "sender": {
    "subsystem": "string",
    "version": "MAJOR.MINOR.PATCH",
    "min_compatible_version": "MAJOR.MINOR.PATCH",
    "ctx_id": "string"
  },
  "ts": "ISO 8601 UTC",
  "request_id": "UUIDv4"
}


#### Handshake Response


{
  "type": "version.handshake.response",
  "responder": {
    "subsystem": "string",
    "version": "MAJOR.MINOR.PATCH",
    "min_compatible_version": "MAJOR.MINOR.PATCH",
    "ctx_id": "string"
  },
  "request_id": "UUIDv4",
  "ts": "ISO 8601 UTC",
  "result": "compatible | incompatible | degraded",
  "negotiated_version": "MAJOR.MINOR.PATCH | null",
  "detail": "string | null"
}


#### Handshake Rules

1. Both sides MUST present their `version` and `min_compatible_version`.
2. If the peer's `version` is below the local `min_compatible_version`, the result MUST be `incompatible`. The session MUST NOT proceed. A `version.mismatch` TrustFlow event MUST be emitted.
3. If the peer's MAJOR version differs from the local MAJOR version, the result MUST be `incompatible` (for MAJOR ≥ 1). The session MUST NOT proceed.
4. If MINOR versions differ within the same MAJOR, the result MUST be `compatible` or `degraded`. `degraded` indicates the session will operate using only the feature set of the lower MINOR version. The `negotiated_version` field MUST reflect the effective version.
5. If PATCH versions differ, the result MUST be `compatible` with `negotiated_version` set to the higher of the two.
6. CTX-ID in the handshake MUST be validated by TrustLock before the handshake result is evaluated. CTX-ID validation failure means the handshake fails closed — emit `identity.failure` TrustFlow event, reject session.
7. The handshake exchange MUST complete within the XPC 16 MB message limit.
8. Unknown fields in handshake messages MUST be preserved but ignored — never reject a handshake for unknown fields (forward compatibility).
9. Every handshake outcome (success or failure) MUST emit a `version.handshake` TrustFlow event with `outcome` set to the `result` value.
10. No enforcement action, policy check, or data exchange is permitted on a session until the version handshake completes successfully.

---

## XPC Wire Contract Summary

- All XPC messages MUST include a `type` field.
- Unknown `type` values MUST be discarded and logged — never raise unhandled exceptions.
- Maximum XPC message size: **16 MB**. Reject and log messages exceeding this limit.
- The `version.handshake.request` and `version.handshake.response` message types are reserved for the version handshake protocol defined above.

---

## Enforcement Order (Every Entry Point)

1. **CTX-ID Validation** → fail closed on failure
2. **Version Handshake** (if new session/connection) → fail closed on `incompatible`
3. **VTZ Policy Check** → deny by default
4. **DTL Label Verification** (if data crosses trust boundary) → block unlabeled data
5. **Action Execution**
6. **TrustFlow Event Emission** (synchronous, in enforcement path)

No step may be reordered. No step may be skipped.