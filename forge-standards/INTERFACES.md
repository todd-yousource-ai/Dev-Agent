# INTERFACES.md

Definitive interface and wire format reference derived from the provided TRD documents and interface contract standards only.

---

# Interface Contracts

## System Boundary

Crafted Dev Agent is a **two-process native macOS system**:

- **Swift shell**
  - Owns UI
  - Owns authentication
  - Owns Keychain / secrets
  - Owns XPC responsibilities
- **Python backend**
  - Owns consensus
  - Owns pipeline
  - Owns GitHub operations

The two processes communicate using:

- **authenticated Unix socket**
- **line-delimited JSON**

Constraint:

- **Neither process ever executes generated code**

---

## Authoritative Sources

The following interface facts are directly established by the provided documents:

- Product architecture and process ownership from `AGENTS.md`, `CLAUDE.md`, and `README`
- Inter-process transport from `CLAUDE.md`
- GitHub PR lifecycle constraints from `GitHub-Integration-Lessons-Learned`
- Mandatory security and enforcement contracts from `Forge Component Interface Contracts`

No additional interfaces are defined beyond those sources.

---

# Per-Subsystem Data Structures (field names, types, constraints)

## 1. Inter-Process Message Envelope

Because Swift and Python communicate via **line-delimited JSON**, the base wire unit is a single JSON object serialized on one line.

### Transport Object

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | Yes for agent actions | Must be validated first at every entry point that processes an agent action |
| `session_id` | string | Required for TrustFlow/audit-bearing actions | Used to correlate session-bound activity |
| `event_type` | string | Required for TrustFlow events | Must identify the event class |
| `ts` | number | Required for TrustFlow events | UTC Unix timestamp with millisecond precision |
| `payload` | object | Contextual | Serialized action payload |
| `payload_hash` | string | Required for TrustFlow events | SHA-256 of serialized action payload |
| `event_id` | string | Required for TrustFlow events | Globally unique, CSPRNG-generated, not sequential |

### Transport Constraints

- Serialization format: **JSON**
- Framing format: **one JSON object per line**
- Transport: **authenticated Unix socket**
- Messages carrying agent actions are subject to:
  - CTX-ID validation
  - VTZ policy check
  - synchronous TrustFlow emission
  - fail-closed error handling

---

## 2. CTX-ID Token

The standards define CTX-ID as an immutable identity/security token.

### CTX-ID Structure

The provided documents do not define token field layout. The following properties are mandatory at the interface level:

| Property | Type | Constraint |
|---|---|---|
| `ctx_id` | string/token | Immutable once issued |
| `vtz_binding` | implicit binding | Every session is bound to exactly one VTZ at issuance |
| `expiry` | implicit validation property | Expired CTX-ID must be rejected |
| `signature` / trust validation material | implicit validation property | Must validate against TrustLock public key; software-only validation is rejected |

### CTX-ID Interface Rules

- Missing `ctx_id` → treat as **UNTRUSTED**
- Expired `ctx_id` → reject
- Rotated `ctx_id` → issue new token and invalidate old token immediately
- CTX-ID validation must happen **before any other processing**
- Identity must never be inferred from ambient context when `ctx_id` is absent

---

## 3. VTZ Enforcement Decision

The standards explicitly define a `VTZEnforcementDecision` record when policy denies an action.

### VTZEnforcementDecision

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | Yes | Must be `block` on policy denial |

No other fields are defined in the supplied documents.

### Behavioral Constraints

- Every action must be checked against VTZ policy **before execution**
- Cross-VTZ tool calls require **explicit policy authorization**
- Implicit cross-VTZ access is denied
- VTZ boundaries are structural and cannot be bypassed by application code
- VTZ policy changes take effect at **next CTX-ID issuance**, not mid-session

---

## 4. TrustFlow Event

TrustFlow event fields are explicitly mandated.

### TrustFlowEvent

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | Yes | Globally unique; generated via CSPRNG; not sequential |
| `session_id` | string | Yes | Session correlation identifier |
| `ctx_id` | string | Yes | CTX-ID for the action/session |
| `ts` | number | Yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | Yes | Event classification |
| `payload_hash` | string | Yes | SHA-256 hash of serialized action payload |

### TrustFlow Constraints

