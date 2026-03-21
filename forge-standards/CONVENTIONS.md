# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and code patterns for the full Forge platform. It applies across all repositories and subsystems unless a subsystem TRD explicitly overrides a convention.

The TRDs in `forge-docs/` are the source of truth. This document standardizes implementation style so code remains consistent with those specifications.

---

## Core Principles

1. **TRDs are authoritative**
   - Before changing code, identify the owning TRD.
   - Do not invent interfaces, state transitions, security behavior, or error semantics.
   - If a convention here conflicts with a TRD, follow the TRD.

2. **Security-first implementation**
   - Treat all external input as untrusted.
   - Never execute generated code.
   - Respect trust boundaries between Swift shell and Python backend.
   - Any credential, auth, policy, execution, CI, replay, or machine identity change must be reviewed against TRD-11.

3. **Clear ownership by subsystem**
   - Code must make subsystem ownership obvious from path, type name, and module usage.
   - Cross-subsystem dependencies must be explicit and minimal.

4. **Deterministic, testable behavior**
   - Prefer pure functions and explicit state transitions.
   - Avoid hidden global state.
   - Make side effects visible at module boundaries.

5. **Consistent naming over cleverness**
   - Use descriptive names.
   - Avoid abbreviations unless they are official subsystem names from the platform.

---

## File and Directory Naming (exact `src/` layout)

The Forge platform uses the following top-level source layout:

```text
src/
  cal/         # Conversation Abstraction Layer
  dtl/         # Data Trust Label
  trustflow/   # TrustFlow audit stream
  vtz/         # Virtual Trust Zone
  trustlock/   # Cryptographic machine identity
  mcp/         # MCP Policy Engine
  rewind/      # Forge Rewind replay engine

sdk/
  connector/   # Forge Connector SDK

tests/
  <subsystem>/ # Mirrors src/ structure exactly
```

### Directory Rules

- Directory names are lowercase.
- Use singular subsystem names exactly as defined:
  - `cal`
  - `dtl`
  - `trustflow`
  - `vtz`
  - `trustlock`
  - `mcp`
  - `rewind`
  - `connector` under `sdk/`
- Do not create alternate aliases such as:
  - `conversation_layer`
  - `data_trust_labels`
  - `audit`
  - `zone`
  - `identity`
- Tests must mirror source structure exactly.

### Nested Directory Naming

Use lowercase snake_case for internal directories:

```text
src/mcp/policy_engine/
src/trustflow/event_stream/
src/rewind/replay_store/
```

Use directories to reflect one of:
- domain
- protocol/interface
- storage
- transport
- policy
- adapters/integrations
- models
- services

Preferred examples:

```text
src/cal/session/
src/cal/providers/
src/dtl/labels/
src/dtl/validation/
src/trustflow/events/
src/trustflow/sinks/
src/vtz/enforcement/
src/vtz/boundaries/
src/trustlock/identity/
src/trustlock/attestation/
src/mcp/policies/
src/mcp/evaluation/
src/rewind/replay/
src/rewind/snapshots/
sdk/connector/client/
sdk/connector/auth/
```

Avoid generic folders like:
- `misc`
- `helpers`
- `common`
- `stuff`
- `utils`

If shared code is necessary, name it by responsibility:
- `serialization`
- `validation`
- `formatting`
- `adapters`
- `contracts`

### File Naming

#### Python
- Use `snake_case.py`
- File names should reflect the primary type or capability in the file.

Examples:
- `policy_evaluator.py`
- `trust_label_parser.py`
- `audit_event_sink.py`
- `replay_coordinator.py`

#### Swift
- Use `PascalCase.swift`
- File name must match the primary type.

Examples:
- `PolicyEvaluator.swift`
- `TrustLabelParser.swift`
- `AuditEventSink.swift`

#### Test Files
- Python tests:
  - `test_<unit>.py`
- Swift tests:
  - `<Unit>Tests.swift`

Examples:
- `tests/mcp/test_policy_evaluator.py`
- `tests/dtl/test_trust_label_parser.py`
- `MCPPolicyEvaluatorTests.swift`

