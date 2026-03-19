# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and code patterns for the full Forge platform. It applies across all repositories and subsystems unless a subsystem TRD imposes a stricter rule. TRDs remain the source of truth for behavior, interfaces, and security requirements.

## Core Principles

- Match the owning TRD before writing code.
- Prefer explicitness over cleverness.
- Keep subsystem boundaries strict.
- Make trust, security, and provenance visible in names.
- Do not invent new patterns when a platform pattern already exists.
- Tests must mirror runtime structure and naming.
- Generated code, external content, and model output must never be treated as trusted by default.
- Never execute generated code unless a TRD explicitly permits a controlled mechanism.

## Repository-Wide Standards

### General Naming

- Use descriptive names tied to domain meaning.
- Avoid abbreviations unless they are platform-standard:
  - `cal`
  - `dtl`
  - `vtz`
  - `mcp`
  - `sdk`
  - `id`
  - `url`
  - `uri`
  - `json`
- Prefer singular nouns for types:
  - `TrustLabel`
  - `PolicyDecision`
  - `ReplaySession`
- Prefer plural nouns for collections:
  - `trust_labels`
  - `policy_rules`
  - `replay_events`
- Boolean names must read as predicates:
  - `is_valid`
  - `has_attestation`
  - `can_execute`
  - `should_redact`
- Use verbs for functions and methods:
  - `parse_label()`
  - `verify_attestation()`
  - `emit_audit_event()`

### Style Priorities

- Optimize for readability and auditability.
- Keep functions small and single-purpose.
- Prefer pure functions for parsing, normalization, validation, and transformation.
- Centralize I/O, external calls, and security-sensitive operations.
- Avoid hidden state.
- Make all trust transitions explicit in code.

### API and Contract Discipline

- Public interfaces must be stable, typed, and documented.
- Do not expose internal transport, persistence, or crypto details unless required by the subsystem contract.
- Use explicit DTOs/schemas for subsystem boundaries.
- Validate all inputs at boundary entry points.
- Normalize data before policy evaluation or persistence.

---

## File and Directory Naming (exact `src/` layout)

Use this structure exactly for platform subsystems:

```text
src/
  cal/           # Conversation Abstraction Layer components
  dtl/           # Data Trust Label components
  trustflow/     # TrustFlow audit stream components
  vtz/           # Virtual Trust Zone enforcement
  trustlock/     # Cryptographic machine identity (TPM-anchored)
  mcp/           # MCP Policy Engine
  rewind/        # Forge Rewind replay engine

sdk/
  connector/     # Forge Connector SDK

tests/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
  connector/
```

### Directory Rules

- Tests must mirror `src/` structure exactly.
- Add new modules under the owning subsystem only.
- Do not place shared domain logic in ad hoc `common`, `misc`, or `utils` directories.
- Shared code must live in a deliberately named module such as:
  - `src/cal/schema/`
  - `src/mcp/evaluation/`
  - `src/trustlock/attestation/`
- If code is cross-subsystem, place it in a clearly governed shared package only if the platform architecture explicitly allows it.

### File Naming Rules

Use `snake_case` for file names.

Examples:

```text
src/dtl/trust_label.py
src/dtl/label_parser.py
src/trustflow/audit_event.py
src/vtz/policy_enforcer.py
src/trustlock/tpm_attestor.py
src/mcp/policy_engine.py
src/rewind/replay_session.py
sdk/connector/client.py
tests/dtl/test_trust_label.py
tests/mcp/test_policy_engine.py
```

### File Name Patterns

Use these suffixes consistently:

- `_model.py` for internal domain models only when the noun alone would be ambiguous
- `_schema.py` for serialization/deserialization schemas
- `_parser.py` for parsers
- `_validator.py` for validation logic
- `_service.py` for orchestration logic
- `_client.py` for external service clients
- `_adapter.py` for protocol/provider adaptation
- `_store.py` for persistence access
- `_engine.py` for deterministic evaluation engines
- `_policy.py` for policy objects or policy logic
- `_event.py` for event definitions
- `_replayer.py` for replay executors
- `_attestor.py` for attestation components

Avoid vague names like:

- `helpers.py`
- `stuff.py`
- `misc.py`
- `common.py`
- `manager.py` unless it manages a concrete lifecycle defined by a TRD

---

## Class and Function Naming

### Classes

Use `PascalCase`.

Examples:

- `ConversationSession`
- `TrustLabel`
- `AuditEvent`
- `VirtualTrustZone`
- `MachineAttestor`
- `PolicyEngine`
- `ReplayController`
- `ConnectorClient`

### Abstract Types and Interfaces

Use names that describe the role, not the implementation.

Examples:

- `LabelParser`
- `AuditSink`
- `PolicyEvaluator`
- `AttestationProvider`
- `ReplayStore`

For abstract base classes or protocols, use one of:

- noun-only if the language/framework standard supports interface semantics cleanly
- `Base...` for shared abstract implementation
- `...Protocol` only if required by the ecosystem

Examples:

- `PolicyEvaluator`
- `BaseAttestor`
- `ConnectorTransport`

### Functions and Methods

Use `snake_case`.

Examples:

- `parse_conversation()`
- `derive_trust_label()`
- `verify_machine_identity()`
- `evaluate_policy()`
- `record_audit_event()`
- `replay_session()`

### Method Name Semantics

Use consistent verbs by responsibility:

- `parse_...` — syntactic interpretation
- `validate_...` — rule checking without mutation
- `normalize_...` — canonicalization
- `derive_...` — computed value from trusted inputs
- `build_...` — assemble an object
- `create_...` — instantiate and persist/register
- `load_...` — retrieve from storage
- `fetch_...` — retrieve from external system
- `list_...` — enumerate many
- `get_...` — retrieve one already-local value or cheap lookup
- `verify_...` — cryptographic or evidence-backed validation
- `evaluate_...` — policy/rule decisioning
- `record_...` — append immutable event/log/audit data
- `emit_...` — publish event to stream or sink
- `apply_...` — enact a decision or transformation
- `replay_...` — deterministic historical reconstruction

### Constants

- Use `UPPER_SNAKE_CASE`.
- Constants must be immutable and centrally defined.
- Security or policy constants must be grouped in subsystem-specific constant modules.

Examples:

- `MAX_LABEL_DEPTH`
- `DEFAULT_REPLAY_WINDOW_SECONDS`
- `TPM_QUOTE_TIMEOUT_MS`
- `POLICY_DECISION_ALLOW`

### Enum Naming

- Enum classes use `PascalCase`.
- Enum members use `UPPER_SNAKE_CASE`.

Examples:

- `TrustLevel`
- `DecisionOutcome`
- `ReplayMode`

Members:

- `HIGH`
- `DENY`
- `DRY_RUN`

---

## Error and Exception Patterns

### General Rules

- Fail closed for trust, policy, identity, and enforcement paths.
- Use typed exceptions, never string-matching on generic exceptions.
- Raise domain-specific exceptions at subsystem boundaries.
- Preserve root cause with exception chaining.
- Do not leak secrets, tokens, private keys, attestation material, or sensitive payloads in exception messages.
- Exception messages must be actionable and non-sensitive.

### Exception Naming

Use `PascalCase` ending in `Error`.

Examples:

- `TrustLabelParseError`
- `TrustLabelValidationError`
- `AuditWriteError`
- `PolicyEvaluationError`
- `PolicyDeniedError`
- `AttestationVerificationError`
- `ReplayConsistencyError`
- `ConnectorAuthenticationError`

### Exception Hierarchy Pattern

Each subsystem should define a base exception:

```python
class DtlError(Exception):
    pass

class TrustLabelParseError(DtlError):
    pass

class TrustLabelValidationError(DtlError):
    pass
```

Preferred pattern:

- `ForgeError` — platform root if needed
- `<Subsystem>Error` — subsystem root
- concrete typed errors beneath it

Examples:

- `CalError`
- `DtlError`
- `TrustflowError`
- `VtzError`
- `TrustlockError`
- `McpError`
- `RewindError`
- `ConnectorError`

### Error Contract Rules

- Parsing failures: `...ParseError`
- Schema/shape failures: `...ValidationError`
- Authentication failures: `...AuthenticationError`
- Authorization/policy denials: `...DeniedError`
- Verification failures: `...VerificationError`
- Missing state/data: `...NotFoundError`
- Conflicts/version mismatches: `...ConflictError`
- External dependency failures: `...DependencyError`
- Timeouts: `...TimeoutError`
- Replay divergence/integrity issues: `...ConsistencyError`

### Logging and Exceptions

- Log context fields, not raw secrets.
- Include stable identifiers when safe:
  - `conversation_id`
  - `event_id`
  - `policy_id`
  - `machine_id`
  - `replay_id`
