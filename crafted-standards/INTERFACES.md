# INTERFACES.md

Definitive interface and wire-format reference derived from the provided TRD materials and contract standards only.

---

# Interface Contracts

## Scope and Authority

This document defines the interface contracts explicitly derivable from the provided source materials:

- `AGENTS.md`
- `CLAUDE.md`
- `README`
- `GitHub-Integration-Lessons-Learned`
- `Forge Component Interface Contracts`

Where the provided materials are silent, this document does **not** invent fields, endpoints, or behaviors.

---

## System Topology

The product is a **two-process native macOS AI coding agent**:

- **Swift shell**
  - Owns:
    - UI
    - authentication
    - Keychain
    - XPC
- **Python backend**
  - Owns:
    - consensus
    - pipeline
    - GitHub operations

### Inter-process transport

The Swift shell and Python backend communicate via:

- **authenticated Unix socket**
- **line-delimited JSON**

### Execution safety boundary

- Neither process ever executes generated code.

---

# Per-Subsystem Data Structures (field names, types, constraints)

## 1. Inter-Process Message Envelope

Derived from:
- “authenticated Unix socket”
- “line-delimited JSON”

Because line-delimited JSON is the declared wire format, each message is one complete JSON object serialized onto a single line.

### `LDJSONMessage`
```json
<object>
```

#### Constraints
- Must be valid JSON.
- Must occupy exactly one line on the wire.
- Message framing is newline-delimited.
- Communication occurs only over an authenticated Unix socket.

#### Required fields
The provided materials do **not** specify a universal envelope schema for all IPC messages. Therefore:
- No global message fields may be asserted beyond “JSON object per line”.

---

## 2. TrustFlow Event

Derived from the **TrustFlow Emission Contract**.

### `TrustFlowEvent`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `event_id` | string | yes | Must be globally unique; generated with CSPRNG; must not be sequential |
| `session_id` | string | yes | Session identifier |
| `ctx_id` | string | yes | Context identity token value or identifier |
| `ts` | integer or number | yes | UTC Unix timestamp with millisecond precision |
| `event_type` | string | yes | Event type identifier |
| `payload_hash` | string | yes | SHA-256 of serialized action payload |

#### Behavioral constraints
- Emission must be synchronous in the enforcement path.
- Async buffering is not permitted.
- Failed emission must produce a WARN-level audit event.
- Failed emission must not be silently skipped.

---

## 3. VTZ Enforcement Decision Record

Derived from the **CAL Enforcement Contract**.

### `VTZEnforcementDecision`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `verdict` | string | yes | Must support value `block` for policy denials |

#### Required behavior
- Every action must be checked against VTZ policy before execution.
- VTZ policy denial must produce a `VTZEnforcementDecision` record with `verdict=block`.

#### Notes
The provided materials do not define additional fields for this record.

---

## 4. Error Record

Derived from the **Error Handling Contract**.

### `ErrorRecord`
| Field | Type | Required | Constraints |
|---|---|---:|---|
| `component` | string | yes | Name of failing component |
| `operation` | string | yes | Name of attempted operation |
| `failure_reason` | string | yes | Failure classification or explanation |
| `ctx_id` | string | conditional | Must be included if available |

#### Prohibited content
Error messages must not include:
- keys
- tokens
- secrets
- cleartext payloads

#### Behavioral constraints
- All trust, identity, policy, and cryptographic failures must fail closed.
- Fail closed means:
  - reject the action
  - log the event
  - surface to caller
- No swallowed exceptions in enforcement paths.

---

## 5. Audit Record

Derived from the **Audit Contract**.

### `AuditRecord`
The provided materials require audit records but do not define a complete schema.

#### Required behavioral properties
- Every security-relevant action must generate an audit record before execution.
- Audit records are append-only.

#### Minimum explicitly derivable fields
No mandatory audit field list is fully specified in the provided materials. However, because security failures must include:
- `component`
- `operation`
- `failure_reason`
- `ctx_id` if available

those fields are required on applicable security error audit entries.

---

## 6. CTX-ID Token

Derived from the **CTX-ID Contract**.

### `CTXID`
The provided materials define lifecycle and validation rules, but not a serialized token schema.

