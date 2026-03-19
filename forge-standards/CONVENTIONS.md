# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and code patterns for the full Forge platform. It applies across all subsystems and should be treated as repository-wide policy.

The Forge platform includes:

- `src/cal/` — Conversation Abstraction Layer
- `src/dtl/` — Data Trust Label
- `src/trustflow/` — TrustFlow audit stream
- `src/vtz/` — Virtual Trust Zone
- `src/trustlock/` — cryptographic machine identity
- `src/mcp/` — MCP Policy Engine
- `src/rewind/` — Forge Rewind replay engine
- `sdk/connector/` — Forge Connector SDK
- `tests/<subsystem>/` — tests mirroring `src/`

Where product behavior is specified by TRDs, the TRD remains authoritative. These conventions define how code is named and structured so implementations remain consistent across the platform.

---

## Core Principles

1. **TRD-first implementation**
   - Do not invent interfaces, state transitions, or security behavior.
   - Read the owning TRD before modifying a subsystem.
   - If a convention here conflicts with a TRD, follow the TRD and update this file later.

2. **Security-sensitive by default**
   - All code that handles credentials, policies, trust labels, replay logs, machine identity, or external content must be explicit and auditable.
   - Prefer small, composable functions over large implicit flows.
   - Never hide trust, policy, or boundary transitions behind vague helpers.

3. **Deterministic, inspectable behavior**
   - Avoid side effects in constructors.
   - Make boundary-crossing actions explicit in names and call sites.
   - Serialize and log structured data using stable schemas.

4. **Subsystem boundaries are real**
   - No subsystem may reach into another subsystem’s internals.
   - Depend on published interfaces, service objects, DTOs, and adapters only.
   - Shared utilities belong in an approved shared module, not copied ad hoc.

5. **Tests mirror implementation**
   - Test directory structure must mirror source structure exactly.
   - Test names must describe behavior, contract, and expected outcome.

---

## File and Directory Naming (exact `src/` layout)

### Source tree

The top-level source layout is fixed:

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

### Directory naming rules

- Use **lowercase directory names** only.
- Use **single-word subsystem roots** exactly as defined:
  - `cal`
  - `dtl`
  - `trustflow`
  - `vtz`
  - `trustlock`
  - `mcp`
  - `rewind`
  - `connector`
- Use **snake_case** for nested Python package directories.
- Do not use hyphens in directory names.
- Do not create aliases or alternate names for subsystem roots.

### File naming rules

#### Python source files
- Use `snake_case.py`.
- File names should describe the primary responsibility, not generic utility status.
- Prefer:
  - `policy_evaluator.py`
  - `trust_label_parser.py`
  - `replay_session_store.py`
- Avoid:
  - `helpers.py`
  - `misc.py`
  - `common.py`
  - `stuff.py`

#### Swift source files
- Use `PascalCase.swift`.
- File name should match the primary type in the file.
- If a file contains extensions only, use:
  - `TypeName+Concern.swift`
  - Example: `SessionState+Serialization.swift`

#### Test files
- Python tests use `test_<subject>.py`.
- Swift tests use `<Subject>Tests.swift`.
- Test filenames must map clearly to the implementation unit or contract being tested.

### Structure mirroring rule

Tests must mirror implementation structure exactly.

Example:

```text
src/dtl/labels/parser.py
tests/dtl/labels/test_parser.py
```

Example:

```text
src/mcp/policy/evaluator.py
tests/mcp/policy/test_evaluator.py
```

### One responsibility per file

A file should usually contain one of the following:

- one primary class
- one cohesive set of related functions
- one protocol/interface plus closely related DTOs
- one schema/model group with a single purpose

If a file name cannot clearly express its purpose, the file is probably doing too much.

---

## Class and Function Naming

Naming must make trust boundaries, lifecycle stage, and intent obvious.

### General naming rules

- **Classes, protocols, enums, structs:** `PascalCase`
- **Functions, methods, variables:** `snake_case` in Python, `camelCase` in Swift
- **Constants:** `UPPER_SNAKE_CASE` for Python module-level constants; Swift constants follow standard Swift style
- **Private helpers:** name for behavior, not visibility
- **Booleans:** prefix with `is_`, `has_`, `can_`, `should_` in Python; `is`, `has`, `can`, `should` in Swift

