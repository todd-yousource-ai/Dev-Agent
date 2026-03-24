# INTERFACES.md

Definitive interface and wire-format reference derived from the provided TRD material only.

---

## Scope

This document captures the interface contracts explicitly present in the provided TRD excerpts and standards material for Crafted Dev Agent.

Product identity established by the source documents:

- Product: **Crafted / Crafted Dev Agent**
- Architecture: **two-process**
  - **Swift shell**: UI, authentication, Keychain, XPC/orchestration responsibilities
  - **Python backend**: consensus, generation pipeline, GitHub operations
- Inter-process communication: **authenticated Unix socket with line-delimited JSON**
- Platform baseline: **macOS 13.0+**
- Languages:
  - Swift 5.9+
  - SwiftUI
  - Python 3.12 (bundled)

This file does **not** invent interfaces beyond what is stated in the provided materials.

---

# Interface Contracts

## System Boundary Overview

### Process boundaries

The system consists of exactly two major runtime subsystems:

1. **macOS Application Shell**
   - Native Swift/SwiftUI container
   - Owns:
     - UI
     - authentication
     - Keychain secret storage
     - session lifecycle
     - packaging/install/update
     - orchestration of subsystems

2. **Python Backend**
   - Owns:
     - intelligence
     - generation
     - consensus
     - GitHub operations

### Cross-process transport

The provided specification states:

- The Swift process and Python process communicate via an **authenticated Unix socket**
- Message framing is **line-delimited JSON**

Therefore, the canonical transport contract is:

- Transport: Unix domain socket
- Authentication: required
- Framing: one JSON object per line

---

# Per-Subsystem Data Structures

Only data structures explicitly named or required in the provided documents are defined below.

## 1. Unix Socket Message Envelope

Because cross-process communication is specified as **line-delimited JSON**, every cross-process message MUST be a single valid JSON object serialized on one line.

### Type

```json
object
```

### Constraints

- MUST serialize to exactly one line of UTF-8 JSON text
- MUST be valid JSON object syntax
- MUST not rely on multi-line framing
- MUST be suitable for authenticated Unix socket transport

### Minimal envelope contract

The provided documents do not define canonical top-level message fields for all IPC messages. Therefore, only the wire constraint is normative:

- one message = one JSON object
- one object = one line

No additional envelope fields are specified in the provided material.

---

## 2. TrustFlow Event

Defined by the **TrustFlow Emission Contract**.

### Structure

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `event_id` | string | Yes | MUST be globally unique; MUST be generated via CSPRNG; MUST NOT be sequential |
| `session_id` | string | Yes | Session identifier |
| `ctx_id` | string | Yes | Context identity token identifier |
| `ts` | number or integer | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Event type discriminator |
| `payload_hash` | string | Yes | MUST be SHA-256 of serialized action payload |

### Semantic requirements

- Every TrustFlow event MUST include all listed fields
- Emission MUST be synchronous in the enforcement path
- Async buffering is not permitted
- Failed emission is a WARN-level audit event
- Emission failure MUST NOT be silently ignored

---

## 3. VTZ Enforcement Decision Record

Defined by the **CAL Enforcement Contract**.

### Structure

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `verdict` | string | Yes | MUST be `"block"` when produced for VTZ policy denial |

### Semantic requirements

- Every action MUST be checked against VTZ policy before execution
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record
- For denial, `verdict` MUST equal `block`

No other fields are explicitly specified in the provided text.

---

## 4. Error Record

Defined by the **Error Handling Contract**.

### Structure

| Field | Type | Required | Constraints |
|---|---:|---:|---|
| `component` | string | Yes | Identifies failing component |
| `operation` | string | Yes | Identifies failing operation |
| `failure_reason` | string | Yes | Failure cause summary |
| `ctx_id` | string | Conditional | Required if available |

### Semantic requirements

- All trust, identity, policy, and cryptographic failures MUST fail closed
- Errors MUST reject the action, log the event, and surface to caller
- Error messages MUST NOT include:
  - keys
  - tokens
  - secrets
  - cleartext payloads