---

## Class and Function Naming

Naming must reflect responsibility, subsystem, and abstraction level.

### General Rules

- **Classes / structs / enums / protocols / actors:** `PascalCase`
- **Functions / methods / variables:** `camelCase` in Swift, `snake_case` in Python
- **Constants:** `UPPER_SNAKE_CASE` in Python, `lowerCamelCase` or `static let` in Swift per language conventions
- **Private helpers:** name by behavior, not by visibility prefix
- Do not use Hungarian notation.
- Do not encode type names in variable names unless needed for clarity.

### Allowed Acronyms

Use official subsystem acronyms exactly:
- `CAL`
- `DTL`
- `MCP`
- `VTZ`

For mixed-case language identifiers:
- Swift type names: `CALSession`, `DTLLabel`, `MCPPolicy`, `VTZBoundary`
- Python class names: `CALSession`, `DTLLabel`, `MCPPolicy`, `VTZBoundary`
- Python functions/modules: `cal_session`, `dtl_label`, `mcp_policy`, `vtz_boundary`

Use `TrustFlow`, `TrustLock`, and `Rewind` as words, not all-caps acronyms.

### Type Naming Patterns

Use suffixes only when they communicate role clearly.

Preferred suffixes:
- `Manager` — lifecycle orchestration, only if it truly manages multiple resources
- `Coordinator` — workflow coordination across components
- `Service` — external-facing service layer
- `Client` — outbound integration/API consumer
- `Adapter` — translation between interfaces
- `Provider` — pluggable backend/provider
- `Repository` — persistence abstraction
- `Store` — lower-level storage implementation
- `Parser` — parsing external or serialized input
- `Validator` — rule checking without side effects
- `Evaluator` — policy or decision logic
- `Resolver` — identifier or dependency resolution
- `Factory` — object construction with nontrivial assembly
- `Builder` — staged object construction
- `Encoder` / `Decoder` — serialization transforms
- `Serializer` / `Deserializer` — format mapping
- `Recorder` — append-only event recording
- `Replayer` — deterministic replay engine
- `Attestor` — attestation generation/verification
- `Enforcer` — policy or boundary enforcement

Avoid weak suffixes:
- `Helper`
- `Util`
- `Base`
- `Impl`
- `Thing`

### Function Naming Patterns

Function names should start with a verb and imply result/side effects.

Preferred verbs:
- `load`
- `save`
- `fetch`
- `create`
- `build`
- `parse`
- `validate`
- `evaluate`
- `enforce`
- `record`
- `replay`
- `issue`
- `verify`
- `attest`
- `authorize`
- `reject`
- `serialize`
- `deserialize`
- `transform`

Boolean-returning functions should read as predicates:
- `is_valid`
- `has_boundary_violation`
- `can_replay`
- `should_redact`

Swift:
- `isValid`
- `hasBoundaryViolation`
- `canReplay`
- `shouldRedact`

### Interface Naming

Protocols and abstract interfaces should be nouns or capability nouns.

Examples:
- `PolicyEvaluator`
- `AuditEventSink`
- `TrustLabelValidator`
- `ReplayStore`
- `MachineAttestor`

Do not prefix interfaces with `I`.

Bad:
- `IPolicyEvaluator`

Good:
- `PolicyEvaluator`

---

## Error and Exception Patterns

Errors must be explicit, typed, and stable. They form part of the contract.

### General Rules

- Never swallow exceptions silently.
- Never use bare `except:` in Python.
- Never use catch-all error handling unless it logs context and re-raises or maps to a typed domain error.
- Map low-level errors into subsystem-level errors at boundaries.
- Error messages must be actionable and safe for logs.
- Do not leak secrets, credentials, tokens, raw prompts, or sensitive payloads in error messages.

### Python Error Conventions

#### Base Pattern

Each subsystem defines a base exception:

```python
class MCPError(Exception):
    """Base exception for MCP subsystem."""
```

Derived exceptions use `PascalCase` and end in `Error` unless they represent a rejection or violation, in which case `Violation` or `Rejected` may be used if specified by TRD.