### Prefer semantic suffixes

Use suffixes consistently to communicate role:

#### Domain and transport types
- `Request`
- `Response`
- `Result`
- `Record`
- `Event`
- `Snapshot`
- `Manifest`
- `Descriptor`
- `Metadata`
- `Config`

#### Behavior and orchestration
- `Service`
- `Manager`
- `Coordinator`
- `Controller`
- `Orchestrator`
- `Scheduler`
- `Runner`

#### Policy, trust, and verification
- `Policy`
- `Rule`
- `Evaluator`
- `Validator`
- `Verifier`
- `Inspector`
- `Resolver`
- `Enforcer`

#### Persistence and I/O
- `Store`
- `Repository`
- `Client`
- `Adapter`
- `Gateway`
- `Publisher`
- `Subscriber`

#### Security and identity
- `Attestor`
- `Signer`
- `Issuer`
- `Authenticator`
- `Authorizer`
- `Identity`
- `Principal`

### Function naming rules

Function names should begin with an action verb and encode observable behavior.

Prefer:
- `load_policy_bundle`
- `validate_trust_label`
- `publish_audit_event`
- `replay_session`
- `resolve_machine_identity`

Avoid:
- `do_policy`
- `handle_data`
- `process`
- `run` when a more specific verb exists

### Side-effect naming

Functions with external side effects must be explicit.

Use names like:
- `write_audit_record`
- `persist_snapshot`
- `submit_attestation`
- `open_connector_session`
- `delete_expired_tokens`

Do not hide side effects in names like:
- `build_*`
- `prepare_*`
- `format_*`

### Async naming

If the language/runtime permits ambiguity, async APIs should make lifecycle obvious.

Prefer:
- `start_replay`
- `stop_replay`
- `await_consensus_result`
- `stream_audit_events`

Use `*_async` only if required by an existing project language pattern.

### Factory naming

Use:
- `from_dict`
- `from_json`
- `from_record`
- `create_for_policy`
- `build_snapshot`

Reserve `build_*` for object construction only, never mutation plus I/O.

---

## Error and Exception Patterns

Errors must be typed, auditable, and boundary-aware.

### General rules

1. **Never raise or throw generic errors for domain failures**
   - Avoid bare `Exception`, `RuntimeError`, or untyped NSError-style propagation for expected failures.
   - Use subsystem-specific error types.

2. **Separate expected domain errors from programmer errors**
   - Domain errors:
     - invalid trust label
     - policy denied
     - missing attestation
     - replay stream corrupted
   - Programmer errors:
     - invariant violation
     - impossible state
     - incorrect internal API use

3. **Errors must preserve context**
   - Include stable identifiers:
     - `request_id`
     - `session_id`
     - `policy_id`
     - `event_id`
     - `connector_id`
   - Do not include secrets or raw sensitive payloads.

4. **Translate errors at subsystem boundaries**
   - Internal parser errors should not leak as transport errors directly.
   - Convert low-level exceptions into subsystem-level contract errors.

### Error naming

Use clear suffixes:

- `Error` — base or generic typed error
- `ValidationError`
- `VerificationError`
- `AuthenticationError`
- `AuthorizationError`
- `PolicyError`
- `ReplayError`
- `SerializationError`
- `TransportError`
- `TimeoutError`
- `ConflictError`
- `NotFoundError`

Examples:
- `TrustLabelValidationError`
- `PolicyEvaluationError`
- `AttestationVerificationError`
- `ReplayIntegrityError`
- `ConnectorTransportError`

### Error hierarchy pattern

Each subsystem should expose a subsystem root error.

Example:

```python
class DtlError(Exception):
    """Base error for DTL subsystem."""

class TrustLabelValidationError(DtlError):
    """Raised when a trust label fails schema or semantic validation."""

class TrustLabelResolutionError(DtlError):
    """Raised when a referenced trust label cannot be resolved."""
```

### Raise with actionable meaning

Error messages should answer:
- what failed
- at what boundary
- using which identifier
- whether retry is appropriate

Good:
- `PolicyEvaluationError("policy denied for connector_id=gh-prod action=repo.write")`

