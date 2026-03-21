# Interface Contracts — Forge Platform

Definitive wire format and API contract reference for the Forge platform.

This document defines the interface-level contracts across all known Forge subsystems based on the provided source materials, including the Consensus Dev Agent shell/backend architecture and the mandatory Forge Component Interface Contracts.

---

## 1. Scope

Forge is a two-process platform:

- **Swift macOS Shell**
  - UI
  - authentication
  - Keychain secret storage
  - session lifecycle
  - local orchestration
  - authenticated IPC endpoint ownership
- **Python Backend**
  - consensus engine
  - provider adapters
  - planning/pipeline
  - GitHub operations
  - review cycle orchestration
  - CI orchestration
  - documentation regeneration orchestration

Primary transport between shell and backend:

- **Authenticated Unix domain socket**
- **Line-delimited JSON (LDJSON / NDJSON style)**
- One complete JSON object per line
- UTF-8 encoding
- No binary frames
- No partial-object streaming at wire level unless explicitly encoded as event messages

Security and enforcement are governed by the Forge contracts below and are **mandatory for every component**.

---

## 2. Normative Language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as RFC 2119 terms.

---

## 3. Global Platform Invariants

1. Generated code is **never executed** by either process directly.
2. All inter-process communication uses **authenticated Unix socket + line-delimited JSON**.
3. Every security-relevant action is subject to:
   - CTX-ID validation
   - VTZ policy enforcement
   - TrustFlow emission
   - audit logging
4. All trust, identity, policy, and cryptographic failures **fail closed**.
5. Missing CTX-ID is treated as **UNTRUSTED**.
6. Labels are immutable after ingestion.
7. Cross-subsystem interfaces are versioned.
8. Unknown required fields cause rejection.
9. Secrets, tokens, keys, and cleartext sensitive payloads MUST NOT appear in error text or audit message bodies.

---

## 4. Common Wire Format

## 4.1 Transport

- **Transport:** Unix domain socket
- **Encoding:** UTF-8
- **Framing:** one JSON object per line
- **Newline delimiter:** `\n`
- **Object size limits:** deployment-defined; receivers MUST reject oversized messages before parsing full payload where possible
- **Ordering:** in-order per socket connection
- **Concurrency:** request/response and event messages MAY interleave; correlation is by `request_id` / `operation_id`

## 4.2 Common Message Envelope

Every cross-process message MUST conform to this base envelope.

```json
{
  "message_type": "request|response|event|error",
  "schema_version": "1.0",
  "message_id": "uuid-or-csprng-id",
  "session_id": "sess_...",
  "ctx_id": "ctx_...",
  "ts": 1742515200123,
  "source": "shell|backend|provider_adapter|pipeline|github|review|ci|audit|trustflow",
  "destination": "shell|backend|pipeline|github|review|ci|audit|trustflow",
  "payload": {}
}
```

### Field Contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `message_type` | string | yes | One of `request`, `response`, `event`, `error` |
| `schema_version` | string | yes | Semver-like protocol schema version, currently `1.0` |
| `message_id` | string | yes | Globally unique, non-sequential, CSPRNG-backed if generated at runtime |
| `session_id` | string | yes | Active session identifier |
| `ctx_id` | string | conditional | REQUIRED for any action in trust scope; absent means untrusted |
| `ts` | integer | yes | UTC Unix timestamp in milliseconds |
| `source` | string | yes | Logical sender subsystem |
| `destination` | string | yes | Logical receiver subsystem |
| `payload` | object | yes | Type-specific payload |

### Validation Rules

- `message_id` MUST be unique across retries; retries get a new `message_id` and preserve `request_id` where applicable.
- `ts` MUST be milliseconds since Unix epoch UTC.
- `payload` MUST be an object, never an array or scalar.
- Unknown top-level envelope fields MAY be ignored only if policy allows forward compatibility; unknown required payload fields MUST be rejected if schema marks payload as closed.
- Missing `ctx_id` MUST force untrusted handling and denial for protected actions.

---

## 5. Core Security Contracts

## 5.1 CAL Enforcement Contract

Every entry point that processes an agent action MUST implement the following exact sequence:

1. **CTX-ID validation FIRST**
2. Reject immediately on validation failure
3. **VTZ policy evaluation BEFORE execution**
4. Emit `VTZEnforcementDecision` with `verdict=block` on denial
5. Emit **TrustFlow** event for every outcome: allow, restrict, block
6. TrustFlow emission failure MUST NOT silently continue; it MUST be logged and surfaced

