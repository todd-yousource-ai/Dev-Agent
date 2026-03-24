# INTERFACES.md

Definitive interface and wire-format reference derived from the provided TRD materials only.

## Scope and Authority

This repository implements **Crafted Dev Agent**, a **two-process native macOS system**:

- **Swift shell**
  - UI
  - authentication
  - Keychain secret storage
  - orchestration
  - XPC
- **Python backend**
  - consensus
  - pipeline
  - GitHub operations

The authoritative interface facts present in the provided TRD materials are:

- Inter-process communication is via an **authenticated Unix socket**
- Wire format is **line-delimited JSON**
- The system **never executes generated code**
- The shell owns installation, authentication, secrets, session lifecycle, and orchestration
- The backend owns intelligence, generation, and GitHub operations
- Security and enforcement behavior is governed by the listed **Forge Component Interface Contracts**

No fields, endpoints, or message types beyond those explicitly stated below are invented.

---

# Interface Contracts

## Global Wire Format

### Transport

All Swift shell ↔ Python backend communication MUST use:

- **Authenticated Unix socket**
- **Line-delimited JSON**

### Framing

Each message MUST be encoded as exactly one JSON object per line.

- Delimiter: `\n`
- Encoding: JSON text
- Record unit: one complete JSON object
- Multiple messages: one JSON object per line, in order sent

### Process Boundary

The only explicit cross-process interface defined in the provided TRDs is:

- **Swift shell**
  - initiates orchestration
  - manages auth/session/secrets/UI
- **Python backend**
  - performs intelligence, generation, and GitHub operations

### Execution Safety Constraint

Neither process may treat generated code as executable input.

- Generated code MUST NOT be executed
- Interface handlers MUST NOT invoke generated artifacts as commands, scripts, binaries, or tests by virtue of being generated content alone

---

## Per-Subsystem Data Structures

Only structures explicitly required by the provided contracts are defined here.

### 1. TrustFlow Event

Required by the **TrustFlow Emission Contract**.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | MUST be globally unique; MUST be generated via CSPRNG; MUST NOT be sequential |
| `session_id` | string | yes | Identifies the agent session |
| `ctx_id` | string | yes | Context identity token associated with the action |
| `ts` | number or integer | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Type of TrustFlow event |
| `payload_hash` | string | yes | MUST be SHA-256 of the serialized action payload |

#### Behavioral constraints

- Emission MUST be synchronous in the enforcement path
- Async buffering is NOT permitted
- Emission failure MUST be:
  - logged
  - surfaced
  - treated as a WARN-level audit event
- Emission failure MUST NOT silently continue

---

### 2. VTZEnforcementDecision

Required by the **CAL Enforcement Contract**.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | MUST support value `block` for policy denial |

#### Behavioral constraints

- Every action MUST be checked against VTZ policy before execution
- VTZ policy denial MUST produce a `VTZEnforcementDecision` record with:
  - `verdict = "block"`

No additional fields are specified in the provided materials.

---

### 3. Error Record

Required by the **Error Handling Contract**.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `component` | string | yes | Identifies the failing component |
| `operation` | string | yes | Identifies the operation being performed |
| `failure_reason` | string | yes | Describes why the failure occurred |
| `ctx_id` | string | conditional | Required if available |

#### Prohibited content

Error messages and records MUST NOT include:

- keys
- tokens
- secrets
- cleartext payloads

#### Behavioral constraints

- All trust, identity, policy, and cryptographic failures MUST fail closed
- Fail closed means:
  - reject the action
  - log the event
  - surface to caller
- No swallowed exceptions in enforcement paths

---

### 4. Audit Record

Required by the **Audit Contract**.

The provided materials define behavioral requirements but do not define a full field schema.

#### Guaranteed properties

- Generated for every security-relevant action
- MUST be created **before execution**
- MUST be **append-only**

No additional wire fields are specified in the provided materials.

---

### 5. CTX-ID Token

Required by the **CTX-ID Contract**.

The provided materials define lifecycle and validation requirements but do not define a complete token field schema.

#### Guaranteed properties

- Immutable once issued
- Rotatable only by issuing a new token
- Old token invalidated immediately upon rotation
- Must be validated against a TrustLock public key
- Missing token implies `UNTRUSTED`
- Expired token must be rejected, subject to deployment-defined clock skew tolerance

No internal token field layout is specified in the provided materials.