Examples:
- `PolicyEvaluationError`
- `PolicyParseError`
- `PolicyViolation`
- `TrustLabelValidationError`
- `AuditStreamWriteError`
- `ReplayIntegrityError`
- `AttestationVerificationError`

#### Python Error Structure

Custom exceptions should support:
- stable message
- optional machine-readable code
- optional wrapped cause
- relevant non-sensitive context

Example pattern:

```python
class PolicyViolation(MCPError):
    def __init__(self, message: str, code: str = "policy_violation", context: dict | None = None):
        super().__init__(message)
        self.code = code
        self.context = context or {}
```

#### Raising Rules

- Raise domain-specific errors from domain modules.
- Raise `ValueError` or `TypeError` only for internal programmer misuse, not user/domain contract failures.
- Use exception chaining:

```python
try:
    policy = parse_policy(raw)
except JsonError as exc:
    raise PolicyParseError("Failed to parse MCP policy") from exc
```

### Swift Error Conventions

- Prefer typed `Error` enums.
- Use `LocalizedError` when user-presentable text is needed.
- Use structured associated values for context, but do not attach secrets.

Example:

```swift
enum MCPPolicyError: Error {
    case parseFailed(reason: String)
    case evaluationFailed(policyId: String)
    case violation(ruleId: String)
}
```

### Error Naming Rules

Use these suffixes consistently:
- `Error` — operational or contract failure
- `Violation` — policy or trust boundary violation
- `Rejected` — explicit deny/reject outcome
- `Timeout` only when it is semantically distinct and handled separately

Examples:
- `ConnectorAuthenticationError`
- `VTZBoundaryViolation`
- `ReplayRequestRejected`
- `TrustFlowFlushTimeout`

### Logging and Errors

When logging errors:
- include operation name
- include subsystem
- include correlation/request/event ID when available
- include sanitized context
- do not include secrets or raw sensitive payloads

Preferred format fields:
- `subsystem`
- `operation`
- `error_code`
- `resource_id`
- `request_id`
- `event_id`

---

## Per-Subsystem Naming Rules

---

### `src/cal/` — Conversation Abstraction Layer

Purpose: conversation/session abstraction, provider interaction, prompt/message normalization, and consensus-facing conversation state.

#### Naming Prefixes and Terms
Use:
- `CALSession`
- `CALMessage`
- `CALTurn`
- `CALProvider`
- `CALTranscript`
- `CALContext`

Do not shorten to:
- `Conv`
- `Chat`
- `Msg`
unless the TRD explicitly names a protocol that way.

#### Recommended Type Names
- `CALSessionCoordinator`
- `CALProviderAdapter`
- `CALTranscriptStore`
- `CALMessageNormalizer`
- `CALContextBuilder`

#### Function Names
- `create_session` / `createSession`
- `append_message` / `appendMessage`
- `normalize_message` / `normalizeMessage`
- `build_context` / `buildContext`
- `load_transcript` / `loadTranscript`

#### Event/Model Names
- `ConversationStarted`
- `TurnAppended`
- `TranscriptPersisted`

Use `Turn` for one interaction unit, `Message` for a single message object, and `Transcript` for persisted ordered history.

---

### `src/dtl/` — Data Trust Label

Purpose: labeling, classification, propagation, validation, and trust-aware handling of data.

#### Naming Prefixes and Terms
Use:
- `DTLLabel`
- `DTLClassification`
- `DTLPolicy`
- `DTLPropagationRule`
- `DTLValidator`

Do not use ambiguous names like:
- `Tag`
- `Marker`
- `Flag`
when the concept is a trust label.

#### Recommended Type Names
- `DTLLabelParser`
- `DTLLabelValidator`
- `DTLClassificationResolver`
- `DTLPropagationEvaluator`
- `DTLRedactionPolicy`

#### Function Names
- `parse_label` / `parseLabel`
- `validate_label` / `validateLabel`
- `classify_data` / `classifyData`
- `propagate_label` / `propagateLabel`
- `redact_content` / `redactContent`