Bad:
- `PolicyEvaluationError("evaluation failed")`

### Never log secrets in errors

Forbidden in exceptions and logs:
- private keys
- raw tokens
- OAuth secrets
- full attestation blobs unless explicitly approved by TRD
- unredacted user content if classified or policy-controlled

### Result vs exception guidance

Use exceptions for:
- invalid state
- contract violations
- transport failures
- security failures
- persistence failures

Use result objects for:
- multi-branch evaluation outcomes
- policy decisions
- validation reports
- consensus/review summaries

Example:
- `PolicyDecisionResult(allowed=False, reason="scope_denied")`
- not an exception for a normal deny result unless the contract requires it

---

## Per-Subsystem Naming Rules

---

### `src/cal/` — Conversation Abstraction Layer

#### Purpose
CAL owns conversation normalization, message abstraction, model/provider-neutral interaction structures, and conversation state handoff across agent workflows.

#### Directory patterns

Recommended nested packages:

```text
src/cal/
  adapters/
  messages/
  sessions/
  transcripts/
  schemas/
```

#### Naming rules

- Use `Conversation*` for top-level conversation concepts:
  - `ConversationSession`
  - `ConversationMessage`
  - `ConversationTranscript`
- Use `Provider*` for provider-specific adapters:
  - `ProviderMessageAdapter`
  - `ProviderTranscriptAdapter`
- Use `Session*` for stateful lifecycle management:
  - `SessionState`
  - `SessionStore`
  - `SessionCoordinator`
- Use `Transcript*` for persisted or replayable conversation logs:
  - `TranscriptRecord`
  - `TranscriptSerializer`

#### Function naming examples

- `normalize_message_sequence`
- `serialize_transcript`
- `hydrate_session_state`
- `map_provider_response`
- `append_conversation_message`

#### Forbidden vague names

- `chat_manager`
- `llm_helper`
- `message_utils`
- `conversation_processor`

---

### `src/dtl/` — Data Trust Label

#### Purpose
DTL defines trust labels, classification metadata, derivation rules, propagation logic, and trust-aware validation.

#### Directory patterns

Recommended nested packages:

```text
src/dtl/
  labels/
  propagation/
  validation/
  schemas/
  resolution/
```

#### Naming rules

- Prefix label domain types with `TrustLabel` when they represent formal labels:
  - `TrustLabel`
  - `TrustLabelRecord`
  - `TrustLabelSchema`
  - `TrustLabelValidator`
- Use `Classification*` for user/data classification concepts:
  - `ClassificationLevel`
  - `ClassificationRule`
- Use `Propagation*` for label inheritance and flow logic:
  - `PropagationRule`
  - `PropagationEvaluator`
  - `PropagationResult`
- Use `Resolution*` for lookup/linking:
  - `TrustLabelResolver`
  - `ResolutionContext`

#### Function naming examples

- `validate_trust_label`
- `resolve_label_references`
- `propagate_labels_to_artifact`
- `merge_classification_metadata`
- `enforce_label_constraints`

#### Forbidden vague names

- `tagger`
- `label_helper`
- `trust_utils`
- `meta_processor`

---

### `src/trustflow/` — TrustFlow audit stream

#### Purpose
TrustFlow records structured audit events, trust decisions, state transitions, and replayable evidence across the platform.

#### Directory patterns

Recommended nested packages:

```text
src/trustflow/
  events/
  streams/
  sinks/
  replay/
  integrity/
```

#### Naming rules

- Prefix audit event types with `Audit` when representing canonical audit records:
  - `AuditEvent`
  - `AuditRecord`
  - `AuditEnvelope`
- Use `TrustFlow*` for subsystem-level orchestration:
  - `TrustFlowPublisher`
  - `TrustFlowStream`
  - `TrustFlowSink`
- Use `Integrity*` for tamper evidence and verification:
  - `IntegrityVerifier`
  - `IntegrityCheckpoint`
  - `IntegrityChainRecord`
- Use `Replay*` only for audit-stream replay artifacts:
  - `ReplayCursor`
  - `ReplayBatch`
  - `ReplayWindow`

#### Function naming examples