- Do not log:
  - plaintext credentials
  - private keys
  - raw tokens
  - full sensitive prompts/content unless explicitly permitted
  - TPM secret material
- Redact by default.

### Result vs Exception

Use exceptions for:

- invariant violation
- malformed input
- policy failure requiring control-flow stop
- cryptographic verification failure
- I/O failure that the caller must handle explicitly

Use result objects only when the TRD defines multi-outcome evaluation semantics, such as:

- `PolicyDecision`
- `AttestationResult`
- `ReplayOutcome`

Do not mix boolean returns with side-channel error meaning.

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

### Purpose

Conversation Abstraction Layer code handles normalized conversation objects, messages, context envelopes, and boundary-safe interaction representations.

### Naming Rules

Use `Conversation`, `Message`, `Transcript`, `Context`, `Turn`, and `Envelope` consistently.

Preferred type names:

- `ConversationSession`
- `ConversationMessage`
- `ConversationTurn`
- `TranscriptEnvelope`
- `ContextWindow`
- `MessageNormalizer`

Preferred file names:

```text
src/cal/conversation_session.py
src/cal/conversation_message.py
src/cal/transcript_envelope.py
src/cal/message_normalizer.py
src/cal/context_window.py
```

### Function Patterns

- `parse_transcript()`
- `normalize_message()`
- `build_context_window()`
- `truncate_context_window()`
- `serialize_envelope()`

### Avoid

- `chat.py`
- `chatbot.py`
- `prompt_magic.py`

Use domain-neutral, transport-neutral naming. CAL is not UI chat logic.

---

## `src/dtl/` — Data Trust Label

### Purpose

DTL code defines trust labels, label derivation, propagation, validation, and serialization.

### Naming Rules

Use `TrustLabel` as the core noun. Related nouns:

- `LabelSource`
- `LabelEvidence`
- `TrustTier`
- `TrustClassification`
- `LabelDeriver`
- `LabelValidator`

Preferred file names:

```text
src/dtl/trust_label.py
src/dtl/label_deriver.py
src/dtl/label_validator.py
src/dtl/label_schema.py
src/dtl/label_evidence.py
```

### Function Patterns

- `derive_trust_label()`
- `validate_trust_label()`
- `merge_trust_labels()`
- `serialize_trust_label()`
- `parse_label_evidence()`

### Error Patterns

- `TrustLabelParseError`
- `TrustLabelValidationError`
- `TrustLabelConflictError`
- `LabelEvidenceError`

### Avoid

- `tag`
- `badge`
- `score` unless the TRD specifically distinguishes those concepts

Use `label` consistently.

---

## `src/trustflow/` — TrustFlow Audit Stream

### Purpose

TrustFlow records immutable audit events, decision traces, provenance, and execution history.

### Naming Rules

Use `Audit`, `Provenance`, `Trace`, `Event`, `Stream`, and `Record` consistently.

Preferred type names:

- `AuditEvent`
- `AuditRecord`
- `ProvenanceTrace`
- `EventStream`
- `AuditSink`
- `TraceEmitter`

Preferred file names:

```text
src/trustflow/audit_event.py
src/trustflow/audit_record.py
src/trustflow/provenance_trace.py
src/trustflow/event_stream.py
src/trustflow/audit_sink.py
```

### Function Patterns

- `record_audit_event()`
- `emit_trace_event()`
- `append_audit_record()`
- `load_provenance_trace()`
- `verify_record_chain()`

### Event Naming

Event types should be noun-based and stable:

- `POLICY_DECISION_RECORDED`
- `ATTESTATION_VERIFIED`
- `REPLAY_STARTED`
- `REPLAY_COMPLETED`
- `CONNECTOR_REQUEST_REJECTED`

### Avoid

- `log` for immutable trust records when `audit` is the intended concept
- `history` when `trace` or `record` is more exact

---

## `src/vtz/` — Virtual Trust Zone

### Purpose

VTZ enforces trust boundaries, isolation policies, action gating, and zone transitions.

### Naming Rules

Use `Zone`, `Boundary`, `Enforcer`, `Guard`, `Capability`, and `Restriction`.

Preferred type names:

- `VirtualTrustZone`
- `ZoneBoundary`
- `PolicyEnforcer`
- `CapabilityGuard`
- `ExecutionRestriction`
- `ZoneTransition`

Preferred file names:

```text
src/vtz/virtual_trust_zone.py
src/vtz/zone_boundary.py
src/vtz/policy_enforcer.py
src/vtz/capability_guard.py
src/vtz/zone_transition.py
```

