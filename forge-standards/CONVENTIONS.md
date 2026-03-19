# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, structural patterns, and error-handling expectations for the full Forge platform.

These conventions apply across all subsystems and languages unless a subsystem-specific rule overrides them.

---

## Core Principles

1. **TRDs are authoritative.**  
   If implementation details conflict with this document, the owning TRD wins.

2. **Security-first by default.**  
   Any code touching credentials, machine identity, remote content, generated code, policy enforcement, audit streams, or CI must follow the security TRD before implementation.

3. **No implicit behavior.**  
   Prefer explicit names, typed interfaces, explicit state transitions, explicit error mapping, and explicit trust boundaries.

4. **Interfaces are contracts.**  
   Public APIs, IPC payloads, SDK contracts, persistence models, and audit events must be versionable and stable.

5. **Generated or external content is untrusted.**  
   Treat model output, repository content, connector input, policy payloads, and replay data as hostile until validated.

6. **Tests mirror implementation structure.**  
   Test placement, naming, and fixture structure must make ownership obvious.

---

## File and Directory Naming

## File and Directory Naming (exact `src/` layout)

The platform uses the following top-level source layout:

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
  connector/
```

### Required directory names

Use these directory names exactly:

- `src/cal/` — Conversation Abstraction Layer components
- `src/dtl/` — Data Trust Label components
- `src/trustflow/` — TrustFlow audit stream components
- `src/vtz/` — Virtual Trust Zone enforcement
- `src/trustlock/` — Cryptographic machine identity
- `src/mcp/` — MCP Policy Engine
- `src/rewind/` — Forge Rewind replay engine
- `sdk/connector/` — Forge Connector SDK
- `tests/<subsystem>/` — tests mirror implementation layout exactly

### General file naming rules

#### Python
- Use `snake_case.py` for all Python modules.
- Module names must describe domain responsibility, not implementation trivia.
- Prefer singular nouns for core models and plural nouns only for collections or registries.

Examples:
- `policy_engine.py`
- `label_resolver.py`
- `audit_event.py`
- `socket_transport.py`

Avoid:
- `utils.py`
- `helpers.py`
- `misc.py`
- `common.py`

If shared functionality exists, name by purpose:
- `json_canonicalization.py`
- `signature_verifier.py`
- `repository_checkout.py`

#### Swift
- Use `PascalCase.swift` matching the primary type in the file.
- One top-level primary type per file.
- Extensions should live in:
  - same file if small and cohesive
  - `TypeName+Concern.swift` if behavior is substantial

Examples:
- `ConsensusEngine.swift`
- `ProviderAdapter.swift`
- `SocketClient.swift`
- `PolicyDecision+Formatting.swift`

#### Test files
- Python tests use `test_<module_or_behavior>.py`
- Swift tests use `<TypeName>Tests.swift`

Examples:
- `tests/dtl/test_label_resolver.py`
- `tests/trustflow/test_audit_emitter.py`
- `PolicyEngineTests.swift`

### Directory structure within each subsystem

Each subsystem should follow a predictable internal layout where applicable:

```text
src/<subsystem>/
  api/
  models/
  services/
  policies/
  transport/
  storage/
  crypto/
  replay/
  adapters/
  validation/
  errors.py
  types.py
  constants.py
