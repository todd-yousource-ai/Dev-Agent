# INTERFACES.md

Definitive interface and wire-format reference derived from the provided TRD-facing repository documents only.

## Scope and Source Authority

This document is derived entirely from the provided repository documentation excerpts:

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `GitHub-Integration-Lessons-Learned`

Where those documents explicitly defer to TRDs, that deferral is preserved here. No unstated fields, endpoints, or behaviors are invented.

## Interface Contracts

### System Boundary

Crafted Dev Agent is a **two-process native macOS system**:

- **Swift shell**
  - owns UI
  - owns authentication
  - owns Keychain access
  - owns XPC-related platform integration
- **Python backend**
  - owns consensus
  - owns generation pipeline
  - owns GitHub operations

### Primary Cross-Process Contract

The Swift shell and Python backend communicate via:

- **transport:** authenticated Unix socket
- **framing:** line-delimited JSON

### Execution Safety Contract

A system-wide behavioral interface constraint is explicitly stated:

- **Neither process ever executes generated code.**

This is a hard contract, not an implementation detail.

---

## Per-Subsystem Data Structures

Only structures directly supported by the provided documents are listed.

### 1. Process Topology

#### `SystemArchitecture`

| Field | Type | Constraints |
|---|---|---|
| `swift_shell` | object | Required logical subsystem |
| `python_backend` | object | Required logical subsystem |

#### `SwiftShell`

| Field | Type | Constraints |
|---|---|---|
| `responsibilities` | array<string> | Includes `UI`, `authentication`, `Keychain`, `XPC` |

#### `PythonBackend`

| Field | Type | Constraints |
|---|---|---|
| `responsibilities` | array<string> | Includes `consensus`, `pipeline`, `GitHub` |

---

### 2. Cross-Process Message Frame

The only explicit wire-format statement provided is **line-delimited JSON** over an authenticated Unix socket.

#### `SocketMessage`

| Field | Type | Constraints |
|---|---|---|
| `json_line` | string | Must be valid JSON encoded on a single line and delimited by newline framing |

#### Constraints

- Each message is one complete JSON value per line.
- Messages are transmitted over an **authenticated Unix socket**.
- Message schemas beyond “JSON object/value per line” are not specified in the provided source excerpts and therefore are owned by the TRDs.

---

### 3. Product Version Structure

From `AGENTS.md` and lessons-learned metadata.

#### `VersionIdentifier`

| Field | Type | Constraints |
|---|---|---|
| `major` | integer | Non-negative |
| `minor` | integer | Non-negative |
| `patch` | integer | Non-negative |

#### Known examples

- `38.153.0`
- `38.209` appears as a document version and is not guaranteed to be the same runtime version schema

Because both forms appear in source material, consumers must not assume all versioned artifacts use identical tuple length unless specified by owning TRD.

---

### 4. Planning and Output Artifacts

From `README.md`.

#### `Intent`

| Field | Type | Constraints |
|---|---|---|
| `text` | string | Plain-language operator intent |

#### `TRDSet`

| Field | Type | Constraints |
|---|---|---|
| `documents` | array<document> | Repository specifications loaded into the agent |
| `source_of_truth` | boolean | Implied true for `forge-docs/` set |

#### `PRDPlan`

| Field | Type | Constraints |
|---|---|---|
| `items` | array<object> | Ordered PRD plan |
| `ordering` | string | Must be ordered |

#### `TypedPullRequestSequence`

| Field | Type | Constraints |
|---|---|---|
| `pull_requests` | array<object> | Sequence of typed pull requests |
| `ordering` | string | Must be sequential/logical |

#### `PullRequestPolicy`

| Field | Type | Constraints |
|---|---|---|
| `open_mode` | string | Every PR is opened as `draft` initially |

---

### 5. Consensus / Model Roles

From `README.md`.

#### `ConsensusConfiguration`

| Field | Type | Constraints |
|---|---|---|
| `providers` | array<string> | Includes `Claude` and `GPT-4o` |
| `arbitrator` | string | `Claude` arbitrates every result |

#### `GenerationFlow`

| Field | Type | Constraints |
|---|---|---|
| `parallel_generation` | boolean | True; two providers operate in parallel |
| `self_correction_pass` | boolean | Supported |
| `lint_gate` | boolean | Supported |
| `iterative_fix_loop` | boolean | Supported |