#### Required properties
- Immutable once issued.
- Rotation creates a new token.
- Old token is invalidated immediately upon rotation.
- Expired token must be rejected.
- Validation must be against TrustLock public key.
- Missing CTX-ID must be treated as untrusted.

#### Explicit non-contract
- No field-level token structure is specified in the provided materials.

---

## 7. VTZ Session Binding

Derived from the **VTZ Enforcement Contract**.

### `SessionVTZBinding`
The provided materials define relationship constraints, not a wire schema.

#### Required properties
- Every agent session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require explicit policy authorization.
- VTZ boundaries are structural and cannot be bypassed by application code.
- VTZ policy changes take effect only at next CTX-ID issuance.

---

## 8. DTL Label Metadata

Derived from the **DTL Label Contract**.

### `DTLLabel`
The provided materials define label semantics, not a full data structure.

#### Recognized explicit classification value
- `CONFIDENTIAL` — required default handling for unlabeled data

#### Required properties
- Labels are assigned at data ingestion.
- Labels are immutable thereafter.
- Derived data inherits the highest classification of any source.
- Label verification must occur before crossing a trust boundary.
- Label stripping is a security event and must be audited and policy-controlled.

---

## 9. GitHub Pull Request Lifecycle Operations

Derived from `GitHub-Integration-Lessons-Learned`.

### Draft PR creation state
- The agent opens every PR as a draft.

### Draft → Ready for Review transition

#### Unsupported REST operation
`PATCH /repos/{owner}/{repo}/pulls/{number}` with:
```json
{"draft": false}
```

#### Constraint
- This does **not** convert a draft PR to ready for review.
- GitHub ignores the `draft` field and returns `200` while leaving the PR as draft.

### Required GraphQL operation
- Use GraphQL mutation `markPullRequestReadyForReview`.

#### Contract
- This is the only officially supported transition mechanism explicitly stated in the provided materials.

---

# Cross-Subsystem Protocols

## 1. Swift Shell ↔ Python Backend IPC Protocol

### Transport
- Authenticated Unix socket

### Encoding
- Line-delimited JSON

### Framing
- One JSON object per line

### Security constraints
- The socket must be authenticated.
- Generated code must not be executed by either side.

### Ownership boundaries
| Subsystem | Responsibilities |
|---|---|
| Swift shell | UI, authentication, Keychain, XPC |
| Python backend | consensus, pipeline, GitHub operations |

---

## 2. Enforcement Path Protocol

Derived from the Forge contracts.

### Required operation order
1. Entry point receives an agent action.
2. CTX-ID validation must occur first.
3. On CTX-ID validation failure:
   - immediate rejection
   - no partial processing
4. VTZ policy check must occur before execution.
5. On VTZ denial:
   - create `VTZEnforcementDecision` with `verdict=block`
6. Every action outcome must emit a TrustFlow event.
7. TrustFlow emission failure:
   - must not silently continue
   - must log and surface failure

### Fail-closed behavior
For trust, identity, policy, and cryptographic failures:
- reject action
- log event
- surface to caller
- never silently continue

---

## 3. Data Classification Propagation Protocol

### At ingestion
- Assign DTL label immediately.

### After ingestion
- Label is immutable.

### Derivation rule
- Derived data inherits the highest classification of any source.

### Boundary crossing rule
- Verify label before data crosses a trust boundary.

### Missing-label rule
- Treat unlabeled data as `CONFIDENTIAL` until explicitly reclassified.

### Label stripping rule
- Label stripping is a security event.
- Must be audited.
- Must be policy-controlled.

---

## 4. Session / Identity / Policy Binding Protocol

### Session establishment
- Agent session is bound to exactly one VTZ at CTX-ID issuance.

### Rotation
- CTX-ID rotation creates a new token.
- Old token becomes invalid immediately.

### Policy update timing
- VTZ policy changes do not take effect mid-session.
- They take effect at next CTX-ID issuance.

### Cross-zone access
- Cross-VTZ tool calls require explicit policy authorization.
- Implicit authorization is denied.

---

## 5. GitHub PR State Transition Protocol

### Initial state
- PRs are opened as drafts.

### Transition to reviewable state
- Must use GraphQL `markPullRequestReadyForReview`.

### Forbidden assumption
- Do not rely on REST PR patch with `{"draft": false}` to change draft status.

