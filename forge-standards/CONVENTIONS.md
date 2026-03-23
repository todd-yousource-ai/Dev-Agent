# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and required code patterns for the full Forge platform.

Forge is specified by TRDs. These conventions are subordinate to the TRDs and exist to make implementation consistent across all subsystems.

## Authority and Scope

- TRDs in `forge-docs/` are the source of truth.
- `TRD-11` governs security-sensitive implementation and must be consulted for:
  - credentials
  - external content
  - generated code
  - CI
  - trust boundaries
  - policy enforcement
- Code must not invent interfaces, states, or error contracts not supported by the owning TRD.
- Tests must mirror subsystem structure and validate published contracts, not incidental implementation.

---

## General Repository Rules

- The platform is split into two major process domains:
  - **Swift shell**: UI, auth, Keychain, XPC, macOS integration
  - **Python backend**: orchestration, consensus, planning, generation, GitHub operations, policy/runtime services where defined by TRD
- Inter-process communication must use authenticated transport as defined by the relevant TRD.
- Generated code must never be executed unless a TRD explicitly permits a specific controlled action.
- All externally sourced content is untrusted by default.
- Prefer explicit contracts over inferred behavior.
- Prefer deterministic behavior over convenience.
- Prefer narrow interfaces over shared mutable state.

---

## File and Directory Naming (exact `src/` layout)

Use the exact directory names below for subsystem-owned code.

```text
src/
  cal/           Conversation Abstraction Layer components
  dtl/           Data Trust Label components
  trustflow/     TrustFlow audit stream components
  vtz/           Virtual Trust Zone enforcement
  trustlock/     Cryptographic machine identity (TPM-anchored)
  mcp/           MCP Policy Engine
  rewind/        Forge Rewind replay engine

sdk/
  connector/     Forge Connector SDK

tests/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
```

### Directory Rules

- Tests must mirror `src/` structure exactly.
- One subsystem must not place implementation files in another subsystem’s directory.
- Shared code must live only in an explicitly designated shared/common package approved by TRD; otherwise keep logic local to the subsystem.
- Avoid “misc”, “helpers”, “utils”, “common”, or “temp” directories unless the owning TRD explicitly defines them.

### File Naming Rules

Use lowercase snake case for Python files:

```text
policy_engine.py
trust_label_resolver.py
audit_stream_writer.py
replay_session_store.py
```

Use descriptive names based on primary responsibility, not generic verbs:

- Good:
  - `consent_gate.py`
  - `zone_boundary_validator.py`
  - `machine_attestation_service.py`
- Bad:
  - `manager.py`
  - `helpers.py`
  - `stuff.py`
  - `misc.py`

### File Suffix Patterns

Use suffixes consistently when they express a stable role:

- `_model.py` — domain models
- `_service.py` — orchestration/service logic
- `_client.py` — external system client
- `_adapter.py` — provider or boundary adaptation
- `_validator.py` — invariant or schema validation
- `_policy.py` — policy definitions/evaluation
- `_store.py` — persistence access
- `_repo.py` or `_repository.py` — repository abstraction, if TRD uses repository pattern
- `_engine.py` — deterministic evaluation/processing engine
- `_runner.py` — controlled execution coordinator
- `_parser.py` — parsing logic
- `_serializer.py` — canonical serialization logic

Use one suffix only where possible.

---

## Class and Function Naming

### Python Naming

Follow PEP 8 unless a TRD requires otherwise.

- Classes: `PascalCase`
- Functions: `snake_case`
- Methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Modules/files: `snake_case`
- Private/internal members: leading underscore
- Type aliases: `PascalCase`
- Enum classes: `PascalCase`
- Enum values: `UPPER_SNAKE_CASE`

Examples:

```python
class TrustLabelResolver:
    def resolve_label(self, artifact_id: str) -> TrustLabel:
        ...

DEFAULT_REPLAY_WINDOW_SECONDS = 300
```

### Swift Naming

Follow Swift API Design Guidelines.

- Types: `PascalCase`
- Functions/methods/properties: `camelCase`
- Enum cases: `camelCase`
- Static constants: `camelCase` unless bridged from C
- Protocols: noun or capability-based adjective, e.g. `PolicyEvaluating`, `AttestationProviding`
- Avoid `I` prefixes for protocols

Examples:

```swift
final class TrustFlowStreamClient {
    func append(event: AuditEvent) async throws { }
}

protocol PolicyEvaluating {
    func evaluate(_ request: PolicyRequest) throws -> PolicyDecision
}
```

### Naming by Responsibility

Prefer names that describe domain responsibility exactly.