---

### 6. GitHub Pull Request Lifecycle Structures

From `GitHub-Integration-Lessons-Learned`.

#### `PullRequestDraftState`

| Field | Type | Constraints |
|---|---|---|
| `draft` | boolean | PRs are initially opened as draft |
| `ready_for_review` | boolean | Transition must be performed via GraphQL mutation |

#### `MarkPullRequestReadyForReviewRequest`

| Field | Type | Constraints |
|---|---|---|
| `pull_request_id` | string | Required GraphQL target identifier |

#### `RestPatchPullRequestDraftAttempt`

| Field | Type | Constraints |
|---|---|---|
| `endpoint` | string | `/repos/{owner}/{repo}/pulls/{number}` |
| `method` | string | `PATCH` |
| `body.draft` | boolean | Setting `false` does not transition draft state |

#### Behavior Contract

- `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{ "draft": false }`
  - may return HTTP `200`
  - does **not** convert a draft PR to ready for review
  - field is silently ignored
- Correct transition mechanism:
  - **GraphQL `markPullRequestReadyForReview` mutation**

---

## Cross-Subsystem Protocols

### 1. Swift Shell ↔ Python Backend Protocol

#### Transport

| Property | Value |
|---|---|
| Transport type | Unix socket |
| Authentication | Required |
| Encoding | JSON |
| Framing | Line-delimited |

#### Ownership Boundaries

| Operation Domain | Owning Subsystem |
|---|---|
| UI | Swift shell |
| Authentication | Swift shell |
| Secrets / Keychain | Swift shell |
| XPC integration | Swift shell |
| Consensus | Python backend |
| Generation pipeline | Python backend |
| GitHub operations | Python backend |

#### Required Protocol Guarantees

- Cross-process messages must be sent through the authenticated Unix socket.
- Payloads must be JSON framed one message per line.
- Secret ownership remains on the Swift side.
- GitHub operations are backend-owned.
- Generated code must not be executed by either side.

---

### 2. Operator → Agent Protocol

From `README.md`, the operator-facing logical flow is:

1. load repository
2. load TRDs
3. provide plain-language intent
4. agent assesses confidence in scope
5. agent decomposes intent into ordered PRD plan
6. agent decomposes PRD into typed pull requests
7. agent generates implementation and tests with two models in parallel
8. agent performs self-correction
9. agent applies lint gate
10. agent runs iterative fix loop
11. agent opens GitHub pull requests
12. operator gates, reviews, and merges

This is a workflow contract. Specific request/response payloads are not defined in the provided excerpts and therefore remain TRD-owned.

---

### 3. Pull Request Lifecycle Protocol

#### Draft-first policy

- Every pull request is opened as a **draft**.

#### Draft → Ready for Review transition