---

### 6. DTL Label

Required by the **DTL Label Contract**.

The provided materials define semantics but not a full serialized structure.

#### Guaranteed properties

- Assigned at data ingestion
- Immutable after assignment
- Derived data inherits the highest classification of any source
- Unlabeled data defaults to `CONFIDENTIAL`
- Must be verified before crossing a trust boundary
- Label stripping is a security event and must be audited and policy-controlled

#### Explicit label value

| Value | Meaning |
|---|---|
| `CONFIDENTIAL` | Default classification for unlabeled data |

No additional label enum values are specified in the provided materials.

---

### 7. Session Binding Record

Inferred only from explicit security contract statements; not otherwise expanded.

#### Guaranteed properties

- Every agent session is bound to exactly one VTZ at CTX-ID issuance

No concrete serialized schema is specified in the provided materials.

---

## Cross-Subsystem Protocols

## 1. Swift Shell ↔ Python Backend Protocol

### Transport contract

| Property | Requirement |
|---|---|
| Channel | Authenticated Unix socket |
| Encoding | JSON |
| Framing | Line-delimited JSON |
| Direction | Bidirectional process-to-process communication |

### Ownership split

| Subsystem | Responsibility |
|---|---|
| Swift shell | UI, authentication, Keychain, session lifecycle, orchestration, XPC |
| Python backend | consensus, pipeline, GitHub operations |

### Minimum protocol invariants

Any action-bearing request that traverses subsystem boundaries and enters an enforcement path MUST satisfy:

1. **CTX-ID validation first**
2. **Immediate rejection on CTX-ID validation failure**
3. **VTZ policy check before execution**
4. **TrustFlow emission for every outcome**
5. **Fail closed on trust/identity/policy/crypto failures**

---

## 2. CAL Enforcement Protocol

Derived from the **CAL Enforcement Contract**.

### Required sequence

For every entry point that processes an agent action:

1. Validate `CTX-ID` first
2. If validation fails:
   - reject immediately
   - perform no partial processing
3. Check action against `VTZ` policy before execution
4. If denied:
   - create `VTZEnforcementDecision` with `verdict = "block"`
5. Emit a `TrustFlow` event for the outcome:
   - allow
   - restrict
   - block
6. If TrustFlow emission fails:
   - log
   - surface failure
   - do not silently continue

### Processing order constraint

This order is mandatory. No action execution may precede CTX-ID validation and VTZ policy evaluation.

---

## 3. CTX-ID Validation Protocol

Derived from the **CTX-ID Contract**.

### Validation rules

A CTX-ID presented to any enforcement path MUST be checked for:

- presence
- validity against TrustLock public key
- expiration
- current issuance status after rotation/invalidation

### Required outcomes

| Condition | Required outcome |
|---|---|
| Missing CTX-ID | Treat as `UNTRUSTED` |
| Expired CTX-ID | Reject |
| CTX-ID modified after issuance | Reject |
| Validation not against TrustLock public key | Reject |
| Rotated-out old token used | Reject |

### Rotation protocol

- Rotation MUST issue a new token
- Old token MUST be invalidated immediately
- VTZ policy changes take effect only at next CTX-ID issuance, not mid-session

---

## 4. VTZ Enforcement Protocol

Derived from the **VTZ Enforcement Contract**.

### Session binding rules

- Each agent session MUST be bound to exactly one VTZ at CTX-ID issuance
- Cross-VTZ tool calls are denied by default
- Cross-VTZ tool calls require explicit policy authorization
- VTZ boundaries are structural and cannot be bypassed by application code

### Policy-change timing

- VTZ policy changes do not apply mid-session
- They take effect at the next CTX-ID issuance

---

## 5. DTL Label Propagation Protocol

Derived from the **DTL Label Contract**.

### Ingestion

At data ingestion:

- a DTL label MUST be assigned

### Immutability

After assignment:

- the label MUST NOT change unless explicitly reclassified per policy
- stripping a label is a security event

### Derivation

For derived data:

- resulting label MUST equal the highest classification among all sources

### Boundary crossing

Before any trust-boundary crossing:

- label verification MUST occur

### Default handling

If a datum is unlabeled:

- it MUST be treated as `CONFIDENTIAL`

---

## 6. Error Handling Protocol

Derived from the **Error Handling Contract**.

### Fail-closed classes

