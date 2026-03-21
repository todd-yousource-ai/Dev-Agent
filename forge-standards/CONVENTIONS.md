# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, error patterns, and code structure for the full Forge platform.

The platform conventions are derived from:
- The Forge TRDs in `forge-docs/` as the source of truth
- Repository guidance in `AGENTS.md`, `CLAUDE.md`, and `README.md`
- The platform’s subsystem naming and directory rules

If any convention here conflicts with a TRD, the TRD wins.

---

## Core Principles

- Match the owning TRD before writing code.
- Keep subsystem boundaries explicit.
- Prefer small, typed, testable units over clever abstractions.
- Never invent protocol fields, error shapes, or security behavior not specified by TRD.
- Keep generated, external, and untrusted content clearly separated from trusted control logic.
- Do not execute generated code.
- Keep naming stable and predictable across Swift, Python, tests, and docs.
- Tests must mirror implementation structure.

---

## File and Directory Naming (exact `src/` layout)

### Top-level source layout

The source tree must use these canonical directories:

```text
src/cal/           # Conversation Abstraction Layer components
src/dtl/           # Data Trust Label components
src/trustflow/     # TrustFlow audit stream components
src/vtz/           # Virtual Trust Zone enforcement
src/trustlock/     # Cryptographic machine identity (TPM-anchored)
src/mcp/           # MCP Policy Engine
src/rewind/        # Forge Rewind replay engine
sdk/connector/     # Forge Connector SDK
tests/<subsystem>/ # Tests mirror src/ structure exactly
```

### Rules

- Directory names are lowercase.
- Subsystem directories use the exact canonical names above.
- Do not create synonyms or aliases such as:
  - `src/conversation_layer/`
  - `src/policy/`
  - `src/audit/`
  - `src/replay/`
- Shared code must live in an explicitly named shared package only if allowed by the owning TRD.
- Do not move a component between subsystems to “simplify” architecture.
- Tests must mirror source structure exactly.

### Internal directory structure

Within each subsystem:

- Use lowercase directory names.
- Prefer noun-based directories for domains and verb-free structure.
- Keep hierarchy shallow unless the TRD requires layered separation.
- Use consistent package partitions such as:
  - `models/`
  - `services/`
  - `adapters/`
  - `validators/`
  - `protocols/`
  - `storage/`
  - `crypto/`
  - `transport/`
  - `policy/`
  - `replay/`

Example:

```text
src/mcp/
  models/
  policy/
  evaluators/
  adapters/
  errors/
```

### File naming

#### Python

- Use `snake_case.py` for all Python file names.
- File names should describe the primary responsibility.
- Prefer singular nouns unless the file is a collection of related handlers or tests.

Examples:
- `policy_engine.py`
- `trust_label.py`
- `audit_stream_writer.py`
- `replay_session.py`
- `machine_identity_verifier.py`

Avoid:
- `utils.py`
- `helpers.py`
- `misc.py`
- `common.py` unless truly cross-cutting and specifically approved

#### Swift

- Use `PascalCase.swift` for type-centric files.
- File name must match the primary public type in the file.
- If a file contains extensions only, use `TypeName+Concern.swift`.

Examples:
- `PolicyEngine.swift`
- `TrustLabel.swift`
- `UnixSocketTransport.swift`
- `AuditEvent+Encoding.swift`

Avoid:
- `Manager.swift` unless it is truly lifecycle orchestration
- `Thing.swift`
- `Extensions.swift`

#### Test files

- Python tests use `test_<module_name>.py`.
- Swift tests use `<TypeName>Tests.swift`.
- Test directories must mirror `src/` exactly.

Examples:

```text
src/dtl/trust_label.py
tests/dtl/test_trust_label.py

src/mcp/policy_engine.py
tests/mcp/test_policy_engine.py
```

---

## Class and Function Naming

## General naming rules

- Types use clear domain names.
- Names must reflect the subsystem vocabulary used in the TRD.
- Prefer full words over abbreviations, except approved subsystem names:
  - CAL
  - DTL
  - MCP
  - VTZ
- Avoid ambiguous names like `Data`, `Info`, `Handler`, `Processor`, `Manager`, `Util`.
- Use suffixes only when they communicate architecture, not habit.

Preferred suffixes:
- `Engine`
- `Evaluator`
- `Validator`
- `Adapter`
- `Provider`
- `Client`
- `Service`
- `Store`
- `Repository`
- `Encoder`
- `Decoder`
- `Serializer`
- `Verifier`
- `Signer`
- `Recorder`
- `Replayer`

### Python naming