- Every action outcome must emit a TrustFlow event:
  - allow
  - restrict
  - block
- Emission must be **synchronous** in the enforcement path
- Async buffering is **not permitted**
- Emission failure:
  - must not silently continue
  - must be logged
  - must be surfaced
  - is a **WARN-level audit event**

---

## 5. Audit Record

Audit is mandatory for security-relevant actions.

### AuditRecord

The supplied documents define required semantics but not full field layout. The following fields are explicitly required for all errors, and audit must occur before execution for security-relevant actions.

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `component` | string | Yes for error-bearing audit records | Identifies emitting subsystem |
| `operation` | string | Yes for error-bearing audit records | Identifies attempted action |
| `failure_reason` | string | Yes for error-bearing audit records | Non-secret failure description |
| `ctx_id` | string | Required if available | Include when available |

### Audit Constraints

- Every security-relevant action must generate an audit record **before execution**
- Audit records are **append-only**
- No modification after append is permitted

---

## 6. Error Object

The standards define minimum required error content.

### Error Structure

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `component` | string | Yes | Subsystem name |
| `operation` | string | Yes | Operation name |
| `failure_reason` | string | Yes | Must not include secrets or cleartext payloads |
| `ctx_id` | string | Conditional | Required if available |

### Error Constraints

- All trust, identity, policy, and cryptographic failures must **fail closed**
- Fail closed means:
  - reject the action
  - log the event
  - surface to caller
  - never silently continue
- No swallowed exceptions in enforcement paths
- Error messages must not include:
  - keys
  - tokens
  - secrets
  - cleartext payloads

---

## 7. DTL Label Metadata

DTL label behavior is defined contractually.

### DTLLabel

Field names are not fully specified by the source documents. The interface-level properties are:

| Property | Type | Constraint |
|---|---|---|
| `label` | enum/string | Assigned at data ingestion and immutable thereafter |
| `inheritance_rule` | rule | Derived data inherits the highest classification of any source |

### DTL Constraints

- Unlabeled data must be treated as **CONFIDENTIAL**
- Label verification must occur before data crosses a trust boundary
- Label stripping is a security event
- Label stripping must be:
  - audited
  - policy-controlled

---

## 8. GitHub Pull Request State Interface

The provided GitHub lessons-learned document defines a concrete external API contract for draft PR state transitions.

### Pull Request Draft Transition

| Operation | API | Supported | Notes |
|---|---|---:|---|
| Convert draft PR to ready for review | REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with body `{"draft": false}` | No | GitHub silently ignores `draft`; returns `200` and PR remains draft |
| Convert draft PR to ready for review | GraphQL `markPullRequestReadyForReview` mutation | Yes | Only officially supported mechanism in provided source |

### GitHub Interface Constraint

Automation that converts a draft PR to ready-for-review **must use GraphQL** `markPullRequestReadyForReview`.

REST `PATCH` with `{"draft": false}` is **non-conformant** for this state transition.

---

## 9. Process Ownership Contract

### Swift Shell Interface Responsibilities

| Subsystem | Ownership |
|---|---|
| UI | Swift shell |
| Authentication | Swift shell |
| Keychain / secrets | Swift shell |
| XPC | Swift shell |

### Python Backend Interface Responsibilities

| Subsystem | Ownership |
|---|---|
| Consensus | Python backend |
| Pipeline | Python backend |
| GitHub operations | Python backend |

### Ownership Constraint

Interfaces must preserve process boundaries as specified above.

---

# Cross-Subsystem Protocols

## 1. Agent Action Enforcement Path

Every entry point that processes an agent action must implement the following protocol in order.

### Required Sequence

1. **Receive action** over authenticated interface
2. **Validate `ctx_id` first**
3. **Reject immediately** on CTX-ID validation failure
4. **Evaluate VTZ policy** before execution
5. If denied:
   - produce `VTZEnforcementDecision` with `verdict = "block"`
6. **Emit TrustFlow event synchronously**
7. **Create audit record** before execution for security-relevant action
8. **Execute action only if allowed**
9. On any trust/identity/policy/crypto failure:
   - fail closed
   - log
   - surface to caller

### Prohibited Behavior

- Partial processing before CTX-ID validation
- Silent continuation after TrustFlow failure
- Async buffering of TrustFlow emissions
- Swallowed exceptions in enforcement paths
- Policy bypass through application logic
- Inferring identity without CTX-ID