### Enforcement Pipeline

```text
receive action
  -> validate envelope
  -> validate CTX-ID
  -> create pre-execution audit record
  -> evaluate VTZ policy
  -> emit VTZ enforcement decision
  -> emit TrustFlow event
  -> if allowed/restricted, execute action
  -> emit completion/result/audit
```

## 5.2 TrustFlow Emission Contract

Every TrustFlow event MUST include:

- `event_id`
- `session_id`
- `ctx_id`
- `ts`
- `event_type`
- `payload_hash`

Additional requirements:

- `event_id` MUST be globally unique and CSPRNG-based
- `ts` MUST be UTC Unix timestamp with millisecond precision
- `payload_hash` MUST be SHA-256 of the serialized action payload
- emission MUST be synchronous in the enforcement path
- failed emission is a WARN-level audit event, not a silent skip

## 5.3 CTX-ID Contract

- CTX-ID tokens are immutable after issuance
- rotation issues a new token and invalidates the old token immediately
- expired CTX-ID MUST be rejected
- CTX-ID MUST be validated against TrustLock public key
- software-only validation without TrustLock public key verification is non-conformant
- missing CTX-ID => untrusted

## 5.4 VTZ Enforcement Contract

- each session is bound to exactly one VTZ at CTX-ID issuance
- cross-VTZ tool calls require explicit authorization
- implicit cross-VTZ access is denied
- VTZ boundaries are structural and cannot be bypassed in application logic
- policy changes take effect at next CTX-ID issuance

## 5.5 DTL Label Contract

- labels assigned at ingestion
- labels immutable thereafter
- derived data inherits highest classification among sources
- unlabeled data treated as `CONFIDENTIAL`
- label verification before crossing trust boundary
- label stripping is a security event and MUST be audited

## 5.6 Error Handling Contract

- all trust, identity, policy, cryptographic failures fail closed
- no swallowed exceptions in enforcement paths
- all errors MUST include:
  - `component`
  - `operation`
  - `failure_reason`
  - `ctx_id` if available
- errors MUST NOT include:
  - keys
  - tokens
  - secrets
  - cleartext payloads

## 5.7 Audit Contract

- every security-relevant action MUST generate audit record BEFORE execution
- audit log is append-only
- no in-place mutation or deletion of historical audit records
- audit write failure in enforcement path MUST surface and fail closed unless system policy explicitly defines a degraded safe mode

---

## 6. Enums and Constants

## 6.1 Message Types

```text
request
response
event
error
```

## 6.2 Subsystem Names

```text
shell
backend
consensus
provider_adapter
planner
pipeline
github
review
ci
docs
audit
trustflow
auth
keychain
session
security
ui
```

## 6.3 Enforcement Verdict

```text
allow
restrict
block
error
```

## 6.4 Session State

```text
created
authenticated
active
locked
expired
terminated
error
```

## 6.5 Build / Workflow State

```text
idle
loading_specs
planning
queued
generating
reviewing
testing
awaiting_user
opening_pr
completed
failed
cancelled
```

## 6.6 Review Pass

```text
pass_1
pass_2
pass_3
```

## 6.7 PR State

```text
not_started
draft_open
ready_for_review
changes_requested
approved
merged
closed
failed
```

## 6.8 CI State

```text
pending
running
passed
failed
cancelled
timed_out
unknown
```

## 6.9 Provider Identity

```text
claude
gpt4o
arbitrator_claude
```

## 6.10 DTL Classification

```text
public
internal
confidential
restricted
```

If casing is normalized in code, wire values SHOULD use uppercase only if schema version requires it. Recommended wire canonicalization:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

## 6.11 Error Codes

```text
INVALID_ENVELOPE
INVALID_CTX_ID
CTX_ID_EXPIRED
CTX_ID_REVOKED
CTX_ID_SIGNATURE_INVALID
UNTRUSTED_REQUEST
VTZ_DENIED
VTZ_CROSS_BOUNDARY_DENIED
TRUSTFLOW_EMIT_FAILED
AUDIT_WRITE_FAILED
AUTH_REQUIRED
AUTH_FAILED
KEYCHAIN_ERROR
BACKEND_UNAVAILABLE
PROVIDER_ERROR
CONSENSUS_ERROR
PLAN_INVALID
PIPELINE_ERROR
GITHUB_ERROR
CI_ERROR
VALIDATION_ERROR
TIMEOUT
INTERNAL_ERROR
```

---

## 7. Cross-Subsystem Protocols

## 7.1 Shell ↔ Backend Protocol

