# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and required code patterns for the full Forge platform. It applies across all repositories and subsystems unless a subsystem TRD states a stricter rule.

## Source of Truth

- The Forge platform is specified by TRDs in `forge-docs/`.
- TRDs override this document when they define stricter or subsystem-specific behavior.
- Security-sensitive work must comply with the platform security TRD before implementation.
- Do not invent interfaces, state machines, or error contracts that contradict the TRDs.

## General Principles

- Prefer explicitness over cleverness.
- Keep module boundaries strict.
- Do not couple subsystems through hidden imports, implicit globals, or ad hoc shared state.
- Keep security, auditability, and replayability visible in code structure.
- Never execute generated, untrusted, or externally retrieved code unless a TRD explicitly permits it.
- Make all external boundaries typed, validated, and observable.
- Tests must mirror production structure and naming.

---

## File and Directory Naming (exact `src/` layout)

Top-level source directories must follow this layout exactly:

```text
src/
  cal/           # Conversation Abstraction Layer components
  dtl/           # Data Trust Label components
  trustflow/     # TrustFlow audit stream components
  vtz/           # Virtual Trust Zone enforcement
  trustlock/     # Cryptographic machine identity
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

- Directory names are lowercase.
- Use singular subsystem directory names exactly as listed above.
- Do not create alias directories, abbreviations beyond approved subsystem names, or duplicate domains.
- Tests must mirror `src/` structure exactly for implementation modules.
- SDK tests live under `tests/connector/`.

### Python File Naming

- Use `snake_case.py` for all Python module filenames.
- Prefer nouns for domain modules:
  - `policy_engine.py`
  - `audit_stream.py`
  - `trust_label.py`
- Use verb-noun names for action-oriented modules only when the module is primarily procedural:
  - `emit_event.py`
  - `replay_session.py`
- Avoid generic names:
  - Bad: `utils.py`, `helpers.py`, `common.py`, `misc.py`
  - Good: `json_canonicalization.py`, `signature_verifier.py`

### Swift File Naming

- Swift filenames must match the primary type name.
- Use `PascalCase.swift`:
  - `SessionCoordinator.swift`
  - `TrustZonePolicy.swift`
- SwiftUI view files end with `View.swift` unless the TRD defines a required suffix:
  - `AuditTimelineView.swift`
  - `PolicyEditorView.swift`

### Test File Naming

- Python tests: `test_<module_name>.py`
- Swift tests: `<TypeName>Tests.swift`
- Integration tests may use behavior naming:
  - `test_replay_end_to_end.py`
  - `test_policy_decision_roundtrip.py`

### Generated and Fixture Directories

Use explicit names only:

```text
fixtures/
snapshots/
schemas/
migrations/
contracts/
examples/
```

Do not use:
- `tmp_data/`
- `junk/`
- `scratch/`
- `new/`

---

## Class and Function Naming

### Classes, Structs, Enums, Protocols, Interfaces

- Use `PascalCase`.
- Names must be domain-specific and role-specific.
- Suffixes should indicate responsibility.

Examples:
- `PolicyEngine`
- `TrustLabelResolver`
- `ReplaySession`
- `MachineIdentityAttestor`
- `AuditEventEncoder`

### Protocol and Interface Naming

#### Swift
- Prefer capability-based protocol names.
- Use `...ing` only if the protocol represents behavior and reads naturally.
- Otherwise use domain-specific nouns.

Good:
- `PolicyEvaluating`
- `AuditStreamWriting`
- `CredentialProviding`

Also acceptable:
- `PolicyEvaluator`
- `AuditWriter`

Avoid:
- `ManagerProtocol`
- `BaseHandler`
- `ITrustService`

#### Python
- For abstract base classes, use concrete role nouns:
  - `PolicyProvider`
  - `TrustAnchorStore`
  - `ReplayTransport`
- Do not prefix with `I`.

### Functions and Methods

- Use `snake_case` in Python.
- Use `camelCase` in Swift.
- Function names must be verbs or verb phrases.
- Predicate functions must read as booleans:
  - Python: `is_trusted()`, `has_expired()`, `can_replay()`
  - Swift: `isTrusted`, `hasExpired`, `canReplay`

### Factory and Constructor Naming

Use explicit creation verbs:
- `from_json`
- `from_bytes`
- `build_policy_context`
- `makeReplaySession()`
- `createAuditEnvelope()`

Avoid ambiguous constructors:
- `load()`
- `initThing()`
- `processData()`

### Async Function Naming

- Do not encode async in the name unless required for clarity.
- Prefer names that describe outcome, not mechanism.
- If both sync and async versions exist, add explicit suffix:
  - Python: `fetch_policy()`, `fetch_policy_async()`
  - Swift: `fetchPolicy() async`

### Constants

- Python module constants: `UPPER_SNAKE_CASE`
- Swift static constants: `camelCase`
- Security, protocol, and wire-format constants should be grouped in dedicated modules/types.

Example:
```python
MAX_AUDIT_BATCH_SIZE = 500
DEFAULT_REPLAY_WINDOW_SECONDS = 30
```

---

## Error and Exception Patterns

Errors must be typed, explicit, and mappable to subsystem contracts.

### Core Rules

- Never raise raw strings.
- Never swallow exceptions silently.
- Never use broad `except Exception:` without rethrowing or mapping to a typed error.
- Every external boundary must convert implementation errors into contract errors.
- Error messages must be actionable and safe for logs.

### Python Error Conventions

- Custom exceptions use `PascalCase` and end with `Error`.
- Exception module names use `snake_case`, usually `errors.py` within a subsystem package.
- Create subsystem-scoped base errors.

Example:
```python
class CalError(Exception):
    pass