---

## 5. Audit Record

Defined by the **Audit Contract** and related security contracts.

### Structure

The provided documents do not define a full field schema for audit records.

### Normative contract

- Every security-relevant action MUST generate an audit record BEFORE execution
- Audit records are APPEND-ONLY

No further wire-level field list is specified in the supplied materials.

---

## 6. CTX-ID Token

Defined by the **CTX-ID Contract**.

### Structure

The provided materials define behavioral constraints but do not provide a full field-level serialized schema.

### Normative properties

- CTX-ID tokens are immutable once issued
- Rotation creates a new token
- Old token is invalidated immediately upon rotation
- Expired tokens MUST be rejected
- Validation MUST occur against a TrustLock public key
- Missing CTX-ID MUST be treated as untrusted
- Identity MUST NOT be inferred from surrounding context in the absence of CTX-ID

---

## 7. DTL Label

Defined by the **DTL Label Contract**.

### Structure

A full serialized schema is not provided. The classification label is the key semantic field.

### Normative properties

- Labels are assigned at data ingestion
- Labels are immutable thereafter
- Derived data inherits the highest classification of any source
- Unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified
- Label verification MUST occur before crossing a trust boundary
- Label stripping is a security event and MUST be audited and policy-controlled

---

# Cross-Subsystem Protocols

## 1. Swift Shell ↔ Python Backend IPC

### Transport

- Authenticated Unix socket

### Framing

- Line-delimited JSON

### Producer requirements

Any process writing messages to the socket MUST:

- serialize each message as a single JSON object
- terminate each message with a newline delimiter
- avoid multi-line JSON formatting

### Consumer requirements

Any process reading from the socket MUST:

- parse one complete line as one complete JSON message
- reject invalid JSON
- reject unauthenticated communication
- fail closed for security-relevant validation failures

---

## 2. Enforcement Path Protocol

Derived from the **CAL Enforcement Contract**, **CTX-ID Contract**, **VTZ Enforcement Contract**, **TrustFlow Emission Contract**, and **Error Handling Contract**.

### Mandatory execution order

For every entry point that processes an agent action:

1. **CTX-ID validation MUST occur first**
2. If CTX-ID validation fails:
   - processing MUST stop immediately
   - no partial processing is allowed
   - failure MUST be surfaced
3. **VTZ policy check MUST occur before execution**
4. If VTZ denies:
   - action MUST NOT execute
   - a `VTZEnforcementDecision` record MUST be produced with `verdict=block`
5. **TrustFlow event MUST be emitted for every outcome**
   - allow
   - restrict
   - block
6. If TrustFlow emission fails:
   - failure MUST be logged
   - failure MUST be surfaced
   - failure MUST NOT be silently ignored

### Fail-closed rule

For trust, identity, policy, and cryptographic failures:

- reject the action
- log the event
- surface to caller
- never silently continue

---

## 3. Session-to-VTZ Binding Protocol

Derived from the **VTZ Enforcement Contract**.

### Binding rules

- Every agent session is bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization
- Implicit cross-VTZ access is denied
- VTZ policy changes take effect at next CTX-ID issuance
- VTZ policy does not change mid-session through application logic

---

## 4. Data Classification Propagation Protocol

Derived from the **DTL Label Contract**.

### Ingestion

- Data labels are assigned at ingestion time

### Mutation

- Labels are immutable after assignment

### Derivation

- Derived data inherits the highest classification of any source input

### Defaulting

- Unlabeled data defaults to `CONFIDENTIAL`

### Boundary crossing

- Label verification MUST happen before data crosses a trust boundary

### Label stripping

- Treated as a security event
- MUST be audited
- MUST be policy-controlled

---

## 5. Security Audit Protocol

Derived from the **Audit Contract** and related enforcement requirements.

### Required behavior

- Every security-relevant action MUST generate an audit record BEFORE execution
- Audit records are append-only
- TrustFlow failures are WARN-level audit events
- Enforcement-path exceptions MUST NOT be swallowed

---

# Enums and Constants