- Good:
  - `PolicyDecision`
  - `ReplayCursor`
  - `TrustZoneBoundary`
  - `ConversationTurnNormalizer`
- Bad:
  - `DataObject`
  - `Manager`
  - `Processor`
  - `Handler`

Use `Manager` only if the owning TRD explicitly defines a manager abstraction.

### Verb Rules

- Use `get_` only when required to distinguish from a property or protocol requirement.
- Prefer:
  - `load`
  - `resolve`
  - `build`
  - `parse`
  - `validate`
  - `evaluate`
  - `append`
  - `replay`
  - `attest`
  - `issue`
  - `verify`
- Avoid vague verbs:
  - `handle`
  - `process`
  - `do`
  - `run` unless it truly coordinates execution
  - `manage`

### Boolean Naming

Name booleans as predicates.

- Good:
  - `is_trusted`
  - `has_attestation`
  - `can_replay`
  - `requires_consent`
- Bad:
  - `trust`
  - `attestation`
  - `replay_flag`

---

## Error and Exception Patterns

Errors are part of the contract. They must be typed, explicit, and mappable to TRD-defined failure modes.

### Core Rules

- Never swallow exceptions silently.
- Never use broad catch-and-ignore patterns.
- Never return `None`/null to represent a meaningful failure when a typed error is expected.
- Do not expose raw provider, transport, or cryptographic exceptions directly across subsystem boundaries.
- Wrap low-level failures in subsystem-defined errors with preserved cause/context.
- Error messages must be actionable but must not leak secrets or sensitive internal state.

### Python Error Pattern

Define subsystem-scoped base exceptions.

```python
class TrustFlowError(Exception):
    """Base exception for TrustFlow subsystem."""
```

Then define specific errors:

```python
class AuditStreamWriteError(TrustFlowError):
    pass

class AuditEventValidationError(TrustFlowError):
    pass
```

Rules:

- One base exception per subsystem or bounded domain.
- Specific exceptions should encode failure category, not incidental implementation detail.
- Include stable machine-readable fields when required by TRD.
- Preserve original cause via `raise ... from exc`.

Example:

```python
try:
    payload = serializer.serialize(event)
except ValueError as exc:
    raise AuditEventValidationError("Invalid audit event payload") from exc
```

### Swift Error Pattern

Use typed `enum` errors conforming to `Error`.

```swift
enum PolicyEngineError: Error {
    case invalidRequest(String)
    case decisionConflict
    case backendUnavailable
}
```

Rules:

- Prefer enums for finite failure sets.
- Use associated values for safe context.
- Do not include secrets, tokens, raw credentials, or unredacted external payloads.
- Convert transport/library errors at subsystem boundaries.

### Logging and Error Separation

- Logs may contain structured diagnostic metadata if allowed by TRD and security policy.
- User-facing errors must be redacted and stable.
- Internal errors should separate:
  - failure category
  - correlation identifier
  - redacted context
  - root cause chain

### Required Failure Handling Pattern

When crossing a subsystem boundary:

1. Validate inputs.
2. Convert external/library failures into local typed errors.
3. Attach correlation or operation ID where required.
4. Emit audit/log records according to TrustFlow/TRD requirements.
5. Return or throw only contract-approved failures.

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation normalization, turn modeling, provider-agnostic interaction abstraction, and conversation boundary handling.

### Naming Rules

- Use `Conversation*` for top-level domain types:
  - `ConversationSession`
  - `ConversationTurn`
  - `ConversationEnvelope`
- Use `Turn*` for per-turn transforms:
  - `TurnClassifier`
  - `TurnNormalizer`
  - `TurnRedactor`
- Use `Message*` only when representing provider-format messages, not canonical CAL entities.
- Use `Envelope` for transport-safe wrapped conversation payloads.
- Use `Transcript` for ordered persisted turn history.
- Use `Adapter` for provider-specific conversation translations.

### Preferred File Names

```text
src/cal/conversation_session_model.py
src/cal/conversation_turn_model.py
src/cal/turn_normalizer.py
src/cal/transcript_store.py
src/cal/provider_message_adapter.py
src/cal/conversation_envelope_serializer.py
```

### Forbidden/Vague Names

- `chat.py`
- `prompt_handler.py`
- `message_manager.py`

---

## `src/dtl/` — Data Trust Label

Purpose: trust classification, provenance labeling, data sensitivity assignment, and trust-state derivation.

### Naming Rules

- Use `TrustLabel` for canonical labels.
- Use `Classification` for taxonomy or category definitions.
- Use `Provenance` for source lineage.
- Use `Sensitivity` for data handling class.
- Use `Resolver`, `Evaluator`, or `Deriver` for logic assigning labels.
- Use `LabelPolicy` for policy governing assignment/propagation.
- Use `LabelAssertion` for explicit declarations.
- Use `LabelEvidence` for supporting facts.