class ConversationStateError(CalError):
    pass

class TranscriptValidationError(CalError):
    pass
```

#### Python Error Hierarchy Pattern

```python
class SubsystemError(Exception):
    """Base error for subsystem."""

class ValidationError(SubsystemError):
    """Input or schema validation failure."""

class ContractError(SubsystemError):
    """Interface or protocol contract violation."""

class ExternalDependencyError(SubsystemError):
    """Provider, network, or upstream service failure."""

class SecurityPolicyError(SubsystemError):
    """Security control or policy enforcement failure."""
```

### Swift Error Conventions

- Use typed `enum` errors conforming to `Error`.
- Name them `<Subsystem><Thing>Error` or `<Thing>Error`.
- Cases must be specific and payload-bearing when useful.

Example:
```swift
enum PolicyDecisionError: Error {
    case invalidInput(reason: String)
    case denied(policyId: String)
    case transportFailure(underlying: Error)
}
```

### Error Mapping Rules

At subsystem boundaries:
- Validation failures map to validation/contract errors.
- Provider/network issues map to external dependency errors.
- Security enforcement failures map to security policy errors.
- Persistence failures map to storage/replay/audit-specific errors.
- Do not leak raw provider errors to UI or public APIs.

### Logging Rules for Errors

- Log with correlation IDs, event IDs, request IDs, or replay IDs when available.
- Do not log secrets, tokens, private keys, full credentials, or sensitive payloads.
- Redact structured fields instead of dropping entire events when possible.
- Security denials must be observable in logs and audit streams if required by TRD.

### Result Pattern

Use explicit result objects when:
- A TRD defines machine-readable failure reasons.
- A caller must branch on failure category without exception handling.
- Policy, audit, replay, or trust decisions need structured denial reasons.

Example:
```python
@dataclass(frozen=True)
class PolicyDecisionResult:
    allowed: bool
    reason_code: str
    explanation: str | None = None
```

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation orchestration, message normalization, intent/session abstractions, and model-facing transcript shaping.

### Naming Rules

- Use `Conversation`, `Message`, `Transcript`, `Turn`, `Intent`, `Session`, `Prompt`, `Adapter` precisely.
- Do not use chat-oriented casual names when the TRD defines formal domain terms.
- Normalization components should use `Normalizer`, `Canonicalizer`, or `Transformer`.
- Model-facing boundary components should use `ProviderAdapter`, `ModelClient`, or `TranscriptEncoder`.
- Session lifecycle components should use `SessionCoordinator`, `SessionState`, `TurnPlanner`.

### Preferred Names

- `ConversationSession`
- `TranscriptNormalizer`
- `IntentClassifier`
- `PromptAssembler`
- `ProviderAdapter`
- `TurnContext`

### Avoid

- `ChatThing`
- `MsgManager`
- `AIWrapper`
- `HandlerBase`

### Typical Module Layout

```text
src/cal/
  session.py
  transcript.py
  messages.py
  intent_classifier.py
  prompt_assembler.py
  provider_adapter.py
  errors.py
