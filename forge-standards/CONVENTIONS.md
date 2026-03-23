# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and required code patterns for the full Forge platform. It applies across all subsystems and languages in this repository.

Forge is a security-sensitive, specification-driven platform. Conventions here are mandatory unless a governing TRD explicitly overrides them.

---

## Source of Truth and Scope

- The TRDs in `forge-docs/` are authoritative.
- `AGENTS.md`, `CLAUDE.md`, and `README.md` define repository identity and architecture expectations.
- Security-sensitive behavior must conform to TRD-11.
- This document defines:
  - repository naming rules
  - file and directory layout
  - class, type, and function naming
  - error and exception conventions
  - cross-subsystem patterns
  - subsystem-specific naming rules

When conventions conflict:
1. TRD
2. Security requirements
3. This document
4. Local style preference

---

## Platform Architecture Conventions

Forge follows a two-process architecture:

- **Swift shell**
  - UI
  - authentication
  - Keychain/secrets handling
  - local platform integrations
  - IPC/XPC/socket ownership
- **Python backend**
  - consensus logic
  - orchestration pipelines
  - planning/generation/review flows
  - GitHub operations
  - policy and trust processing

General rules:

- Keep trust boundaries explicit in code.
- Never blur Swift-owned responsibilities into Python, or Python-owned responsibilities into Swift.
- Generated code is never executed automatically.
- IPC contracts must be versioned and validated.
- Security controls are implemented as code, not comments.

---

## General Naming Principles

Use names that are:

- precise
- domain-aligned
- stable over time
- explicit about trust or security effects
- consistent with subsystem vocabulary

Prefer:

- `TrustLabel`, not `LabelThing`
- `PolicyDecision`, not `Result`
- `ReplayCursor`, not `Pointer`
- `MachineIdentityAttestation`, not `IdentityInfo`

Avoid:

- vague abbreviations outside approved subsystem namespaces
- overloaded names like `Manager`, `Helper`, `Util`, `Stuff`, `Data`
- names that hide side effects
- names that imply execution of untrusted content unless that is explicitly allowed

---

# File and Directory Naming (exact `src/` layout)

## Required Top-Level Layout

```text
src/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/

sdk/
  connector/

tests/
  cal/
  dtl/
  trustflow/
  vtz/
  trustlock/
  mcp/
  rewind/
```

Rules:

- All production code for these subsystems must live under the exact directory listed.
- Tests must mirror `src/` structure exactly.
- New subsystem code may not be placed at `src/common/` or `src/utils/` as a catch-all.
- Shared code must be narrowly scoped and named by responsibility, not convenience.

## Directory Naming Rules

- Use lowercase directories.
- Use singular subsystem roots exactly as defined:
  - `cal`
  - `dtl`
  - `trustflow`
  - `vtz`
  - `trustlock`
  - `mcp`
  - `rewind`
- Use nested directories for bounded responsibilities.

Good:

```text
src/dtl/parser/
src/dtl/validation/
src/trustflow/audit_stream/
src/vtz/enforcement/
src/trustlock/attestation/
sdk/connector/python/
sdk/connector/swift/
```

Bad:

```text
src/DTL/
src/trustFlow/
src/helpers/
src/misc/
src/commonstuff/
```

## File Naming Rules

### Python

- Use `snake_case.py`.
- Module filenames should describe a single primary concept.
- Prefer nouns for models and protocols, verbs for operation modules only when justified.

Good:

```text
policy_engine.py
trust_label.py
audit_stream_writer.py
machine_identity_attestor.py
replay_session.py
```

Bad:

```text
PolicyEngine.py
engineStuff.py
misc.py
helpers.py
all_models.py
```

### Swift

- Use `PascalCase.swift` for primary type files.
- File name must match the main type in the file when there is one.
- Extensions may use:
  - `TypeName+Concern.swift`
  - `TypeName+Validation.swift`
  - `TypeName+IPC.swift`

Good:

```text
TrustLabel.swift
PolicyDecision.swift
ReplaySession.swift
UnixSocketTransport.swift
TrustLabel+Validation.swift
```

Bad:

```text
trustLabel.swift
extensions.swift
misc.swift
socket_utils.swift
```

## Test File Naming

### Python tests

- Use `test_<module_or_behavior>.py`.
- One behavior group per file.
- Mirror source ownership.