---

## 2. Swift ↔ Python IPC Protocol

### Transport

- Authenticated Unix socket
- Line-delimited JSON

### Framing

Each message is:

- one complete JSON object
- serialized to a single line
- terminated by newline

### Semantic Requirements

For any message representing an agent action:

- `ctx_id` validation occurs first
- payload hashing must use serialized payload bytes/object representation as the basis for SHA-256
- TrustFlow event emission is part of the enforcement path

No additional command grammar is defined in the provided documents.

---

## 3. Data Trust Boundary Protocol

When data crosses a trust boundary:

1. Verify DTL label
2. Treat unlabeled data as `CONFIDENTIAL`
3. Preserve immutable labels
4. Apply highest-classification inheritance to derived data
5. Audit any label stripping
6. Require policy control for label stripping

---

## 4. Session-to-VTZ Binding Protocol

- A session is bound to **exactly one** VTZ at CTX-ID issuance
- Cross-VTZ calls require explicit authorization
- VTZ policy updates apply at next CTX-ID issuance
- Mid-session rebinding is not supported by the provided standards

---

## 5. GitHub PR Promotion Protocol

For PRs created as draft and later promoted to ready-for-review:

1. Identify draft PR
2. Do **not** rely on REST `PATCH /pulls/{number}` with `{"draft": false}`
3. Invoke GraphQL `markPullRequestReadyForReview`
4. Treat REST success code `200` without state change as non-effective for this transition

---

# Enums and Constants

## 1. Enforcement Verdict

### `VTZEnforcementVerdict`

| Value | Meaning |
|---|---|
| `block` | Action denied by VTZ policy |

Only `block` is explicitly defined in the provided materials.

---

## 2. Trust Outcome Classes

The CAL enforcement contract defines possible action outcomes.

### `TrustOutcome`

| Value | Meaning |
|---|---|
| `allow` | Action permitted |
| `restrict` | Action permitted with restriction |
| `block` | Action denied |

These outcomes must emit TrustFlow events.

---

## 3. Data Classification Constant

### `DTLLabel`

| Value | Meaning |
|---|---|
| `CONFIDENTIAL` | Default treatment for unlabeled data |

No other classification literals are explicitly provided.

---

## 4. Error Severity Constant

### Audit Severity

| Value | Meaning |
|---|---|
| `WARN` | Required severity for failed TrustFlow emission audit event |

---

## 5. Time Format Constant

### `ts`

| Property | Value |
|---|---|
| Time base | UTC Unix timestamp |
| Precision | Millisecond |

---

## 6. Cryptographic Constants

### `payload_hash`

| Property | Value |
|---|---|
| Algorithm | SHA-256 |
| Input | Serialized action payload |

### `event_id`

| Property | Value |
|---|---|
| Uniqueness | Global |
| Generation source | CSPRNG |
| Disallowed form | Sequential identifiers |

---

## 7. Transport Constants

| Constant | Value |
|---|---|
| IPC transport | Authenticated Unix socket |
| Message framing | Line-delimited JSON |

---

# Validation Rules

## 1. CTX-ID Validation

A message/action fails validation if any of the following are true:

- `ctx_id` is missing
- `ctx_id` is expired
- `ctx_id` is invalid against TrustLock public key
- `ctx_id` has been rotated and invalidated
- `ctx_id` has been modified after issuance

### Required Handling

- Reject immediately
- Do not partially process
- Treat missing `ctx_id` as untrusted
- Surface failure to caller
- Log/audit failure with required error fields when available

---

## 2. VTZ Validation

An action fails VTZ validation if:

- policy denies the action
- action attempts unauthorized cross-VTZ tool call
- application code attempts to bypass VTZ structural boundary

### Required Handling

- Produce `VTZEnforcementDecision` with `verdict = "block"`
- Emit TrustFlow event
- Fail closed

---

## 3. TrustFlow Event Validation

A TrustFlow event is valid only if:

- `event_id` is present
- `event_id` is globally unique
- `event_id` is not sequential
- `session_id` is present
- `ctx_id` is present
- `ts` is present and millisecond UTC Unix timestamp
- `event_type` is present
- `payload_hash` is present
- `payload_hash` is SHA-256 of serialized action payload