#### Data Model Rules
- Use `classification` for trust level/category.
- Use `label` for the attached trust artifact.
- Use `source_of_truth` or `sourceOfTruth` for originating authority.
- Use `redaction_reason` / `redactionReason` for redaction metadata.

---

### `src/trustflow/` — TrustFlow audit stream

Purpose: append-only audit/event stream, trust decisions, policy actions, and compliance-visible traceability.

#### Naming Prefixes and Terms
Use:
- `TrustFlowEvent`
- `TrustFlowRecord`
- `TrustFlowStream`
- `TrustFlowSink`
- `TrustFlowEnvelope`

Do not collapse to generic:
- `AuditItem`
- `LogEntry`
- `Record`
without subsystem context.

#### Recommended Type Names
- `TrustFlowEventRecorder`
- `TrustFlowStreamWriter`
- `TrustFlowEnvelopeEncoder`
- `TrustFlowSinkClient`
- `TrustFlowRetentionPolicy`

#### Function Names
- `record_event` / `recordEvent`
- `append_record` / `appendRecord`
- `flush_stream` / `flushStream`
- `encode_envelope` / `encodeEnvelope`
- `verify_chain` / `verifyChain`

#### Event Naming Rules
Events should be past-tense, domain-specific, and immutable in meaning.

Examples:
- `PolicyEvaluated`
- `BoundaryViolationDetected`
- `ReplayStarted`
- `ReplayCompleted`
- `AttestationVerified`

Use stable event names once introduced. Do not rename historical event types casually.

---

### `src/vtz/` — Virtual Trust Zone

Purpose: trust boundary enforcement, isolation rules, ingress/egress control, and protected execution constraints.

#### Naming Prefixes and Terms
Use:
- `VTZBoundary`
- `VTZPolicy`
- `VTZEnforcer`
- `VTZIngressRule`
- `VTZEgressRule`

Do not use:
- `Sandbox` unless the TRD explicitly means OS sandboxing
- `ZoneGuard` unless defined by spec

#### Recommended Type Names
- `VTZBoundaryEnforcer`
- `VTZIngressValidator`
- `VTZEgressValidator`
- `VTZIsolationPolicy`
- `VTZAccessDecision`

#### Function Names
- `enforce_boundary` / `enforceBoundary`
- `validate_ingress` / `validateIngress`
- `validate_egress` / `validateEgress`
- `reject_transfer` / `rejectTransfer`
- `authorize_transfer` / `authorizeTransfer`

#### Outcome Naming
Use:
- `allowed`
- `rejected`
- `violated`
- `requires_redaction`

Avoid vague states like:
- `bad`
- `unsafe`
- `maybe_ok`

---

### `src/trustlock/` — Cryptographic machine identity

Purpose: machine identity, attestation, TPM/hardware-rooted trust, key material references, and verification flows.

#### Naming Prefixes and Terms
Use:
- `TrustLockIdentity`
- `TrustLockAttestation`
- `TrustLockKeyHandle`
- `TrustLockVerifier`
- `TrustLockIssuer`

Do not use:
- `MachineKey` for higher-level identity artifacts if the spec defines them as TrustLock identities or attestations.

#### Recommended Type Names
- `TrustLockAttestor`
- `TrustLockAttestationVerifier`
- `TrustLockIdentityStore`
- `TrustLockKeyResolver`
- `TrustLockCertificateChainValidator`

#### Function Names
- `issue_attestation` / `issueAttestation`
- `verify_attestation` / `verifyAttestation`
- `resolve_key_handle` / `resolveKeyHandle`
- `load_identity` / `loadIdentity`
- `validate_certificate_chain` / `validateCertificateChain`

#### Data Naming
- `key_handle` / `keyHandle` for indirect key references
- `attestation_document` / `attestationDocument`
- `identity_claims` / `identityClaims`
- `verification_result` / `verificationResult`

Never imply raw key extraction if the design uses handles/references.

---

### `src/mcp/` — MCP Policy Engine

Purpose: policy definition, parsing, evaluation, decisioning, and enforcement integration.