```

---

## `src/dtl/` — Data Trust Label

Purpose: data classification, provenance, trust labeling, label propagation, and trust policy metadata.

### Naming Rules

- Use `TrustLabel`, `Provenance`, `Classification`, `Source`, `Lineage`, `Sensitivity`.
- Label calculators should use `Resolver`, `Evaluator`, or `Propagator`.
- Encoded forms should use `Envelope`, `Descriptor`, or `Record`.
- Validation logic should use `Validator`.

### Preferred Names

- `TrustLabel`
- `TrustLabelResolver`
- `ProvenanceRecord`
- `ClassificationPolicy`
- `LabelPropagator`
- `SensitivityValidator`

### Avoid

- `Tag`
- `MetaInfo`
- `TrustStuff`
- `DataFlags`

### Typical Module Layout

```text
src/dtl/
  trust_label.py
  provenance.py
  classification.py
  label_propagator.py
  validator.py
  errors.py
```

---

## `src/trustflow/` — TrustFlow Audit Stream

Purpose: append-only audit stream, event serialization, integrity chaining, ingestion, export, and verification.

### Naming Rules

- Use `AuditEvent`, `AuditEnvelope`, `AuditStream`, `ChainLink`, `Sequence`, `Verifier`, `Emitter`.
- Append-only semantics must be reflected in names.
- Serialization components use `Encoder` / `Decoder`.
- Integrity components use `Hasher`, `Signer`, `Verifier`, `ChainBuilder`.

### Preferred Names

- `AuditEvent`
- `AuditStreamWriter`
- `AuditEnvelopeEncoder`
- `IntegrityChainVerifier`
- `AuditSequenceCursor`
- `EventEmitter`

### Avoid

- `Logger` for audit-stream writers unless it is truly plain logging.
- `HistoryManager`
- `RecordKeeper`
- `StreamStuff`

### Typical Module Layout

```text
src/trustflow/
  audit_event.py
  audit_stream.py
  envelope.py
  chain_builder.py
  verifier.py
  emitter.py
  errors.py
```

---

## `src/vtz/` — Virtual Trust Zone

Purpose: trust boundary enforcement, isolation policy application, zone transitions, capability gating, and execution constraints.

### Naming Rules

- Use `TrustZone`, `Boundary`, `Capability`, `Transition`, `Guard`, `Enforcer`, `Constraint`.
- Policy decision objects should include `Decision`, `Verdict`, or `Evaluation`.
- Transition components should use `TransitionGuard`, `BoundaryEnforcer`, `ZonePolicy`.

### Preferred Names

- `TrustZonePolicy`
- `BoundaryEnforcer`
- `CapabilityGuard`
- `ZoneTransition`
- `ExecutionConstraint`
- `ZoneDecision`

### Avoid

- `Sandbox` unless the TRD explicitly uses that term.
- `SecurityManager`
- `Restrictor`
- `MagicGate`

### Typical Module Layout

```text
src/vtz/
  trust_zone.py
  boundary.py
  capability_guard.py
  transition.py
  constraints.py
  policy.py
  errors.py
```

---

## `src/trustlock/` — Cryptographic Machine Identity

Purpose: machine identity, attestation, TPM-anchored trust, key lifecycle, and cryptographic proof material.

### Naming Rules

- Use `MachineIdentity`, `Attestation`, `TrustAnchor`, `KeyHandle`, `KeyMaterial`, `Signer`, `Verifier`.
- Hardware-bound identities should be explicit in names.
- Key lifecycle modules use `Provisioner`, `Rotator`, `Deriver`, `Store`.
- Do not use ambiguous names like `token`, `secret`, or `credential` when the artifact is a key, certificate, or attestation.

### Preferred Names

- `MachineIdentityAttestor`
- `AttestationVerifier`
- `TrustAnchorStore`
- `KeyProvisioner`
- `KeyRotationPolicy`
- `IdentityProofEnvelope`

### Avoid

- `CryptoUtils`
- `TPMHelper`
- `SecretManager`
- `IdentityThing`

### Typical Module Layout

```text
src/trustlock/
  machine_identity.py
  attestation.py
  trust_anchor.py
  key_provisioner.py
  verifier.py
  errors.py
```

---

## `src/mcp/` — MCP Policy Engine

Purpose: policy evaluation, rule execution, policy loading, decision trace generation, and enforcement recommendations.

### Naming Rules

- Use `Policy`, `Rule`, `Decision`, `Effect`, `Evaluator`, `Resolver`, `Trace`.
- Machine-readable policy results should use `DecisionResult`, `DecisionTrace`, `EvaluationContext`.
- Policy sources should use `Loader`, `Repository`, or `Provider`.
- Enforcement output should use `Recommendation` or `Directive` if distinct from decision.

### Preferred Names

- `PolicyEngine`
- `RuleEvaluator`
- `DecisionTrace`
- `PolicyLoader`
- `EvaluationContext`
- `EnforcementDirective`

### Avoid

- `Checker`
- `LogicManager`
- `Brain`
- `PolicyStuff`

### Typical Module Layout

```text
src/mcp/
  policy_engine.py
  rule_evaluator.py
  decision.py
  trace.py
  loader.py
  errors.py
