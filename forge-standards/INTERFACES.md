# INTERFACES.md

Definitive wire format and API contract reference derived from the provided TRD materials only.

---

# Scope

This document captures the interface and wire-format contracts explicitly stated in the provided materials for Crafted Dev Agent.

Source materials used:

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `TRD-1: macOS Application Shell`
- `Forge Component Interface Contracts`

Where the provided materials name a subsystem but do not define a field-level schema, this document records only the contract that is actually specified. No unstated requirements are invented.

---

# System Interface Overview

Crafted is a **two-process macOS application**:

- **Swift shell**
  - Owns UI
  - Owns authentication
  - Owns Keychain secret storage
  - Owns orchestration
  - Owns XPC-related shell responsibilities per repository identity text
- **Python backend**
  - Owns intelligence / generation
  - Owns consensus / pipeline
  - Owns GitHub operations

## Inter-process transport

The provided documents explicitly define the shell/backend transport as:

- **authenticated Unix socket**
- **line-delimited JSON**

This is the only wire-format statement provided for shell/backend IPC.

---

# Interface Contracts

## Global Interface Requirements

The following requirements apply across components where relevant.

### Process boundary contract

- Swift shell and Python backend are separate processes.
- Communication between them occurs over an **authenticated Unix socket**.
- Messages are encoded as **line-delimited JSON**.

### Execution safety contract

- Neither process may execute generated code.

### Specification authority contract

- Interfaces, error contracts, state machines, security controls, and performance requirements are governed by TRDs.
- Security-relevant behavior is governed by `TRD-11`, but no additional `TRD-11` field schemas were provided in the input.

---

# Per-Subsystem Data Structures

Only structures explicitly named or constrained in the provided materials are included.

## 1. Shell ↔ Backend Message Envelope

### Transport
- Medium: authenticated Unix socket
- Encoding: JSON
- Framing: one JSON object per line

### Message structure
The provided documents define framing and encoding, but do **not** define a canonical top-level message schema.

#### Contractually known properties
- Must be valid JSON
- Must be delimited by newline boundaries for message framing
- Must be sent over an authenticated Unix socket

#### Undefined by provided materials
The following are not specified in the provided text and therefore have no normative schema here:
- request id field
- method or command field
- response correlation field
- success/error envelope
- version field
- batching semantics

---

## 2. TrustFlow Event

The TrustFlow Emission Contract defines a required event structure.

### Data structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Globally unique; generated via CSPRNG; must not be sequential |
| `session_id` | string | Yes | Session identifier |
| `ctx_id` | string | Yes | CTX-ID associated with the event |
| `ts` | number or integer | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Event type name |
| `payload_hash` | string | Yes | SHA-256 of the serialized action payload |

### Behavioral constraints
- Every TrustFlow event must include all fields above.
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failure to emit is a WARN-level audit event.
- Failed emission must not be silently skipped.
- Every action outcome (`allow`, `restrict`, `block`) must emit a TrustFlow event.

---

## 3. VTZ Enforcement Decision Record

The CAL Enforcement Contract explicitly names this record.

### Data structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Must be `block` when generated for VTZ policy denial |

### Behavioral constraints
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

### Undefined by provided materials
No additional fields for `VTZEnforcementDecision` are specified in the provided text.

---

## 4. Error Record

The Error Handling Contract defines mandatory error contents.

### Data structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `component` | string | Yes | Name of emitting component |
| `operation` | string | Yes | Operation being performed |
| `failure_reason` | string | Yes | Non-secret description of failure |
| `ctx_id` | string | Conditional | Required if available |

### Behavioral constraints
- All trust, identity, policy, and cryptographic failures must fail closed.
- Fail closed means:
  - reject the action
  - log the event
  - surface to caller
  - never silently continue
- No swallowed exceptions in enforcement paths.
- Error messages must not include:
  - keys
  - tokens
  - secrets
  - cleartext payloads

---

## 5. Audit Record

The Audit Contract defines lifecycle and mutability requirements, but the provided text is truncated and does not provide a full field schema.

### Contractually known properties
- Every security-relevant action must generate an audit record **before execution**.
- Audit records are **append-only**.

### Undefined by provided materials
No complete field list is present in the provided input.

---

## 6. CTX-ID Token

The CTX-ID Contract defines validation and lifecycle properties.