#### Naming Prefixes and Terms
Use:
- `MCPPolicy`
- `MCPRule`
- `MCPDecision`
- `MCPEvaluator`
- `MCPPolicySet`

Do not use generic names like:
- `RuleEngine`
- `PolicyThing`
without MCP qualification in shared or boundary code.

#### Recommended Type Names
- `MCPPolicyParser`
- `MCPPolicyEvaluator`
- `MCPDecisionResolver`
- `MCPRuleMatcher`
- `MCPPolicyRepository`

#### Function Names
- `parse_policy` / `parsePolicy`
- `evaluate_policy` / `evaluatePolicy`
- `resolve_decision` / `resolveDecision`
- `match_rule` / `matchRule`
- `load_policy_set` / `loadPolicySet`

#### Decision Naming
Decision enums or values should use explicit outcomes:
- `allow`
- `deny`
- `redact`
- `escalate`

Avoid:
- `pass`
- `fail`
- `ok`

---

### `src/rewind/` — Forge Rewind replay engine

Purpose: deterministic replay, audit reconstruction, time-ordered event recovery, and historical verification.

#### Naming Prefixes and Terms
Use:
- `RewindReplay`
- `RewindSnapshot`
- `RewindCursor`
- `RewindEventSource`
- `RewindIntegrityVerifier`

Do not use:
- `Playback` unless explicitly defined by the TRD
- `HistoryThing`

#### Recommended Type Names
- `RewindReplayCoordinator`
- `RewindSnapshotStore`
- `RewindCursorEncoder`
- `RewindIntegrityVerifier`
- `RewindEventReplayer`

#### Function Names
- `start_replay` / `startReplay`
- `resume_replay` / `resumeReplay`
- `load_snapshot` / `loadSnapshot`
- `advance_cursor` / `advanceCursor`
- `verify_replay_integrity` / `verifyReplayIntegrity`

#### State Naming
Use explicit replay states:
- `not_started`
- `running`
- `paused`
- `completed`
- `failed`

Swift:
- `notStarted`
- `running`
- `paused`
- `completed`
- `failed`

---

### `sdk/connector/` — Forge Connector SDK

Purpose: external integration SDK for connectors into the Forge platform.

#### Naming Prefixes and Terms
Use:
- `ConnectorClient`
- `ConnectorSession`
- `ConnectorAuthProvider`
- `ConnectorRequest`
- `ConnectorResponse`

Use `ForgeConnector` when qualification is needed outside the SDK boundary.

#### Recommended Type Names
- `ConnectorAPIClient`
- `ConnectorSessionManager`
- `ConnectorCredentialProvider`
- `ConnectorRequestSigner`
- `ConnectorWebhookVerifier`

#### Function Names
- `create_session` / `createSession`
- `sign_request` / `signRequest`
- `send_request` / `sendRequest`
- `verify_webhook` / `verifyWebhook`
- `refresh_credentials` / `refreshCredentials`

#### SDK Design Rules
- Public API names must be stable and explicit.
- Avoid leaking internal subsystem names into connector-facing APIs unless they are part of the formal contract.
- Public types require docstrings/documentation comments.

---

## Cross-Subsystem Naming Rules

### Boundary Types Must Be Qualified

If a type crosses subsystem boundaries, qualify it with the subsystem name.

Good:
- `MCPDecision`
- `DTLLabel`
- `TrustFlowEvent`

Bad:
- `Decision`
- `Label`
- `Event`

### Avoid Generic Shared Models

Do not create broad shared types such as:
- `Context`
- `Payload`
- `Data`
- `Result`
unless they are narrowly scoped or namespace-qualified.

Prefer:
- `CALContext`
- `ConnectorRequestPayload`
- `ReplayResult`
- `TrustFlowEventEnvelope`

### Adapter Naming

For bridges between subsystems, use both names in the adapter.

Examples:
- `MCPToVTZDecisionAdapter`
- `DTLToTrustFlowRecordAdapter`
- `CALToConnectorRequestTransformer`

### Serialization Naming