### Function Patterns

- `enforce_boundary()`
- `evaluate_zone_transition()`
- `restrict_capability()`
- `allow_operation()`
- `deny_operation()`

### Error Patterns

- `BoundaryViolationError`
- `CapabilityDeniedError`
- `ZoneTransitionError`

### Avoid

- `sandbox` unless the TRD specifically uses it
- `jail` or vague security metaphors

Use `zone` and `boundary` terminology.

---

## `src/trustlock/` — Cryptographic Machine Identity

### Purpose

TrustLock handles TPM-anchored machine identity, attestation, key material references, and verification.

### Naming Rules

Use `Attestation`, `Quote`, `Identity`, `KeyHandle`, `Verifier`, and `Evidence`.

Preferred type names:

- `MachineIdentity`
- `TpmAttestor`
- `AttestationVerifier`
- `QuoteEvidence`
- `KeyHandleReference`
- `IdentityBinding`

Preferred file names:

```text
src/trustlock/machine_identity.py
src/trustlock/tpm_attestor.py
src/trustlock/attestation_verifier.py
src/trustlock/quote_evidence.py
src/trustlock/key_handle_reference.py
```

### Function Patterns

- `generate_quote()`
- `verify_attestation()`
- `bind_machine_identity()`
- `load_key_handle()`
- `rotate_attestation_key()`

### Security Naming Rules

- Secret-bearing values must be named explicitly:
  - `private_key_pem`
  - `sealed_secret`
  - `attestation_nonce`
- Non-secret references must also be explicit:
  - `key_handle`
  - `public_key_der`
  - `quote_blob`

### Avoid

- `key` by itself when the type is ambiguous
- `token` for attestation evidence unless the TRD uses that exact term

---

## `src/mcp/` — MCP Policy Engine

### Purpose

MCP evaluates policy, produces deterministic decisions, and explains allow/deny outcomes.

### Naming Rules

Use `Policy`, `Rule`, `Decision`, `Evaluator`, `Constraint`, and `Explanation`.

Preferred type names:

- `PolicyEngine`
- `PolicyRule`
- `PolicyDecision`
- `RuleEvaluator`
- `ConstraintSet`
- `DecisionExplanation`

Preferred file names:

```text
src/mcp/policy_engine.py
src/mcp/policy_rule.py
src/mcp/policy_decision.py
src/mcp/rule_evaluator.py
src/mcp/constraint_set.py
```

### Function Patterns

- `evaluate_policy()`
- `evaluate_rule()`
- `build_decision_explanation()`
- `resolve_constraints()`
- `deny_by_default()`

### Decision Naming

Policy results should use explicit outcome naming:

- `ALLOW`
- `DENY`
- `CONDITIONAL_ALLOW` only if defined by TRD
- `NOT_APPLICABLE` only if defined by TRD

### Avoid

- `judge`
- `rank`
- `guess`
- `maybe_allow`

Policy output must sound deterministic and auditable.

---

## `src/rewind/` — Forge Rewind Replay Engine

### Purpose

Rewind reconstructs and replays historical event sequences for audit, debugging, and verification.

### Naming Rules

Use `Replay`, `Snapshot`, `Checkpoint`, `Timeline`, `Session`, and `Divergence`.

Preferred type names:

- `ReplaySession`
- `ReplayController`
- `TimelineSnapshot`
- `CheckpointRecord`
- `ReplayDivergence`
- `EventReplayer`

Preferred file names:

```text
src/rewind/replay_session.py
src/rewind/replay_controller.py
src/rewind/timeline_snapshot.py
src/rewind/checkpoint_record.py
src/rewind/event_replayer.py
```

### Function Patterns

- `start_replay()`
- `replay_event_sequence()`
- `load_checkpoint()`
- `capture_snapshot()`
- `detect_divergence()`

### Error Patterns

- `ReplayConsistencyError`
- `CheckpointLoadError`
- `ReplayDivergenceError`

### Avoid

- `undo` when the operation is historical reconstruction rather than mutation reversal
- `time_travel` in production code names

---

## `sdk/connector/` — Forge Connector SDK

### Purpose

Connector SDK code integrates external systems into Forge using stable, authenticated, policy-aware interfaces.

### Naming Rules

Use `Connector`, `Client`, `Transport`, `Request`, `Response`, `Credential`, and `Session`.

Preferred type names:

- `ConnectorClient`
- `ConnectorTransport`
- `ConnectorRequest`
- `ConnectorResponse`
- `CredentialProvider`
- `ConnectorSession`

Preferred file names:

```text
sdk/connector/connector_client.py
sdk/connector/connector_transport.py
sdk/connector/connector_request.py
sdk/connector/credential_provider.py
sdk/connector/connector_session.py
```

### Function Patterns

- `send_request()`
- `authenticate_session()`
- `refresh_credentials()`
- `validate_response()`
- `close_session()`

### Error Patterns

- `ConnectorAuthenticationError`
- `ConnectorTimeoutError`
- `ConnectorDependencyError`
- `ConnectorResponseValidationError`

### Avoid

- provider-specific naming in shared SDK layers
- embedding vendor names in base abstractions

Use vendor names only in adapter implementations, for example:

- `GithubConnectorClient`
- `SlackConnectorAdapter`

---

## Code Patterns

## Data Models

- Prefer explicit typed models for boundary data.
- Keep domain models immutable where practical.
- Serialization concerns should live in schema/adapter layers, not core models.
- A model representing trust or policy state must not silently mutate after validation.

Recommended split:

- domain model
- schema/serialization layer
- validator
- service/orchestrator

## Validation Pattern

Perform validation in this order:

1. Parse shape
2. Normalize
3. Validate invariants
4. Verify trust/identity if applicable
5. Persist or evaluate

Do not combine parsing, policy evaluation, and persistence into one function.

## Enforcement Pattern

For security and trust-sensitive code:

- validate inputs first
- evaluate policy second
- enforce third
- record audit event fourth
- return structured result last

If enforcement fails, emit an appropriate audit/error record as required by the owning TRD.

## Auditability Pattern

Any operation that changes trust state, policy state, machine identity binding, replay state, or external connector state should produce explicit audit records where required.

Names should make this visible:

- `record_policy_decision()`
- `emit_attestation_verified()`
- `append_replay_checkpoint()`

## Adapter Pattern

Use adapters for:

- provider-specific external APIs
- transport conversions
- schema translation
- legacy compatibility layers

Naming:

- `...Adapter` for translation roles
- `...Client` for remote calls
- `...Transport` for communication layer
- `...Provider` for pluggable source of capability/data

## Test Conventions

### Directory Layout

Tests mirror source structure exactly.

Examples:

```text
tests/dtl/test_trust_label.py
tests/trustlock/test_tpm_attestor.py
tests/mcp/test_policy_engine.py
tests/rewind/test_replay_controller.py
tests/connector/test_connector_client.py
```

### Test Naming

- Test files use `test_<module>.py`
- Test functions use `test_<expected_behavior>()`
- Test classes, if used, use `Test<Subject>`

Examples:

- `test_validate_trust_label_rejects_missing_source()`
- `test_verify_attestation_rejects_invalid_quote()`
- `test_evaluate_policy_denies_untrusted_connector()`

### Test Requirements

- Cover allow and deny paths.
- Cover malformed input.
- Cover boundary and trust-transition behavior.
- Cover replay consistency and divergence behavior where relevant.
- Cover redaction and non-leakage in errors/logs for sensitive paths.
- Security-sensitive code must include negative tests.

---

## Naming Anti-Patterns

Do not use:

- vague nouns: `data`, `info`, `item`, `object`
- vague verbs: `handle`, `process`, `do`
- overloaded names: `manager`, `helper`, `util`
- security-ambiguous names: `key`, `secret`, `token` without qualifiers
- trust-ambiguous names: `safe`, `trusted`, `verified` unless the code has actually established that property

Prefer:

- `attestation_nonce` over `nonce`
- `policy_decision` over `result`
- `trust_label` over `tag`
- `connector_response` over `payload`
- `replay_divergence` over `mismatch`

---

## Documentation and Comments

- Document public classes, boundary functions, and security-critical logic.
- Comments must explain why, not restate what.
- If a naming choice follows a TRD term of art, use the TRD’s exact wording.
- If behavior is security-sensitive, reference the owning TRD section in code comments where appropriate.

---

## Change Discipline

Before adding or renaming any major class, module, or error type:

1. Identify the owning TRD.
2. Confirm terminology matches the TRD exactly.
3. Preserve subsystem naming consistency.
4. Update mirrored tests.
5. Update schemas, adapters, and audit event names if contracts changed.
6. Re-run the relevant test suite.

## Final Rule

When code, naming, or structure is unclear, do not improvise. Use the owning TRD terminology and patterns exactly.