### Contractually known properties
- CTX-ID tokens are immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately upon rotation.
- Expired CTX-ID must be rejected.
- Validation must be against a TrustLock public key.
- Software-only validation is rejected.
- Missing CTX-ID must be treated as untrusted.
- Identity must never be inferred from context when CTX-ID is missing.

### Undefined by provided materials
The token field layout, encoding, cryptographic envelope, and serialized representation are not specified in the provided text.

---

## 7. DTL Label

The DTL Label Contract defines lifecycle semantics.

### Contractually known properties
- Labels are assigned at data ingestion.
- Labels are immutable thereafter.
- Derived data inherits the highest classification of any source.
- Unlabeled data must be treated as `CONFIDENTIAL` until explicitly reclassified.
- Label verification must occur before crossing a trust boundary.
- Label stripping is a security event and must be audited and policy-controlled.

### Undefined by provided materials
No explicit label field schema or exhaustive label enum is defined in the provided text beyond `CONFIDENTIAL`.

---

## 8. Agent Action

The standards define behavior for “every entry point that processes an agent action,” but no full schema is given.

### Contractually known properties
An action payload exists and is serialized for hashing, because:

- `payload_hash` must be SHA-256 of the serialized action payload
- every action must undergo:
  - CTX-ID validation first
  - VTZ policy evaluation before execution
  - TrustFlow emission for outcome
  - audit record generation before execution for security-relevant actions

### Undefined by provided materials
No normative action field list is provided.

---

## 9. Session Binding

The VTZ Enforcement Contract defines a session-level association.

### Contractually known properties
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- VTZ policy changes take effect at next CTX-ID issuance, not mid-session.

### Undefined by provided materials
The serialized session structure is not defined in the provided text.

---

# Cross-Subsystem Protocols

## 1. Shell ↔ Backend IPC Protocol

### Transport contract
- Authenticated Unix socket
- Line-delimited JSON

### Security contract
- Socket must be authenticated.
- No additional handshake format is specified in the provided materials.

### Message framing contract
- Exactly one JSON message per line.
- Newline acts as record boundary.

### Undefined by provided materials
Not specified:
- request/response semantics
- streaming semantics
- heartbeat
- retry behavior
- backpressure
- schema version negotiation

---

## 2. CAL Enforcement Protocol

Applies to every entry point that processes an agent action.

### Required sequence
1. **CTX-ID validation first**
2. Immediate rejection on CTX-ID validation failure
3. **VTZ policy check before execution**
4. If VTZ denied, produce `VTZEnforcementDecision` with `verdict=block`
5. Emit TrustFlow event for action outcome
6. If TrustFlow emission fails, do not silently continue; log and surface the failure

### Ordering constraints
- CTX-ID validation must happen before any partial processing.
- VTZ authorization must happen before execution.
- TrustFlow emission is in the enforcement path and synchronous.

---

## 3. CTX-ID Validation Protocol

### Required behavior
- Validate CTX-ID first for any agent action entry point.
- Reject missing CTX-ID as untrusted.
- Reject expired CTX-ID.
- Validate against TrustLock public key.
- Do not rely on software-only validation.
- Rotation invalidates the old token immediately.

### Session coupling
- Each agent session is bound to exactly one VTZ at CTX-ID issuance.

---

## 4. VTZ Policy Enforcement Protocol

### Required behavior
- Every action must be checked against VTZ policy before execution.
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes apply only at next CTX-ID issuance.

### Denial behavior
- Produce a `VTZEnforcementDecision` record with `verdict=block`.
- Emit corresponding TrustFlow event.
- Fail closed.

---

## 5. TrustFlow Emission Protocol

### Required event contents
- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Required behavior
- `event_id` must be globally unique and CSPRNG-generated.
- `ts` must be UTC Unix timestamp with millisecond precision.
- `payload_hash` must be SHA-256 of the serialized action payload.
- Emission must be synchronous in the enforcement path.
- Async buffering is not allowed.
- Failure is WARN-level audit event and must be surfaced, not silently skipped.

---

## 6. DTL Label Propagation Protocol

### Required behavior
- Assign labels at ingestion.
- Labels are immutable after assignment.
- Derived data inherits highest classification among sources.
- Unlabeled data defaults to `CONFIDENTIAL`.
- Verify labels before crossing trust boundaries.
- Label stripping must be audited and controlled by policy.

---

## 7. Error Propagation Protocol

### Required behavior
For trust, identity, policy, and cryptographic failures:

- fail closed
- reject action
- log event
- surface to caller
- do not silently continue

### Required error fields
- `component`
- `operation`
- `failure_reason`
- `ctx_id` if available

### Redaction rules
Errors must not contain:
- keys
- tokens
- secrets
- cleartext payloads

---

## 8. Audit Protocol

### Required behavior
- Every security-relevant action must generate an audit record before execution.
- Audit records are append-only.

### Undefined by provided materials
- no audit schema fields were fully provided
- no retention or export format was provided

---

# Enums and Constants

Only values explicitly stated in the provided materials are listed.

## Verdict Values

### `VTZEnforcementDecision.verdict`
| Value | Meaning |
|---|---|
| `block` | Required value for VTZ policy denial |

### Action outcome values for TrustFlow emission
The CAL Enforcement Contract explicitly names these outcomes:

| Value | Meaning |
|---|---|
| `allow` | Action permitted |
| `restrict` | Action restricted |
| `block` | Action denied |

---

## DTL Classification Values

| Value | Meaning |
|---|---|
| `CONFIDENTIAL` | Default treatment for unlabeled data until explicitly reclassified |

No additional classifications are provided in the supplied text.

---

## Time Format Constant

### `ts`
- UTC Unix timestamp
- millisecond precision

---

## Cryptographic Constant

### `payload_hash`
- Algorithm: `SHA-256`

---

## Platform / Version Constants

These are product constraints rather than wire constants, but are explicitly specified.

| Name | Value |
|---|---|
| Product | `Crafted` |
| Min macOS | `13.0` |
| Swift | `5.9+` |
| Python | `3.12` |

---

# Validation Rules

## 1. JSON Framing Validation

For shell/backend IPC messages:

- message must be valid JSON
- one message per line
- newline is the record delimiter
- transport must be authenticated Unix socket

If any of the above are violated, message is non-conformant.

---

## 2. CTX-ID Validation Rules

- CTX-ID validation must occur first at every agent action entry point.
- Missing CTX-ID:
  - treat as untrusted
  - never infer identity from context
- Expired CTX-ID:
  - reject
- CTX-ID immutability:
  - no field modification after issuance
- Rotation:
  - issue new token
  - invalidate old token immediately
- Validation method:
  - must validate against TrustLock public key
  - software-only validation is rejected

---

## 3. VTZ Validation Rules

- Every session must be bound to exactly one VTZ at CTX-ID issuance.
- Every action must be checked against VTZ policy before execution.
- Cross-VTZ tool calls:
  - require explicit policy authorization
  - implicit authorization is denied
- VTZ boundaries cannot be bypassed by application code.
- Policy changes apply only at next CTX-ID issuance.

---

## 4. TrustFlow Validation Rules

A TrustFlow event is valid only if all required fields are present:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional validation:
- `event_id` must be globally unique
- `event_id` must be CSPRNG-generated
- `event_id` must not be sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must equal SHA-256 of serialized action payload

Operational validation:
- emission must be synchronous in enforcement path
- async buffering is prohibited

---

## 5. DTL Label Validation Rules

- Label must be assigned at ingestion.
- Label cannot be modified after assignment.
- Derived data must inherit highest source classification.
- Unlabeled data must be treated as `CONFIDENTIAL`.
- Label verification is required before trust-boundary crossing.
- Label stripping must be audited and policy-controlled.

---

## 6. Error Validation Rules

Every trust, identity, policy, or cryptographic error must:

- fail closed
- reject the action
- log the event
- surface to caller

Every such error record must include:
- `component`
- `operation`
- `failure_reason`
- `ctx_id` if available

Error content must exclude:
- keys
- tokens
- secrets
- cleartext payloads

Swallowed exceptions are forbidden in enforcement paths.

---

## 7. Audit Validation Rules

- Security-relevant actions require audit record generation before execution.
- Audit records must be append-only.

---

# Wire Format Examples

Examples below are constrained to the schemas and fields explicitly provided by the source materials.

## 1. Line-delimited JSON over Unix socket

Example conceptual stream:

```json
{"type":"request","payload":"example"}
{"type":"response","payload":"example"}
```

Notes:
- The use of `type` and `payload` here is illustrative only.
- The provided materials specify **line-delimited JSON** transport, but do **not** define these fields as normative.

---

## 2. TrustFlow event