For format-specific components:
- `<Type>Encoder`
- `<Type>Decoder`
- `<Type>Serializer`
- `<Type>Deserializer`

Include format only when needed:
- `TrustFlowEventJsonEncoder`
- `MCPPolicyYamlParser`

---

## Code Patterns

### Prefer Explicit Domain Models

Use explicit models over unstructured dictionaries/maps at internal boundaries.

Bad:
```python
decision = {"ok": True, "rule": "R-1"}
```

Good:
```python
@dataclass
class MCPDecision:
    outcome: str
    rule_id: str
```

### Separate Parsing, Validation, and Evaluation

Do not combine multiple responsibilities in one function when they are conceptually distinct.

Preferred flow:
1. parse
2. validate
3. evaluate/enforce
4. record

Bad:
```python
def process_policy(raw):
    ...
```

Good:
```python
policy = parse_policy(raw)
validate_policy(policy)
decision = evaluate_policy(policy, request)
record_event(decision_event)
```

### Boundary Mapping

At external boundaries, map:
- transport types -> domain types
- domain errors -> boundary-safe errors
- internal events -> audit events

### Immutable Event Models

Audit and replay events should be immutable after creation wherever language/runtime supports it.

### One Primary Responsibility per File

A file should contain one primary type or closely related type group.
If a file contains multiple unrelated classes, split it.

---

## Testing Conventions

### Test Layout

Tests mirror source structure exactly.

Examples:

```text
src/mcp/policy_evaluator.py
tests/mcp/test_policy_evaluator.py

src/rewind/replay/replay_coordinator.py
tests/rewind/replay/test_replay_coordinator.py
```

### Test Naming

#### Python
- Test files: `test_<unit>.py`
- Test functions: `test_<behavior>_<expected_outcome>()`

Examples:
- `test_evaluate_policy_denies_untrusted_input`
- `test_verify_attestation_rejects_invalid_chain`

#### Swift
- Test methods:
  - `test<Behavior><ExpectedOutcome>()`

Examples:
- `testEvaluatePolicyDeniesUntrustedInput`
- `testVerifyAttestationRejectsInvalidChain`

### Test Requirements

- Test success paths and failure paths.
- Test policy violations explicitly.
- Test replay determinism.
- Test serialization compatibility for persisted or wire-visible models.
- Test redaction/sanitization behavior for logs and audit output.
- Add regression tests for every bug fix.

---

## Documentation Conventions

- Public types and functions in SDKs and external boundary modules require documentation comments.
- Document:
  - purpose
  - inputs
  - outputs
  - error conditions
  - security-sensitive behavior where relevant
- Keep examples aligned with actual API names.

---

## Prohibited Patterns

Do not introduce:
- unnamed magic values for trust/policy decisions
- generic `utils` dumping grounds
- silent fallback behavior for policy enforcement
- exception swallowing
- mutable global policy state
- ambiguous names like `Manager` when role is evaluator/parser/validator
- raw secret/token logging
- non-mirrored test layouts
- subsystem alias names that differ from the canonical directory names

---

## Naming Examples

### Good

- `MCPPolicyEvaluator`
- `DTLLabelValidator`
- `TrustFlowEventRecorder`
- `VTZBoundaryEnforcer`
- `TrustLockAttestationVerifier`
- `RewindReplayCoordinator`
- `ConnectorRequestSigner`

### Bad

- `Engine`
- `Helper`
- `Utils`
- `DataManager`
- `PolicyThing`
- `ReplayStuff`
- `AuditHelper`

---

## Final Rules for Contributors and Agents

Before submitting a change:

1. Confirm the file path matches the canonical subsystem layout.
2. Confirm names use the subsystem vocabulary defined above.
3. Confirm errors are typed and sanitized.
4. Confirm tests mirror source structure exactly.
5. Confirm the implementation matches the owning TRD.
6. Confirm security-relevant changes have been checked against TRD-11.

If unsure, prefer the name and structure that is:
- more explicit
- more local to the subsystem
- easier to test
- easier to audit
- closer to TRD terminology