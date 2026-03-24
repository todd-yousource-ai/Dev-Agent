# Code Conventions

This document defines repository-wide coding conventions derived from the provided technical requirements and repository guidance. The architecture is a two-process system:

- A native macOS shell in Swift for UI, authentication, Keychain, and local IPC ownership
- A Python backend for planning, consensus, generation, validation, and repository operations

The technical requirements documents are the source of truth. All code, names, interfaces, tests, and security-sensitive behaviors must align with the governing specification for the subsystem being changed.

## File and Directory Naming

### Repository layout

Use a subsystem-oriented layout. Keep code and tests predictable, mirrored, and easy to map back to owning requirements.

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

### Exact `src/` layout rules

#### `src/cal/`
Conversation Abstraction Layer components.

Use for:
- conversation orchestration
- message normalization
- provider-neutral dialogue state
- prompt/request packaging
- response decoding

Preferred file names:
- `models.py`
- `types.py`
- `protocols.py`
- `adapters.py`
- `engine.py`
- `service.py`
- `validators.py`
- `serializer.py`

#### `src/dtl/`
Data Trust Label components.

Use for:
- trust labels
- content classification
- provenance tagging
- label validation
- policy mapping inputs

Preferred file names:
- `labels.py`
- `taxonomy.py`
- `validator.py`
- `classifier.py`
- `provenance.py`
- `mapping.py`

#### `src/trustflow/`
Audit stream components.

Use for:
- append-only event models
- audit emission
- stream persistence
- replay-safe event serialization
- trace correlation

Preferred file names:
- `events.py`
- `writer.py`
- `reader.py`
- `models.py`
- `codec.py`
- `correlation.py`

#### `src/vtz/`
Virtual Trust Zone enforcement.

Use for:
- trust boundary checks
- execution prohibition enforcement
- resource access gating
- policy guardrails around untrusted/generated content

Preferred file names:
- `policy.py`
- `guards.py`
- `enforcement.py`
- `boundary.py`
- `validator.py`

#### `src/trustlock/`
Cryptographic machine identity.

Use for:
- local identity binding
- hardware-anchored key operations
- attestation material handling
- signing and verification wrappers

Preferred file names:
- `identity.py`
- `keystore.py`
- `attestation.py`
- `signer.py`
- `verifier.py`

#### `src/mcp/`
Policy engine components.

Use for:
- policy models
- evaluation engines
- rule execution
- policy decisions
- enforcement integration

Preferred file names:
- `policy.py`
- `rules.py`
- `engine.py`
- `decision.py`
- `context.py`

#### `src/rewind/`
Replay engine components.

Use for:
- deterministic replay
- historical event reconstruction
- timeline traversal
- playback validation

Preferred file names:
- `replay.py`
- `timeline.py`
- `cursor.py`
- `snapshot.py`
- `validator.py`

#### `sdk/connector/`
Connector SDK.

Use for:
- public connector interfaces
- SDK-facing models
- client wrappers
- integration helpers

Preferred file names:
- `client.py`
- `models.py`
- `types.py`
- `errors.py`
- `auth.py`
- `transport.py`

### Test layout

Tests must mirror `src/` exactly by subsystem.

Examples:

```text
src/cal/engine.py            -> tests/cal/test_engine.py
src/dtl/validator.py         -> tests/dtl/test_validator.py
src/trustflow/writer.py      -> tests/trustflow/test_writer.py
src/vtz/guards.py            -> tests/vtz/test_guards.py
src/trustlock/signer.py      -> tests/trustlock/test_signer.py
src/mcp/engine.py            -> tests/mcp/test_engine.py
src/rewind/replay.py         -> tests/rewind/test_replay.py
```

### File naming rules

- Use lowercase snake_case for Python files.
- Use one primary concept per file.
- Name files by role, not by implementation detail.
- Prefer stable semantic names such as `engine.py`, `policy.py`, `validator.py`, `models.py`.
- Avoid vague names such as `helpers.py`, `misc.py`, `utils.py`, `common.py` unless the TRD explicitly defines a shared utility layer.
- If a file contains only protocol/interface definitions, prefer `protocols.py` or `interfaces.py`.
- If a file contains only data models, prefer `models.py` or a domain-specific plural noun such as `events.py`, `labels.py`, `rules.py`.
- Keep transport-specific code separate from business logic, with names like `transport.py`, `socket_client.py`, or `codec.py`.

## Class and Function Naming

## General naming style

### Python

- Classes: `PascalCase`
- Exceptions: `PascalCase` ending in `Error`
- Enums: `PascalCase`
- Functions and methods: `snake_case`
- Module-level constants: `UPPER_SNAKE_CASE`
- Private/internal helpers: leading underscore, e.g. `_normalize_label`
- Type aliases: `PascalCase`
- Protocol or abstract base names: `PascalCase` with role suffix where useful, e.g. `ProviderAdapter`, `PolicyEvaluator`