The shell is the transport owner and trust boundary front-end. The backend is the execution and orchestration engine.

### Supported message families

- session/auth lifecycle
- spec ingestion
- intent submission
- planning
- PR unit generation
- review cycle
- CI orchestration
- GitHub PR operations
- progress events
- audit/trust events
- cancellation
- heartbeat/health

### Request/Response Correlation

Every `request` payload MUST contain `request_id`.

Every terminal `response` or `error` related to a request MUST echo:

- `request_id`
- `operation`
- `status`

Long-running operations MUST additionally expose `operation_id`.

## 7.2 User Intent → Plan → PR Sequence Protocol

High-level workflow:

1. ingest TRDs/specs
2. validate labels/classification
3. submit plain-language intent
4. produce ordered PRD/plan
5. decompose plan into PR units
6. generate implementation via two providers in parallel
7. arbitrate with Claude
8. run 3-pass review cycle
9. execute CI
10. open draft PR
11. await user gate
12. continue next PR when approved

## 7.3 Consensus Protocol

Two model providers generate candidate outputs in parallel.

- provider A: Claude
- provider B: GPT-4o
- arbitrator: Claude

The backend MUST preserve provider provenance, prompt lineage, and result hashes for auditability.

## 7.4 GitHub Protocol

Backend owns GitHub operations.

Typical actions:

- repository inspection
- branch creation
- commit creation
- draft PR creation
- PR status polling
- comment posting
- review retrieval

Shell MUST NOT directly perform GitHub mutation if architecture follows TRD authority.

## 7.5 Documentation Regeneration Protocol

After build completion, docs regeneration MAY be invoked.

- input: repository state, specs, completed PR set
- output: regenerated documentation artifacts
- generated docs remain non-executed artifacts

---

## 8. Per-Subsystem Data Structures

## 8.1 Shell Subsystem

### 8.1.1 AppSession

