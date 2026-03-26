# INTERFACES.md

This document is the definitive interface and wire-format reference derived only from the provided TRD-adjacent materials in this repository input. Where the provided materials name a contract but do not define its full schema, this document records only what is explicitly specified and marks the rest as unspecified.

## Interface Contracts

### Scope and Source Authority

The provided source materials establish these interface authorities:

- The product is a **two-process native macOS agent**.
- The **Swift shell** owns:
  - UI
  - authentication
  - Keychain/secrets
  - XPC
- The **Python backend** owns:
  - consensus
  - pipeline
  - GitHub operations
- The two processes communicate via:
  - **authenticated Unix socket**
  - **line-delimited JSON**
- The system opens GitHub pull requests and uses GitHub REST and GraphQL APIs.
- The full authoritative specification is stated to live in TRDs under `forge-docs/`, but those TRDs were not included here. Therefore, this file includes only contracts explicitly present in the provided documents.

---

## Per-Subsystem Data Structures

## 1. Swift Shell ↔ Python Backend IPC

### Transport Envelope

The only explicitly specified wire format for inter-process communication is:

- transport: **authenticated Unix socket**
- framing: **line-delimited**
- serialization: **JSON**

#### IPC Record

| Field | Type | Required | Constraints | Source |
|---|---|---:|---|---|
| entire message | JSON value | yes | Must be serialized as one complete JSON object/value per line | CLAUDE.md |
| line terminator | newline | yes | One JSON message per line-delimited frame | CLAUDE.md |

#### Constraints

- Messages **must** be newline-delimited.
- Each line **must** contain exactly one JSON payload.
- Authentication is required at the Unix socket level, but the authentication mechanism is **unspecified in provided materials**.
- No binary framing, length-prefixing, or multiplexing format is specified in the provided materials.

#### Unspecified

The following are not defined in the provided materials:

- message type field names
- request/response correlation fields
- error envelope schema
- authentication token field structure
- version negotiation fields
- streaming semantics beyond line delimitation

---

## 2. Swift Shell Subsystem

The Swift shell responsibilities are explicitly identified, but internal data structures are not defined in the provided materials.

### Owned Domains

| Domain | Responsibility |
|---|---|
| UI | Native macOS user interface |
| Authentication | User auth flows |
| Keychain / secrets | Secret storage and secret ownership |
| XPC | Local process/service integration |

### Implied Data Domains

The following entities are implied by ownership statements but not structurally specified:

#### Authentication State
Unspecified schema.

#### Keychain Secret Record
Unspecified schema.

#### XPC Request / Response
Unspecified schema.

#### UI State Models
Unspecified schema.

---

## 3. Python Backend Subsystem

The Python backend responsibilities are explicitly identified, but internal schemas are not defined in the provided materials.

### Owned Domains

| Domain | Responsibility |
|---|---|
| Consensus | Multi-model generation and arbitration |
| Pipeline | Build/generation/fix workflow |
| GitHub | Pull request and repository operations |

### Implied Data Domains

#### Consensus Result
Unspecified schema.

#### Provider Output
Unspecified schema.

#### PRD Plan
Implied by README; unspecified schema.

#### Pull Request Unit
Implied by README as “typed pull requests”; unspecified schema.

#### Lint Gate Result
Implied by README; unspecified schema.

#### Iterative Fix Loop State
Implied by README; unspecified schema.

---

## 4. GitHub Integration

The provided GitHub integration document defines one concrete API behavior contract.

### Draft Pull Request Lifecycle

#### Pull Request State

| Field / Concept | Type | Constraints |
|---|---|---|
| draft | boolean | `true` for draft PR, `false` for ready-for-review target state |

#### Supported Transition: Draft → Ready for Review

##### Unsupported REST Attempt

| API | Method | Payload | Result |
|---|---|---|---|
| `/repos/{owner}/{repo}/pulls/{number}` | `PATCH` | `{"draft": false}` | Returns 200 but silently does not convert PR out of draft |

##### Supported GraphQL Mutation

| Operation | Purpose | Constraint |
|---|---|---|
| `markPullRequestReadyForReview` | Converts draft PR to ready for review | Identified as the only officially supported mechanism in provided materials |

#### GitHub Pull Request Data Elements