```

Only create directories that are meaningfully used. Do not create empty architectural folders.

### Test mirroring rules

Tests must mirror implementation paths as closely as possible.

Example:

```text
src/dtl/models/label.py
tests/dtl/models/test_label.py
```

Example:

```text
src/mcp/policies/policy_engine.py
tests/mcp/policies/test_policy_engine.py
```

For SDK code:

```text
sdk/connector/session.py
tests/connector/test_session.py
```

---

## Class and Function Naming

## Class and Function Naming

### General naming rules

- **Classes, structs, enums, protocols, and Swift actors:** `PascalCase`
- **Python functions, variables, module names:** `snake_case`
- **Swift functions, properties, methods, parameters:** `camelCase`
- **Constants:**  
  - Python module-level constants: `UPPER_SNAKE_CASE`
  - Swift static constants: `camelCase` unless interoperating with C-style APIs
- **Private/internal helpers** must still be descriptively named; do not use abbreviations unless domain-standard.

### Naming by responsibility

Prefer names that reveal role:

- `Resolver` — determines a value from inputs and rules
- `Validator` — checks structure or semantics; does not mutate
- `Verifier` — validates cryptographic or proof-bearing claims
- `Parser` — converts raw input into structured representation
- `Encoder` / `Decoder` — serialization concerns
- `Adapter` — boundary translation between systems
- `Client` — outbound integration
- `Service` — orchestrates domain behavior
- `Engine` — core decision or execution logic
- `Registry` — lookup/registration
- `Store` / `Repository` — persistence access
- `Emitter` — sends events
- `Recorder` — persists event streams
- `Replayer` — deterministic playback
- `Factory` / `Builder` — object creation with nontrivial assembly
- `Coordinator` — multi-component workflow owner

### Boolean naming

Use boolean names that read as predicates.

Python:
- `is_verified`
- `has_signature`
- `can_replay`
- `should_quarantine`

Swift:
- `isVerified`
- `hasSignature`
- `canReplay`
- `shouldQuarantine`

Avoid ambiguous names:
- `valid`
- `enabled`
- `check`
- `status_ok`

### Verb conventions for functions

Use consistent verbs by operation type:

- `get_` / `get...` — only when retrieval may be nontrivial or remote
- `load_` / `load...` — fetch from persistence
- `read_` / `read...` — raw IO
- `parse_` / `parse...` — convert syntax to structure
- `validate_` / `validate...` — check and report
- `verify_` / `verify...` — cryptographic or provenance checks
- `resolve_` / `resolve...` — derive from policy/rules/context
- `build_` / `build...` — construct output
- `create_` / `create...` — instantiate or persist new entity
- `update_` / `update...` — mutate persisted state
- `record_` / `record...` — append auditable information
- `emit_` / `emit...` — send event externally
- `replay_` / `replay...` — deterministic event execution
- `enforce_` / `enforce...` — apply policy or security controls

Avoid weak verbs:
- `handle`
- `process`
- `do`
- `run`
- `manage`

Only use them when the abstraction truly spans multiple concrete operations.

### Interface naming

#### Python abstract interfaces
Use one of:
- `...Protocol` for typing protocol
- `...ABC` for abstract base class

Examples:
- `PolicyStoreProtocol`
- `AuditEmitterProtocol`
- `ConnectorClientABC`

#### Swift protocols
Protocols use role-based names, usually without `Protocol` suffix.

Examples:
- `PolicyEvaluating`
- `AuditEmitting`
- `TrustLabelResolving`

Use `Protocol` suffix only when required to avoid collisions or improve clarity for generated bindings.

---

## Error and Exception Patterns

## Error and Exception Patterns

### General rules

1. **Never swallow exceptions silently.**
2. **Never expose secrets in error messages, logs, or audit events.**
3. **Map low-level errors into domain errors at subsystem boundaries.**
4. **Errors must preserve enough context for diagnosis without leaking sensitive material.**
5. **Validation failures are not crashes.** They must produce typed, expected error outcomes.
6. **Security denials must be explicit.** Distinguish deny, invalid, unavailable, and internal failure.

### Python error structure

Each subsystem should define a dedicated error hierarchy in `errors.py`.

Pattern:

```python
class DtlError(Exception):
    """Base exception for the DTL subsystem."""

class LabelValidationError(DtlError):
    """Raised when a trust label is structurally or semantically invalid."""

class LabelResolutionError(DtlError):
    """Raised when a trust label cannot be resolved from available context."""

class SignatureVerificationError(DtlError):
    """Raised when a signature is missing, malformed, or invalid."""
```

Rules:
- One subsystem base exception per subsystem.
- Publicly raised exceptions must inherit from subsystem base.
- Name exceptions as nouns ending in `Error`.
- Use specific subclasses for actionable cases.
- Keep transport-specific exceptions wrapped before crossing subsystem boundaries.

### Swift error structure

Use typed enums conforming to `Error`.

Pattern:

```swift
enum PolicyEngineError: Error {
    case invalidPolicy(reason: String)
    case decisionUnavailable
    case signatureVerificationFailed
    case accessDenied(operation: String)
}
```

Rules:
- One primary error enum per major component or subsystem.
- Use associated values for safe, non-sensitive diagnostics.
- Conform to `LocalizedError` only if the message is user-safe.
- Separate user-display errors from internal diagnostic errors when needed.

### Error taxonomy

Use these categories consistently:

- `ValidationError` / `.invalid...` — input malformed or violates schema/rules
- `VerificationError` / `.verificationFailed` — cryptographic/provenance proof failed
- `AuthorizationError` / `.accessDenied` — caller not allowed
- `PolicyDecisionError` / `.decisionUnavailable` — engine cannot safely decide
- `ConflictError` / `.versionConflict` — optimistic concurrency or state race
- `TransportError` / `.connectionFailed` — IPC/network issue
- `TimeoutError` / `.timedOut` — operation exceeded limits
- `ReplayError` / `.replayFailed` — deterministic replay could not proceed
- `InternalError` / `.internalFailure` — invariant or unexpected fault

### Result patterns

#### Python
For domain operations that can fail as part of normal flow, prefer:
- typed exceptions for invalid/unrecoverable conditions
- explicit result objects when callers must branch on decision outcomes

Example:
```python
@dataclass(frozen=True)
class PolicyDecision:
    effect: PolicyEffect
    reason_code: str
    obligations: tuple[str, ...]