- `publish_audit_event`
- `append_integrity_checkpoint`
- `verify_stream_integrity`
- `load_replay_window`
- `write_audit_record`

#### Forbidden vague names

- `logger`
- `event_helper`
- `stream_processor`
- `audit_utils`

---

### `src/vtz/` — Virtual Trust Zone

#### Purpose
VTZ enforces trust boundaries, execution policy, isolation constraints, and cross-zone data movement controls.

#### Directory patterns

Recommended nested packages:

```text
src/vtz/
  zones/
  enforcement/
  boundaries/
  transfers/
  policies/
```

#### Naming rules

- Use `TrustZone*` for zone definitions and instances:
  - `TrustZone`
  - `TrustZoneDescriptor`
  - `TrustZoneRegistry`
- Use `Boundary*` for zone crossing semantics:
  - `BoundaryRule`
  - `BoundaryVerifier`
  - `BoundaryCrossingRequest`
- Use `Enforcement*` for runtime enforcement:
  - `EnforcementAction`
  - `EnforcementResult`
  - `EnforcementEngine`
- Use `Transfer*` for data or artifact movement across zones:
  - `TransferPolicy`
  - `TransferManifest`
  - `TransferValidator`

#### Function naming examples

- `verify_boundary_crossing`
- `enforce_zone_policy`
- `validate_transfer_manifest`
- `resolve_zone_for_artifact`
- `deny_cross_zone_write`

#### Forbidden vague names

- `sandbox`
- `guard`
- `zone_helper`
- `isolate_data` as a catch-all without explicit semantics

---

### `src/trustlock/` — Cryptographic machine identity

#### Purpose
TrustLock owns machine identity, attestation, TPM-anchored or hardware-rooted trust material, signing, and identity verification flows.

#### Directory patterns

Recommended nested packages:

```text
src/trustlock/
  identity/
  attestation/
  signing/
  verification/
  stores/
```

#### Naming rules

- Use `MachineIdentity*` for canonical machine identity models:
  - `MachineIdentity`
  - `MachineIdentityRecord`
  - `MachineIdentityResolver`
- Use `Attestation*` for attestation artifacts and validation:
  - `AttestationBundle`
  - `AttestationVerifier`
  - `AttestationChallenge`
- Use `Signing*` for signing workflows:
  - `SigningKeyHandle`
  - `SigningRequest`
  - `SigningService`
- Use `Verification*` for identity or attestation verification pipelines:
  - `VerificationResult`
  - `VerificationPolicy`

#### Function naming examples

- `resolve_machine_identity`
- `verify_attestation_bundle`
- `sign_integrity_checkpoint`
- `load_hardware_key_handle`
- `issue_attestation_challenge`

#### Forbidden vague names

- `crypto_helper`
- `machine_auth`
- `identity_utils`
- `secure_sign`

---

### `src/mcp/` — MCP Policy Engine

#### Purpose
MCP defines policy interpretation, evaluation, authorization decisions, rule execution, and policy-bound action gating.

#### Directory patterns

Recommended nested packages:

```text
src/mcp/
  policy/
  evaluation/
  rules/
  enforcement/
  schemas/
```

#### Naming rules

- Prefix policy objects with `Policy` when canonical:
  - `PolicyDocument`
  - `PolicyBundle`
  - `PolicyClause`
  - `PolicyVersion`
- Use `Rule*` for atomic evaluable units:
  - `RuleCondition`
  - `RuleEvaluator`
  - `RuleMatchResult`
- Use `Decision*` for evaluation output:
  - `DecisionResult`
  - `DecisionTrace`
  - `DecisionReason`
- Use `Authorization*` for access decisions tied to principals/actions/resources:
  - `AuthorizationRequest`
  - `AuthorizationDecision`
  - `AuthorizationContext`
- Use `Enforcement*` when translating policy decisions into runtime controls:
  - `EnforcementPlan`
  - `EnforcementAdapter`

#### Function naming examples

- `evaluate_policy_bundle`
- `build_decision_trace`
- `authorize_action`
- `resolve_applicable_rules`
- `enforce_decision_result`

#### Forbidden vague names

- `policy_manager` if it mixes load/eval/enforce
- `auth_helper`
- `rules_engine`
- `permission_checker` unless narrowly scoped and accurate