### Preferred File Names

```text
src/dtl/trust_label_model.py
src/dtl/provenance_model.py
src/dtl/sensitivity_classification.py
src/dtl/trust_label_resolver.py
src/dtl/label_policy.py
src/dtl/label_evidence_model.py
```

### Rules

- Do not use `tag` when the semantics are trust labels; use `label`.
- Do not use `metadata` for provenance if provenance is the actual concept.
- Keep taxonomy names stable and TRD-aligned.

---

## `src/trustflow/` — TrustFlow Audit Stream

Purpose: append-only audit stream, event integrity, redaction-safe observability, and traceable policy/security events.

### Naming Rules

- Use `AuditEvent` for atomic records.
- Use `AuditStream` for logical event stream abstractions.
- Use `Append` for write-path operations.
- Use `Cursor` or `Offset` for ordered read position.
- Use `Redaction` for sensitive-field masking behavior.
- Use `Integrity` for signing, hashing, chaining, or tamper-evidence operations.
- Use `Emission` only for event publication semantics if distinct from append semantics.

### Preferred File Names

```text
src/trustflow/audit_event_model.py
src/trustflow/audit_stream_writer.py
src/trustflow/audit_stream_reader.py
src/trustflow/stream_cursor_model.py
src/trustflow/redaction_policy.py
src/trustflow/integrity_chain_validator.py
```

### Rules

- Distinguish append-path names from publish/notify-path names.
- `Event` means immutable record, not callback.
- Hash chain and signature code must use explicit names:
  - `IntegrityChain`
  - `EventDigest`
  - `SignatureEnvelope`

---

## `src/vtz/` — Virtual Trust Zone

Purpose: trust boundary enforcement, zone isolation, access mediation, and controlled movement across trust zones.

### Naming Rules

- Use `TrustZone` for canonical zone entities.
- Use `Boundary` for crossing logic.
- Use `BoundaryCheck` or `BoundaryValidator` for gate decisions.
- Use `Escalation` for privilege or trust elevation flows.
- Use `IsolationPolicy` for zone separation rules.
- Use `TransferRequest` / `TransferDecision` for movement across zones.
- Use `Containment` for restrictions inside a zone.

### Preferred File Names

```text
src/vtz/trust_zone_model.py
src/vtz/zone_boundary_validator.py
src/vtz/isolation_policy.py
src/vtz/transfer_request_model.py
src/vtz/transfer_decision_model.py
src/vtz/escalation_service.py
```

### Rules

- Do not use `sandbox` unless the TRD explicitly defines a sandbox concept distinct from a trust zone.
- Use `zone` consistently; do not mix `realm`, `domain`, and `scope` unless they are distinct TRD concepts.

---

## `src/trustlock/` — Cryptographic Machine Identity

Purpose: TPM-anchored identity, attestation, machine-bound key operations, and cryptographic proof of device identity.

### Naming Rules

- Use `Attestation` for claims/proofs about machine state.
- Use `MachineIdentity` for canonical identity object.
- Use `KeyBinding` for binding keys to machine or platform state.
- Use `Seal` / `Unseal` for TPM-bound secret wrapping if TRD uses those terms.
- Use `Quote` only for TPM quote semantics.
- Use `Verifier` for cryptographic verification logic.
- Use `Evidence` for collected attestation inputs.
- Use `Challenge` / `Response` for challenge-based protocols.

### Preferred File Names

```text
src/trustlock/machine_identity_model.py
src/trustlock/attestation_service.py
src/trustlock/attestation_evidence_model.py
src/trustlock/key_binding_service.py
src/trustlock/quote_verifier.py
src/trustlock/challenge_response_protocol.py
```

### Rules

- Do not use `token` for attestation artifacts unless the TRD explicitly names them tokens.
- Do not abbreviate cryptographic concepts beyond established standards.
- Key material types must be named explicitly:
  - `PublicKey`
  - `WrappedPrivateKey`
  - `AttestationStatement`

---

## `src/mcp/` — MCP Policy Engine

Purpose: policy evaluation, request authorization, policy composition, obligations, and deterministic policy decisions.

### Naming Rules

- Use `Policy` for static rules/definitions.
- Use `PolicyRequest` and `PolicyDecision` for evaluation I/O.
- Use `Evaluator` or `Engine` for decision logic.
- Use `Obligation` for required follow-up actions attached to decisions.
- Use `Constraint` for bounded rule elements.
- Use `Subject`, `Resource`, `Action`, `Context` if the TRD defines ABAC-like structure.
- Use `DecisionTrace` for explainability/output traces when specified.

