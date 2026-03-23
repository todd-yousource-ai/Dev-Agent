# INTERFACES.md

# Interface Contracts — Forge Platform

This document defines the wire formats, API contracts, cross-subsystem protocols, validation rules, and required constants derivable from the provided TRD materials only.

## Source Authority

This interface reference is derived from:

- `TRD-1: macOS Application Shell`
- repository-level product descriptions in `README.md`
- agent operating constraints in `AGENTS.md`
- agent implementation guidance in `CLAUDE.md`
- Forge Component Interface Contracts

Where the supplied materials do not define a field, endpoint, payload member, or state value explicitly, this document does not invent one.

---

## System Boundary Overview

Crafted is a two-process macOS application:

- **Swift shell**
  - owns UI
  - owns authentication
  - owns Keychain secret storage
  - owns local orchestration
  - owns XPC-related shell responsibilities
- **Python backend**
  - owns intelligence
  - owns generation
  - owns consensus
  - owns GitHub operations

### Primary Inter-process Transport

The Swift shell and Python backend communicate via:

- **authenticated Unix socket**
- **line-delimited JSON**

### Execution Constraint

- Neither process executes generated code.

---

## Per-Subsystem Data Structures

Only structures explicitly required by the provided documents are defined below.

## 1. Inter-Process Message Envelope

The shell/backend transport is line-delimited JSON over an authenticated Unix socket.

Because the provided TRDs specify the transport format but do not provide a canonical top-level envelope schema, the only guaranteed wire-level contract is:

- each message is exactly one JSON value serialized on a single line
- message framing is newline-delimited
- messages must be valid JSON
- communication occurs only over an authenticated Unix socket

### Wire Type

```text
JSON object serialized as one line, UTF-8 encoded, terminated by '\n'
```

### Constraints

- Must be valid JSON.
- Must fit within a single line-delimited frame.
- Must not rely on multi-line framing.
- Must be exchanged only over an authenticated Unix socket.
- Authentication of the socket is mandatory.

### Not Guaranteed by Provided TRDs

The following are not defined in the supplied materials and therefore are not contractually specified here:

- required top-level keys
- request/response correlation key names
- message type discriminator names
- error payload schema for socket messages

---

## 2. TrustFlow Event

Defined by the Forge Component Interface Contracts.

### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Must be globally unique; must be generated via CSPRNG; must not be sequential |
| `session_id` | string | Yes | Session identifier |
| `ctx_id` | string | Yes | Context identity token associated with the action |
| `ts` | number | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Event type identifier |
| `payload_hash` | string | Yes | SHA-256 of the serialized action payload |

### Behavioral Requirements

- Every action outcome must emit a TrustFlow event.
- Outcomes include:
  - allow
  - restrict
  - block
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Emission failure:
  - must not silently continue
  - must be logged
  - must be surfaced
  - is a WARN-level audit event

---

## 3. VTZ Enforcement Decision Record

Defined indirectly by the CAL Enforcement Contract.

### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Must support value `block` when VTZ policy denies an action |

### Guaranteed Value

- `block`

### Behavioral Requirements

- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with:
  - `verdict=block`

### Not Defined by Provided TRDs

The supplied materials do not define additional fields for this record.

---

## 4. Error Record

Defined by the Error Handling Contract.

### Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `component` | string | Yes | Name of failing component |
| `operation` | string | Yes | Name of failing operation |
| `failure_reason` | string | Yes | Reason for failure; must not include secrets or cleartext payloads |
| `ctx_id` | string | Conditionally | Include if available |

### Behavioral Requirements

- All trust, identity, policy, and cryptographic failures must fail closed.
- Fail closed means:
  - reject the action
  - log the event
  - surface to caller
  - never silently continue
- No swallowed exceptions in enforcement paths.
- Errors must not include:
  - keys
  - tokens
  - secrets
  - cleartext payloads

---

## 5. Audit Record

Defined by the Audit Contract.

### Required Properties

The supplied document fragment defines these record-level requirements:

- every security-relevant action must generate an audit record **before execution**
- audit records are **append-only**

### Partially Specified Structure

The provided materials do not enumerate concrete field names for audit records beyond the requirements above. Therefore the contractually guaranteed structure is limited to:

| Property | Requirement |
|---|---|
| creation timing | Must occur before execution of a security-relevant action |
| mutability | Append-only |

---

## 6. CTX-ID Token

Defined by the CTX-ID Contract.