```

---

## `src/rewind/` — Forge Rewind Replay Engine

Purpose: deterministic replay, event reconstruction, execution timeline recovery, debugging replay, and audit-correlated re-simulation.

### Naming Rules

- Use `Replay`, `Timeline`, `Checkpoint`, `Cursor`, `Reconstructor`, `Session`.
- Determinism-related components should use `Deterministic`, `Canonical`, or `Stable`.
- State reconstruction modules should use `Rebuilder`, `Reconstructor`, or `Projector`.

### Preferred Names

- `ReplaySession`
- `TimelineCursor`
- `CheckpointStore`
- `EventReconstructor`
- `DeterministicProjector`
- `ReplayVerifier`

### Avoid

- `TimeMachine`
- `DebugRunner`
- `ReplayerThing`
- `PlaybackManager`

### Typical Module Layout

```text
src/rewind/
  replay_session.py
  timeline.py
  checkpoint.py
  reconstructor.py
  projector.py
  errors.py
```

---

## `sdk/connector/` — Forge Connector SDK

Purpose: external integration SDK for connectors into Forge systems.

### Naming Rules

- Use `Connector`, `Client`, `Request`, `Response`, `Capability`, `Registration`, `Handshake`.
- Public SDK APIs must favor stable, descriptive names over internal shorthand.
- Version-sensitive APIs should include `Version`, `Contract`, or `Schema` where relevant.
- Adapter layers should use `Adapter` only when translating external contracts.

### Preferred Names

- `ForgeConnector`
- `ConnectorClient`
- `RegistrationRequest`
- `CapabilityDescriptor`
- `HandshakeResponse`
- `ConnectorContract`

### Avoid

- `SDKManager`
- `ClientWrapper`
- `GlueCode`
- `Helper`

### Typical Module Layout

```text
sdk/connector/
  client.py
  connector.py
  registration.py
  capability.py
  handshake.py
  errors.py
```

---

## Cross-Subsystem Patterns

### Data Models

- Use immutable models by default where language and subsystem permit.
- Separate wire models from domain models.
- Separate policy input models from policy decision output models.
- Give serialization methods explicit names:
  - `to_dict`
  - `from_dict`
  - `to_json`
  - `from_json`

### Validation

- Validate at boundaries:
  - API ingress
  - socket ingress
  - file parsing
  - environment/config loading
  - connector handshakes
  - policy loading
- Use dedicated validators for nontrivial schemas.
- Validation code must not mutate input.

### Serialization

- Prefer canonical serialization where replay, audit, signatures, or hashing are involved.
- Encoder/decoder names must indicate format:
  - `JsonEncoder`
  - `CanonicalJsonEncoder`
  - `LineDelimitedJsonDecoder`

### State Machines

- State types should be explicit:
  - `SessionState`
  - `ReplayState`
  - `TransitionState`
- Allowed transitions should be centralized, testable, and not hidden in UI or transport code.

### Dependency Boundaries

- `cal` must not absorb policy logic that belongs in `mcp`.
- `mcp` must not absorb cryptographic trust identity concerns from `trustlock`.
- `trustflow` owns audit stream semantics, not application logging.
- `rewind` consumes durable event history; it does not define source-of-truth business policy.
- `vtz` owns boundary enforcement semantics, not generic business authorization naming.
- `dtl` owns trust labels and provenance semantics, not arbitrary metadata.

---

## Code Patterns

### Preferred Module Pattern

```python
from dataclasses import dataclass

class McpError(Exception):
    pass

@dataclass(frozen=True)
class EvaluationContext:
    subject_id: str
    resource_id: str
    action: str

class PolicyEngine:
    def evaluate(self, context: EvaluationContext) -> "DecisionResult":
        ...
```

### Preferred Boundary Pattern

```python
class PolicyLoader:
    def load_from_file(self, path: str) -> Policy:
        try:
            raw = self._read_file(path)
            return self._parse_policy(raw)
        except OSError as exc:
            raise ExternalDependencyError("failed to read policy file") from exc
        except ValueError as exc:
            raise ValidationError("invalid policy format") from exc