### Preferred File Names

```text
src/mcp/policy_model.py
src/mcp/policy_request_model.py
src/mcp/policy_decision_model.py
src/mcp/policy_engine.py
src/mcp/obligation_model.py
src/mcp/decision_trace_model.py
```

### Rules

- Reserve `authorize` for externally visible authorization entrypoints.
- Use `evaluate` for internal policy computation.
- Distinguish:
  - `deny` as a decision
  - `error` as a failure to decide
- Never encode a failed evaluation as an implicit deny unless the TRD explicitly requires fail-closed behavior and the interface documents it.

---

## `src/rewind/` — Forge Rewind Replay Engine

Purpose: deterministic replay, event/session reconstruction, timeline traversal, and replay validation.

### Naming Rules

- Use `Replay` for replay-domain entities.
- Use `Session` for replayable grouped execution/history units.
- Use `Timeline` for ordered temporal/event view.
- Use `Cursor` for replay position.
- Use `Checkpoint` for resumable replay state.
- Use `Reconstructor` for state rebuild logic.
- Use `Determinism` for replay consistency validation.
- Use `Artifact` for replay inputs/outputs only if the TRD uses artifact terminology.

### Preferred File Names

```text
src/rewind/replay_session_model.py
src/rewind/replay_timeline.py
src/rewind/replay_cursor_model.py
src/rewind/checkpoint_store.py
src/rewind/state_reconstructor.py
src/rewind/determinism_validator.py
```

### Rules

- Do not use `history` when the actual concept is replay timeline.
- Distinguish:
  - `replay` = deterministic re-execution/reconstruction
  - `playback` = UI or passive viewing, only if TRD defines it separately

---

## `sdk/connector/` — Forge Connector SDK

Purpose: external integration SDK, connector contracts, typed client APIs, and extension-safe interfaces.

### Naming Rules

- Use `Connector` for integration-facing primary abstractions.
- Use `Client` for API consumers.
- Use `Provider` only when a plugin supplies capability implementation.
- Use `Capability` for declared supported behavior.
- Use `Registration` for connector registration flows.
- Use `Manifest` for connector metadata/schema.
- Use `Contract` for SDK-enforced interface agreements.

### Preferred File Names

```text
sdk/connector/connector_client.py
sdk/connector/connector_manifest_model.py
sdk/connector/capability_model.py
sdk/connector/registration_service.py
sdk/connector/contract_validator.py
sdk/connector/provider_adapter.py
```

### Rules

- Public SDK names must be stable and semantically obvious.
- Avoid leaking internal subsystem terminology into SDK APIs unless intentionally exposed by TRD.
- Versioned SDK contracts must include explicit version suffixing or package versioning as defined by TRD.

---

## Model, DTO, and Schema Conventions

### Domain Models

Use `*Model` suffix only for persistence or serialization boundary types when needed. Prefer pure domain names for canonical entities.

- Preferred:
  - `TrustLabel`
  - `PolicyDecision`
  - `ReplayCursor`
- Acceptable at boundaries:
  - `TrustLabelModel`
  - `PolicyDecisionRecord`

Do not suffix every class with `Model` by default.

### DTOs

Use `Request`, `Response`, `Envelope`, `Record`, `Snapshot`, or `Payload` according to meaning.

- `Request` — caller input for an operation
- `Response` — operation output at an API boundary
- `Envelope` — wrapped payload with metadata/security fields
- `Record` — persisted row/document/event-shaped value
- `Snapshot` — point-in-time state capture
- `Payload` — serialized transferable content

### Schemas

Use `Schema` only for actual schema definitions, not arbitrary validators.

- Good:
  - `PolicyRequestSchema`
  - `AuditEventSchema`
- Bad:
  - `TrustLabelSchema` if it is actually a parser or mapper

---

## Interface and Abstraction Conventions

- Name interfaces by capability, not implementation:
  - `PolicyEvaluating`
  - `AuditAppending`
  - `AttestationVerifying`
- Adapters convert between representations or providers.
- Services coordinate multi-step domain workflows.
- Engines perform deterministic evaluation/transformation.
- Clients call external systems.
- Stores persist and retrieve data.
- Validators check invariants and reject invalid inputs.
- Reconstructors rebuild state from canonical data.

If a class both validates and mutates, split it unless the TRD explicitly defines them as one operation.

---

## State Machine and Enum Conventions