Good:

```text
tests/dtl/test_trust_label_parser.py
tests/mcp/test_policy_decision_engine.py
tests/rewind/test_replay_cursor_resume.py
```

### Swift tests

- Use `<TypeName>Tests.swift` or `<BehaviorName>Tests.swift`.
- Keep one primary test target concern per file.

Good:

```text
TrustLabelParserTests.swift
PolicyDecisionTests.swift
UnixSocketTransportTests.swift
```

---

# Class and Function Naming

## Class, Struct, Enum, Protocol, and Type Naming

### Swift

- Use `PascalCase`.
- Protocols describe capability or role and should read naturally.
- Do not prefix protocol names with `I`.
- Enums should be nouns unless modeling actions.

Good:

- `TrustLabel`
- `PolicyDecision`
- `ReplaySession`
- `MachineIdentityAttestor`
- `SocketMessageValidating`
- `AuditStreamEvent`

Bad:

- `ITrustLabel`
- `trustLabel`
- `PolicyDecisionManager`
- `StuffProcessor`

### Python

- Use `PascalCase` for classes.
- Use descriptive suffixes only when they carry architectural meaning:
  - `Parser`
  - `Validator`
  - `Adapter`
  - `Encoder`
  - `Decoder`
  - `Client`
  - `Service`
  - `Repository`
  - `PolicyEngine`
  - `Attestor`

Good:

- `TrustLabelParser`
- `ReplaySession`
- `MachineIdentityAttestor`
- `AuditStreamWriter`
- `PolicyDecisionEngine`

Bad:

- `LabelMgr`
- `DataHelper`
- `RewindThing`

## Function and Method Naming

### General

- Use verbs for functions that do work.
- Use noun phrases for accessors or computed properties.
- Include trust/security intent in names where relevant.
- Be explicit about side effects.

Good:

- `parse_trust_label`
- `validate_attestation`
- `emit_audit_event`
- `enforce_zone_boundary`
- `derive_connector_token`
- `replay_until_checkpoint`

Bad:

- `handle`
- `process`
- `run`
- `do_it`
- `manage_policy`

### Swift

- Follow Swift API Design Guidelines:
  - method names should read as a sentence at call site
  - first argument label required unless idiomatically omitted
- Prefer:
  - `validate(label:)`
  - `emit(event:)`
  - `enforce(boundary:for:)`
  - `replay(until:)`

### Python

- Use `snake_case`.
- Private/internal helpers start with single underscore.
- Do not use double underscore name mangling except when required by framework semantics.

Good:

- `validate_policy_input`
- `_normalize_label_fields`
- `build_audit_envelope`

Bad:

- `ValidatePolicyInput`
- `__doStuff`
- `helper_method`

## Boolean Naming

- Prefix booleans with `is_`, `has_`, `can_`, `should_` in Python.
- In Swift prefer `is`, `has`, `can`, `should`.

Good:

- `is_trusted`
- `has_attestation`
- `can_replay`
- `should_quarantine`

Bad:

- `trusted`
- `attestation`
- `replayable`
- `quarantine_flag`

## Async Naming

- Async functions should be verbs.
- Do not suffix names with `Async` unless required to distinguish a synchronous counterpart.
- If both forms exist:
  - `load_policy()`
  - `load_policy_async()` in Python only if unavoidable
  - in Swift prefer overloads with `async`

---

# Error and Exception Patterns

Security and orchestration code must produce explicit, typed, actionable failures.

## Core Rules

- Never raise or throw raw strings.
- Never swallow exceptions silently.
- Never return `null`/`None` to mean “error” when a typed failure is required.
- Preserve root cause when rethrowing.
- Sanitize secrets and sensitive payloads in error messages.
- Errors crossing subsystem or process boundaries must be structured.

## Error Naming

### Python

- Exception classes use `PascalCase` and end with `Error`.
- Domain-specific validation failures may use `Violation` where semantically required.

Good:

- `TrustLabelParseError`
- `PolicyDecisionError`
- `ZoneBoundaryViolation`
- `MachineIdentityError`
- `ReplayCheckpointError`

Bad:

- `TrustLabelException`
- `BadThingError`
- `GeneralError`

### Swift

- Error types use `PascalCase`.
- Prefer enums conforming to `Error` for bounded cases.
- Use structs when attaching richer context is necessary.