```

Do not use exceptions for ordinary deny outcomes.

#### Swift
Use:
- `throws` for exceptional failures
- enums/results for ordinary control flow decisions

Example:
```swift
enum PolicyEffect {
    case allow
    case deny
    case quarantine
}
```

A deny is a decision, not an exception.

### Logging and audit interaction

- Errors may be logged with correlation IDs, entity IDs, policy IDs, and redacted metadata.
- Never log:
  - raw secrets
  - tokens
  - private keys
  - full prompt contents unless explicitly permitted
  - unredacted connector payloads
  - sensitive replay artifacts

- Use structured logging fields rather than interpolated freeform strings where available.

---

## Per-Subsystem Naming Rules

## Per-Subsystem Naming Rules

### `src/cal/` — Conversation Abstraction Layer

Purpose: normalize conversation/session interactions across providers and internal orchestration.

#### File naming
Use names such as:
- `conversation_session.py`
- `message_envelope.py`
- `provider_adapter.py`
- `consensus_engine.py`
- `socket_transport.py`

#### Type naming
- `ConversationSession`
- `MessageEnvelope`
- `ProviderAdapter`
- `ConsensusEngine`
- `ConversationTurn`
- `ResponseCandidate`
- `ArbitrationResult`

#### Function naming
- `start_session`
- `append_turn`
- `build_prompt_context`
- `request_candidate_responses`
- `arbitrate_responses`
- `serialize_message_envelope`

#### Naming guidance
- Use `candidate` for model outputs prior to selection.
- Use `arbitration` for Claude-selected consensus outcomes.
- Use `turn` for one interaction unit.
- Use `session` for persistent conversation state.
- Do not use `chat` in core abstractions unless it specifically maps to an external provider API.

---

### `src/dtl/` — Data Trust Label

Purpose: assign, validate, propagate, and enforce trust metadata on data objects.

#### File naming
Use names such as:
- `label.py`
- `label_resolver.py`
- `label_validator.py`
- `classification_policy.py`
- `provenance_chain.py`
- `signature_verifier.py`

#### Type naming
- `TrustLabel`
- `LabelResolver`
- `LabelValidator`
- `ClassificationPolicy`
- `ProvenanceChain`
- `LabelEvidence`
- `TrustTier`
- `DataOrigin`

#### Function naming
- `resolve_label`
- `validate_label`
- `verify_provenance_chain`
- `attach_label`
- `propagate_label`
- `downgrade_label`
- `quarantine_object`

#### Naming guidance
- Use `label` for the canonical trust object.
- Use `classification` for policy-assigned sensitivity/trust grouping.
- Use `provenance` for origin and lineage.
- Use `evidence` for supporting facts used in label derivation.
- Use `tier` for ordinal trust level names, not `level` unless numerically defined by TRD.

---

### `src/trustflow/` — TrustFlow Audit Stream

Purpose: append-only, queryable audit stream for trust-relevant actions and decisions.

#### File naming
Use names such as:
- `audit_event.py`
- `audit_emitter.py`
- `audit_recorder.py`
- `event_canonicalizer.py`
- `stream_cursor.py`
- `integrity_verifier.py`

#### Type naming
- `AuditEvent`
- `AuditEmitter`
- `AuditRecorder`
- `AuditStreamCursor`
- `EventCanonicalizer`
- `IntegrityVerifier`
- `AuditEnvelope`

#### Function naming
- `record_event`
- `emit_event`
- `canonicalize_event`
- `verify_stream_integrity`
- `read_from_cursor`
- `append_audit_envelope`

#### Naming guidance
- Use `event` for logical audit records.
- Use `envelope` for signed/wrapped transport form.
- Use `stream` for append-only ordered records.
- Use `cursor` for consumer read position.
- Use `integrity` for tamper-evidence checks; use `authenticity` when verifying issuer identity.

---

### `src/vtz/` — Virtual Trust Zone

Purpose: isolation and enforcement boundary for operations based on trust constraints.

#### File naming
Use names such as:
- `zone_policy.py`
- `zone_enforcer.py`
- `execution_guard.py`
- `boundary_rule.py`
- `artifact_quarantine.py`
- `zone_context.py`

#### Type naming
- `VirtualTrustZone`
- `ZonePolicy`
- `ZoneEnforcer`
- `ExecutionGuard`
- `BoundaryRule`
- `ArtifactQuarantine`
- `ZoneContext`

#### Function naming
- `enforce_zone_policy`
- `is_operation_permitted`
- `quarantine_artifact`
- `validate_boundary_crossing`
- `build_zone_context`
- `deny_execution`

#### Naming guidance
- Use `zone` for the isolation domain.
- Use `boundary` for transitions between trust domains.
- Use `quarantine` for containment of untrusted artifacts.
- Use `guard` for preventive checks.
- Use `execution` only when discussing actual runnable operations; generated code remains non-executed unless explicitly allowed by TRD.

---

### `src/trustlock/` — Cryptographic Machine Identity

Purpose: TPM-anchored or hardware-backed machine identity, signing, attestation, and key lifecycle.

#### File naming
Use names such as:
- `machine_identity.py`
- `attestation_verifier.py`
- `key_handle_store.py`
- `signing_service.py`
- `device_claim.py`
- `nonce_challenge.py`

#### Type naming
- `MachineIdentity`
- `AttestationVerifier`
- `KeyHandleStore`
- `SigningService`
- `DeviceClaim`
- `NonceChallenge`
- `AttestationStatement`
- `KeyProvisioningRecord`

#### Function naming
- `generate_attestation`
- `verify_attestation`
- `load_key_handle`
- `sign_payload`
- `rotate_key_material`
- `validate_device_claim`

#### Naming guidance
- Use `attestation` for hardware/device proof material.
- Use `claim` for asserted properties.
- Use `statement` for signed attestation payloads.
- Use `handle` for opaque references to secure key storage.
- Never name private key material as plain `key`; distinguish:
  - `key_handle`
  - `public_key`
  - `wrapped_key`
  - `key_reference`

---

### `src/mcp/` — MCP Policy Engine

Purpose: evaluate policy, produce decisions, and enforce obligations for machine control policies.

#### File naming
Use names such as:
- `policy_engine.py`
- `policy_bundle.py`
- `decision_context.py`
- `obligation_resolver.py`
- `rule_evaluator.py`
- `policy_store.py`

#### Type naming
- `PolicyEngine`
- `PolicyBundle`
- `DecisionContext`
- `PolicyDecision`
- `PolicyEffect`
- `ObligationResolver`
- `RuleEvaluator`
- `PolicyStore`

#### Function naming
- `evaluate_policy`
- `resolve_obligations`
- `load_policy_bundle`
- `compile_rule_set`
- `build_decision_context`
- `apply_policy_decision`

#### Naming guidance
- Use `decision` for the complete evaluative result.
- Use `effect` for allow/deny/quarantine-style action.
- Use `obligation` for required follow-up actions.
- Use `rule` for atomic evaluative logic.
- Use `bundle` for signed/versioned policy packages.

---

### `src/rewind/` — Forge Rewind Replay Engine

Purpose: deterministic replay of prior workflows, event streams, and decisions for audit/debugging.

#### File naming
Use names such as:
- `replay_engine.py`
- `replay_session.py`
- `timeline_cursor.py`
- `determinism_checker.py`
- `event_reconstructor.py`
- `replay_snapshot.py`

#### Type naming
- `ReplayEngine`
- `ReplaySession`
- `TimelineCursor`
- `DeterminismChecker`
- `EventReconstructor`
- `ReplaySnapshot`
- `ReplayOutcome`

#### Function naming
- `start_replay_session`
- `replay_event_stream`
- `advance_timeline_cursor`
- `reconstruct_state`
- `check_determinism`
- `capture_replay_snapshot`

#### Naming guidance
- Use `replay` for deterministic re-execution from recorded artifacts.
- Use `timeline` for ordered temporal traversal.
- Use `snapshot` for point-in-time reconstructed state.
- Use `reconstructor` for rebuilding prior state from events.
- Use `outcome` for replay result classification.

---

### `sdk/connector/` — Forge Connector SDK

Purpose: external integrations into Forge platform services with stable SDK contracts.

#### File naming
Use names such as:
- `connector_client.py`
- `connector_session.py`
- `request_signer.py`
- `payload_validator.py`
- `webhook_adapter.py`
- `sdk_errors.py`

#### Type naming
- `ConnectorClient`
- `ConnectorSession`
- `RequestSigner`
- `PayloadValidator`
- `WebhookAdapter`
- `ConnectorRequest`
- `ConnectorResponse`

#### Function naming
- `open_session`
- `sign_request`
- `validate_payload`
- `send_connector_request`
- `parse_connector_response`
- `register_webhook`

#### Naming guidance
- Use `connector` for SDK-facing integration abstractions.
- Use `client` for caller-facing API entry points.
- Use `session` for authenticated interaction scope.
- Use `request` / `response` for wire contracts.
- Use `adapter` for provider-specific translation layers.

---

## Additional Cross-Cutting Conventions

### Data model naming

Use suffixes consistently:

- `...Request` — inbound API or command payload
- `...Response` — outbound API payload
- `...Event` — audit/domain event
- `...Envelope` — signed or transport wrapper
- `...Record` — persisted row/document form
- `...Snapshot` — point-in-time state capture
- `...Context` — execution/evaluation inputs
- `...Result` — operation outcome
- `...Outcome` — classified end state
- `...Evidence` — supporting proof inputs

### Enum naming

- Enum types use singular `PascalCase`.
- Enum members should be domain words, not encoded strings.

Python:
```python
class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    QUARANTINE = "quarantine"
```

Swift:
```swift
enum PolicyEffect {
    case allow
    case deny
    case quarantine
}
```

### Acronyms and abbreviations

Avoid unexplained abbreviations in type names. Approved subsystem abbreviations may be used in directory names, but expand them in class/type names where clarity is improved.

Prefer:
- `VirtualTrustZone` over `VTZ`
- `DataTrustLabel` or `TrustLabel` over `DTLLabel`
- `MachineControlPolicy` only if needed; otherwise `Policy`

Use acronyms only when already product-standard:
- `MCP`
- `TPM`
- `SDK`
- `JSON`
- `XPC`
- `CI`

### Serialization and schema naming

- JSON field names: `snake_case` unless external protocol requires otherwise
- Versioned schemas should include explicit version fields:
  - `schema_version`
  - `policy_version`
  - `event_version`

Do not infer schema version from filenames alone.

### Time and identifiers

- Use `created_at`, `updated_at`, `recorded_at`, `expires_at`
- Use `*_id` suffix for identifiers
- Use `correlation_id` for cross-component traceability
- Use `request_id` for request-scoped tracing
- Use `session_id` for session-scoped identifiers
- Use `event_id` for audit events

Avoid generic `id` in public data contracts unless the entity type is unambiguous.

---

## Patterns to Avoid

Do not introduce:

- `utils.py`, `helpers.py`, `misc.py`, `common.py`
- god objects like `Manager`, `Processor`, `Handler` without explicit bounded purpose
- broad exception catches without re-raising or mapping
- implicit trust upgrades
- boolean parameters that hide policy decisions
- hidden global state for security, policy, or replay logic
- side effects in validation functions
- transport-layer names inside core domain models unless the model is transport-specific

Bad:
```python
def process(data): ...
```

Good:
```python
def validate_payload(payload: bytes) -> ConnectorRequest: ...
def evaluate_policy(context: DecisionContext) -> PolicyDecision: ...
```

---

## Documentation Expectations

- Public classes, exported functions, and boundary modules must have concise docstrings/comments.
- Docstrings should describe:
  - purpose
  - inputs
  - outputs
  - failure conditions
  - security constraints if applicable

Do not restate the function name in prose without adding meaning.

---

## Convention Compliance Checklist

Before merging code, confirm:

- File path matches subsystem ownership.
- File name is domain-specific and follows naming rules.
- Public types use consistent role-based names.
- Errors map to subsystem-specific typed hierarchies.
- Normal deny/decision flow is not implemented as an exception.
- Tests mirror source structure.
- Sensitive data is excluded from logs and errors.
- External/generated content is validated before use.
- Names reflect trust, policy, replay, audit, and identity semantics consistently.
- Implementation matches the owning TRD.