### Swift

- Types: `PascalCase`
- Methods and properties: `camelCase`
- Enum cases: `camelCase`
- Protocols: `PascalCase`, usually noun- or capability-based
- Error types: `PascalCase` ending in `Error`

## Naming by responsibility

### Engines

Use `Engine` for orchestration components that coordinate multiple lower-level collaborators.

Examples:
- `ConsensusEngine`
- `PolicyEngine`
- `ReplayEngine`

Rules:
- An `Engine` should coordinate; it should not become a grab-bag for unrelated logic.
- If logic is narrow and stateless, prefer `Validator`, `Codec`, `Mapper`, or `Adapter` instead.

### Adapters

Use `Adapter` for provider-specific or boundary-specific translations.

Examples:
- `ProviderAdapter`
- `SocketAdapter`
- `RepositoryAdapter`

Rules:
- Adapters translate between internal canonical models and external APIs/protocols.
- Avoid embedding policy decisions in adapters unless mandated by the owning specification.

### Services

Use `Service` for long-lived application-facing operations.

Examples:
- `AuthService`
- `AuditService`
- `PlanningService`

Rules:
- Services may hold dependencies and lifecycle state.
- Services should expose clear entrypoints and delegate specialized logic to validators, mappers, engines, or repositories.

### Validators

Use `Validator` for deterministic checks that accept input and return or raise on validity.

Examples:
- `LabelValidator`
- `BoundaryValidator`
- `ReplayValidator`

Rules:
- Validators should not mutate unrelated state.
- Validation errors must be precise and typed.

### Managers and Controllers

Use these sparingly.
- Prefer `Service`, `Engine`, `Coordinator`, `Store`, or a more specific domain name.
- Use `Coordinator` when the main responsibility is sequencing multi-step flows across components.

### Stores and Repositories

- Use `Store` for local state ownership or persistence abstractions.
- Use `Repository` only when the abstraction represents domain object retrieval/persistence rather than a source code repository operation.
- For source control hosting interactions, prefer names like `PullRequestService`, `GitService`, or `RemoteRepositoryAdapter`.

## Function naming rules

- Prefer verb-first names for actions:
  - `load_labels`
  - `validate_policy`
  - `emit_event`
  - `replay_timeline`
- Prefer `get_` only when returning a value without side effects and when a bare noun would be unclear.
- Use `build_` for object construction from inputs.
- Use `parse_` for syntax decoding.
- Use `serialize_` and `deserialize_` for stable wire/storage transformations.
- Use `to_` and `from_` for type conversions.
- Use `can_`, `should_`, `is_`, `has_` for predicates.
- Use `list_` for collection retrieval.
- Use `apply_` for policy/rule/transformation application.
- Use `enforce_` only when violating input will trigger rejection or hard failure.
- Use `record_`, `append_`, or `emit_` for audit/event writing based on the subsystem’s semantics.

## Parameter naming rules

- Use domain terms from the governing specification.
- Prefer explicit parameter names:
  - `trust_label` not `label` when ambiguity exists
  - `audit_event` not `event`
  - `policy_context` not `context` when multiple contexts exist
- Use `raw_` prefix for unparsed external content.
- Use `normalized_` prefix for canonicalized values.
- Use `source_` and `target_` consistently for transformations.
- Use `request` and `response` only at transport or API boundaries.

## Error and Exception Patterns

## General rules

- Use typed exceptions, never anonymous string-only failures.
- Every subsystem must define a focused error hierarchy.
- Error names must end with `Error`.
- Error messages must be actionable, stable, and safe for logs.
- Do not leak secrets, credentials, tokens, raw key material, or sensitive generated content into exception text.
- Distinguish validation failures, policy denials, transport failures, parsing failures, and internal invariant violations.

## Error hierarchy pattern

Each subsystem should define a base error.

Examples:
- `CalError`
- `DtlError`
- `TrustflowError`
- `VtzError`
- `TrustlockError`
- `McpError`
- `RewindError`

Then derive specific errors beneath the base.

Example pattern:

```python
class McpError(Exception):
    pass


class PolicyValidationError(McpError):
    pass


class PolicyDecisionError(McpError):
    pass


class PolicyContextError(McpError):
    pass
```

## Recommended error categories

Use these categories where applicable:

- `ValidationError` for malformed or semantically invalid input
- `PolicyDeniedError` for explicit policy rejection
- `SerializationError` / `DeserializationError` for codec failures
- `TransportError` for IPC/network/socket boundary issues
- `AuthenticationError` for identity/auth failures
- `AuthorizationError` for permission failures
- `ConflictError` for state or version conflicts
- `TimeoutError` for bounded waits that expire
- `InvariantViolationError` for impossible internal states
- `ExternalProviderError` for provider-side failures
- `ReplayError` for deterministic replay failures
- `AuditWriteError` for append/persist failures