- Classes: `PascalCase`
- Functions: `snake_case`
- Methods: `snake_case`
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private/internal helpers: prefix with `_`
- Module-level singleton state is discouraged unless required by TRD

Examples:
- `class PolicyEngine`
- `def evaluate_policy(...)`
- `TRUST_LABEL_VERSION = 1`
- `def _normalize_subject(...)`

### Swift naming

- Types, protocols, enums: `PascalCase`
- Functions, methods, properties, enum cases: `camelCase`
- Static constants: `camelCase`
- Acronyms follow Swift conventions unless subsystem acronym is a defined term:
  - `MCPPolicyEngine`
  - `DTLLabel`
  - `VTZBoundary`
  - `url`, `id`, `xpcClient`

Examples:
- `struct TrustLabel`
- `enum PolicyDecision`
- `protocol AuditEventEncoder`
- `func evaluate(request: PolicyRequest)`

---

## Class design conventions

- One primary type per file.
- Public APIs must expose domain language, not implementation details.
- Constructors must validate required invariants early.
- Prefer immutable value objects for labels, claims, events, and decisions.
- Stateful components must make lifecycle explicit:
  - `start()`
  - `stop()`
  - `close()`
  - `reset()`
- Side-effecting classes should expose intent in the name:
  - `AuditStreamWriter`
  - `ReplaySessionRecorder`
  - `MachineIdentityVerifier`

### Protocols and interfaces

Use capability-oriented names:
- `PolicyEvaluating`
- `AuditEventWriting`
- `TrustLabelEncoding`
- `ReplayStore`

Do not use:
- `IPolicyEngine`
- `AbstractPolicy`
- `BaseManager`

### Factory and builder naming

Use these only when warranted by complexity:
- `...Factory`
- `...Builder`
- `...Assembler`

Examples:
- `TrustZoneFactory`
- `PolicyRequestBuilder`

---

## Function naming conventions

### Query vs command separation

Functions that return data without side effects should use query names:
- `get_label()` only if required by external API
- Prefer `load_label()`, `fetch_label()`, `read_label()`, `find_label()`
- In Swift, prefer `label(for:)` or `loadLabel(for:)`

Functions with side effects should use command verbs:
- `apply_policy()`
- `write_event()`
- `record_session()`
- `verify_attestation()`

### Boolean-returning functions

Use affirmative predicates:
- `is_trusted()`
- `is_within_boundary()`
- `has_required_claims()`
- `can_replay()`
- `should_quarantine()`

Avoid:
- `check_trust()`
- `process_policy()`
- `handle_data()`

### Async naming

#### Python
- Do not suffix async functions with `_async` unless needed to distinguish from sync variants.
- Prefer clear coroutine names:
  - `fetch_attestation()`
  - `stream_audit_events()`

#### Swift
- Do not suffix async APIs with `Async`.
- Rely on Swift concurrency syntax.

---

## Error and Exception Patterns

## General rules

- Errors are part of the interface contract.
- Match TRD-defined error categories and payloads exactly.
- Never swallow security-relevant or policy-relevant failures.
- Fail closed for trust, identity, policy, and boundary enforcement.
- Error messages must be actionable but must not leak secrets, credentials, or sensitive internals.
- External input errors, policy denials, system failures, and integrity failures must be distinguishable.

---

## Error taxonomy

Every subsystem should classify errors into one or more of these categories where applicable:

- `ValidationError`
- `ConfigurationError`
- `AuthenticationError`
- `AuthorizationError`
- `PolicyEvaluationError`
- `TrustViolationError`
- `IntegrityError`
- `AttestationError`
- `TransportError`
- `SerializationError`
- `StorageError`
- `ReplayError`
- `TimeoutError`
- `DependencyUnavailableError`

If a TRD defines subsystem-specific error names, use those exact names.

---

## Python exception conventions

- Custom exceptions must inherit from a subsystem-scoped base exception.
- Name exceptions with `Error` suffix.
- Use typed exceptions, not generic `Exception`.
- Preserve root cause with `raise ... from exc`.

Example:

```python
class MCPError(Exception):
    """Base exception for MCP subsystem."""

class PolicyEvaluationError(MCPError):
    """Raised when policy evaluation cannot complete."""

class AuthorizationError(MCPError):
    """Raised when a subject is denied by policy."""
```

Rules:
- Do not return error strings in place of exceptions.
- Do not catch broad `Exception` unless:
  - adding context,
  - sanitizing output,
  - or converting to a boundary-safe error type.
- Log with structured fields.
- Secret-bearing values must never appear in exception text.

Example:

```python
try:
    decision = evaluator.evaluate(request)
except ParserError as exc:
    raise PolicyEvaluationError("invalid policy document") from exc
```

---

## Swift error conventions

- Define typed errors as `enum ...Error: Error`.
- Use narrow error enums per component or subsystem.
- Conform to `LocalizedError` only when user-facing messages are required.
- Separate internal diagnostic detail from user-presentable messaging.
- Use associated values only for non-sensitive context.

Example:

```swift
enum TrustLockError: Error {
    case invalidAttestationFormat
    case signatureVerificationFailed
    case attestationExpired
}
```

Rules:
- Do not use `NSError` as the primary domain model.
- Convert external framework errors at boundaries.
- Do not expose raw backend or crypto errors directly to UI layers.
- Prefer exhaustive switching for error handling in critical paths.

---

## Error boundary patterns

At every subsystem boundary:
- Convert foreign errors into local domain errors.
- Preserve original cause internally where supported.
- Sanitize logs and user-visible messages.
- Attach correlation IDs or request IDs where defined by TRD.

Pattern:
- External library error -> adapter error
- Adapter error -> subsystem error
- Subsystem error -> API or UI-safe error

---

## Logging and error coupling

- Logs must complement errors, not replace them.
- Every critical failure path should emit:
  - subsystem name
  - operation name
  - correlation/request ID if present
  - non-sensitive reason code
- Never log:
  - tokens
  - private keys
  - raw attestation blobs unless explicitly permitted by TRD
  - unredacted user secrets
  - complete untrusted payloads in sensitive paths

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation orchestration, message abstraction, provider-neutral conversational state and exchange models.

### Naming rules

- Prefix domain types with `Conversation`, `Message`, `Turn`, `Transcript`, or `Session` where appropriate.
- Provider-agnostic interfaces must not include vendor names.
- Adapter types may include provider names only in adapter implementations.

Preferred names:
- `ConversationSession`
- `ConversationTurn`
- `TranscriptStore`
- `MessageEnvelope`
- `ProviderAdapter`
- `ConversationRequestEncoder`

Avoid:
- `ClaudeConversation`
- `GPTManager`
- `ChatThing`

### File examples

- `src/cal/conversation_session.py`
- `src/cal/message_envelope.py`
- `src/cal/provider_adapter.py`

### Error examples

- `ConversationStateError`
- `ProviderAdapterError`
- `TranscriptSerializationError`

---

## `src/dtl/` — Data Trust Label

Purpose: trust labeling, classification, provenance, handling constraints.

### Naming rules

- Core types should use `TrustLabel`, `LabelClaim`, `Provenance`, `Classification`, `HandlingRule`.
- Validation logic should use `Validator` or `Verifier`.
- Encoding/decoding types should be explicit.

Preferred names:
- `TrustLabel`
- `TrustLabelValidator`
- `ProvenanceChain`
- `ClassificationLevel`
- `HandlingConstraint`
- `TrustLabelEncoder`

Avoid:
- `Tag`
- `Meta`
- `Stamp`
- `DataInfo`

### File examples

- `src/dtl/trust_label.py`
- `src/dtl/provenance_chain.py`
- `src/dtl/trust_label_validator.py`

### Error examples

- `TrustLabelValidationError`
- `ProvenanceError`
- `ClassificationError`

---

## `src/trustflow/` — TrustFlow audit stream

Purpose: immutable or append-only audit event pipelines, trust event capture, audit query and export.

### Naming rules

- Core event types should use `AuditEvent`, `TrustEvent`, `EventEnvelope`, `EventRecord`.
- Components that write streams should use `Writer`, `Appender`, or `Recorder`.
- Components that read/query should use `Reader`, `QueryService`, or `Exporter`.

Preferred names:
- `AuditEvent`
- `TrustEventRecorder`
- `AuditStreamWriter`
- `AuditQueryService`
- `EventEnvelopeEncoder`

Avoid:
- `Logger` for audit-meaningful streams
- `HistoryManager`
- `EventThing`

### File examples

- `src/trustflow/audit_event.py`
- `src/trustflow/audit_stream_writer.py`
- `src/trustflow/audit_query_service.py`

### Error examples

- `AuditWriteError`
- `AuditIntegrityError`
- `AuditExportError`

---

## `src/vtz/` — Virtual Trust Zone

Purpose: trust boundary enforcement, isolation checks, zone transitions, containment policy.

### Naming rules

- Core types should use `TrustZone`, `Boundary`, `ZonePolicy`, `ZoneTransition`, `Containment`.
- Enforcement components should use `Enforcer`, `Guard`, `BoundaryEvaluator`, `TransitionValidator`.