- State names must be nouns or adjectives, never implementation notes.
- Enum cases must be closed and explicit.
- Do not use free-form strings for internal states where enums are possible.
- Persisted enum/string values must match TRD-defined wire/storage contracts exactly.
- Add parsing layers when internal naming differs from external wire naming.

Examples:

- Good:
  - `pending`
  - `validated`
  - `sealed`
  - `denied`
- Bad:
  - `done`
  - `ok`
  - `bad_state`
  - `step2`

---

## Function Design Conventions

- One public function should perform one contract-visible action.
- Validate at boundaries, not repeatedly at every internal layer without reason.
- Prefer explicit parameters over context bags.
- Avoid long positional argument lists; use typed request objects when the operation is complex.
- Functions with side effects should indicate action clearly:
  - `append_event`
  - `seal_secret`
  - `evaluate_policy`
- Pure transforms should use names like:
  - `normalize_turn`
  - `derive_label`
  - `build_timeline`

### Return Patterns

- Return typed values for success.
- Raise/throw typed errors for contract failures.
- Avoid returning mixed success/error dictionaries.
- Avoid boolean-only returns when callers need failure reason.

---

## Logging, Auditing, and Observability Conventions

- Use structured logs.
- Include stable keys, not prose-only diagnostics.
- Redact secrets, credentials, and sensitive payloads.
- Audit events must use subsystem-defined event types and field names.
- Correlation IDs must propagate across subsystem boundaries where required.
- Log levels must be meaningful:
  - `debug` for local diagnostics
  - `info` for normal lifecycle milestones
  - `warning` for recoverable anomalies
  - `error` for failed operations
  - `critical` only for severe integrity, security, or availability failures

Do not log:
- access tokens
- private keys
- full attestation payloads unless explicitly approved
- raw untrusted content if policy forbids it
- generated code contents unless TRD explicitly requires capture

---

## Test Naming and Layout Conventions

Tests must mirror source structure exactly.

Examples:

```text
src/dtl/trust_label_resolver.py
tests/dtl/test_trust_label_resolver.py

src/trustflow/audit_stream_writer.py
tests/trustflow/test_audit_stream_writer.py
```

### Test Function Naming

Use:

```text
test_<unit>_<behavior>_<expected_result>
```

Examples:

- `test_trust_label_resolver_with_missing_provenance_raises_validation_error`
- `test_policy_engine_with_conflicting_rules_returns_deny`
- `test_replay_timeline_from_checkpoint_restores_cursor_position`

### Test Rules

- One test file per primary implementation file where practical.
- Use fixtures for canonical domain setup.
- Prefer explicit factory helpers over opaque shared globals.
- Test published contracts:
  - success behavior
  - validation failures
  - boundary conditions
  - redaction/security behavior
  - deterministic replay where applicable
- Include regression tests for any bug fix.

---

## Security-Sensitive Coding Patterns

These rules apply across all subsystems and are especially important for `dtl`, `trustflow`, `vtz`, `trustlock`, and `mcp`.

- Default to fail closed when the TRD requires it.
- Validate all external input before use.
- Treat connector input and model/provider output as untrusted.
- Keep secrets in approved secret storage/boundary only.
- Never hardcode credentials, tokens, or cryptographic material.
- Never weaken attestation, policy, or trust checks for convenience.
- Redact before logging, persisting, or emitting audit events.
- Use canonical serialization where integrity or signatures matter.
- Compare sensitive values using approved constant-time primitives where applicable.
- Keep policy enforcement and policy explanation paths consistent.

---

## Anti-Patterns

Do not introduce:

- `helpers.py`, `utils.py`, `common.py` without TRD justification
- God classes named `Manager`, `Processor`, `Handler`
- Broad exception catches that mask contract failures
- Unstructured dict/object blobs where typed models are expected
- Boolean flags controlling unrelated behavior in one function
- Cross-subsystem leakage of internal terminology
- Implicit trust upgrades
- Logging of secrets or raw sensitive content
- Non-deterministic replay code in `rewind`
- Ambiguous names like `data`, `item`, `obj`, `thing`

---

## Preferred Patterns Summary

### Good Names

- `TrustLabelResolver`
- `PolicyDecision`
- `ZoneBoundaryValidator`
- `AttestationEvidence`
- `AuditStreamWriter`
- `ReplayCheckpointStore`
- `ConnectorManifest`

### Bad Names

- `DataManager`
- `PolicyHelper`
- `ThingProcessor`
- `MiscUtils`
- `SandboxManager`
- `HistoryHandler`

---

## Final Rule

If naming, error structure, or code organization is unclear:

1. Find the owning TRD.
2. Use the TRD’s exact domain language.
3. Keep names explicit, typed, and boundary-aware.
4. Preserve security, determinism, and auditability.