The following failures MUST fail closed:

- trust failures
- identity failures
- policy failures
- cryptographic failures

### Fail-closed behavior

On such failure, the system MUST:

1. reject the action
2. log the event
3. surface the error to the caller

### Error payload requirements

Every error MUST include:

- `component`
- `operation`
- `failure_reason`
- `ctx_id` if available

### Error payload prohibitions

Errors MUST NOT include:

- keys
- tokens
- secrets
- cleartext payloads

### Exception handling constraint

- Swallowed exceptions are forbidden in enforcement paths

---

## 7. Audit Protocol

Derived from the **Audit Contract**.

### Required behavior

For every security-relevant action:

1. Create audit record
2. Do so before execution
3. Preserve as append-only record

### Mutation constraint

- Audit records MUST NOT be modified in place

The provided materials do not define retention, storage engine, or complete field schema.

---

# Enums and Constants

Only constants and enum values explicitly stated in the provided materials are included.

## Verdict Values

### `VTZEnforcementDecision.verdict`

| Value | Meaning |
|---|---|
| `block` | Action denied by VTZ policy |

---

## Enforcement Outcomes

The CAL Enforcement Contract explicitly requires TrustFlow emission for these outcomes:

| Value | Meaning |
|---|---|
| `allow` | Action allowed |
| `restrict` | Action restricted |
| `block` | Action blocked |

These are required outcome categories, though no formal enum container is defined in the provided materials.

---

## Trust Classification Values

| Value | Meaning |
|---|---|
| `CONFIDENTIAL` | Default classification for unlabeled data |

---

## Identity State Values

| Value | Meaning |
|---|---|
| `UNTRUSTED` | Required treatment for missing CTX-ID |

---

## Time and Hash Constants

| Name | Value |
|---|---|
| Timestamp basis | UTC Unix timestamp |
| Timestamp precision | Millisecond precision |
| Payload hash algorithm | SHA-256 |

---

## Platform and Runtime Constants

Explicitly stated in the provided materials:

| Name | Value |
|---|---|
| Minimum macOS version | 13.0 (Ventura) |
| Swift language | 5.9+ |
| Python language | 3.12 (bundled) |

---

# Validation Rules

## Transport Validation

- Messages between Swift shell and Python backend MUST use an authenticated Unix socket
- Messages MUST be line-delimited JSON
- Non-JSON or non-line-delimited input is non-conformant to the specified transport

---

## Message Framing Validation

- Each line MUST contain exactly one complete JSON object
- Partial objects MUST NOT be treated as valid complete messages
- Multiple JSON objects on a single line are outside the specified framing contract

---

## CTX-ID Validation Rules

- CTX-ID validation MUST happen before any processing of an agent action
- Missing CTX-ID MUST result in `UNTRUSTED` treatment
- Expired CTX-ID MUST be rejected
- Modified CTX-ID MUST be rejected
- Validation MUST use TrustLock public key
- Software-only validation without TrustLock public key is rejected
- Old CTX-ID after rotation MUST be rejected immediately

---

## VTZ Validation Rules

- Every action MUST undergo VTZ policy validation before execution
- Session MUST be bound to exactly one VTZ
- Cross-VTZ tool calls are denied unless explicitly authorized
- VTZ policy changes MUST NOT alter an already-issued session mid-flight

---

## TrustFlow Validation Rules

A valid TrustFlow event MUST contain all of:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional validation:

- `event_id` MUST be globally unique and non-sequential
- `ts` MUST be UTC Unix timestamp with millisecond precision
- `payload_hash` MUST equal SHA-256 of serialized action payload

Operational validation:

- emission MUST be synchronous in the enforcement path
- async buffering is not permitted
- failed emission MUST be logged and surfaced

---

## Error Validation Rules

Every enforcement-path error MUST:

- include `component`
- include `operation`
- include `failure_reason`
- include `ctx_id` if available

Every enforcement-path error MUST NOT include:

- keys
- tokens
- secrets
- cleartext payloads

---

## DTL Validation Rules

- Every ingested datum MUST receive a label
- Labels MUST be immutable after assignment
- Unlabeled data MUST be treated as `CONFIDENTIAL`
- Derived data MUST inherit the highest classification of source inputs
- Labels MUST be verified before trust-boundary crossing
- Label stripping MUST be audited and policy-controlled

---

## Audit Validation Rules