```json
{
  "event_id": "4f7c8b1d-7f66-4b14-bf85-1f10e4f92c35",
  "session_id": "sess_01HZZZZZZZZZZZZZZZZZZZZZZ",
  "ctx_id": "ctx_01HYYYYYYYYYYYYYYYYYYYYY",
  "ts": 1773883200123,
  "event_type": "action.block",
  "payload_hash": "7f83b1657ff1fc53b92dc18148a1d65dfa135014a5f1f4a5f5d1f8a7c5e9f3d2"
}
```

This example is valid with respect to the provided contract if:
- `event_id` is globally unique and CSPRNG-generated
- `ts` is UTC Unix time in milliseconds
- `payload_hash` is SHA-256 of the serialized action payload

---

## 3. VTZ enforcement denial record

```json
{
  "verdict": "block"
}
```

This is the only required field explicitly specified for `VTZEnforcementDecision` in the provided materials.

---

## 4. Error record

```json
{
  "component": "policy_enforcer",
  "operation": "evaluate_action",
  "failure_reason": "CTX-ID expired",
  "ctx_id": "ctx_01HYYYYYYYYYYYYYYYYYYYYY"
}
```

Conformance notes:
- must not include secrets, tokens, keys, or cleartext payloads
- must fail closed operationally

---

## 5. Missing CTX-ID case

Illustrative error representation:

```json
{
  "component": "action_gateway",
  "operation": "validate_ctx",
  "failure_reason": "Missing CTX-ID"
}
```

Conformance notes:
- missing CTX-ID must be treated as untrusted
- identity must not be inferred from context
- action must be rejected immediately

---

## 6. TrustFlow event for restricted action outcome

```json
{
  "event_id": "9c5d4c89-8f17-4d58-a845-b87210db0cb4",
  "session_id": "sess_01HZZZZZZZZZZZZZZZZZZZZZZ",
  "ctx_id": "ctx_01HYYYYYYYYYYYYYYYYYYYYY",
  "ts": 1773883201456,
  "event_type": "action.restrict",
  "payload_hash": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
}
```

---

# Conformance Checklist

A component is interface-conformant to the provided materials only if all applicable requirements below are met.

## IPC conformance
- Uses authenticated Unix socket
- Uses line-delimited JSON framing

## CAL enforcement conformance
- Validates CTX-ID first
- Rejects immediately on CTX-ID failure
- Checks VTZ before execution
- Emits `VTZEnforcementDecision.verdict=block` on VTZ denial
- Emits TrustFlow event for allow/restrict/block
- Does not silently continue on TrustFlow emission failure

## TrustFlow conformance
- Includes all required fields
- Uses CSPRNG global-unique `event_id`
- Uses millisecond UTC Unix `ts`
- Uses SHA-256 `payload_hash`
- Emits synchronously in enforcement path

## CTX-ID conformance
- Immutable after issuance
- Rotation creates new token and invalidates old token
- Expired token rejected
- Missing token treated as untrusted
- Validated against TrustLock public key
- No software-only validation

## VTZ conformance
- Exactly one VTZ per session at CTX-ID issuance
- Cross-VTZ calls require explicit authorization
- No application bypass of VTZ boundary
- Policy updates effective only at next CTX-ID issuance

## DTL conformance
- Labels assigned at ingestion
- Labels immutable
- Derived data inherits highest classification
- Unlabeled data treated as `CONFIDENTIAL`
- Labels verified before trust-boundary crossing
- Label stripping audited and policy-controlled

## Error conformance
- Fails closed on trust/identity/policy/crypto failure
- Logs and surfaces failure
- Includes required error fields
- Excludes secrets and cleartext payloads
- No swallowed exceptions in enforcement path

## Audit conformance
- Generates audit record before security-relevant execution
- Keeps audit records append-only

---

# Explicit Non-Specified Areas

The following interfaces are mentioned by subsystem name in the provided materials but are not defined at field level in the supplied text, so no normative schema is included here:

- shell/backend request and response message schema
- authentication payload structures
- biometric gate payloads
- Keychain record formats
- XPC message schemas
- GitHub operation request/response bodies
- consensus engine inputs/outputs
- PRD / PR planning object schemas
- CI result schemas
- Sparkle update feed or update payload schema
- audit record field schema beyond append-only and pre-execution requirement
- CTX-ID serialized token schema
- DTL full classification enum
- TrustLock public key distribution format

If those schemas exist, they are outside the provided source excerpt and therefore intentionally omitted here.

---