| Field | Type | Required | Constraints |
|---|---|---:|---|
| owner | string | yes | GitHub repository owner |
| repo | string | yes | GitHub repository name |
| number | integer | yes | Pull request number |
| draft | boolean | yes | Draft-state indicator where applicable |

#### Unspecified

Not defined in provided materials:

- GraphQL variable names
- GraphQL response schema
- authentication headers
- error retry policy
- rate-limit handling
- webhook payloads

---

## 5. Build / Planning Workflow Entities

From the README, the system behavior implies several workflow entities.

### Intent

| Field | Type | Required | Constraints |
|---|---|---:|---|
| user intent | plain-language text | yes | Input from operator describing desired work |

### Technical Specifications Input

| Field | Type | Required | Constraints |
|---|---|---:|---|
| TRDs | document set | yes | User loads TRDs/specifications into the system |

### Confidence Assessment

| Field | Type | Required | Constraints |
|---|---|---:|---|
| confidence | unspecified | implied | System assesses confidence in scope before committing |

### PRD Plan

| Field | Type | Required | Constraints |
|---|---|---:|---|
| ordered plan | sequence | implied | Intent is decomposed into an ordered PRD plan |

### Typed Pull Requests

| Field | Type | Required | Constraints |
|---|---|---:|---|
| pull request sequence | sequence | implied | Each PRD is decomposed into typed pull requests |
| draft state | boolean | implied | Every PR is opened as draft before operator review |

### Consensus Generation

| Field | Type | Required | Constraints |
|---|---|---:|---|
| provider 1 | model output | implied | Claude participates |
| provider 2 | model output | implied | GPT-4o participates |
| arbitrator | model/process | implied | Claude arbitrates every result |

### Validation / Correction Stages

| Stage | Type | Constraint |
|---|---|---|
| self-correction pass | pipeline stage | occurs after generation |
| lint gate | pipeline stage | must pass before progression |
| iterative fix loop | pipeline stage | repeats until acceptance condition, unspecified |

### Unspecified

The provided materials do not define:

- field names
- canonical JSON schema
- confidence scale
- PR type enum
- plan item schema
- consensus payload format
- lint result schema
- fix loop termination contract

---

## Cross-Subsystem Protocols

## 1. Swift Shell ↔ Python Backend Protocol

### Protocol Summary

| Property | Value |
|---|---|
| topology | two-process |
| initiators | unspecified |
| transport | authenticated Unix socket |
| serialization | JSON |
| framing | line-delimited JSON |

### Contract

1. Swift and Python communicate only through the authenticated Unix socket contract stated in the provided materials.
2. Each protocol frame is one newline-terminated JSON message.
3. Authentication is mandatory for the IPC channel.
4. Secret ownership remains with the Swift shell.
5. Intelligence, generation, and GitHub operations remain with the Python backend.

### Responsibility Boundary

| Capability | Swift Shell | Python Backend |
|---|---:|---:|
| UI | yes | no |
| Authentication | yes | no |
| Keychain / secrets | yes | no |
| XPC | yes | no |
| Consensus | no | yes |
| Pipeline | no | yes |
| GitHub operations | no | yes |

### Security Boundary

The provided documents state:

- Swift owns secrets.
- Python owns generation and GitHub operations.
- Neither process ever executes generated code.

This creates the following explicit protocol constraint:

| Rule | Constraint |
|---|---|
| Generated code execution | prohibited in both processes |

---

## 2. Human Operator ↔ Agent Workflow Protocol

### Workflow Sequence

Derived from README and GitHub lessons:

1. Operator provides:
   - repository
   - TRDs/specifications
   - plain-language intent
2. Agent assesses confidence in scope.
3. Agent decomposes intent into ordered PRD plan.
4. Agent decomposes each PRD into typed pull requests.
5. Agent generates implementation and tests using two models in parallel.
6. Claude arbitrates results.
7. Agent performs:
   - self-correction
   - lint gate
   - iterative fix loop
8. Agent opens a GitHub PR.
9. PR is opened as **draft**.
10. CI runs before operator review.
11. To transition draft PR to reviewable state, GitHub GraphQL `markPullRequestReadyForReview` must be used.

### Explicit Workflow Constraints