---

# Enums and Constants

## Explicitly Defined Values

### Enforcement verdicts
| Enum | Allowed / Required Values |
|---|---|
| `VTZEnforcementDecision.verdict` | `block` |

### DTL classifications
| Enum | Explicitly Defined Value |
|---|---|
| `DTLLabel` | `CONFIDENTIAL` |

### Audit severity
| Enum | Explicitly Defined Value |
|---|---|
| TrustFlow emission failure audit severity | `WARN` |

### Trust disposition for missing identity
| Condition | Required Interpretation |
|---|---|
| Missing `ctx_id` / missing CTX-ID | `UNTRUSTED` |

### Time format constants
| Constant | Value |
|---|---|
| TrustFlow timestamp basis | UTC Unix timestamp |
| TrustFlow timestamp precision | millisecond |

### Hash algorithm constants
| Constant | Value |
|---|---|
| `payload_hash` algorithm | SHA-256 |

### Randomness requirement
| Field | Requirement |
|---|---|
| `event_id` | CSPRNG-generated global uniqueness; not sequential |

### IPC format constants
| Constant | Value |
|---|---|
| IPC transport | authenticated Unix socket |
| IPC message format | line-delimited JSON |

### GitHub PR transition constant
| Operation | Required Mechanism |
|---|---|
| Draft → Ready for Review | GraphQL `markPullRequestReadyForReview` |

---

# Validation Rules

## 1. IPC Message Validation

For every Swift↔Python IPC message:
- Must be valid JSON.
- Must be newline-delimited as a single complete message per line.
- Must be transmitted over the authenticated Unix socket.

If any of the above fail:
- reject message
- fail closed if in an enforcement path

---

## 2. CTX-ID Validation

For every entry point processing an agent action:
- CTX-ID validation must occur first.

Validation requirements:
- Missing CTX-ID → treat as untrusted
- Expired CTX-ID → reject
- Validation must be against TrustLock public key
- Software-only validation is rejected

Additional rules:
- CTX-ID fields may not be modified after issuance
- Rotation must issue a new token
- Old token must be invalidated immediately

---

## 3. VTZ Policy Validation

Before any action executes:
- Check VTZ policy.

Rules:
- Session must be bound to exactly one VTZ
- Cross-VTZ tool calls require explicit authorization
- Implicit cross-VTZ access is denied
- VTZ boundaries cannot be bypassed by application code

If denied:
- produce `VTZEnforcementDecision` with `verdict=block`
- do not execute the action

---

## 4. TrustFlow Event Validation

Every action outcome must emit a TrustFlow event.

Required field checks:
- `event_id` present, globally unique, non-sequential
- `session_id` present
- `ctx_id` present
- `ts` present, UTC Unix timestamp, millisecond precision
- `event_type` present
- `payload_hash` present, SHA-256 of serialized action payload

Behavioral checks:
- emission must be synchronous in enforcement path
- async buffering is prohibited

On emission failure:
- create WARN-level audit event
- do not silently continue
- surface failure

---

## 5. Error Record Validation

All trust, identity, policy, and cryptographic errors must:
- fail closed
- include `component`
- include `operation`
- include `failure_reason`
- include `ctx_id` if available

Content restrictions:
- must not include keys
- must not include tokens
- must not include secrets
- must not include cleartext payloads

Implementation restriction:
- no swallowed exceptions in enforcement code

---

## 6. Audit Validation

For security-relevant actions:
- generate audit record before execution

Storage rule:
- audit records are append-only

Additional derived validation:
- security audit paths must not silently skip record generation where required by fail-closed handling

---

## 7. DTL Label Validation

At ingestion:
- assign label

After ingestion:
- do not modify label

Derived data:
- assign highest classification of any source

Before trust-boundary crossing:
- verify label

If data is unlabeled:
- treat as `CONFIDENTIAL`

If label stripping occurs:
- treat as security event
- audit it
- require policy control

---

## 8. GitHub Pull Request Transition Validation

When converting a draft PR to ready for review:
- use GraphQL `markPullRequestReadyForReview`

Validation failures:
- A successful REST patch response with unchanged draft status must not be interpreted as success.

