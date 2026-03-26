# INTERFACES.md

This document defines the interface contracts explicitly stated in the provided TRD-derived repository documents. It is limited to formats and contracts that appear in the supplied source material.

## Interface Contracts

### Source Authority

The repository documents establish the following interface authorities:

- The product is a **two-process** system:
  - **Swift shell**: UI, authentication, Keychain, XPC
  - **Python backend**: consensus, pipeline, GitHub
- The two processes communicate via:
  - **authenticated Unix socket**
  - **line-delimited JSON**
- The TRDs in `forge-docs/` are the source of truth for all unspecified details.
- Neither process executes generated code.

Because only partial TRD-derived content was provided, this file includes only interfaces directly recoverable from that content and does not invent undocumented fields or endpoints.

---

## Per-Subsystem Data Structures

### 1. Interprocess Message Frame

The only explicit on-wire format provided for Swift ↔ Python communication is **line-delimited JSON** over an **authenticated Unix socket**.

#### Structure

Each message frame:

- MUST be a valid JSON value
- SHOULD be a JSON object for extensibility
- MUST be terminated by a newline (`\n`)
- MUST occupy exactly one line on the stream

#### Type

```text
LineDelimitedJsonFrame := UTF-8 encoded JSON + "\n"
```

#### Constraints

- Encoding: UTF-8
- Delimiter: newline
- Transport: authenticated Unix socket
- Framing: one JSON message per line
- Messages MUST NOT rely on multi-line JSON formatting
- Receivers MUST parse input incrementally by newline boundaries

---

### 2. Pull Request State Representation

The GitHub integration document explicitly identifies a draft PR lifecycle distinction.

#### Fields explicitly evidenced

```json
{
  "draft": true
}
```

#### Field contract

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `draft` | boolean | `true` or `false` | Present in GitHub PR context |

#### Behavioral constraint

- `PATCH /repos/{owner}/{repo}/pulls/{number}` with body `{"draft": false}` is documented as ineffective for converting a draft PR to ready for review.
- Conversion from draft to ready-for-review MUST use the GraphQL `markPullRequestReadyForReview` mutation.

---

### 3. Repository Pull Request Locator

The GitHub REST path supplied in the lessons-learned document implies the following locator fields.

#### Implied structure

| Field | Type | Constraints |
|---|---|---|
| `owner` | string | GitHub repository owner identifier |
| `repo` | string | GitHub repository name |
| `number` | integer | Pull request number |

#### REST path template

```text
/repos/{owner}/{repo}/pulls/{number}
```

---

### 4. Product Version

The repository metadata explicitly provides a version string.

#### Structure

| Field | Type | Constraints |
|---|---|---|
| `version` | string | Semantic-like dotted version string |

#### Example

```json
{
  "version": "38.153.0"
}
```

No stronger semantic-versioning rules are stated in the provided materials.

---

### 5. Process Responsibility Boundary

The provided documents define subsystem ownership, which is an interface contract at the architectural boundary.

#### Swift shell responsibilities

| Capability | Ownership |
|---|---|
| UI | Swift shell |
| Authentication | Swift shell |
| Keychain | Swift shell |
| XPC | Swift shell |

#### Python backend responsibilities

| Capability | Ownership |
|---|---|
| Consensus | Python backend |
| Pipeline | Python backend |
| GitHub operations | Python backend |

#### Constraint

- Interfaces crossing this boundary MUST respect the ownership split above.
- Secrets handling belongs to the Swift-owned security/authentication side unless specified otherwise by the governing TRD.

---

## Cross-Subsystem Protocols

### 1. Swift Shell ↔ Python Backend IPC

#### Transport

- **Authenticated Unix socket**

#### Framing

- **Line-delimited JSON**

#### Protocol requirements

| Requirement | Contract |
|---|---|
| Authentication | Socket communication MUST be authenticated |
| Message format | Messages MUST be JSON |
| Framing | Each message MUST be newline-delimited |
| Process model | Swift shell and Python backend are separate processes |
| Execution safety | Neither side may execute generated code |

#### Sender requirements

- MUST serialize each outbound message as one JSON document
- MUST append `\n`
- MUST NOT emit pretty-printed/multi-line JSON

#### Receiver requirements

- MUST buffer until newline
- MUST parse each complete line as one JSON document
- MUST reject malformed JSON frames
- MUST treat framing violations as protocol errors

---

### 2. GitHub Pull Request Lifecycle Protocol

The provided lessons-learned document defines one concrete lifecycle rule.

#### Draft PR creation policy

- The agent opens every PR as a **draft**

#### Transition: Draft → Ready for Review

##### Unsupported/ineffective method

```http
PATCH /repos/{owner}/{repo}/pulls/{number}
Content-Type: application/json

{"draft": false}
```

Documented behavior:

- Returns `200`
- Field is silently ignored
- PR remains draft

##### Required method

- Use GraphQL mutation:
  - `markPullRequestReadyForReview`

#### Contract

| Action | Required Interface |
|---|---|
| Create PR as draft | GitHub PR draft workflow |
| Convert draft PR to ready | GraphQL `markPullRequestReadyForReview` |
| Convert via REST `PATCH ... {"draft": false}` | MUST NOT be relied upon |

---

### 3. Build and Review Workflow Boundary

From the provided repository documents, the product-level interaction contract is:

1. User provides:
   - repository
   - TRDs
   - plain-language intent
2. Agent:
   - assesses confidence in scope
   - decomposes intent into ordered PRD plan
   - decomposes PRD into typed pull requests
   - generates implementation and tests using two providers in parallel
   - runs self-correction pass
   - runs lint gate
   - runs iterative fix loop
   - opens GitHub pull requests