Only values explicitly present in the supplied documents are listed.

## Verdict Values

### `VTZEnforcementDecision.verdict`

| Value | Meaning |
|---|---|
| `block` | VTZ policy denied the action |

---

## Action Outcome Values

The CAL contract states every action outcome is one of:

| Value | Meaning |
|---|---|
| `allow` | Action permitted |
| `restrict` | Action permitted with restriction |
| `block` | Action denied |

These are normative outcome categories for TrustFlow emission and enforcement behavior.

---

## DTL Classification Constants

| Value | Meaning |
|---|---|
| `CONFIDENTIAL` | Default classification for unlabeled data |

No other classification labels are explicitly defined in the provided excerpts.

---

## Timestamp Precision Constant

| Constant | Requirement |
|---|---|
| `ts` precision | UTC Unix timestamp with millisecond precision |

---

## Platform / Runtime Constants

| Constant | Value |
|---|---|
| Minimum macOS version | `13.0` |
| Swift version baseline | `5.9+` |
| Python version baseline | `3.12` |

---

# Validation Rules

## 1. IPC Message Validation

For every cross-process message:

- MUST be valid JSON
- MUST be a JSON object
- MUST fit on a single line
- MUST be sent over an authenticated Unix socket

Messages failing these constraints are non-conformant.

---

## 2. CTX-ID Validation Rules

For every action-processing entry point:

- CTX-ID validation MUST happen first
- Missing CTX-ID MUST be treated as untrusted
- Expired CTX-ID MUST be rejected
- CTX-ID MUST be validated against TrustLock public key
- Software-only validation is rejected
- CTX-ID fields MUST NOT be modified after issuance
- Rotation MUST create a new token
- Old CTX-ID MUST be invalidated immediately on rotation

If CTX-ID validation fails:

- reject immediately
- perform no partial processing
- fail closed

---

## 3. VTZ Validation Rules

For every action:

- MUST be checked against VTZ policy before execution
- session MUST be bound to exactly one VTZ
- cross-VTZ tool calls require explicit authorization
- implicit cross-VTZ access is denied

If VTZ denies:

- action MUST NOT execute
- `VTZEnforcementDecision` MUST be emitted or recorded with `verdict=block`
- TrustFlow event MUST still be emitted for the blocked outcome

---

## 4. TrustFlow Validation Rules

Every TrustFlow event MUST include:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional rules:

- `event_id` MUST be globally unique
- `event_id` MUST be CSPRNG-generated
- `event_id` MUST NOT be sequential
- `ts` MUST be UTC Unix time with millisecond precision
- `payload_hash` MUST be SHA-256 of the serialized action payload
- emission MUST be synchronous in enforcement path
- async buffering is not permitted

On emission failure:

- MUST log
- MUST surface failure
- MUST NOT silently continue
- MUST create WARN-level audit visibility

---

## 5. Error Record Validation Rules

Every applicable error MUST include:

- `component`
- `operation`
- `failure_reason`
- `ctx_id` if available

Error content MUST NOT include:

- keys
- tokens
- secrets
- cleartext payloads

Swallowing exceptions in enforcement paths is prohibited.

---

## 6. Audit Validation Rules

For every security-relevant action:

- audit record MUST be generated before execution
- audit log MUST be append-only

---

## 7. DTL Label Validation Rules

For classified data handling:

- labels MUST be assigned at ingestion
- labels MUST be immutable
- unlabeled data MUST be treated as `CONFIDENTIAL`
- derived data MUST inherit highest source classification
- label verification MUST occur before trust-boundary crossing
- label stripping MUST be audited and policy-controlled

---

# Wire Format Examples

Examples below use only structures explicitly defined or minimally implied by the provided documents.

## 1. Line-Delimited JSON IPC Message

```json
{"message_type":"action_request","session_id":"sess_01HZX8YQ7YF8K4A1M2N3P4Q5R6","ctx_id":"ctx_01HZX8Z2B3C4D5E6F7G8H9J0K1","action":"generate_pr"}
```

Wire representation on socket:

```text
{"message_type":"action_request","session_id":"sess_01HZX8YQ7YF8K4A1M2N3P4Q5R6","ctx_id":"ctx_01HZX8Z2B3C4D5E6F7G8H9J0K1","action":"generate_pr"}\n
```

Notes:

- JSON object is on one line
- newline terminates the frame
- field names beyond framing are illustrative except where otherwise specified by contract

---

## 2. TrustFlow Event

```json
{
  "event_id": "tf_2f6c4c9b9d1e4b7d8a0f6e2c3b1a9d55",
  "session_id": "sess_01HZX8YQ7YF8K4A1M2N3P4Q5R6",
  "ctx_id": "ctx_01HZX8Z2B3C4D5E6F7G8H9J0K1",
  "ts": 1773890123456,
  "event_type": "policy_block",
  "payload_hash": "4d967a7fbbd6c0e1b2e6c3ff7a18c7d4b3d6aa9d8f1e2c4b5a69788776655443"
}
```

---

## 3. VTZ Enforcement Decision Record

```json
{
  "verdict": "block"
}
```

---

## 4. Error Record

```json
{
  "component": "policy_enforcer",
  "operation": "validate_ctx_id",
  "failure_reason": "expired_ctx_id",
  "ctx_id": "ctx_01HZX8Z2B3C4D5E6F7G8H9J0K1"
}
```

---

## 5. Blocked Action Enforcement Sequence

This example demonstrates contract ordering across subsystems.

### Action request

```json
{
  "message_type": "action_request",
  "session_id": "sess_01HZX8YQ7YF8K4A1M2N3P4Q5R6",
  "ctx_id": "ctx_01HZX8Z2B3C4D5E6F7G8H9J0K1",
  "action": "cross_vtz_tool_call"
}
```

### VTZ denial record

```json
{
  "verdict": "block"
}
```

### TrustFlow record for blocked outcome

```json
{
  "event_id": "tf_e9f7b4a3c2d14e57a8f90b1c2d3e4f55",
  "session_id": "sess_01HZX8YQ7YF8K4A1M2N3P4Q5R6",
  "ctx_id": "ctx_01HZX8Z2B3C4D5E6F7G8H9J0K1",
  "ts": 1773890123999,
  "event_type": "block",
  "payload_hash": "f0d1c2b3a495867768594a3b2c1d0e9fa8b7c6d5e4f30123456789abcdef0123"
}
```

---

## 6. CTX-ID Validation Failure Error

```json
{
  "component": "auth_gateway",
  "operation": "process_agent_action",
  "failure_reason": "missing_ctx_id"
}
```

Behavioral consequence:

- request is rejected immediately
- no partial processing occurs
- failure is logged and surfaced
- no identity is inferred from surrounding context

---

# Conformance Summary

A component is non-conformant with the provided interface contracts if any of the following occur:

- agent action processing begins before CTX-ID validation
- VTZ policy is not checked before execution
- VTZ denial does not produce `verdict=block`
- TrustFlow event is missing required fields
- TrustFlow emission is async-buffered in enforcement path
- TrustFlow emission failure is silently ignored
- missing or expired CTX-ID is allowed
- software-only CTX-ID validation is used
- cross-VTZ access is implicitly permitted
- unlabeled data is treated as anything other than `CONFIDENTIAL`
- label verification is skipped before trust-boundary crossing
- security-relevant actions execute before audit record creation
- enforcement-path exceptions are swallowed
- error messages include secrets or cleartext payloads
- IPC is not authenticated Unix-socket line-delimited JSON

---

# Source-Derived Notes

The following are stated in the supplied source excerpts and therefore part of the interface context:

- The shell owns UI, authentication, Keychain, and session lifecycle concerns
- The backend owns intelligence, generation, consensus, and GitHub operations
- Generated code is never executed by either process
- TRDs are the source of truth for all interfaces and error contracts
- Security-relevant implementation is governed by the specified security controls above

No additional wire formats, RPC method names, payload schemas, or event taxonomies were defined in the provided materials, so they are intentionally omitted here.