## Error handling conventions

- Raise the most specific error possible.
- Preserve the original cause when wrapping lower-level exceptions.
- Convert external library errors into domain errors at subsystem boundaries.
- Do not allow raw provider, socket, or persistence exceptions to leak across public interfaces.
- Fail closed for policy and trust decisions.
- Security-relevant denials must be explicit and auditable where required by the owning specification.
- Generated or external content must be treated as untrusted in both happy-path and error-path handling.

## Result and error contract consistency

If a public function returns structured results:
- return canonical domain objects on success
- raise typed domain exceptions on failure

Avoid:
- returning `None` for ambiguous failure
- returning booleans when the caller needs denial reason
- mixing sentinel values and exceptions in the same API family

## Logging and error text

- Error text must be concise and deterministic.
- Include identifiers and state only when safe and necessary.
- Prefer structured logging fields over string interpolation for machine-consumable diagnostics.
- Never log:
  - secrets
  - authentication tokens
  - full credentials
  - raw attestation material
  - private keys
  - unsafe generated code content unless explicitly permitted and scrubbed

## Per-Subsystem Naming Rules

## `cal` — Conversation Abstraction Layer

Purpose:
- canonicalize provider-facing and provider-returned conversational artifacts
- isolate conversation logic from provider-specific transport and formatting

Naming rules:
- Core canonical models: `Conversation`, `Message`, `Turn`, `ToolCall`, `ProviderRequest`, `ProviderResponse`
- Translation components: `*Adapter`, `*Mapper`, `*Codec`
- Conversation sequencing components: `*Engine`, `*Coordinator`
- Request shaping helpers: `build_*`, `normalize_*`, `sanitize_*`
- Provider neutrality is required in core model names; provider-specific names belong only in adapter modules

Examples:
- `ConversationEngine`
- `ProviderAdapter`
- `MessageNormalizer`
- `ResponseCodec`

Avoid:
- embedding provider names in shared model types
- naming canonical objects after a specific external API concept unless the TRD does so

## `dtl` — Data Trust Label

Purpose:
- classify data and preserve provenance/trust semantics across flows

Naming rules:
- Label entities use `Label`, `TrustLabel`, `LabelSet`, `LabelDecision`, `ProvenanceRecord`
- Classification logic uses `Classifier`
- Validation logic uses `Validator`
- Mapping between taxonomies uses `Mapper` or `TaxonomyMapper`
- Predicates should read clearly:
  - `is_trusted`
  - `is_external`
  - `has_required_label`

Examples:
- `TrustLabel`
- `LabelValidator`
- `ProvenanceRecord`
- `TaxonomyMapper`

Avoid:
- vague names like `Tag`
- overloading `metadata` when `provenance` or `trust_label` is the actual concept

## `trustflow` — Audit Stream

Purpose:
- immutable or append-oriented audit/event recording for traceability

Naming rules:
- Event models end with `Event` when they represent a single audit datum
- Stream interaction types use `Writer`, `Reader`, `Appender`, `Cursor`
- Correlation names use `CorrelationId`, `TraceId`, `SpanId` if the specification distinguishes them
- Functions should clearly express audit semantics:
  - `append_event`
  - `emit_audit_event`
  - `read_stream`
  - `replay_events`

Examples:
- `AuditEvent`
- `TrustflowWriter`
- `EventCursor`
- `CorrelationId`

Avoid:
- mutable-sounding names for immutable records
- generic `log` naming when the semantics are audit-grade events

## `vtz` — Virtual Trust Zone

Purpose:
- enforce trust boundaries and prohibit unsafe behavior around untrusted or generated content

Naming rules:
- Enforcement types use `Guard`, `Policy`, `Boundary`, `Enforcer`
- Explicit deny behaviors use `deny_*`, `reject_*`, `enforce_*`
- Boundary state names should be semantically strict:
  - `trusted`
  - `untrusted`
  - `restricted`
  - `isolated`
- Validation helpers should distinguish checking from enforcing:
  - `validate_boundary`
  - `enforce_boundary`

Examples:
- `BoundaryGuard`
- `TrustBoundaryPolicy`
- `ExecutionEnforcer`
- `GeneratedContentGuard`

Avoid:
- soft or ambiguous names like `filter` for hard trust controls
- names that imply generated code execution is permitted

## `trustlock` — Cryptographic Machine Identity

Purpose:
- manage hardware-anchored identity, key operations, and attestation-related workflows