```

### Preferred Audit Pattern

```python
@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    sequence_id: int
    event_type: str
    occurred_at: str
```

### Preferred Replay Pattern

```python
class ReplaySession:
    def replay_until(self, checkpoint_id: str) -> ReplayState:
        ...
```

---

## Naming Anti-Patterns

Do not introduce these names unless a TRD explicitly requires them:

- `Manager`
- `Helper`
- `Util` / `Utils`
- `BaseThing`
- `Processor` when the role is actually evaluator, encoder, verifier, resolver, or coordinator
- `Data` as a suffix when the actual type is known
- `Info` as a suffix when the actual type is known
- `Wrapper` unless it is literally a compatibility wrapper
- `Impl` suffixes in public code
- `Final` / `New` / `Temp` in filenames or types

Replace vague names with role-specific names:
- `PolicyManager` → `PolicyEngine` or `PolicyRepository`
- `AuditHelper` → `AuditEnvelopeEncoder`
- `TrustData` → `TrustLabelRecord`
- `ReplayProcessor` → `EventReconstructor`

---

## Test Conventions

- Tests must mirror production module paths.
- One test module per production module where practical.
- Test names must describe behavior, not implementation details.
- Prefer:
  - `test_denies_transition_without_required_capability`
  - `test_reconstructs_timeline_from_canonical_audit_events`
- Avoid:
  - `test_policy_engine_1`
  - `test_happy_path`
  - `test_misc`

### Test Class Naming

- Python test classes: `Test<Thing>`
- Swift test classes: `<Thing>Tests`

### Required Test Areas

For every subsystem, add tests for:
- valid input behavior
- invalid input behavior
- boundary/contract violations
- serialization round-trips where applicable
- replay determinism where applicable
- error mapping
- audit emission if the subsystem emits audit-relevant events
- security denials and enforcement behavior where applicable

---

## Documentation Conventions

- Public modules, classes, and functions must have concise docstrings or documentation comments.
- Docstrings must describe:
  - purpose
  - key inputs
  - key outputs
  - failure conditions when non-obvious
- Keep examples aligned with actual names and contracts.
- Do not document speculative behavior.

---

## Security Conventions

- Never hardcode credentials, secrets, private keys, or tokens.
- Never log secret-bearing values.
- Use explicit names for sensitive material:
  - `access_token`
  - `private_key_pem`
  - `attestation_blob`
- Redaction helpers must be centralized and tested.
- Security decisions must be represented with typed outcomes or typed errors.
- Any code touching credentials, attestation, policy enforcement, external content, CI, or generated code must follow the governing security TRD.

---

## Compatibility and Versioning

- Public SDK and connector contracts must be version-aware.
- When behavior depends on a versioned contract, encode that in names or type fields:
  - `contract_version`
  - `schema_version`
  - `api_version`
- Avoid silent fallback across versions unless a TRD explicitly requires it.

---

## Commit-Level Expectations

Before merging any convention-affecting change:

- confirm naming aligns with subsystem TRD vocabulary
- confirm tests mirror source structure
- confirm errors map cleanly to contract boundaries
- confirm no vague filenames or type names were introduced
- confirm logs and audit records do not expose sensitive values
- confirm replay- or audit-relevant serialization remains canonical where required

---

## Quick Reference

### Approved subsystem directories

- `src/cal/`
- `src/dtl/`
- `src/trustflow/`
- `src/vtz/`
- `src/trustlock/`
- `src/mcp/`
- `src/rewind/`
- `sdk/connector/`

### Naming styles

- Python files: `snake_case.py`
- Swift files: `PascalCase.swift`
- Python functions: `snake_case`
- Swift methods: `camelCase`
- Types: `PascalCase`
- Python constants: `UPPER_SNAKE_CASE`

### Approved role suffixes

- `Engine`
- `Evaluator`
- `Resolver`
- `Verifier`
- `Encoder`
- `Decoder`
- `Coordinator`
- `Assembler`
- `Propagator`
- `Reconstructor`
- `Projector`
- `Provider`
- `Repository`
- `Store`
- `Guard`
- `Enforcer`
- `Directive`
- `Trace`

### Disallowed vague suffixes

- `Manager`
- `Helper`
- `Utils`
- `Thing`
- `Stuff`
- `Wrapper`
- `Impl`

This document is the default naming and structure contract for Forge platform code. When implementing a subsystem, prefer the exact vocabulary of that subsystem’s TRD and keep interfaces explicit, typed, and testable.