---

### `src/rewind/` — Forge Rewind replay engine

#### Purpose
Rewind provides deterministic replay, timeline reconstruction, event sequencing, forensic analysis, and execution trace rehydration.

#### Directory patterns

Recommended nested packages:

```text
src/rewind/
  replay/
  timelines/
  cursors/
  snapshots/
  analysis/
```

#### Naming rules

- Use `Replay*` for active replay process types:
  - `ReplayEngine`
  - `ReplaySession`
  - `ReplayRequest`
  - `ReplayResult`
- Use `Timeline*` for ordered historical representations:
  - `TimelineSegment`
  - `TimelineCursor`
  - `TimelineSnapshot`
- Use `Snapshot*` for persisted replay checkpoints:
  - `SnapshotRecord`
  - `SnapshotStore`
  - `SnapshotManifest`
- Use `Analysis*` for diagnostics and post-hoc reasoning:
  - `AnalysisReport`
  - `AnalysisFinding`

#### Function naming examples

- `replay_session`
- `reconstruct_timeline`
- `load_snapshot_manifest`
- `advance_timeline_cursor`
- `analyze_replay_divergence`

#### Forbidden vague names

- `time_travel`
- `replayer_utils`
- `history_processor`
- `trace_helper`

---

### `sdk/connector/` — Forge Connector SDK

#### Purpose
The Connector SDK exposes stable integration interfaces for external systems to participate in trust-aware Forge workflows.

#### Directory patterns

Recommended nested packages:

```text
sdk/connector/
  client/
  server/
  auth/
  schemas/
  transport/
```

#### Naming rules

- Prefix public SDK entry points with `Connector` when they are part of the stable API:
  - `ConnectorClient`
  - `ConnectorServer`
  - `ConnectorSession`
  - `ConnectorRequest`
  - `ConnectorResponse`
- Use `Transport*` for wire/runtime transport abstractions:
  - `TransportClient`
  - `TransportEnvelope`
- Use `Auth*` for SDK authentication flows:
  - `AuthTokenProvider`
  - `AuthChallengeHandler`
- Use `Schema*` or explicit object names for wire compatibility models:
  - `ConnectorEventSchema`
  - `ConnectorHandshakeRequest`

#### Function naming examples

- `open_connector_session`
- `submit_connector_request`
- `validate_connector_signature`
- `negotiate_transport_capabilities`
- `refresh_auth_token`

#### Public API rule

SDK public names are semver-sensitive.
- Avoid renaming exported types without a versioning plan.
- Keep internal helpers out of the public namespace.
- Use explicit `internal`/private module boundaries where supported.

#### Forbidden vague names

- `client_helper`
- `sdk_utils`
- `api_manager`
- `connector_impl` as a public type

---

## Cross-Subsystem Patterns

### DTOs and schemas

Use DTO/model names consistently:

- `*Request` — inbound operation input
- `*Response` — outbound operation output
- `*Result` — operation outcome, often internal or domain-level
- `*Record` — persisted unit
- `*Event` — immutable event payload
- `*Envelope` — wrapped payload with metadata/signature/context
- `*Manifest` — collection descriptor for artifacts
- `*Snapshot` — point-in-time state capture

Do not use multiple names for the same concept across subsystems unless required by a TRD.

### Interface and adapter naming

Use:
- `*Protocol` in Swift when appropriate
- `*Interface` only where language or existing codebase patterns require it
- `*Adapter` for translation layers
- `*Client` for outbound external calls
- `*Gateway` for infrastructural access behind a domain boundary

### State machine naming

If implementing lifecycle/state machines:

- enum/type names:
  - `SessionState`
  - `ReplayState`
  - `AttestationState`
- transition methods:
  - `transition_to_validated`
  - `mark_as_persisted`
  - `fail_with_timeout`

Avoid opaque status methods like:
- `update_status`
- `set_state`

### Serialization and parsing naming

Use:
- `serialize_*`
- `deserialize_*`
- `parse_*`
- `encode_*`
- `decode_*`

Use `parse_*` for syntax/structure interpretation.
Use `validate_*` for semantic or policy checks.
Do not mix both concerns in one method unless unavoidable and explicitly documented.