```json
{
  "session_id": "sess_01HV...",
  "state": "authenticated",
  "user_id": "local_user",
  "created_at": 1742515200123,
  "authenticated_at": 1742515201123,
  "expires_at": 1742558401123,
  "locked_at": null,
  "ctx_id": "ctx_01HV...",
  "vtz_id": "vtz_local_default"
}
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `session_id` | string | yes | Unique session identifier |
| `state` | enum | yes | See Session State |
| `user_id` | string | yes | Local principal identifier |
| `created_at` | int | yes | ms epoch UTC |
| `authenticated_at` | int\|null | no | set when auth succeeds |
| `expires_at` | int | yes | hard session expiry |
| `locked_at` | int\|null | no | populated when shell locks |
| `ctx_id` | string | conditional | required once trust-bound |
| `vtz_id` | string | conditional | required for trusted session |

### 8.1.2 AuthenticationRequest

```json
{
  "request_id": "req_01",
  "operation": "authenticate",
  "method": "biometric",
  "reason": "unlock_session"
}
```

### 8.1.3 AuthenticationResponse

```json
{
  "request_id": "req_01",
  "operation": "authenticate",
  "status": "ok",
  "session": {
    "session_id": "sess_01HV...",
    "state": "authenticated",
    "ctx_id": "ctx_01HV...",
    "vtz_id": "vtz_local_default"
  }
}
```

### 8.1.4 KeychainSecretRef

The shell stores secrets; the backend receives references or capability-scoped material, not raw secret inventory dumps.

```json
{
  "secret_ref": "kc_gh_token_primary",
  "secret_type": "github_token",
  "access_scope": ["repo:read", "repo:write", "pull_request:write"],
  "last_validated_at": 1742515202123
}
```

## 8.2 Auth and Identity Subsystem

### 8.2.1 CTXIDToken

```json
{
  "ctx_id": "ctx_01HV5R...",
  "session_id": "sess_01HV...",
  "principal_id": "local_user",
  "vtz_id": "vtz_local_default",
  "issued_at": 1742515201123,
  "expires_at": 1742558401123,
  "rotates_from": null,
  "signature": "base64url...",
  "key_id": "trustlock_pubkey_2026_01"
}
```

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `ctx_id` | string | yes | Immutable token identifier |
| `session_id` | string | yes | Bound session |
| `principal_id` | string | yes | User/service principal |
| `vtz_id` | string | yes | Exactly one VTZ |
| `issued_at` | int | yes | ms epoch UTC |
| `expires_at` | int | yes | > issued_at |
| `rotates_from` | string\|null | no | Previous token if rotation |
| `signature` | string | yes | TrustLock verifiable signature |
| `key_id` | string | yes | Public key identifier |

### Validation Rules

- `expires_at > issued_at`
- rotation MUST invalidate prior `ctx_id`
- verification MUST succeed against `key_id`
- no field mutation after issuance

## 8.3 Security / Enforcement Subsystem

### 8.3.1 VTZEnforcementDecision

```json
{
  "decision_id": "vtzdec_01HV...",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "vtz_id": "vtz_local_default",
  "operation": "github.create_pull_request",
  "resource": "repo:owner/name",
  "verdict": "allow",
  "policy_id": "vtz_policy_default_v12",
  "reason_code": "POLICY_MATCH",
  "evaluated_at": 1742515210001
}
```

### 8.3.2 TrustFlowEvent

```json
{
  "event_id": "tf_01HV...",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515210002,
  "event_type": "action_allowed",
  "payload_hash": "sha256:9f2c4d...",
  "component": "pipeline",
  "operation": "github.create_pull_request"
}
```

### 8.3.3 AuditRecord

```json
{
  "audit_id": "aud_01HV...",
  "ts": 1742515210000,
  "component": "github",
  "operation": "create_pull_request",
  "phase": "pre_execution",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "severity": "INFO",
  "outcome": "pending",
  "failure_reason": null,
  "details_hash": "sha256:4ab1..."
}
```

### 8.3.4 DataLabel

```json
{
  "label_id": "lbl_01HV...",
  "classification": "CONFIDENTIAL",
  "assigned_at": 1742515205000,
  "source": "trd_ingestion",
  "immutable": true
}
```

## 8.4 Spec Ingestion Subsystem

### 8.4.1 SpecDocument

```json
{
  "spec_id": "spec_trd_1",
  "title": "TRD-1: macOS Application Shell",
  "doc_type": "TRD",
  "version": "1.1",
  "source_path": "forge-docs/TRD-1-macOS-Application-Shell.md",
  "content_hash": "sha256:abc123...",
  "classification": "CONFIDENTIAL",
  "ingested_at": 1742515204000
}
```

### 8.4.2 SpecIngestionRequest

```json
{
  "request_id": "req_ingest_01",
  "operation": "ingest_specs",
  "repository_id": "repo_local_01",
  "documents": [
    {
      "path": "forge-docs/TRD-1-macOS-Application-Shell.md",
      "declared_type": "TRD"
    }
  ]
}
```

### 8.4.3 SpecIngestionResponse

```json
{
  "request_id": "req_ingest_01",
  "operation": "ingest_specs",
  "status": "ok",
  "accepted": [
    {
      "spec_id": "spec_trd_1",
      "content_hash": "sha256:abc123..."
    }
  ],
  "rejected": []
}
```

## 8.5 Intent Subsystem

### 8.5.1 IntentSubmission

```json
{
  "request_id": "req_intent_01",
  "operation": "submit_intent",
  "intent_id": "intent_01HV...",
  "repository_id": "repo_local_01",
  "text": "Implement full Forge platform interface contract documentation.",
  "spec_refs": ["spec_trd_1", "spec_trd_2", "spec_trd_11"],
  "submitted_at": 1742515220000
}
```

Constraints:

- `text` MUST be non-empty UTF-8 text
- `spec_refs` MUST reference ingested specs if provided
- intent payload hash SHOULD be auditable

## 8.6 Planning Subsystem

### 8.6.1 PRDPlan

```json
{
  "plan_id": "plan_01HV...",
  "intent_id": "intent_01HV...",
  "repository_id": "repo_local_01",
  "summary": "Create interface contract documentation and supporting validations.",
  "status": "planning",
  "steps": [
    {
      "step_id": "step_1",
      "order": 1,
      "title": "Analyze source TRDs",
      "description": "Extract authoritative interface requirements",
      "dependencies": []
    }
  ],
  "created_at": 1742515230000
}
```

### 8.6.2 PRUnit

```json
{
  "pr_unit_id": "pru_01HV...",
  "plan_id": "plan_01HV...",
  "sequence": 1,
  "title": "Add interface contracts document",
  "scope": "documentation",
  "base_branch": "main",
  "working_branch": "forge/pru-01-interface-contracts",
  "state": "queued"
}
```

## 8.7 Consensus Subsystem

### 8.7.1 ConsensusJob

```json
{
  "job_id": "cons_01HV...",
  "pr_unit_id": "pru_01HV...",
  "providers": ["claude", "gpt4o"],
  "arbitrator": "claude",
  "prompt_bundle_hash": "sha256:beef...",
  "created_at": 1742515240000,
  "status": "generating"
}
```

### 8.7.2 ProviderInvocation

```json
{
  "invocation_id": "pinv_01HV...",
  "job_id": "cons_01HV...",
  "provider": "claude",
  "model": "claude-sonnet",
  "input_hash": "sha256:111...",
  "started_at": 1742515240100,
  "completed_at": null,
  "status": "running"
}
```

### 8.7.3 ProviderResult

```json
{
  "result_id": "pres_01HV...",
  "invocation_id": "pinv_01HV...",
  "provider": "gpt4o",
  "output_hash": "sha256:222...",
  "artifact_refs": ["art_01", "art_02"],
  "token_usage": {
    "input": 1200,
    "output": 3400
  },
  "status": "completed"
}
```

### 8.7.4 ConsensusDecision

```json
{
  "decision_id": "cdec_01HV...",
  "job_id": "cons_01HV...",
  "arbitrator": "claude",
  "selected_result_id": "pres_01HV...",
  "merge_strategy": "select_with_edits",
  "rationale_hash": "sha256:333...",
  "decided_at": 1742515250000
}
```

## 8.8 Review Subsystem

Three-pass review is mandatory per product description.

### 8.8.1 ReviewCycle

```json
{
  "review_cycle_id": "rev_01HV...",
  "pr_unit_id": "pru_01HV...",
  "passes_total": 3,
  "current_pass": "pass_1",
  "status": "reviewing",
  "started_at": 1742515260000
}
```

### 8.8.2 ReviewPassResult

```json
{
  "review_cycle_id": "rev_01HV...",
  "pass": "pass_1",
  "issues_found": 4,
  "severity_max": "medium",
  "summary_hash": "sha256:444...",
  "status": "changes_required",
  "completed_at": 1742515265000
}
```

## 8.9 CI Subsystem

### 8.9.1 CIExecution

```json
{
  "ci_execution_id": "ci_01HV...",
  "pr_unit_id": "pru_01HV...",
  "provider": "local_or_remote_ci",
  "status": "running",
  "started_at": 1742515270000,
  "completed_at": null
}
```

### 8.9.2 CIResult

```json
{
  "ci_execution_id": "ci_01HV...",
  "status": "passed",
  "checks": [
    {
      "name": "pytest",
      "status": "passed"
    }
  ],
  "artifact_refs": [],
  "completed_at": 1742515280000
}
```

## 8.10 GitHub Subsystem

### 8.10.1 GitHubRepositoryRef

```json
{
  "repository_id": "repo_local_01",
  "owner": "example",
  "name": "forge",
  "default_branch": "main",
  "provider": "github"
}
```

### 8.10.2 BranchRef

```json
{
  "branch_name": "forge/pru-01-interface-contracts",
  "commit_sha": "abcde12345",
  "base_branch": "main"
}
```

### 8.10.3 PullRequestDraft

```json
{
  "pull_request_id": "ghpr_01HV...",
  "repository_id": "repo_local_01",
  "number": 42,
  "title": "Add Forge interface contracts",
  "body_hash": "sha256:555...",
  "source_branch": "forge/pru-01-interface-contracts",
  "target_branch": "main",
  "state": "draft_open",
  "created_at": 1742515290000
}
```

## 8.11 Documentation Subsystem

### 8.11.1 DocumentationRegenerationJob

```json
{
  "doc_job_id": "doc_01HV...",
  "repository_id": "repo_local_01",
  "trigger": "build_completed",
  "input_refs": ["plan_01HV...", "ghpr_01HV..."],
  "status": "queued",
  "created_at": 1742515300000
}
```

## 8.12 UI Subsystem

### 8.12.1 UIStateSnapshot

```json
{
  "session_state": "active",
  "workflow_state": "reviewing",
  "active_plan_id": "plan_01HV...",
  "active_pr_unit_id": "pru_01HV...",
  "notifications": 2,
  "updated_at": 1742515305000
}
```

---

## 9. Standard Operation Payloads

## 9.1 Health Check

### Request

```json
{
  "message_type": "request",
  "schema_version": "1.0",
  "message_id": "msg_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515200123,
  "source": "shell",
  "destination": "backend",
  "payload": {
    "request_id": "req_health_01",
    "operation": "health_check"
  }
}
```

### Response

```json
{
  "message_type": "response",
  "schema_version": "1.0",
  "message_id": "msg_002",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515200223,
  "source": "backend",
  "destination": "shell",
  "payload": {
    "request_id": "req_health_01",
    "operation": "health_check",
    "status": "ok",
    "backend_state": "ready",
    "capabilities": [
      "ingest_specs",
      "submit_intent",
      "plan",
      "generate",
      "review",
      "ci",
      "github"
    ]
  }
}
```

## 9.2 Ingest Specs

### Request

```json
{
  "message_type": "request",
  "schema_version": "1.0",
  "message_id": "msg_010",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515210000,
  "source": "shell",
  "destination": "backend",
  "payload": {
    "request_id": "req_ingest_01",
    "operation": "ingest_specs",
    "repository_id": "repo_local_01",
    "documents": [
      {
        "path": "forge-docs/TRD-1-macOS-Application-Shell.md",
        "declared_type": "TRD"
      }
    ]
  }
}
```

## 9.3 Submit Intent

### Request

```json
{
  "message_type": "request",
  "schema_version": "1.0",
  "message_id": "msg_020",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515220000,
  "source": "shell",
  "destination": "backend",
  "payload": {
    "request_id": "req_intent_01",
    "operation": "submit_intent",
    "intent_id": "intent_01HV...",
    "repository_id": "repo_local_01",
    "text": "Implement interface contracts for Forge.",
    "spec_refs": ["spec_trd_1"]
  }
}
```

## 9.4 Start Planning

```json
{
  "message_type": "request",
  "schema_version": "1.0",
  "message_id": "msg_030",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515230000,
  "source": "shell",
  "destination": "backend",
  "payload": {
    "request_id": "req_plan_01",
    "operation": "create_plan",
    "intent_id": "intent_01HV..."
  }
}
```

## 9.5 Progress Event

```json
{
  "message_type": "event",
  "schema_version": "1.0",
  "message_id": "msg_evt_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515245000,
  "source": "backend",
  "destination": "shell",
  "payload": {
    "operation_id": "op_01HV...",
    "event_name": "workflow_progress",
    "workflow_state": "generating",
    "plan_id": "plan_01HV...",
    "pr_unit_id": "pru_01HV...",
    "percent": 42
  }
}
```

## 9.6 Open Draft PR Result

```json
{
  "message_type": "response",
  "schema_version": "1.0",
  "message_id": "msg_090",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515291000,
  "source": "backend",
  "destination": "shell",
  "payload": {
    "request_id": "req_open_pr_01",
    "operation": "open_pull_request",
    "status": "ok",
    "pull_request": {
      "pull_request_id": "ghpr_01HV...",
      "number": 42,
      "state": "draft_open"
    }
  }
}
```

---

## 10. Error Wire Format

Every error response MUST use `message_type: "error"`.

```json
{
  "message_type": "error",
  "schema_version": "1.0",
  "message_id": "msg_err_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515210003,
  "source": "backend",
  "destination": "shell",
  "payload": {
    "request_id": "req_open_pr_01",
    "operation": "open_pull_request",
    "status": "error",
    "error": {
      "code": "VTZ_DENIED",
      "component": "security",
      "operation": "github.create_pull_request",
      "failure_reason": "operation_not_permitted_in_bound_vtz",
      "retryable": false
    }
  }
}
```

## Error Object Contract

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `code` | string | yes | See Error Codes |
| `component` | string | yes | Source component |
| `operation` | string | yes | Failed operation |
| `failure_reason` | string | yes | Sanitized, no secrets |
| `retryable` | boolean | yes | Indicates caller retry advisability |
| `ctx_id` | string | no | MAY be present if duplicated inside error detail |

### Validation Rules

- error text MUST be sanitized
- no secrets or raw payloads
- protected operation failures without valid CTX-ID MUST fail closed
- receivers MUST NOT reinterpret an `error` frame as partial success

---

## 11. Validation Rules

## 11.1 General Validation

- all timestamps are integer milliseconds UTC
- all IDs are non-empty strings
- all hashes SHOULD be prefixed with algorithm, e.g. `sha256:...`
- arrays with semantic ordering MUST preserve order as transmitted
- null allowed only where schema explicitly permits it
- booleans MUST NOT be encoded as strings

## 11.2 Envelope Validation

Reject message if:

- invalid JSON
- missing newline framing boundary
- duplicate top-level keys after parsing
- missing required envelope field
- unsupported `schema_version`
- invalid `message_type`
- `payload` not object
- `ts` not integer millisecond epoch

## 11.3 CTX-ID Validation

Reject protected action if:

- `ctx_id` missing
- expired
- revoked
- signature invalid
- bound session mismatch
- VTZ mismatch with session

## 11.4 DTL Validation

Before data crosses subsystem or process boundary:

- verify label exists
- verify label is immutable
- verify derived label is highest source classification
- reject unlabeled outbound payload unless explicitly marked `CONFIDENTIAL`

## 11.5 TrustFlow Validation

- event emission MUST be synchronous
- `payload_hash` MUST be SHA-256 over canonical serialized payload
- if TrustFlow emission fails, action MUST surface failure and MUST NOT silently proceed as though emission succeeded

## 11.6 Audit Validation

- pre-execution audit record MUST exist for security-relevant actions
- append-only semantics MUST be enforced
- record updates, if modeled, MUST be additive follow-up records, not mutation of prior record

---

## 12. Canonical Serialization Rules

To ensure stable `payload_hash` and audit hashes, components SHOULD use canonical JSON serialization:

1. UTF-8
2. object keys sorted lexicographically
3. no insignificant whitespace
4. integers represented in base-10
5. no NaN or Infinity
6. strings normalized consistently per implementation policy

Recommended canonical payload example before hashing:

```json
{"operation":"open_pull_request","request_id":"req_open_pr_01","title":"Add Forge interface contracts"}
```

Then:

```text
payload_hash = "sha256:<hex of canonical-json-bytes>"
```

---

## 13. Wire Format Examples

## 13.1 TrustFlow Event Example

```json
{
  "message_type": "event",
  "schema_version": "1.0",
  "message_id": "msg_tf_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515210002,
  "source": "trustflow",
  "destination": "shell",
  "payload": {
    "event_id": "tf_01HV...",
    "session_id": "sess_01HV...",
    "ctx_id": "ctx_01HV...",
    "ts": 1742515210002,
    "event_type": "action_allowed",
    "payload_hash": "sha256:9f2c4d...",
    "component": "github",
    "operation": "create_pull_request"
  }
}
```

## 13.2 VTZ Denial Example

```json
{
  "message_type": "event",
  "schema_version": "1.0",
  "message_id": "msg_vtz_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515210001,
  "source": "security",
  "destination": "audit",
  "payload": {
    "decision_id": "vtzdec_01HV...",
    "session_id": "sess_01HV...",
    "ctx_id": "ctx_01HV...",
    "vtz_id": "vtz_local_default",
    "operation": "github.create_pull_request",
    "resource": "repo:owner/name",
    "verdict": "block",
    "policy_id": "vtz_policy_default_v12",
    "reason_code": "CROSS_VTZ_DENIED",
    "evaluated_at": 1742515210001
  }
}
```

## 13.3 Audit Record Example

```json
{
  "message_type": "event",
  "schema_version": "1.0",
  "message_id": "msg_aud_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_01HV...",
  "ts": 1742515210000,
  "source": "audit",
  "destination": "shell",
  "payload": {
    "audit_id": "aud_01HV...",
    "ts": 1742515210000,
    "component": "github",
    "operation": "create_pull_request",
    "phase": "pre_execution",
    "session_id": "sess_01HV...",
    "ctx_id": "ctx_01HV...",
    "severity": "INFO",
    "outcome": "pending",
    "failure_reason": null,
    "details_hash": "sha256:4ab1..."
  }
}
```

## 13.4 Invalid CTX-ID Error Example

```json
{
  "message_type": "error",
  "schema_version": "1.0",
  "message_id": "msg_err_ctx_001",
  "session_id": "sess_01HV...",
  "ctx_id": "ctx_bad",
  "ts": 1742515209999,
  "source": "backend",
  "destination": "shell",
  "payload": {
    "request_id": "req_plan_01",
    "operation": "create_plan",
    "status": "error",
    "error": {
      "code": "CTX_ID_SIGNATURE_INVALID",
      "component": "security",
      "operation": "validate_ctx_id",
      "failure_reason": "trustlock_signature_verification_failed",
      "retryable": false
    }
  }
}
```

## 13.5 End-to-End Operation Sequence Example

### 1. Intent request

```json
{"message_type":"request","schema_version":"1.0","message_id":"m1","session_id":"sess_1","ctx_id":"ctx_1","ts":1742515220000,"source":"shell","destination":"backend","payload":{"request_id":"req1","operation":"submit_intent","intent_id":"intent_1","repository_id":"repo_1","text":"Build feature X","spec_refs":["spec_trd_1"]}}
```

### 2. Pre-execution audit event

```json
{"message_type":"event","schema_version":"1.0","message_id":"m2","session_id":"sess_1","ctx_id":"ctx_1","ts":1742515220001,"source":"audit","destination":"shell","payload":{"audit_id":"aud_1","ts":1742515220001,"component":"planner","operation":"submit_intent","phase":"pre_execution","session_id":"sess_1","ctx_id":"ctx_1","severity":"INFO","outcome":"pending","failure_reason":null,"details_hash":"sha256:aaa..."}} 
```

### 3. TrustFlow allow event

```json
{"message_type":"event","schema_version":"1.0","message_id":"m3","session_id":"sess_1","ctx_id":"ctx_1","ts":1742515220002,"source":"trustflow","destination":"shell","payload":{"event_id":"tf_1","session_id":"sess_1","ctx_id":"ctx_1","ts":1742515220002,"event_type":"action_allowed","payload_hash":"sha256:bbb...","component":"planner","operation":"submit_intent"}}
```

### 4. Success response

```json
{"message_type":"response","schema_version":"1.0","message_id":"m4","session_id":"sess_1","ctx_id":"ctx_1","ts":1742515220100,"source":"backend","destination":"shell","payload":{"request_id":"req1","operation":"submit_intent","status":"ok","intent_id":"intent_1"}}
```

---

## 14. Subsystem Compliance Matrix

| Subsystem | Must validate CTX-ID first | Must enforce VTZ | Must emit TrustFlow | Must pre-audit | Must fail closed |
|---|---:|---:|---:|---:|---:|
| Shell | yes | yes | yes | yes | yes |
| Backend | yes | yes | yes | yes | yes |
| Auth | yes | yes | yes | yes | yes |
| Security | yes | yes | yes | yes | yes |
| Planner | yes | yes | yes | yes | yes |
| Consensus | yes | yes | yes | yes | yes |
| Provider Adapter | yes | yes | yes | yes | yes |
| Review | yes | yes | yes | yes | yes |
| CI | yes | yes | yes | yes | yes |
| GitHub | yes | yes | yes | yes | yes |
| Docs | yes | yes | yes | yes | yes |
| Audit | n/a | policy-bound | self-emits | append-only | yes |

---

## 15. Non-Conformance Conditions

A component is non-conformant if it does any of the following:

- processes agent actions before CTX-ID validation
- permits partial execution after CTX-ID failure
- evaluates VTZ after execution
- skips VTZ decision record on denial
- omits TrustFlow emission
- buffers TrustFlow asynchronously in enforcement path
- suppresses TrustFlow emission failure
- mutates CTX-ID fields after issuance
- allows expired or unverifiable CTX-ID
- permits cross-VTZ access implicitly
- mutates DTL labels after ingestion
- treats unlabeled data as less than `CONFIDENTIAL`
- swallows enforcement exceptions
- logs secrets or cleartext sensitive payloads in errors
- writes security action audit records only after execution
- mutates or deletes append-only audit history

---

## 16. Implementation Notes

These notes are informative, but aligned to the mandatory contracts:

- The shell should be considered the trusted local front-end and secret owner.
- The backend should consume scoped credentials or references, not act as a general secret vault.
- Since the wire protocol is LDJSON, large artifacts should be passed by reference where possible:
  - path refs
  - artifact ids
  - content hashes
- Long-running operations should emit progress `event` frames instead of blocking until completion.
- Stable hashing requires canonical serialization across Swift and Python implementations.

---

## 17. Minimum Required Operations

The following operations are the minimum interoperable set implied by the provided platform description:

```text
health_check
authenticate
lock_session
unlock_session
terminate_session
ingest_specs
submit_intent
create_plan
list_pr_units
start_pr_unit
run_consensus
run_review_cycle
run_ci
open_pull_request
poll_pull_request
approve_and_continue
cancel_operation
regenerate_docs
```

Each MUST use the common envelope and MUST honor all security contracts in this document.

---

## 18. Versioning

- Current interface schema version: `1.0`
- Backward-incompatible changes MUST increment major version
- New optional fields MAY be added in minor revisions if receivers are defined to ignore unknown optional fields
- Security-critical field changes SHOULD be treated as major changes
- Canonical hash inputs MUST be version-stable within a major version

---

## 19. Summary

This document defines the authoritative interface contract for Forge platform interoperability:

- line-delimited JSON over authenticated Unix socket
- strict common envelope
- mandatory CTX-ID → audit → VTZ → TrustFlow → execution flow
- append-only audit semantics
- immutable identity and data labels
- typed subsystem payloads
- explicit error wire format
- fail-closed enforcement everywhere

Any implementation that diverges from these contracts is non-conformant.