| Attempted Mechanism | Result |
|---|---|
| REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{ "draft": false }` | No state change; ignored |
| GraphQL `markPullRequestReadyForReview` | Supported and required |

#### Integration requirement

Any GitHub integration subsystem must implement draft promotion using GraphQL, not REST field patching.

---

## Enums and Constants

Only values explicitly present in source material are listed.

### `SubsystemName`

```text
SwiftShell
PythonBackend
```

### `SwiftShellResponsibility`

```text
UI
authentication
Keychain
XPC
```

### `PythonBackendResponsibility`

```text
consensus
pipeline
GitHub
```

### `TransportType`

```text
unix_socket
```

### `WireEncoding`

```text
json
```

### `FrameFormat`

```text
line_delimited_json
```

### `ModelProvider`

```text
Claude
GPT-4o
```

### `ArbitrationProvider`

```text
Claude
```

### `PullRequestOpenMode`

```text
draft
```

### `GitHubDraftPromotionMethod`

```text
graphql_markPullRequestReadyForReview
```

### `UnsupportedOrIneffectiveDraftPromotionMethod`

```text
rest_patch_pulls_with_draft_false
```

### `DocumentAuthority`

```text
forge-docs
TRD-11
TRD-1
TRD-8
```

Notes:

- `TRD-11` is explicitly the governing security specification.
- `TRD-1` and `TRD-8` are cited as ownership references in `CLAUDE.md`.
- No further enum expansion is justified from the provided excerpts.

---

## Validation Rules

### 1. Source-of-Truth Validation

- Code and interfaces must match the TRDs in `forge-docs/`.
- If an interface detail is not present in the provided documents, it must be treated as unspecified here.
- Security-relevant changes must defer to **TRD-11**.

### 2. Transport Validation

For any Swift↔Python message:

- transport must be a Unix socket
- socket must be authenticated
- each frame must be valid JSON
- each frame must be newline-delimited
- no multi-message JSON blob without line framing
- no alternate framing format is specified

### 3. Responsibility Boundary Validation

A component is invalid if it violates ownership boundaries:

- Swift shell must own:
  - UI
  - authentication
  - Keychain/secrets
  - XPC integration
- Python backend must own:
  - consensus
  - generation pipeline
  - GitHub operations

### 4. Execution Safety Validation

Invalid behavior:

- executing generated code in Swift shell
- executing generated code in Python backend

Valid behavior:

- generate code
- analyze code
- lint code
- self-correct code
- iterate fixes
- open PRs

### 5. GitHub Draft Lifecycle Validation

When promoting a PR from draft:

- invalid implementation:
  - REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with `{"draft": false}`
- valid implementation:
  - GraphQL `markPullRequestReadyForReview`

If a system treats HTTP 200 from the REST patch as success for draft promotion, that behavior is non-compliant with the documented contract.

### 6. Planning Workflow Validation

A compliant end-to-end build flow must preserve the documented ordering semantics:

- intent is assessed before commitment to scope
- intent is decomposed into an ordered PRD plan
- PRD is decomposed into typed pull requests
- generation uses two-model consensus with parallel providers
- Claude arbitrates every result
- self-correction, lint gate, and iterative fix loop occur before or within PR-production workflow as documented

### 7. Pull Request Creation Validation

- pull requests must be opened as draft initially
- operator remains the reviewer/gate/merge authority

---

## Wire Format Examples

Only formats directly supportable from the provided documents are shown.

### 1. Line-Delimited JSON Over Authenticated Unix Socket

Example stream:

```json
{"type":"intent","text":"Implement the next TRD-defined subsystem"}
{"type":"status","phase":"planning"}
{"type":"result","artifact":"pull_request","mode":"draft"}
```

Notes:

- The example demonstrates **JSON lines** only.
- Field names such as `type`, `phase`, and `artifact` are illustrative of framing shape, not normative schema from the provided excerpts.
- The normative contract is: **one valid JSON value per newline-delimited message over an authenticated Unix socket**.

### 2. Operator Intent Payload Example

```json
{"text":"Build the repository according to the loaded TRDs and open logical draft PRs"}
```

Normative support:

- intent is plain-language
- operator provides the intent
- exact envelope schema is TRD-owned

### 3. Consensus Configuration Example

```json
{
  "providers": ["Claude", "GPT-4o"],
  "arbitrator": "Claude",
  "parallel_generation": true
}
```

Normative support:

- two providers
- Claude arbitrates every result
- generation occurs in parallel

### 4. Pull Request Open State Example

```json
{
  "pull_request": {
    "mode": "draft"
  }
}
```

Normative support:

- every PR is opened as draft

### 5. Incorrect REST Draft Promotion Attempt

```http
PATCH /repos/{owner}/{repo}/pulls/{number}
Content-Type: application/json

{"draft":false}
```

Observed contract from provided lessons learned:

- may return `200`
- draft state remains unchanged
- field is silently ignored

### 6. Correct GraphQL Draft Promotion Example

```graphql
mutation MarkReady($pullRequestId: ID!) {
  markPullRequestReadyForReview(input: { pullRequestId: $pullRequestId }) {
    pullRequest {
      id
      isDraft
    }
  }
}
```

Associated variables example:

```json
{
  "pullRequestId": "PR_NODE_ID"
}
```

Normative support:

- `markPullRequestReadyForReview` is the required supported mechanism

---

## Non-Normative Notes on Unspecified Areas

The provided excerpts indicate that many detailed interfaces exist in the TRDs, but they are not included here. Therefore this document does **not** define:

- full Swift↔Python message schemas
- XPC payload contracts
- auth token structures
- Keychain record formats
- consensus result object schemas
- PRD or typed PR JSON schema
- error codes or error envelope structure
- GitHub REST/GraphQL schemas beyond the explicitly documented draft-promotion behavior

Those remain owned by the referenced TRDs and must not be inferred beyond what is documented above.