### Emission Validation

- Emission must be synchronous
- Async buffering is invalid
- Emission failure must be surfaced and logged
- Silent skip is invalid

---

## 4. Error Object Validation

An enforcement-path error is valid only if:

- `component` is present
- `operation` is present
- `failure_reason` is present
- `ctx_id` is included if available
- no keys/tokens/secrets/cleartext payloads are present in the message

---

## 5. DTL Label Validation

Data handling is valid only if:

- label assigned at ingestion remains immutable
- derived data inherits highest classification among inputs
- unlabeled data is treated as `CONFIDENTIAL`
- label verification occurs before trust-boundary crossing
- label stripping is audited and policy-controlled

---

## 6. Audit Validation

Audit behavior is valid only if:

- security-relevant action produces audit record before execution
- records are append-only
- no post-append modification occurs

---

## 7. GitHub Draft PR Transition Validation

A draft→ready transition is valid only if:

- GraphQL `markPullRequestReadyForReview` is used

The following does **not** satisfy the contract even if HTTP status is 200:

- REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}`

---

## 8. Process Boundary Validation

Implementation is conformant only if responsibilities remain partitioned as follows:

- Swift shell:
  - UI
  - auth
  - Keychain/secrets
  - XPC
- Python backend:
  - consensus
  - pipeline
  - GitHub operations

Generated code execution is always invalid.

---

# Wire Format Examples

## 1. Line-Delimited JSON Agent Action

```json
{"ctx_id":"ctx_01","session_id":"sess_01","payload":{"action":"open_pr","repo":"owner/repo"}}
```

Notes:

- Single JSON object
- One line
- Suitable for authenticated Unix socket transport
- `ctx_id` must be validated first before any processing

---

## 2. TrustFlow Event

```json
{"event_id":"8f2d7f2e-9b2d-4d4b-a7d5-8c4d2e8c9a11","session_id":"sess_01","ctx_id":"ctx_01","ts":1773330123456,"event_type":"action.allow","payload_hash":"7f83b1657ff1fc53b92dc18148a1d65dfa135014aafa4b5a9d6f5f8f5d5e9c1a"}
```

Properties demonstrated:

- globally unique `event_id`
- UTC Unix timestamp in milliseconds
- SHA-256 `payload_hash`

---

## 3. VTZ Policy Denial Record

```json
{"verdict":"block"}
```

This is the only explicitly defined field/value pair for `VTZEnforcementDecision` in the provided materials.

---

## 4. Enforcement Error

```json
{"component":"policy_engine","operation":"authorize_action","failure_reason":"ctx_id validation failed","ctx_id":"ctx_01"}
```

Rules:

- Must not contain secrets
- Must be surfaced to caller
- Must be logged
- Must fail closed

---

## 5. Audit Record Example

```json
{"component":"trust_enforcement","operation":"execute_agent_action","failure_reason":"pre-execution audit record","ctx_id":"ctx_01"}
```

Note: The provided documents define audit semantics and append-only behavior, but do not define a larger mandatory field set.

---

## 6. GitHub GraphQL Draft Promotion Intent

Illustrative operation name from the provided source:

```json
{"operation":"markPullRequestReadyForReview"}
```

Constraint:

- This GraphQL mutation is the supported mechanism for converting draft PRs to ready-for-review.

---

## 7. Invalid REST Draft Promotion Example

```json
{"method":"PATCH","path":"/repos/{owner}/{repo}/pulls/{number}","body":{"draft":false}}
```

Status:

- Returns `200`
- `draft` field is silently ignored
- PR remains draft
- Must not be treated as a successful draft→ready transition

---

# Conformance Summary

A component is interface-conformant only if it satisfies all of the following:

- Uses the specified two-process boundary correctly
- Uses authenticated Unix socket with line-delimited JSON for Swift↔Python IPC
- Validates CTX-ID first for every agent action
- Enforces VTZ before execution
- Emits synchronous TrustFlow records with required fields
- Fails closed on trust/identity/policy/crypto failure
- Produces append-only pre-execution audit records for security-relevant actions
- Applies immutable DTL labels and `CONFIDENTIAL` default for unlabeled data
- Uses GraphQL `markPullRequestReadyForReview` for draft PR promotion
- Never executes generated code

---