Unsupported mechanism:
```json
{"draft": false}
```
sent to:
`PATCH /repos/{owner}/{repo}/pulls/{number}`

---

# Wire Format Examples

## 1. Line-Delimited JSON IPC Message

Example of one message on the Unix socket:
```json
{"type":"action_request","session_id":"sess_123","ctx_id":"ctx_abc"}
```

As transmitted:
```text
{"type":"action_request","session_id":"sess_123","ctx_id":"ctx_abc"}\n
```

Notes:
- `type` is illustrative only; no universal IPC envelope field is specified by the provided materials.
- The only guaranteed contract is one JSON object per line over an authenticated Unix socket.

---

## 2. TrustFlow Event

```json
{
  "event_id": "0f6d4a57-5b2d-4f6c-97f2-89b7c89d8d57",
  "session_id": "sess_123",
  "ctx_id": "ctx_abc",
  "ts": 1772012345123,
  "event_type": "action_allow",
  "payload_hash": "3f0c0c7f8d2d4a4e0a7c92a5d7d5c8d2e5f4b8f7d4c3b2a19088776655443322"
}
```

---

## 3. VTZ Enforcement Decision

```json
{
  "verdict": "block"
}
```

---

## 4. Error Record

```json
{
  "component": "policy_engine",
  "operation": "evaluate_action",
  "failure_reason": "ctx_id_validation_failed",
  "ctx_id": "ctx_abc"
}
```

Example without available context ID:
```json
{
  "component": "policy_engine",
  "operation": "evaluate_action",
  "failure_reason": "missing_ctx_id"
}
```

---

## 5. Security Audit Entry

Minimal example constrained only by provided materials:
```json
{
  "component": "trustflow",
  "operation": "emit_event",
  "failure_reason": "emission_failed",
  "ctx_id": "ctx_abc"
}
```

Notes:
- The provided materials do not define a complete audit schema.
- This example shows only explicitly required error fields where applicable.

---

## 6. GitHub REST Draft Conversion Attempt That Must Not Be Relied On

Request:
```http
PATCH /repos/{owner}/{repo}/pulls/{number}
Content-Type: application/json
```

Body:
```json
{
  "draft": false
}
```

Contractual interpretation:
- Even if GitHub returns `200`, the PR may remain draft.
- This call must not be used as the authoritative transition mechanism.

---

## 7. GitHub GraphQL Draft → Ready Transition

Illustrative mutation name required by contract:
```graphql
mutation {
  markPullRequestReadyForReview(input: { pullRequestId: "PR_ID" }) {
    pullRequest {
      id
    }
  }
}
```

Notes:
- The provided materials specify the mutation name and required use.
- Full response schema is not defined in the provided materials.

---

# Non-Invented Areas

The provided materials do **not** define, and this document therefore does not assert:

- a complete Swift↔Python message envelope schema
- specific IPC message types
- complete CTX-ID token structure
- complete audit record schema
- complete DTL label enumeration beyond `CONFIDENTIAL`
- complete VTZ decision schema beyond `verdict=block`
- GitHub authentication headers or token formats
- complete GraphQL request/response envelope structure
- XPC message schemas
- Keychain item schemas
- UI view model interfaces

---

# Conformance Summary

A component is conformant to the provided interface contracts only if it satisfies all of the following:

1. Swift and Python communicate via authenticated Unix socket using line-delimited JSON.
2. No generated code is executed.
3. Every agent action entry point validates CTX-ID first.
4. CTX-ID failures reject immediately with no partial processing.
5. Every action is checked against VTZ policy before execution.
6. VTZ denial emits a decision record with `verdict=block`.
7. Every action outcome emits a TrustFlow event with all required fields.
8. TrustFlow emission is synchronous in enforcement paths.
9. TrustFlow emission failure is surfaced and audited at WARN level.
10. Trust, identity, policy, and cryptographic failures fail closed.
11. Error records include required fields and exclude secrets.
12. Security-relevant actions generate append-only audit records before execution.
13. DTL labels are assigned at ingestion, immutable, inherited by highest classification, and verified before trust-boundary crossing.
14. Unlabeled data is treated as `CONFIDENTIAL`.
15. Draft PRs are transitioned to ready-for-review using GraphQL `markPullRequestReadyForReview`, not REST `draft: false`.

---