Good:

- `enum TrustLabelError: Error`
- `enum PolicyEngineError: Error`
- `struct AuditStreamWriteError: Error`

## Error Structure

All errors should answer, directly or indirectly:

- what failed
- where it failed
- why it failed
- whether retry is valid
- whether user action is required
- whether the event is security-relevant

Preferred fields for structured errors/log payloads:

- `code`
- `message`
- `subsystem`
- `operation`
- `retryable`
- `user_action_required`
- `security_relevant`
- `correlation_id`
- `cause`

## Boundary Translation

At subsystem boundaries:

- convert low-level library exceptions into domain errors
- preserve original cause
- avoid leaking implementation details to UI or IPC consumers

Example pattern:

```python
try:
    envelope = parser.parse(raw_input)
except ValueError as exc:
    raise TrustLabelParseError(
        message="Invalid trust label payload",
        operation="parse_trust_label",
        cause=exc,
    ) from exc
```

## IPC and API Error Contracts

Errors crossing process boundaries must be:

- serializable
- version-safe
- stable in code and field shape
- non-secret-bearing

Required:

- machine-readable `code`
- human-readable `message`
- stable `subsystem`
- correlation/request identifier when available

## Validation Failures vs System Failures

Use distinct categories:

- **Validation failure**
  - malformed input
  - unsupported state transition
  - policy denial
  - attestation mismatch
- **System failure**
  - socket failure
  - disk I/O
  - unavailable provider
  - timeout
  - database/index corruption

Do not collapse these into one generic error path.

## Logging Errors

- Log once at the owning boundary.
- Do not log and re-log the same exception at every layer.
- Security-sensitive errors must redact:
  - secrets
  - tokens
  - raw credentials
  - private keys
  - full untrusted payloads
  - generated code unless explicitly approved by TRD/policy

---

## Code Patterns and Structural Rules

## Single Responsibility

Each file, type, and module should own one clear responsibility.

Good:

- `TrustLabelParser` parses labels
- `TrustLabelValidator` validates labels
- `AuditStreamWriter` writes events
- `ReplayCursorStore` persists cursor state

Bad:

- one class that parses, validates, logs, persists, and emits metrics

## Explicit Boundary Objects

Use explicit models for boundary crossings:

- IPC messages
- trust labels
- policy decisions
- replay checkpoints
- attestation documents
- connector requests/responses

Do not pass raw dictionaries/maps deep into the system when a typed model is expected.

## Immutability Preference

Prefer immutable value types for:

- trust metadata
- policy decisions
- event payloads
- identity claims
- replay checkpoints

Mutation is allowed only when lifecycle semantics demand it.

## No Generic “Utils”

Do not create files or classes named:

- `utils`
- `helpers`
- `common`
- `base`
- `misc`

unless the name is scoped and justified by architecture.

Instead use purpose-driven names:

- `label_normalizer.py`
- `socket_frame_decoder.py`
- `checkpoint_serializer.py`

## Dependency Direction

Higher-trust layers must not depend on lower-trust interpretation of untrusted content without validation.

Examples:

- UI may display policy results, but not reinterpret enforcement logic.
- replay components may consume audit events, but only validated and versioned events.
- connector SDK must not bypass MCP policy checks.

## Serialization Rules

- Use explicit schemas/models.
- Include version fields for persisted or cross-process payloads.
- Normalize timestamps and IDs consistently.
- Never deserialize untrusted content into executable behavior.

## Time and ID Conventions

- Use UTC everywhere for persisted timestamps.
- Use ISO 8601 / RFC 3339 strings unless TRD requires otherwise.
- Use monotonic clocks for durations/timeouts.
- Correlation IDs must be stable for one request/flow.
- Name fields consistently:
  - `created_at`
  - `updated_at`
  - `issued_at`
  - `expires_at`
  - `correlation_id`
  - `request_id`
  - `checkpoint_id`

---

## Testing Conventions

- Tests mirror subsystem layout exactly.
- Name tests by externally visible behavior.
- Include failure-path tests for:
  - malformed input
  - trust boundary violations
  - policy denials
  - serialization mismatches
  - replay divergence
  - attestation failures
- Security regressions require explicit tests.
- Prefer deterministic fixtures.
- Do not rely on network access in unit tests unless the test is explicitly integration-scoped.