Preferred names:
- `VirtualTrustZone`
- `TrustBoundary`
- `ZonePolicyEnforcer`
- `ZoneTransitionValidator`
- `ContainmentRule`

Avoid:
- `SandboxManager` unless that is the exact TRD term
- `SecurityLayer`
- `ZoneThing`

### File examples

- `src/vtz/trust_boundary.py`
- `src/vtz/zone_policy_enforcer.py`
- `src/vtz/zone_transition_validator.py`

### Error examples

- `BoundaryViolationError`
- `ZoneTransitionError`
- `ContainmentPolicyError`

---

## `src/trustlock/` — Cryptographic machine identity

Purpose: TPM-anchored identity, attestation, key lifecycle, machine verification.

### Naming rules

- Core types should use `MachineIdentity`, `Attestation`, `KeyMaterial`, `KeyHandle`, `Signer`, `Verifier`.
- TPM-related names should be explicit when TRD requires them.
- Crypto adapters must name the primitive or trust source clearly.

Preferred names:
- `MachineIdentityVerifier`
- `AttestationDocument`
- `TPMAttestationProvider`
- `MachineKeyStore`
- `IdentitySigner`

Avoid:
- `CryptoManager`
- `KeyStuff`
- `SecureThing`

### File examples

- `src/trustlock/machine_identity_verifier.py`
- `src/trustlock/attestation_document.py`
- `src/trustlock/tpm_attestation_provider.py`

### Error examples

- `AttestationError`
- `MachineIdentityError`
- `KeyProvisioningError`
- `SignatureVerificationError`

---

## `src/mcp/` — MCP Policy Engine

Purpose: policy evaluation, policy parsing, decisioning, enforcement integration.

### Naming rules

- Core types should use `Policy`, `PolicyRule`, `PolicyRequest`, `PolicyDecision`, `Subject`, `Resource`, `Action`.
- Decisioning components should use `Evaluator`, `Engine`, `Resolver`, `Matcher`.
- Integration points should use `Adapter` or `Client`.

Preferred names:
- `MCPPolicyEngine`
- `PolicyEvaluator`
- `PolicyDecision`
- `PolicyRuleSet`
- `SubjectContext`
- `ResourceDescriptor`

Avoid:
- `RulesManager`
- `PolicyThing`
- `DecisionMaker`

### File examples

- `src/mcp/policy_engine.py`
- `src/mcp/policy_evaluator.py`
- `src/mcp/policy_decision.py`

### Error examples

- `PolicyParseError`
- `PolicyEvaluationError`
- `AuthorizationError`

---

## `src/rewind/` — Forge Rewind replay engine

Purpose: replay, deterministic reconstruction, session trace playback, audit-linked state recreation.

### Naming rules

- Core types should use `Replay`, `Rewind`, `Trace`, `Session`, `Checkpoint`, `Timeline`.
- Stateful replay components should use `Replayer`, `SessionReplayer`, `TraceLoader`, `CheckpointStore`.
- Deterministic reconstruction logic should be named explicitly.

Preferred names:
- `ReplaySession`
- `SessionReplayer`
- `TraceEnvelope`
- `TimelineCheckpoint`
- `DeterministicReconstructor`

Avoid:
- `PlaybackManager`
- `TimeMachine`
- `ReplayThing`

### File examples

- `src/rewind/replay_session.py`
- `src/rewind/session_replayer.py`
- `src/rewind/timeline_checkpoint.py`

### Error examples

- `ReplayIntegrityError`
- `CheckpointLoadError`
- `DeterminismError`

---

## `sdk/connector/` — Forge Connector SDK

Purpose: external integration SDK, connector contracts, typed client interfaces, trust-aware interoperability.

### Naming rules

- Public SDK names must be stable, explicit, and vendor-neutral.
- Use `Connector`, `Client`, `Request`, `Response`, `Event`, `Credential`, `Session`.
- Language-specific wrappers may add ecosystem idioms, but not rename protocol concepts.

Preferred names:
- `ForgeConnectorClient`
- `ConnectorRequest`
- `ConnectorResponse`
- `ConnectorSession`
- `ConnectorCredentialProvider`

Avoid:
- `SDKManager`
- `ApiHelper`
- `ServiceWrapper`

### File examples

- `sdk/connector/connector_client.py`
- `sdk/connector/connector_request.py`
- `sdk/connector/credential_provider.py`

### Error examples

- `ConnectorProtocolError`
- `ConnectorAuthenticationError`
- `ConnectorTransportError`