- Every security-relevant action MUST have an audit record
- Audit record creation MUST occur before execution
- Audit records MUST be append-only

---

## Generated Code Safety Validation

- Neither process may execute generated code
- Interfaces handling generated content MUST treat it as data, not executable authority

---

# Wire Format Examples

Examples below use only structures and fields explicitly defined by the provided materials.

## 1. Line-Delimited JSON over Authenticated Unix Socket

Two messages sent over the socket, one JSON object per line:

```json
{"event_id":"7d5c9d3f-2a61-4c87-a57f-8ec7a8c1e201","session_id":"sess-001","ctx_id":"ctx-001","ts":1760000000123,"event_type":"allow","payload_hash":"8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"}
{"event_id":"2b2af8fd-5f8f-4f63-8c66-7d305ad9ac42","session_id":"sess-001","ctx_id":"ctx-001","ts":1760000000456,"event_type":"block","payload_hash":"d4e5f6d8a4cbf4f0f7b3b7a2a6b1d9d0d0cc1f9f6b89a4f2d3140ef85c9f1abc"}
```

---

## 2. TrustFlow Event

```json
{
  "event_id": "3f8f74b1-b9a2-4fc1-a6ce-d5dc7d72e0b8",
  "session_id": "session-42",
  "ctx_id": "ctx-42",
  "ts": 1760001234567,
  "event_type": "restrict",
  "payload_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd38b0f5f0d5f5d4c2b"
}
```

---

## 3. VTZ Policy Denial Decision

```json
{
  "verdict": "block"
}
```

---

## 4. Enforcement Error Record

```json
{
  "component": "policy-engine",
  "operation": "vtz_check",
  "failure_reason": "cross_vtz_call_not_authorized",
  "ctx_id": "ctx-42"
}
```

---

## 5. Error Record Without Available CTX-ID

```json
{
  "component": "ctx-validator",
  "operation": "validate",
  "failure_reason": "missing_ctx_id"
}
```

---

## 6. DTL-Labeled Datum Example

The provided materials do not define a full label container schema. The minimal conformant representation is therefore illustrative of the required label value only:

```json
{
  "label": "CONFIDENTIAL"
}
```

---

## 7. Invalid Examples

### Missing TrustFlow required field

Invalid because `payload_hash` is missing:

```json
{
  "event_id": "3f8f74b1-b9a2-4fc1-a6ce-d5dc7d72e0b8",
  "session_id": "session-42",
  "ctx_id": "ctx-42",
  "ts": 1760001234567,
  "event_type": "allow"
}
```

### Invalid error payload containing secret material

Invalid because errors must not contain secrets or tokens:

```json
{
  "component": "auth",
  "operation": "keychain_read",
  "failure_reason": "token invalid: sk_live_ABC123",
  "ctx_id": "ctx-42"
}
```

### Invalid processing order

Non-conformant behavior:

1. execute action
2. validate CTX-ID
3. emit TrustFlow

Required behavior:

1. validate CTX-ID
2. check VTZ policy
3. audit/security handling as required
4. execute or block
5. emit TrustFlow synchronously for the outcome

---

# Conformance Summary

A component is conformant to the provided interface requirements only if it satisfies all of the following:

- Uses the defined **authenticated Unix socket + line-delimited JSON** process protocol where applicable
- Validates **CTX-ID first** for every agent action entry point
- Enforces **VTZ policy before execution**
- Produces `VTZEnforcementDecision` with `verdict="block"` on denial
- Emits a complete **TrustFlow event** for every allow/restrict/block outcome
- Emits TrustFlow synchronously in the enforcement path
- Fails closed for trust, identity, policy, and cryptographic failures
- Produces required error fields without disallowed sensitive content
- Assigns and enforces immutable **DTL labels**
- Creates **append-only audit records before execution**
- Never executes generated code

---

# Non-Specified Areas

The following are intentionally left unspecified because they are not defined in the provided TRD materials:

- Full request/response message schemas between shell and backend
- Socket path, handshake payload, or authentication mechanism details
- Full CTX-ID token structure
- Full audit record field schema
- Full DTL label schema beyond required semantics
- Full VTZ policy object schema
- GitHub API request/response objects
- XPC message definitions
- Sparkle update feed/schema
- UI view model payloads
- Consensus engine provider request/response payloads

No additional contract details should be assumed without the governing TRD text.