---

## Code Patterns

### Prefer explicit dependency injection

Construct services with explicit dependencies.

Good:
```python
class PolicyEvaluator:
    def __init__(self, rule_resolver: RuleResolver, trace_builder: DecisionTraceBuilder) -> None:
        self._rule_resolver = rule_resolver
        self._trace_builder = trace_builder
```

Avoid:
```python
class PolicyEvaluator:
    def __init__(self) -> None:
        self._rule_resolver = GlobalRegistry.rule_resolver()
```

### Keep boundary validation at edges

Validate external input as early as possible:
- SDK ingress
- transport ingress
- file load
- policy load
- attestation receipt
- replay import

Do not pass partially validated external data deep into the system.

### Keep policy and trust decisions structured

Prefer:

```python
DecisionResult(
    allowed=False,
    reason="zone_mismatch",
    decision_trace=trace,
)
```

Over:
```python
False
```

### Prefer immutable event and record types

Audit events, attestation bundles, replay records, snapshots, and policy documents should be immutable where language support allows.

### Avoid hidden cross-subsystem coupling

Bad:
- `dtl` directly writing `trustflow` storage internals
- `rewind` depending on `mcp` private evaluation classes
- `connector` importing internal-only enforcement modules

Good:
- depend on published event schemas
- use adapters
- use stable subsystem service interfaces

---

## Testing Conventions

### Test naming

Name tests for behavior and outcome.

Python:
```python
def test_validate_trust_label_rejects_missing_classification_level():
    ...
```

Swift:
```swift
func testValidateTrustLabelRejectsMissingClassificationLevel() {
    ...
}
```

### Test organization

Mirror source layout exactly.

Example:
```text
src/trustlock/attestation/verifier.py
tests/trustlock/attestation/test_verifier.py
```

### Required test categories

Where applicable, each subsystem should include:

- unit tests
- contract/interface tests
- serialization tests
- error contract tests
- security-sensitive negative tests
- replay/determinism tests for evented subsystems

### Test data naming

Use:
- `fixture_*`
- `sample_*`
- `invalid_*`
- `expected_*`

Examples:
- `fixture_policy_bundle`
- `invalid_attestation_bundle`
- `expected_decision_trace`

Avoid:
- `data1`
- `thing`
- `obj`

---

## Names to Avoid Globally

The following names are too vague and should not be introduced unless narrowly scoped and justified:

- `utils`
- `helpers`
- `common`
- `base` for domain code
- `manager` when a more specific role exists
- `processor`
- `handler`
- `service` when the service boundary is unclear
- `data`
- `info`
- `item`
- `thing`
- `misc`

If one of these appears in a file or type name, require a specific reason in review.

---

## Documentation and Docstring Conventions

- Public types and functions must document:
  - purpose
  - inputs/outputs
  - trust or policy implications if any
  - raised/thrown errors
- Security-sensitive modules must document:
  - boundary assumptions
  - redaction behavior
  - integrity requirements
- Docstrings/comments must describe **why** where behavior is non-obvious, not narrate syntax.

Good:
```python
def verify_attestation_bundle(bundle: AttestationBundle) -> VerificationResult:
    """Verify bundle integrity and hardware-rooted claims before policy admission."""
```

Bad:
```python
def verify_attestation_bundle(bundle):
    """This function verifies the bundle."""
```

---

## Review Checklist

Before merging code, verify:

- File path matches subsystem ownership.
- Names reflect exact domain semantics.
- Errors are typed and translated at boundaries.
- No vague helper or utility names were introduced.
- Tests mirror source structure.
- Security-sensitive paths avoid secret leakage.
- Cross-subsystem dependencies use public contracts only.
- Public SDK names are stable and intentional.

---

## Summary Rules

1. Keep subsystem roots exactly as defined.
2. Use descriptive, domain-specific names.
3. Encode trust, policy, replay, and boundary behavior explicitly in names.
4. Use typed errors with subsystem-root hierarchies.
5. Mirror `src/` in `tests/`.
6. Avoid generic helpers, implicit globals, and hidden side effects.
7. Protect public SDK naming stability.
8. Let TRDs override style when product requirements demand it.