| Constraint | Source |
|---|---|
| Every PR is opened as a draft | GitHub-Integration-Lessons-Learned |
| CI runs before operator sees it | GitHub-Integration-Lessons-Learned |
| Draft cannot be reliably cleared via REST `PATCH pulls` with `{"draft": false}` | GitHub-Integration-Lessons-Learned |
| GraphQL mutation must be used to mark ready for review | GitHub-Integration-Lessons-Learned |

---

## 3. Agent ↔ GitHub Protocol

### Supported API Families

| API Family | Status |
|---|---|
| GitHub REST API | used |
| GitHub GraphQL API | used |

### Explicit Behavior Contract

#### REST Pull Update Limitation

- Endpoint: `PATCH /repos/{owner}/{repo}/pulls/{number}`
- Body: `{"draft": false}`
- Behavior: returns `200` but does not convert the PR from draft to ready-for-review.

#### GraphQL Required Mutation

- Mutation: `markPullRequestReadyForReview`
- Purpose: convert draft PR into ready-for-review state.

### Protocol Implication

Any subsystem that attempts draft-state transition **must** route that transition through GraphQL, not REST.

---

## Enums and Constants

Only enums/constants directly supported by the provided materials are included.

## 1. Process Roles

| Name | Type | Values |
|---|---|---|
| process_role | enum | `swift_shell`, `python_backend` |

## 2. Transport Constants

| Name | Type | Value |
|---|---|---|
| ipc_transport | constant | `unix_socket` |
| ipc_serialization | constant | `json` |
| ipc_framing | constant | `line_delimited` |

## 3. Pull Request State

| Name | Type | Values |
|---|---|---|
| pull_request_state | enum | `draft`, `ready_for_review` |

## 4. API Family

| Name | Type | Values |
|---|---|---|
| github_api_family | enum | `rest`, `graphql` |

## 5. Model Roles

| Name | Type | Values |
|---|---|---|
| model_role | enum | `generator`, `arbitrator` |

## 6. Named Models Mentioned

| Name | Type | Values |
|---|---|---|
| provider_model | enum | `Claude`, `GPT-4o` |

## 7. Pipeline Stages Mentioned

| Name | Type | Values |
|---|---|---|
| pipeline_stage | enum | `confidence_assessment`, `prd_decomposition`, `pull_request_decomposition`, `parallel_generation`, `arbitration`, `self_correction`, `lint_gate`, `iterative_fix_loop`, `draft_pr_open`, `ready_for_review_transition` |

## 8. Prohibited Operation

| Name | Type | Value |
|---|---|---|
| generated_code_execution | constant | `forbidden` |

## 9. Version

A version string is explicitly present in the provided materials.

| Name | Type | Value |
|---|---|---|
| current_version | string | `38.153.0` |

Note: another provided document references `v38.209` for lessons learned documentation. The materials do not define a single authoritative runtime/version interface contract beyond these document-local version strings.

---

## Validation Rules

## 1. IPC Validation Rules

### Required

- IPC messages must be valid JSON.
- IPC messages must be line-delimited.
- One line must correspond to one JSON message.
- IPC channel must be authenticated.

### Prohibited

- Multi-line JSON as a single frame, unless the transport still emits it as a single line after escaping.
- Non-JSON payloads on the IPC wire.
- Unauthenticated IPC connections.

### Unspecified

- Maximum message size
- UTF encoding requirements
- compression
- heartbeat messages
- backpressure semantics

---

## 2. Responsibility Validation Rules

These are architectural contract checks derived from the provided materials.

### Swift Shell

Must own:

- UI
- authentication
- Keychain/secrets
- XPC

Must not own, per provided architecture statements:

- consensus engine behavior
- generation pipeline
- GitHub operations

### Python Backend

Must own:

- consensus
- pipeline
- GitHub operations

Must not violate:

- secret ownership by Swift
- prohibition on executing generated code

---

## 3. Security Validation Rules

Explicitly present or directly implied from the provided materials:

- Neither process may execute generated code.
- Secrets belong to the Swift shell boundary.
- Any security-relevant change should follow TRD-11, but TRD-11 content is not included here and therefore not restated.

---

## 4. GitHub Validation Rules

### Draft PR Handling

- New PRs are opened as draft.
- CI should run before operator review.
- Transition from draft to ready-for-review must use GraphQL `markPullRequestReadyForReview`.