3. Operator:
   - gates
   - reviews
   - merges

This is a workflow contract, not a complete wire schema. No additional field-level payloads are stated in the provided content.

---

## Enums and Constants

### 1. Process Roles

```text
ProcessRole =
  - swift_shell
  - python_backend
```

### 2. Transport Type

```text
TransportType =
  - authenticated_unix_socket
```

### 3. Message Encoding

```text
MessageEncoding =
  - json
  - utf8
  - line_delimited
```

### 4. Pull Request State

Only values evidenced in provided material are included.

```text
PullRequestReviewState =
  - draft
  - ready_for_review
```

### 5. Provider Set

The README explicitly names the consensus providers.

```text
ModelProvider =
  - claude
  - gpt_4o
```

### 6. Governance Constants

```text
SecurityAuthority = "TRD-11"
SpecificationAuthority = "forge-docs/"
CurrentVersion = "38.153.0"
```

### 7. File/Document Constants

```text
AgentInstructionFiles =
  - AGENTS.md
  - CLAUDE.md

PrimarySpecificationDocs =
  - README.md
  - forge-docs/*
```

---

## Validation Rules

### 1. IPC Message Validation

For every Swift ↔ Python IPC message:

- MUST be valid JSON
- MUST be UTF-8 encoded
- MUST terminate with newline
- MUST fit on a single line
- MUST be transmitted over the authenticated Unix socket
- MUST NOT contain embedded framing semantics that depend on multi-line parsing

#### Invalid conditions

- malformed JSON
- missing newline terminator
- multi-line pretty-printed JSON
- unauthenticated socket usage
- non-UTF-8 payloads

---

### 2. Responsibility Validation

Changes or interfaces MUST preserve subsystem boundaries:

- Swift shell MUST own:
  - UI
  - auth
  - Keychain
  - XPC
- Python backend MUST own:
  - consensus
  - pipeline
  - GitHub operations

Any interface that relocates these responsibilities would violate the documented architecture unless another TRD explicitly authorizes it.

---

### 3. Generated Code Safety Validation

- Neither process may execute generated code.

This is a hard behavioral contract and must be preserved by any interface or workflow.

---

### 4. GitHub Draft PR Transition Validation

When transitioning a PR from draft to reviewable:

- GraphQL `markPullRequestReadyForReview` MUST be used
- REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}` MUST NOT be treated as a valid state transition mechanism

#### Failure interpretation

If a REST patch returns success but PR remains draft, that result is consistent with the documented GitHub behavior and is not a valid transition.

---

### 5. Specification Validation

- Interfaces MUST derive from TRDs in `forge-docs/`
- Security-relevant interfaces MUST conform to TRD-11
- Implementations MUST NOT invent requirements absent from TRDs

This document itself is intentionally incomplete where the provided material does not specify structure.

---

## Wire Format Examples

## 1. IPC Line-Delimited JSON

### Example frame

```json
{"type":"ping"}
```

On the wire:

```text
{"type":"ping"}\n
```

### Example stream with multiple messages

```text
{"type":"session_start"}\n
{"type":"status","state":"running"}\n
{"type":"session_end"}\n
```

Note: message field names beyond the JSON framing are illustrative only; the provided documents do not define a canonical IPC schema.

---

## 2. GitHub REST Attempt That Must Not Be Relied Upon

```http
PATCH /repos/{owner}/{repo}/pulls/{number}
Content-Type: application/json

{"draft": false}
```

Documented outcome:

- HTTP 200 may be returned
- PR may remain in draft state
- Client MUST NOT interpret this as successful conversion to ready-for-review

---

## 3. Required GitHub Draft Conversion Operation

The exact mutation payload is not fully provided in the source excerpt, but the required interface is:

```graphql
mutation {
  markPullRequestReadyForReview(...)
}
```

Contract:

- This mutation is the required mechanism for converting a draft PR to ready for review.

---

## 4. Pull Request Locator Example

```json
{
  "owner": "example-org",
  "repo": "crafted",
  "number": 42
}
```

Associated REST path:

```text
/repos/example-org/crafted/pulls/42
```

---

## 5. Version Example

```json
{
  "version": "38.153.0"
}
```

---

## 6. Responsibility Boundary Example

```json
{
  "swift_shell": ["ui", "authentication", "keychain", "xpc"],
  "python_backend": ["consensus", "pipeline", "github"]
}
```

This is a normalized representation of the documented subsystem ownership, not a declared runtime payload.

---

## Non-Derivable Interfaces

The provided material references many detailed TRDs but does not include their actual field-level content. Therefore, this document intentionally does **not** define undocumented schemas for:

- XPC payloads
- Keychain record formats
- auth token structures
- consensus request/response schemas
- provider adapter payloads
- PRD plan schemas
- typed pull request schemas
- lint/fix-loop result objects
- error envelope formats
- security token wire formats
- test result schemas

Those interfaces must be taken directly from the relevant TRDs in `forge-docs/`.

---

## Summary

The explicit interface contracts recoverable from the provided TRD-derived documents are:

- Swift ↔ Python communication uses an **authenticated Unix socket**
- The wire format is **UTF-8 line-delimited JSON**
- The system is a strict **two-process architecture**
- Subsystem ownership is split between **Swift shell** and **Python backend**
- **Generated code is never executed**
- GitHub draft PRs must be transitioned to ready-for-review using GraphQL
- REST patching `{"draft": false}` on a PR must not be relied upon

All other interfaces remain governed by the underlying TRDs and are intentionally unspecified here absent direct source text.