### Contractual Properties

| Property | Requirement |
|---|---|
| mutability | Immutable once issued |
| rotation | Rotation creates a new token; old token invalidated immediately |
| expiration | Expired token must be rejected |
| validation | Must be validated against TrustLock public key |
| identity inference | Missing token must be treated as untrusted |

### Behavioral Requirements

- No field modification after issuance.
- Validation must not be software-only if that means bypassing TrustLock public key validation.
- Missing `CTX-ID` must never be inferred from surrounding context.

### Not Defined by Provided TRDs

The supplied materials do not define:

- token serialization format
- embedded claims
- signature algorithm
- token transport header name
- TTL field name
- issuer/audience field names

---

## 7. DTL Label

Defined by the DTL Label Contract.

### Contractual Properties

| Property | Requirement |
|---|---|
| assignment timing | Assigned at data ingestion |
| mutability | Immutable after assignment |
| inheritance | Derived data inherits highest classification of any source |
| unlabeled handling | Must be treated as `CONFIDENTIAL` until explicitly reclassified |
| boundary verification | Must be verified before crossing a trust boundary |
| stripping | Label stripping is a security event; must be audited and policy-controlled |

### Guaranteed Classification Value

- `CONFIDENTIAL`

### Not Defined by Provided TRDs

The full label taxonomy is not provided in the supplied materials. Only `CONFIDENTIAL` is explicitly guaranteed.

---

## 8. Session Binding to VTZ

Defined by the VTZ Enforcement Contract.

### Contractual Properties

| Property | Requirement |
|---|---|
| VTZ cardinality | Every agent session is bound to exactly one VTZ at CTX-ID issuance |
| cross-VTZ calls | Require explicit policy authorization |
| default behavior | Implicit cross-VTZ access is denied |
| enforcement model | VTZ boundaries are structural and cannot be bypassed by application code |
| policy update timing | Policy changes take effect at next CTX-ID issuance, not mid-session |

### Implied Data Elements

The following identifiers are contractually required at the system level, though not fully schema-defined:

- `session_id`
- `ctx_id`
- VTZ identity reference

The exact field name for VTZ identity is not provided in the supplied materials.

---

## 9. Security-Relevant Action

The standards require multiple behaviors around “actions” and “agent actions,” but do not define a concrete object schema. The minimum contractually relevant action-related data elements are:

| Data Element | Source |
|---|---|
| action payload | TrustFlow payload hash requirement |
| ctx_id | CAL / CTX-ID / Error Handling contracts |
| session_id | TrustFlow contract |
| policy evaluation result | CAL / VTZ contracts |
| audit-before-execution | Audit contract |

Because no explicit action schema is provided, implementations must not assume additional required action fields from this document alone.

---

## Cross-Subsystem Protocols

## 1. Shell ↔ Backend IPC Protocol

### Transport

- authenticated Unix socket

### Framing

- line-delimited JSON

### Encoding

- JSON text
- one complete JSON message per line

### Security Requirements

- transport endpoint must be authenticated
- no unauthenticated transport is conformant
- generated code must not be executed by either side

### Ownership Split

| Concern | Owning Process |
|---|---|
| UI | Swift shell |
| authentication | Swift shell |
| Keychain secret storage | Swift shell |
| intelligence | Python backend |
| generation | Python backend |
| consensus | Python backend |
| GitHub operations | Python backend |

---

## 2. CAL Enforcement Protocol

Every entry point that processes an agent action must perform the following sequence.

### Required Order of Operations

1. **CTX-ID validation first**
2. immediate rejection on CTX-ID validation failure
3. **VTZ policy check before execution**
4. if denied, produce `VTZEnforcementDecision` with `verdict=block`
5. emit TrustFlow event for every outcome
6. if TrustFlow emission fails, log and surface the failure

### Hard Constraints

- No partial processing before CTX-ID validation.
- No execution before VTZ policy evaluation.
- No silent continuation after emission failure.

### Enforcement Flow

```text
receive action
→ validate CTX-ID first
  → if invalid/missing/expired: fail closed
→ evaluate VTZ policy
  → if denied: create VTZEnforcementDecision(verdict=block), emit TrustFlow, reject
  → if allowed/restricted: emit TrustFlow, continue per policy
```

---

## 3. TrustFlow Emission Protocol

### Trigger

- every action outcome:
  - allow
  - restrict
  - block

### Required Event Fields

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