---

## Test Naming and Structure

### Mirroring rule

Tests must mirror implementation layout exactly.

Example:

```text
src/trustlock/attestation_document.py
tests/trustlock/test_attestation_document.py
```

### Naming rules

- Test names must describe behavior, not implementation trivia.
- Prefer:
  - `test_rejects_expired_attestation`
  - `test_records_audit_event_with_monotonic_sequence`
  - `test_denies_transition_across_untrusted_boundary`

Avoid:
- `test_basic`
- `test_happy_path`
- `test_1`

### Test organization

- Group tests by subsystem first, component second.
- Separate unit, integration, and conformance concerns clearly if the TRD requires.
- Use deterministic fixtures.
- Security-sensitive tests must include denial and tamper cases.
- Replay and audit tests must verify deterministic behavior where specified.

---

## Cross-Subsystem Patterns

## DTOs and models

- Use explicit model names:
  - `PolicyRequest`
  - `TrustLabel`
  - `AuditEvent`
  - `ZoneTransitionRequest`
- Serialization types should be distinct from runtime domain types if semantics differ.
- Do not overload one model for transport, persistence, and UI unless the TRD explicitly allows it.

## Adapters

- Adapters isolate external dependencies.
- Name them `<Dependency><Role>Adapter` or `<Provider>Adapter`.
- Keep external SDK naming at the edge.

Examples:
- `GitHubPolicyAdapter`
- `TPMAttestationAdapter`
- `ProviderAdapter`

## Stores and persistence

- Use:
  - `Store` for simple persistence interfaces
  - `Repository` for domain-aware retrieval
  - `Cache` only for non-authoritative storage
- Persistence implementations should indicate backend only when useful:
  - `SqliteAuditStore`
  - `FileCheckpointStore`

## Encoders and decoders

- `Encoder` and `Decoder` for semantic translation
- `Serializer` and `Deserializer` for format-oriented conversion
- `Parser` only when interpreting language or grammar inputs

---

## Forbidden Naming Patterns

Do not introduce these unless required by an external interface or TRD:

- `util`, `utils`, `helper`, `helpers`
- `common` for unrelated shared code
- `manager` as a default suffix
- `processor` without a clear domain qualifier
- `data` as a primary type name
- `info`, `object`, `item`, `thing`, `stuff`
- `misc`, `temp`, `new`, `old`, `final`
- single-letter class names
- vague prefixes like `my`, `custom`, `base`

If a file appears to need one of these names, split the responsibility and rename by domain behavior.

---

## Security-Sensitive Convention Additions

Applies especially to `dtl`, `trustflow`, `vtz`, `trustlock`, `mcp`, and `rewind`.

- Security enforcement types must be named so their role is unmistakable:
  - `Verifier`
  - `Enforcer`
  - `Validator`
  - `Guard`
- Fail-closed logic must be easy to locate by name.
- Trust decisions must return typed decision objects or typed denial errors.
- Tamper checks, attestation checks, signature checks, and boundary checks must be explicit in code and naming.
- Redaction logic should use names like:
  - `Redactor`
  - `Sanitizer`
  - `SecretFilter`

Avoid euphemistic names such as:
- `Cleaner`
- `Fixer`
- `Normalizer` for security enforcement steps unless they truly normalize only

---

## Documentation Conventions in Code

- Public types and functions should have concise docstrings/comments describing:
  - purpose
  - inputs/outputs
  - important invariants
  - trust or security assumptions where relevant
- Do not restate obvious code.
- Comments must explain why, not narrate syntax.
- Security-sensitive code must document trust boundaries and failure behavior.

---

## Change Discipline

Before adding or renaming any type, file, or directory:

1. Identify the owning TRD.
2. Verify subsystem ownership.
3. Match existing naming patterns in that subsystem.
4. Ensure tests mirror the structure.
5. Confirm error names and failure modes match the contract.
6. Prefer extending existing domain vocabulary over inventing new synonyms.

---

## Quick Reference

### Canonical subsystem paths

```text
src/cal/
src/dtl/
src/trustflow/
src/vtz/
src/trustlock/
src/mcp/
src/rewind/
sdk/connector/
tests/<subsystem>/
```

### Python

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Exceptions: `PascalCaseError`

### Swift

- Files: `PascalCase.swift`
- Types: `PascalCase`
- Methods/properties: `camelCase`
- Errors: `EnumNameError`

### Required qualities

- Typed errors
- Explicit domain names
- No vague helpers
- Tests mirror source
- TRD-first implementation
- Security semantics visible in naming