Naming rules:
- Identity types use `Identity`, `MachineIdentity`, `Attestation`, `KeyHandle`, `SignatureBundle`
- Cryptographic operators use `Signer`, `Verifier`
- Secret-bearing abstractions use `KeyStore`, `SecureStore`, `IdentityStore`
- Functions should be explicit:
  - `load_identity`
  - `generate_attestation`
  - `sign_payload`
  - `verify_signature`

Examples:
- `MachineIdentity`
- `AttestationVerifier`
- `KeyStore`
- `PayloadSigner`

Avoid:
- generic names like `Token` when the object is an attestation or signature
- exposing raw key material through naming or public interfaces

## `mcp` — Policy Engine

Purpose:
- evaluate policy inputs and produce deterministic decisions

Naming rules:
- Core types use `Policy`, `Rule`, `Decision`, `PolicyContext`, `EvaluationResult`
- Evaluation components use `Engine`, `Evaluator`
- Denial outcomes should be named explicitly:
  - `PolicyDeniedError`
  - `DecisionDenied`
- Functions should emphasize determinism:
  - `evaluate_policy`
  - `apply_rules`
  - `build_decision`

Examples:
- `PolicyEngine`
- `RuleEvaluator`
- `PolicyDecision`
- `PolicyContext`

Avoid:
- naming policy results as vague `status`
- collapsing context, rule input, and decision output into one generic object

## `rewind` — Replay Engine

Purpose:
- reproduce or inspect prior system behavior deterministically from recorded history

Naming rules:
- Timeline concepts use `Timeline`, `Snapshot`, `Cursor`, `ReplaySession`
- Replay operations use `replay_*`, `seek_*`, `restore_*`, `reconstruct_*`
- Validation components use `ReplayValidator`, `ConsistencyChecker`
- Deterministic comparison names should be explicit:
  - `compare_snapshot`
  - `validate_replay_consistency`

Examples:
- `ReplayEngine`
- `ReplaySession`
- `TimelineCursor`
- `SnapshotValidator`

Avoid:
- real-time oriented names like `stream_processor` unless the specification explicitly requires streaming replay
- ambiguous `history` names when `timeline` or `replay` is the actual concept

## Cross-Process and Boundary Conventions

Because the system is split across a Swift shell and Python backend, names at process boundaries must be especially strict.

### IPC and transport naming

- Use `Request`, `Response`, `Envelope`, `Message`, and `Codec` only for transport concerns.
- Use line-delimited JSON terminology consistently where applicable:
  - `encode_message`
  - `decode_message`
  - `socket_reader`
  - `socket_writer`
- Authentication and integrity checks on IPC channels should be reflected in names such as:
  - `AuthenticatedSocket`
  - `SessionAuthenticator`
  - `EnvelopeVerifier`

### Boundary model separation

- Keep transport DTOs separate from domain models.
- Suggested naming:
  - transport: `*Request`, `*Response`, `*Envelope`
  - domain: `Plan`, `PolicyDecision`, `TrustLabel`, `AuditEvent`
- Do not expose raw transport payload dictionaries beyond codec layers.

## Test Naming Conventions

- Test files use `test_<module>.py`.
- Test classes, if used, use `Test<BehaviorOrType>`.
- Test function names describe behavior, not implementation:
  - `test_validate_policy_rejects_missing_label`
  - `test_append_event_preserves_correlation_id`
  - `test_replay_timeline_is_deterministic`
- Mirror subsystem vocabulary in test names.
- Keep fixture names domain-specific:
  - `policy_context`
  - `audit_event`
  - `trust_label`
  - `replay_session`

## Prohibited Naming Patterns

Do not use:
- hardcoded product names in code identifiers where a subsystem/domain term exists
- `helpers`, `misc`, `stuff`, `thing`, `manager` without a precise responsibility
- `data` when a domain noun is known
- `info` when the real concept is `metadata`, `provenance`, `attestation`, or `decision`
- `exec`, `run_generated`, or any name implying execution of generated code
- provider-specific terminology in shared canonical models
- untyped `Error` or `Exception` as public error contracts

## Preferred Patterns Summary

### Good

- `PolicyEngine`
- `TrustLabel`
- `AuditEvent`
- `BoundaryGuard`
- `MachineIdentity`
- `ReplaySession`
- `validate_policy`
- `append_event`
- `sign_payload`
- `reconstruct_timeline`

### Bad

- `Manager`
- `Helper`
- `DataThing`
- `Tag`
- `Info`
- `do_it`
- `handle`
- `process` when a more exact verb exists
- `run_code`
- `provider_message` as a canonical domain type

## Final Rule

Choose names that reveal:
- subsystem ownership
- trust semantics
- transport vs domain separation
- deterministic error behavior
- security posture

If a name is shorter but less precise, prefer the more precise name.