Naming patterns:

- `test_rejects_unsigned_attestation`
- `test_emits_audit_event_with_correlation_id`
- `test_denies_connector_request_outside_policy`
- `test_replay_stops_at_checkpoint_boundary`

---

## Documentation and Comment Conventions

- Comments explain why, not what.
- Public APIs require concise docstrings/comments when semantics are not obvious.
- Security-sensitive code must document:
  - trust assumptions
  - validation preconditions
  - redaction expectations
  - failure behavior
- TODOs must include:
  - owner or subsystem
  - reason
  - removal condition

Good:

```python
# SECURITY: Raw connector payload must be schema-validated before policy evaluation.
```

Bad:

```python
# parse stuff here
```

---

# Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation/session abstraction and message normalization across providers and orchestration flows.

### Directory Patterns

```text
src/cal/
  session/
  message/
  provider/
  normalization/
  transport/
```

### Naming Rules

Use `Cal` prefix only when needed to avoid ambiguity outside the subsystem. Prefer domain names first.

Preferred type names:

- `ConversationSession`
- `ConversationMessage`
- `MessageEnvelope`
- `ProviderConversationAdapter`
- `MessageNormalizer`
- `ConversationTranscript`
- `TurnContext`

Preferred function names:

- `normalize_message`
- `append_turn`
- `build_transcript`
- `translate_provider_response`
- `validate_message_envelope`

Avoid:

- `ChatManager`
- `MessageHelper`
- `ProviderStuff`

### Error Names

- `ConversationSessionError`
- `MessageNormalizationError`
- `ProviderConversationError`
- `TranscriptBuildError`

---

## `src/dtl/` — Data Trust Label

Purpose: representation, parsing, validation, propagation, and enforcement of data trust labels.

### Directory Patterns

```text
src/dtl/
  parser/
  validation/
  model/
  propagation/
  enforcement/
  serialization/
```

### Naming Rules

All core domain types should use `TrustLabel` terminology consistently.

Preferred type names:

- `TrustLabel`
- `TrustLabelParser`
- `TrustLabelValidator`
- `TrustLabelSet`
- `TrustLabelPropagationRule`
- `TrustLabelEnvelope`
- `TrustLabelSerializer`

Preferred function names:

- `parse_trust_label`
- `validate_trust_label`
- `merge_trust_labels`
- `propagate_trust_label`
- `serialize_trust_label`

Avoid:

- `Tag`
- `Marking`
- `MetadataFlag`
- `LabelManager`

### Error Names

- `TrustLabelParseError`
- `TrustLabelValidationError`
- `TrustLabelPropagationError`
- `TrustLabelSerializationError`

---

## `src/trustflow/` — TrustFlow Audit Stream

Purpose: append-only trust and audit event stream, event envelopes, correlation, and audit retrieval.

### Directory Patterns

```text
src/trustflow/
  audit_stream/
  envelope/
  storage/
  query/
  retention/
  export/
```

### Naming Rules

Use `Audit`, `TrustEvent`, and `Envelope` consistently.

Preferred type names:

- `AuditStreamWriter`
- `AuditStreamReader`
- `AuditEventEnvelope`
- `TrustEvent`
- `EventCorrelationContext`
- `RetentionPolicy`
- `AuditExportJob`

Preferred function names:

- `emit_audit_event`
- `append_trust_event`
- `query_audit_stream`
- `build_event_envelope`
- `export_audit_range`

Avoid:

- `Logger` for audit stream components
- `EventManager`
- `AuditHelper`

### Error Names

- `AuditStreamWriteError`
- `AuditStreamReadError`
- `AuditEnvelopeError`
- `AuditRetentionError`
- `AuditExportError`

---

## `src/vtz/` — Virtual Trust Zone

Purpose: trust boundary enforcement, isolation semantics, zone membership, and boundary checks.

### Directory Patterns

```text
src/vtz/
  enforcement/
  boundary/
  membership/
  policy/
  isolation/
```

### Naming Rules

Use `Zone`, `Boundary`, `Isolation`, and `Enforcement` as primary terms.

Preferred type names:

- `VirtualTrustZone`
- `ZoneBoundary`
- `ZoneMembership`
- `BoundaryEnforcer`
- `IsolationPolicy`
- `ZoneContext`
- `BoundaryDecision`