### Processing Rules

- emission is synchronous in the enforcement path
- async buffering is forbidden
- failed emission is a WARN-level audit event
- failure must not be silently skipped

---

## 4. CTX-ID Lifecycle Protocol

### Issuance

- token becomes immutable once issued
- each session is bound to exactly one VTZ at issuance time

### Rotation

- rotation creates a new token
- old token is invalidated immediately

### Validation

- must validate against TrustLock public key
- expired token must be rejected
- missing token must be treated as untrusted

### Policy Interaction

- VTZ policy changes do not alter an in-flight session mid-session
- policy changes apply at next CTX-ID issuance

---

## 5. DTL Label Handling Protocol

### At Ingestion

- assign label at ingestion time

### After Ingestion

- label is immutable

### Derivation

- derived data inherits the highest classification of any source

### Boundary Crossing

- verify label before any trust-boundary crossing

### Exceptional Case

- label stripping is a security event
- label stripping must be:
  - audited
  - policy-controlled

---

## 6. Error Handling Protocol

### Applies To

- trust failures
- identity failures
- policy failures
- cryptographic failures

### Required Behavior

- fail closed
- reject the action
- log the event
- surface to caller
- never silently continue

### Error Record Requirements

Errors must include:

- `component`
- `operation`
- `failure_reason`
- `ctx_id` if available

Errors must not include:

- keys
- tokens
- secrets
- cleartext payloads

### Forbidden Pattern

- swallowed exceptions in enforcement paths

---

## 7. Audit Protocol

### Trigger

- every security-relevant action

### Required Timing

- audit record must be generated before execution

### Storage Semantics

- append-only

---

## Enums and Constants

Only values explicitly present in the supplied materials are included.

## 1. TrustFlow Outcome Values

```text
allow
restrict
block
```

## 2. VTZ Enforcement Verdict Values

```text
block
```

## 3. DTL Classification Values Explicitly Defined

```text
CONFIDENTIAL
```

## 4. Failure Severity / Handling Constants

```text
WARN
```

Used for:

- failed TrustFlow emission is a WARN-level audit event

## 5. Time Format Constants

```text
UTC Unix timestamp with millisecond precision
```

Applies to:

- `TrustFlowEvent.ts`

## 6. Cryptographic Constants

```text
SHA-256
```

Applies to:

- `TrustFlowEvent.payload_hash`

## 7. Platform / Runtime Constants

Explicitly stated in supplied documents:

| Constant | Value |
|---|---|
| minimum macOS version | `13.0 (Ventura)` |
| Swift language baseline | `Swift 5.9+` |
| Python runtime baseline | `Python 3.12` |
| current version | `38.153.0` |

## 8. Distribution / Packaging Constants

Explicitly stated in `TRD-1`:

- `.app bundle`
- drag-to-Applications
- Sparkle auto-update

These are product packaging/distribution interfaces, not message enums.

---

## Validation Rules

## 1. JSON Transport Validation

A shell/backend IPC message is valid only if:

- it is valid JSON
- it is encoded as a single line-delimited frame
- it is sent over an authenticated Unix socket

Reject if:

- malformed JSON
- message spans invalid framing boundaries
- unauthenticated socket
- transport is not the Unix socket contract

---

## 2. CTX-ID Validation Rules

A CTX-ID must be rejected if:

- missing
- expired
- invalid under TrustLock public key validation

Additional rules:

- validation must occur before any action processing
- missing CTX-ID is treated as untrusted
- old token becomes invalid immediately after rotation
- token contents must not be modified after issuance

---

## 3. VTZ Validation Rules

A session/operation is non-conformant if:

- an action executes before VTZ policy evaluation
- a cross-VTZ tool call occurs without explicit policy authorization
- application code attempts to bypass VTZ structural enforcement
- policy changes are applied mid-session instead of at next CTX-ID issuance

If VTZ denies an action:

- emit `VTZEnforcementDecision` with `verdict=block`
- reject action
- emit TrustFlow event
- fail closed

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
- `event_id` must not be sequential
- `ts` must be UTC Unix timestamp with millisecond precision
- `payload_hash` must be SHA-256 of the serialized action payload

Invalid if:

- emitted asynchronously from the enforcement path
- buffered for later emission
- emission failure is ignored or silently skipped

---

## 5. DTL Label Validation Rules

A DTL label flow is valid only if:

- label is assigned at ingestion
- label is immutable after assignment
- derived label reflects highest classification among sources
- unlabeled data is treated as `CONFIDENTIAL`
- label verification occurs before trust-boundary crossing

Security violation if:

- label is stripped without audit
- label is stripped without policy control

---

## 6. Error Object Validation Rules

An enforcement-path error is conformant only if:

- action is rejected
- event is logged
- error is surfaced to caller
- no silent continuation occurs

Error object content must:

- include `component`
- include `operation`
- include `failure_reason`
- include `ctx_id` if available

Error object must not contain:

- keys
- tokens
- secrets
- cleartext payloads

---

## 7. Audit Validation Rules

An audit flow is conformant only if:

- each security-relevant action produces an audit record
- the audit record is created before execution
- the audit log is append-only

---

## Wire Format Examples

Examples below use only fields and values explicitly grounded in the supplied materials. Where field names are not defined by the TRDs, examples are limited accordingly.

## 1. TrustFlow Event Example

```json
{
  "event_id": "7b9cb7c8-9d6d-4d89-a437-2f5b4a2c0d8f",
  "session_id": "sess-01",
  "ctx_id": "ctx-01",
  "ts": 1773912345678,
  "event_type": "block",
  "payload_hash": "6f9c4e6f4b2d0d1b4d3f4aee3d8b0d7f9b0a1e2d3c4b5a697887766554433221"
}
```

## 2. VTZ Enforcement Decision Example

```json
{
  "verdict": "block"
}
```

## 3. Error Record Example

```json
{
  "component": "PolicyEnforcement",
  "operation": "validate_ctx_id",
  "failure_reason": "expired ctx_id",
  "ctx_id": "ctx-01"
}
```

## 4. Line-Delimited JSON IPC Example

Single-frame message on the authenticated Unix socket:

```json
{"event_id":"7b9cb7c8-9d6d-4d89-a437-2f5b4a2c0d8f","session_id":"sess-01","ctx_id":"ctx-01","ts":1773912345678,"event_type":"allow","payload_hash":"6f9c4e6f4b2d0d1b4d3f4aee3d8b0d7f9b0a1e2d3c4b5a697887766554433221"}
```

Wire framing:

```text
<json>\n
```

## 5. DTL Handling Example

Because the supplied materials do not define a full label object schema, only the guaranteed classification constant can be shown:

```json
{
  "label": "CONFIDENTIAL"
}
```

## 6. Fail-Closed Sequence Example

Illustrative sequence using only specified concepts:

```text
1. Receive agent action
2. Validate CTX-ID first
3. CTX-ID invalid or expired
4. Reject action immediately
5. Log event
6. Surface error to caller
7. Do not continue processing
```

---

## Non-Conformance Conditions

A component is non-conformant if any of the following occur:

- processes an agent action before CTX-ID validation
- allows partial processing after CTX-ID validation failure
- executes an action before VTZ policy evaluation
- fails to create `VTZEnforcementDecision(verdict=block)` on VTZ denial
- fails to emit a TrustFlow event for allow/restrict/block outcomes
- emits TrustFlow asynchronously or via async buffering
- silently ignores TrustFlow emission failure
- treats missing CTX-ID as trusted
- allows mutable CTX-ID content after issuance
- permits old CTX-ID to remain valid after rotation
- permits implicit cross-VTZ calls
- treats VTZ boundaries as advisory
- mutates DTL labels after ingestion
- fails to treat unlabeled data as `CONFIDENTIAL`
- allows label stripping without audit and policy control
- swallows enforcement-path exceptions
- fails open on trust, identity, policy, or crypto errors
- emits errors containing secrets, tokens, keys, or cleartext payloads
- writes audit records after execution instead of before
- permits audit log mutation rather than append-only behavior

---

## Known Undefined Areas

The provided materials do **not** define the following concrete interfaces, so they are intentionally omitted from this contract:

- REST endpoints
- CLI argument schemas
- XPC method names or message schemas
- socket request/response envelope key names
- PRD schema
- pull request object schema
- consensus request/response schema
- GitHub operation payload schemas
- Keychain item identifiers
- Sparkle feed schema
- authentication prompt payloads
- UI view model payloads
- audit record field schema beyond timing and append-only requirements
- CTX-ID internal token structure
- DTL complete classification taxonomy
- explicit enumeration of `event_type` values beyond action outcomes implied by the standards

Only the interfaces and constraints explicitly supported by the supplied TRD content are normative in this document.