### Invalid/Unsupported Draft Transition Method

The following must be treated as invalid for actual state transition purposes:

- REST `PATCH /repos/{owner}/{repo}/pulls/{number}` with body `{"draft": false}`

Reason:

- GitHub silently ignores the field while returning HTTP 200.

### Repository Identifier Validation

Where GitHub PR operations are performed, the following identifiers are required:

- `owner`
- `repo`
- `number`

Type expectations:

- `owner`: string
- `repo`: string
- `number`: integer

---

## 5. Workflow Validation Rules

### Required Inputs

The workflow requires, at minimum, the following inputs stated in the README:

- repository
- TRDs/specifications
- plain-language intent

### Required High-Level Processing Stages

The system behavior must include these stages, though exact schemas are unspecified:

- confidence assessment before commitment
- decomposition into ordered PRD plan
- decomposition into typed pull requests
- two-model parallel generation
- Claude arbitration
- self-correction
- lint gate
- iterative fix loop
- GitHub PR creation

---

## Wire Format Examples

Only examples that are justified by the provided materials are included. Field names not explicitly defined in the source are avoided where possible or clearly marked illustrative.

## 1. IPC Line-Delimited JSON

Example of the required framing style:

```json
{"message":"example"}
```

```json
{"event":"example","value":1}
```

As transmitted on the wire, each JSON object occupies a single newline-delimited line:

```text
{"message":"example"}
{"event":"example","value":1}
```

## 2. GitHub REST Attempt That Does Not Clear Draft State

Request:

```http
PATCH /repos/{owner}/{repo}/pulls/{number}
Content-Type: application/json

{"draft": false}
```

Observed contract from provided materials:

- HTTP status may be `200`
- PR remains draft
- No error is emitted for the ignored field

## 3. GitHub GraphQL Transition Requirement

The provided materials specify the required mutation name but not the exact full schema. The minimal operation form is therefore:

```graphql
mutation {
  markPullRequestReadyForReview(...)
}
```

Because the provided materials do not include argument names or response fields, they are intentionally omitted here.

## 4. Minimal PR Identifier Shape

A minimal data shape implied by the REST endpoint path is:

```json
{
  "owner": "string",
  "repo": "string",
  "number": 123
}
```

## 5. Draft PR State Shape

A minimal state-bearing shape implied by the materials is:

```json
{
  "draft": true
}
```

and target state:

```json
{
  "draft": false
}
```

Important: per provided materials, sending `{"draft": false}` to the REST pull update endpoint does **not** reliably enact the state transition.

## 6. Workflow Input Shape

The README defines these inputs conceptually:

```json
{
  "repository": "unspecified-format",
  "trds": ["specification documents"],
  "intent": "plain-language user request"
}
```

Field names and exact repository encoding are not defined in the provided materials; this example is conceptual only.

---

## Summary of Explicit Contracts

The provided materials explicitly establish these interface contracts:

1. The product is a **two-process architecture**:
   - `swift_shell`
   - `python_backend`

2. Inter-process communication is:
   - **authenticated**
   - over **Unix socket**
   - using **line-delimited JSON**

3. Ownership boundaries are strict:
   - Swift: UI, auth, Keychain/secrets, XPC
   - Python: consensus, pipeline, GitHub

4. **Generated code must never be executed** by either process.

5. GitHub draft PR lifecycle has a hard integration rule:
   - open PRs as draft
   - do **not** rely on REST `PATCH pulls {"draft": false}`
   - use GraphQL `markPullRequestReadyForReview`

6. The workflow includes:
   - intent input
   - confidence assessment
   - PRD decomposition
   - typed PR decomposition
   - two-model parallel generation
   - Claude arbitration
   - self-correction
   - lint gate
   - iterative fix loop
   - PR creation

---

## Non-Specified Areas

The following interfaces are referenced but not fully specified in the provided materials and therefore cannot be authoritatively defined here:

- IPC message schemas and field names
- authentication payload formats
- XPC contracts
- Keychain record structures
- consensus result schemas
- PRD and pull request type schemas
- error envelopes
- retry/backoff policies
- test result wire formats
- GitHub GraphQL variable and response schemas
- repository object schema
- confidence scoring schema

If the missing TRD documents are later provided, this file should be expanded only with information directly traceable to those TRDs.