Preferred function names:

- `enforce_zone_boundary`
- `validate_zone_membership`
- `resolve_zone_context`
- `apply_isolation_policy`
- `deny_boundary_crossing`

Avoid:

- `SandboxManager`
- `ZoneHelper`
- `SecurityLayer`

### Error Names

- `ZoneBoundaryViolation`
- `ZoneMembershipError`
- `IsolationPolicyError`
- `BoundaryEnforcementError`

---

## `src/trustlock/` — Cryptographic Machine Identity

Purpose: TPM-anchored or equivalent machine identity, attestation, identity proofing, and key-bound trust establishment.

### Directory Patterns

```text
src/trustlock/
  attestation/
  identity/
  keychain/
  proof/
  verification/
```

### Naming Rules

Use `MachineIdentity`, `Attestation`, `Proof`, and `Verification` consistently.

Preferred type names:

- `MachineIdentity`
- `MachineIdentityAttestor`
- `AttestationDocument`
- `AttestationVerifier`
- `IdentityProof`
- `KeyMaterialReference`
- `TrustAnchor`

Preferred function names:

- `generate_attestation`
- `verify_attestation`
- `bind_machine_identity`
- `derive_identity_proof`
- `resolve_trust_anchor`

Avoid:

- `TPMStuff`
- `IdentityManager` unless it owns a clearly defined lifecycle
- `CryptoHelper`

### Error Names

- `MachineIdentityError`
- `AttestationVerificationError`
- `IdentityProofError`
- `TrustAnchorResolutionError`

---

## `src/mcp/` — MCP Policy Engine

Purpose: policy evaluation, connector authorization, request mediation, and policy decisions.

### Directory Patterns

```text
src/mcp/
  policy/
  evaluation/
  connector/
  mediation/
  decision/
```

### Naming Rules

Use `Policy`, `Decision`, `Evaluation`, and `Connector` consistently.

Preferred type names:

- `PolicyEngine`
- `PolicyEvaluator`
- `PolicyDecision`
- `ConnectorRequest`
- `ConnectorAuthorizationContext`
- `MediationRule`
- `PolicyDecisionEnvelope`

Preferred function names:

- `evaluate_policy`
- `authorize_connector_request`
- `build_authorization_context`
- `mediate_connector_call`
- `emit_policy_decision`

Avoid:

- `RulesManager`
- `PolicyHelper`
- `AccessThing`

### Error Names

- `PolicyEvaluationError`
- `PolicyDecisionError`
- `ConnectorAuthorizationError`
- `MediationError`

---

## `src/rewind/` — Forge Rewind Replay Engine

Purpose: deterministic replay, checkpointing, event reconstruction, divergence detection, and replay inspection.

### Directory Patterns

```text
src/rewind/
  replay/
  checkpoint/
  divergence/
  inspection/
  reconstruction/
```

### Naming Rules

Use `Replay`, `Checkpoint`, `Divergence`, and `Reconstruction` consistently.

Preferred type names:

- `ReplaySession`
- `ReplayEngine`
- `ReplayCheckpoint`
- `ReplayCursor`
- `DivergenceDetector`
- `EventReconstructor`
- `ReplayInspectionReport`

Preferred function names:

- `start_replay`
- `resume_from_checkpoint`
- `detect_divergence`
- `reconstruct_event_sequence`
- `inspect_replay_state`

Avoid:

- `TimeTravel`
- `ReplayHelper`
- `HistoryManager`

### Error Names

- `ReplayError`
- `ReplayCheckpointError`
- `ReplayDivergenceError`
- `EventReconstructionError`

---

## `sdk/connector/` — Forge Connector SDK

Purpose: external connector integration under Forge policy and trust controls.

### Directory Patterns

```text
sdk/connector/
  python/
  swift/
  schemas/
  examples/
  tests/
```

### Naming Rules

SDK names must make policy mediation explicit.

Preferred type names:

- `ForgeConnectorClient`
- `ConnectorRequest`
- `ConnectorResponse`
- `ConnectorPolicyContext`
- `ConnectorSession`
- `ConnectorCapabilityDescriptor`

Preferred function names:

- `submit_connector_request`
- `validate_connector_response`
- `build_connector_policy_context`
- `negotiate_connector_session`

Avoid:

- `Client` alone
- `SDKHelper`
- names implying direct bypass of policy or mediation

### Error Names

- `ConnectorError`
- `ConnectorProtocolError`
- `ConnectorPolicyError`
- `ConnectorSessionError`

---

## Cross-Subsystem Shared Naming Rules

These names should be reused consistently across the platform where applicable:

### Context Types

- `...Context` for scoped execution metadata
- examples:
  - `TurnContext`
  - `ZoneContext`
  - `ConnectorAuthorizationContext`

### Decision Types

- `...Decision` for evaluated outcomes
- examples:
  - `PolicyDecision`
  - `BoundaryDecision`

### Envelope Types

- `...Envelope` for boundary-safe serialized wrappers
- examples:
  - `MessageEnvelope`
  - `AuditEventEnvelope`
  - `PolicyDecisionEnvelope`

### Session Types

- `...Session` for lifecycle-bound interactions
- examples:
  - `ConversationSession`
  - `ReplaySession`
  - `ConnectorSession`

### Validator Types

- `...Validator` for invariant checking
- examples:
  - `TrustLabelValidator`
  - `AttestationVerifier` if verification semantics exceed validation
  - `SocketMessageValidator`

### Adapter Types

- `...Adapter` for external/provider translations
- examples:
  - `ProviderConversationAdapter`
  - `GitHubAdapter`
  - `SocketTransportAdapter`

### Store/Repository Types

- `...Store` for low-level persistence primitives
- `...Repository` for domain-centric persistence access

Do not mix these terms casually.

---

## Banned and Discouraged Naming

Avoid these unless a TRD-defined interface requires them:

- `Helper`
- `Util`
- `Manager`
- `Thing`
- `Stuff`
- `Data`
- `Info`
- `Common`
- `Base`
- `Misc`
- `handle_*` for domain actions when a more precise verb exists
- `process_*` when parse/validate/evaluate/emit/enforce/replay is more accurate

If a `Manager` exists, it must represent a real orchestration lifecycle and be narrowly named, e.g. `ReplaySessionManager`. Generic `Manager` types are not allowed.

---

## Security-Specific Naming Conventions

Use names that reveal security intent.

Prefer:

- `redact_sensitive_fields`
- `validate_untrusted_payload`
- `verify_attestation_signature`
- `enforce_policy_decision`
- `sanitize_audit_export`

Avoid:

- `clean_data`
- `check_input`
- `secure_it`
- `verify_stuff`

Security-relevant booleans should be explicit:

- `is_untrusted`
- `is_attested`
- `requires_redaction`
- `has_policy_approval`
- `is_boundary_crossing_allowed`

---

## Versioning and Contract Naming

For payloads that cross process, storage, or SDK boundaries:

- include schema or contract version in the type or field where required
- prefer:
  - `version`
  - `schema_version`
  - `protocol_version`

Type naming examples:

- `AuditEventEnvelopeV1` only when multiple versions must coexist in code
- otherwise keep type name stable and include `schema_version` in payload

---

## Example Naming Matrix

| Concern | Preferred | Avoid |
|---|---|---|
| Trust label parser | `TrustLabelParser` | `LabelHelper` |
| Policy evaluation | `PolicyEvaluator` | `RulesManager` |
| Zone enforcement | `BoundaryEnforcer` | `SecurityManager` |
| Audit writing | `AuditStreamWriter` | `AuditLogger` |
| Replay checkpoint | `ReplayCheckpoint` | `ReplayStateData` |
| Machine attestation | `MachineIdentityAttestor` | `TPMHelper` |
| Connector mediation | `mediate_connector_call` | `process_request` |

---

## Compliance Checklist

Before merging code, verify:

- file is in the correct subsystem directory
- filename matches language conventions
- primary type names are domain-specific and precise
- trust/security effects are explicit in naming
- no generic `utils/helpers/misc/common` names were introduced
- errors are typed and boundary-safe
- tests mirror source structure
- subsystem vocabulary matches this document
- behavior remains aligned with governing TRDs

---

## Final Rule

If a name or pattern makes a security-sensitive action sound generic, it is probably wrong.

Forge code should read like a precise technical system:
- what trust level it handles
- what boundary it crosses
- what policy it evaluates
- what event it records
- what replay state it reconstructs

Clarity is a security property.