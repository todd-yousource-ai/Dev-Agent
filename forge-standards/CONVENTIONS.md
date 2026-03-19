# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, file layout, and implementation patterns for the full Forge platform.

It applies to all source code, tests, generated interfaces, and supporting modules across every subsystem.

---

## Core Principles

1. **TRDs are authoritative.**  
   If a convention here conflicts with a TRD, the TRD wins.

2. **Security-sensitive code is explicit, not clever.**  
   Prefer readable control flow, typed errors, narrow interfaces, and audit-friendly names.

3. **Subsystem boundaries must remain visible in code.**  
   Directory names, class names, DTOs, and tests should make ownership obvious.

4. **Names should reveal trust level and execution role.**  
   Distinguish clearly between:
   - trusted vs untrusted content
   - validated vs raw input
   - policy vs transport vs storage types
   - control-plane vs data-plane components

5. **Tests mirror production structure exactly.**  
   Every `src/<subsystem>/...` path should have corresponding tests under `tests/<subsystem>/...`.

6. **Do not invent cross-subsystem abstractions prematurely.**  
   Shared code is allowed only when ownership, lifecycle, and security model are unambiguous.

---

## File and Directory Naming (exact `src/` layout)

### Canonical source layout

```text
src/
  cal/           # Conversation Abstraction Layer
  dtl/           # Data Trust Label
  trustflow/     # TrustFlow audit stream
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

### Directory rules

- Subsystem directories are **lowercase**.
- Use **single-word subsystem roots** exactly as defined:
  - `cal`
  - `dtl`
  - `trustflow`
  - `vtz`
  - `trustlock`
  - `mcp`
  - `rewind`
  - `connector`
- Do not create alias directories such as:
  - `conversation_layer/`
  - `data_trust_label/`
  - `virtual_trust_zone/`
- Nested directories use **snake_case**.
- Directory names should represent one of:
  - domain area
  - protocol
  - adapter type
  - storage mechanism
  - enforcement layer
  - test fixture category

### Preferred nested directory patterns

```text
src/<subsystem>/models/
src/<subsystem>/services/
src/<subsystem>/adapters/
src/<subsystem>/policies/
src/<subsystem>/validators/
src/<subsystem>/serializers/
src/<subsystem>/storage/
src/<subsystem>/audit/
src/<subsystem>/runtime/
src/<subsystem>/transport/
src/<subsystem>/crypto/
src/<subsystem>/fixtures/        # only if runtime fixtures are required
```

Use only directories that fit the subsystem’s actual design. Do not create empty pattern folders.

### File naming rules

- Source files use **snake_case**.
- One file should generally contain one primary class, service, protocol, or cohesive type group.
- File names should match the main exported symbol when practical.

Examples:

```text
src/dtl/models/trust_label.py
src/mcp/policies/policy_evaluator.py
src/trustflow/audit/audit_event_writer.py
src/vtz/runtime/zone_session_manager.py
src/trustlock/crypto/attestation_verifier.py
sdk/connector/client/forge_connector_client.py
```

### Disallowed file naming patterns

- Generic names without subsystem context:
  - `utils.py`
  - `helpers.py`
  - `misc.py`
  - `common.py`
- Vague lifecycle names:
  - `manager.py` unless the type is actually a manager
  - `processor.py` unless it truly processes a stream or pipeline
- Redundant subsystem repetition inside same folder:
  - `src/dtl/models/dtl_label.py` → prefer `trust_label.py`
  - `src/vtz/runtime/vtz_session.py` → prefer `zone_session.py`

### Test file naming

- Test files use `test_<production_file>.py`.
- Tests mirror source paths exactly.

Example:

```text
src/trustflow/audit/event_envelope.py
tests/trustflow/audit/test_event_envelope.py
```

If a source file contains multiple tightly coupled public types, the test file may still remain singular if it maps clearly.

---

## Class and Function Naming

### General naming style

- **Classes:** `PascalCase`
- **Functions/methods:** `snake_case`
- **Variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private/internal helpers:** prefix with single underscore where language/runtime allows
- **Protocols/interfaces/abstract base classes:** `PascalCase`, named by role

### Class naming rules

Use suffixes only when they communicate a real architectural role.

Preferred suffixes:
- `Service`
- `Client`
- `Adapter`
- `Provider`
- `Repository`
- `Store`
- `Validator`
- `Parser`
- `Serializer`
- `Encoder`
- `Decoder`
- `Factory`
- `Builder`
- `Evaluator`
- `Resolver`
- `Verifier`
- `Signer`
- `Reader`
- `Writer`
- `Publisher`
- `Collector`
- `Recorder`
- `Replayer`
- `Policy`
- `Session`
- `Controller` only for explicit orchestration boundaries

Examples:
- `TrustLabelValidator`
- `PolicyEvaluator`
- `AuditEventWriter`
- `ZoneSession`
- `AttestationVerifier`
- `ReplayCursorStore`

Avoid meaningless suffixes:
- `Helper`
- `Thing`
- `Object`
- `Impl`
- `BaseManager`
- `SuperClient`

### Function naming rules

Functions should be verb-led and reveal side effects.

Preferred verbs by intent:
- `parse_*`
- `validate_*`
- `verify_*`
- `serialize_*`
- `deserialize_*`
- `encode_*`
- `decode_*`
- `load_*`
- `save_*`
- `read_*`
- `write_*`
- `build_*`
- `create_*`
- `issue_*`
- `revoke_*`
- `enforce_*`
- `evaluate_*`
- `record_*`
- `publish_*`
- `replay_*`
- `attest_*`

Boolean-returning functions should use:
- `is_*`
- `has_*`
- `can_*`
- `should_*`

Examples:
- `validate_trust_label()`
- `verify_attestation_chain()`
- `evaluate_policy_bundle()`
- `record_audit_event()`
- `replay_session_timeline()`
- `is_zone_transition_allowed()`

### Async naming

If the language/runtime does not distinguish async methods clearly, append `_async` only when needed for clarity or API parity. Do not mix styles arbitrarily.

Prefer:
- `fetch_policy_bundle()`
- `publish_audit_batch()`

Use `_async` only if sync and async variants coexist:
- `load_snapshot()`
- `load_snapshot_async()`

### DTO and schema naming

For structured transport types, use explicit suffixes:
- `Request`
- `Response`
- `Command`
- `Event`
- `Envelope`
- `Record`
- `Snapshot`
- `Manifest`
- `Descriptor`

Examples:
- `PolicyDecisionRequest`
- `PolicyDecisionResponse`
- `AuditEventEnvelope`
- `ReplaySnapshot`
- `ConnectorManifest`

### Enum naming

- Enum type names: `PascalCase`
- Enum values: use the language’s conventional style, but prefer explicit, stable names
- Avoid abbreviations in enum members unless domain-standard

Examples:
- `TrustLevel.HIGH`
- `ZoneState.ACTIVE`
- `ReplayMode.STRICT`

---

## Error and Exception Patterns

### General rules

- Raise or return **typed, domain-specific errors**.
- Never use broad, opaque exceptions for expected failures.
- Error messages must be:
  - concise
  - stable enough for logs and tests
  - safe for audit trails
- Never include secrets, tokens, key material, raw credentials, or unredacted sensitive payloads in error messages.

### Error naming

Custom exception classes use `PascalCase` and end with one of:
- `Error`
- `Exception` only if the local codebase already uses it consistently

Prefer `Error`.

Examples:
- `TrustLabelValidationError`
- `PolicyEvaluationError`
- `AuditPublishError`
- `ZoneTransitionError`
- `AttestationVerificationError`
- `ReplayConsistencyError`

### Error categories

Every subsystem should distinguish at minimum between:

1. **Validation errors**  
   Input malformed, incomplete, or semantically invalid.

2. **Policy errors**  
   Request denied by policy or trust rules.

3. **Integrity errors**  
   Signature mismatch, hash mismatch, tampering, replay inconsistency.

4. **Transport or I/O errors**  
   Socket, storage, network, queue, stream, persistence failures.

5. **State errors**  
   Illegal transition, missing prerequisite, expired session, closed cursor.

6. **Internal invariant errors**  
   Unexpected state that should not happen if code is correct.

### Pattern for exception hierarchy

Each subsystem should define a root error and derive typed variants.

Example:

```python
class DtlError(Exception):
    pass

class TrustLabelValidationError(DtlError):
    pass

class TrustLabelIntegrityError(DtlError):
    pass

class TrustLabelSerializationError(DtlError):
    pass
```

### Wrapping lower-level errors

- Wrap third-party or infrastructure errors at subsystem boundaries.
- Preserve original cause where supported.
- Convert generic exceptions into domain terms before crossing API boundaries.

Preferred pattern:
- low-level parser error → `TrustLabelSerializationError`
- crypto backend failure → `AttestationVerificationError`
- queue publish failure → `AuditPublishError`

### Prohibited error practices

- `except Exception:` without immediate re-raise or domain wrapping
- returning `None` to mean “error”
- mixing success payloads and error strings
- embedding stack traces in user-facing responses
- leaking raw policy source or secret material through exceptions

---

## Per-Subsystem Naming Rules

---

### `src/cal/` — Conversation Abstraction Layer

#### Purpose
Owns conversation abstraction, message normalization, interaction state, and conversation-safe representations used by upstream orchestration.

#### Naming rules
Use the term **conversation** for user/agent interaction threads, and **message** for atomic units.

#### Preferred type names
- `ConversationSession`
- `ConversationMessage`
- `MessageEnvelope`
- `MessageNormalizer`
- `ConversationStateStore`
- `PromptBoundaryValidator`
- `InteractionContext`

#### Preferred function names
- `normalize_message()`
- `append_message()`
- `build_conversation_context()`
- `validate_prompt_boundary()`
- `serialize_message_envelope()`

#### Avoid
- `chat_*`
- `bot_*`
- `thread_*` unless the TRD explicitly uses thread terminology
- `prompt_manager` when the component actually validates or transforms prompts

#### File examples
```text
src/cal/models/conversation_message.py
src/cal/services/message_normalizer.py
src/cal/validators/prompt_boundary_validator.py
```

---

### `src/dtl/` — Data Trust Label

#### Purpose
Owns data trust labeling, trust classification, provenance labeling, and trust metadata validation.

#### Naming rules
Use **trust_label** as the canonical term, not `tag`, `badge`, or `marker`.

#### Preferred type names
- `TrustLabel`
- `TrustLabelValidator`
- `TrustLabelParser`
- `TrustLabelSerializer`
- `TrustProvenanceRecord`
- `TrustClassification`
- `LabelDerivationPolicy`

#### Preferred function names
- `validate_trust_label()`
- `parse_trust_label()`
- `serialize_trust_label()`
- `derive_trust_classification()`
- `attach_provenance_record()`

#### Avoid
- `label_utils`
- `trust_helper`
- `metadata_processor` when trust semantics are central

#### File examples
```text
src/dtl/models/trust_label.py
src/dtl/validators/trust_label_validator.py
src/dtl/policies/label_derivation_policy.py
```

---

### `src/trustflow/` — TrustFlow audit stream

#### Purpose
Owns audit event creation, integrity-preserving event flow, audit publication, and stream consumption.

#### Naming rules
Use **audit_event**, **envelope**, **stream**, **batch**, and **cursor** consistently.

#### Preferred type names
- `AuditEvent`
- `AuditEventEnvelope`
- `AuditEventWriter`
- `AuditStreamPublisher`
- `AuditBatchBuilder`
- `AuditCursor`
- `StreamCheckpointStore`

#### Preferred function names
- `record_audit_event()`
- `publish_audit_batch()`
- `load_stream_checkpoint()`
- `advance_audit_cursor()`
- `verify_event_envelope()`

#### Avoid
- `log_event` for structured audit records
- `logger` for event pipeline writers unless it truly wraps a logging framework
- `queue_item` when the object is an audit event envelope

#### File examples
```text
src/trustflow/models/audit_event.py
src/trustflow/audit/audit_event_writer.py
src/trustflow/storage/stream_checkpoint_store.py
```

---

### `src/vtz/` — Virtual Trust Zone enforcement

#### Purpose
Owns zone boundaries, zone lifecycle, trust-zone transitions, and enforcement decisions.

#### Naming rules
Use **zone**, **boundary**, **transition**, **session**, and **enforcement** as canonical terms.

#### Preferred type names
- `ZoneSession`
- `ZoneBoundary`
- `ZoneTransitionPolicy`
- `ZoneEnforcementService`
- `BoundaryViolationError`
- `TrustZoneDescriptor`

#### Preferred function names
- `open_zone_session()`
- `close_zone_session()`
- `enforce_zone_boundary()`
- `evaluate_zone_transition()`
- `is_zone_transition_allowed()`

#### Avoid
- `sandbox` unless the TRD explicitly means sandbox
- `container` unless integrating with container runtime
- `permission_check` when evaluating trust-zone semantics

#### File examples
```text
src/vtz/runtime/zone_session.py
src/vtz/policies/zone_transition_policy.py
src/vtz/services/zone_enforcement_service.py
```

---

### `src/trustlock/` — Cryptographic machine identity

#### Purpose
Owns machine identity, attestation, TPM-backed identity proofs, trust anchors, and verification flows.

#### Naming rules
Use **attestation**, **identity**, **anchor**, **quote**, **verifier**, and **signer** consistently.

#### Preferred type names
- `MachineIdentity`
- `AttestationQuote`
- `AttestationVerifier`
- `TrustAnchorStore`
- `IdentityProvisioner`
- `QuoteSigner`
- `CredentialBinding`

#### Preferred function names
- `issue_machine_identity()`
- `verify_attestation_quote()`
- `load_trust_anchors()`
- `bind_credential_to_identity()`
- `rotate_identity_material()`

#### Avoid
- `crypto_utils`
- `key_manager` unless full key lifecycle management is actually implemented
- `token_verifier` when attestation semantics are involved

#### File examples
```text
src/trustlock/models/machine_identity.py
src/trustlock/crypto/attestation_verifier.py
src/trustlock/storage/trust_anchor_store.py
```

---

### `src/mcp/` — MCP Policy Engine

#### Purpose
Owns policy evaluation, policy bundles, rule resolution, decisioning, and enforcement recommendations.

#### Naming rules
Use **policy**, **rule**, **bundle**, **decision**, **evaluator**, and **resolver** consistently.

#### Preferred type names
- `PolicyBundle`
- `PolicyRule`
- `PolicyEvaluator`
- `DecisionResolver`
- `PolicyDecisionRequest`
- `PolicyDecisionResponse`
- `EnforcementRecommendation`

#### Preferred function names
- `evaluate_policy_bundle()`
- `resolve_policy_decision()`
- `load_policy_rules()`
- `validate_policy_bundle()`
- `build_enforcement_recommendation()`

#### Avoid
- `engine_utils`
- `checker`
- `handler` when the code actually performs policy evaluation

#### File examples
```text
src/mcp/models/policy_bundle.py
src/mcp/policies/policy_evaluator.py
src/mcp/resolvers/decision_resolver.py
```

---

### `src/rewind/` — Forge Rewind replay engine

#### Purpose
Owns replay, deterministic reconstruction, timeline traversal, snapshots, and replay consistency validation.

#### Naming rules
Use **replay**, **timeline**, **snapshot**, **cursor**, **checkpoint**, and **consistency** consistently.

#### Preferred type names
- `ReplayEngine`
- `ReplaySnapshot`
- `ReplayCursor`
- `TimelineSegment`
- `ConsistencyVerifier`
- `CheckpointLoader`

#### Preferred function names
- `replay_timeline()`
- `load_replay_snapshot()`
- `advance_replay_cursor()`
- `verify_replay_consistency()`
- `restore_checkpoint_state()`

#### Avoid
- `history_manager`
- `time_travel`
- `debug_replay` for production replay semantics

#### File examples
```text
src/rewind/runtime/replay_engine.py
src/rewind/models/replay_snapshot.py
src/rewind/validators/consistency_verifier.py
```

---

### `sdk/connector/` — Forge Connector SDK

#### Purpose
Owns SDK-facing integration contracts, connector client libraries, manifests, transport wrappers, and public integration surface.

#### Naming rules
Public SDK names must be stable, explicit, and integration-friendly. Prefer **connector**, **client**, **manifest**, **session**, and **transport**.

#### Preferred type names
- `ForgeConnectorClient`
- `ConnectorManifest`
- `ConnectorSession`
- `ConnectorTransport`
- `ConnectorRequest`
- `ConnectorResponse`
- `ConnectorAuthProvider`

#### Preferred function names
- `connect()`
- `open_connector_session()`
- `send_connector_request()`
- `load_connector_manifest()`
- `validate_connector_response()`

#### Avoid
- `sdk_helper`
- `integration_utils`
- public names tied to internal implementation details

#### File examples
```text
sdk/connector/client/forge_connector_client.py
sdk/connector/models/connector_manifest.py
sdk/connector/transport/connector_transport.py
```

---

## Cross-Subsystem Naming Rules

### Trusted vs untrusted data

Names must reveal trust state whenever ambiguous.

Prefer:
- `raw_payload`
- `untrusted_input`
- `validated_request`
- `verified_attestation`
- `sanitized_content`
- `redacted_event`

Avoid:
- `data`
- `payload`
- `content`
- `input`

### Serialized vs structured forms

Always distinguish bytes/string forms from parsed objects.

Prefer:
- `serialized_label`
- `encoded_quote`
- `event_json`
- `parsed_manifest`
- `policy_document`

Avoid:
- `label`
- `quote`
- `manifest` when type ambiguity exists

### IDs and references

Use stable suffixes:
- `_id` for opaque identifiers
- `_key` for map lookup keys
- `_hash` for hashes
- `_digest` for digests
- `_uri` for URIs
- `_path` for filesystem paths
- `_at` for timestamps
- `_by` for actor identities

Examples:
- `event_id`
- `zone_id`
- `anchor_hash`
- `created_at`
- `issued_by`

### Booleans

Boolean variables must read as propositions.

Prefer:
- `is_verified`
- `has_boundary_access`
- `can_publish`
- `should_replay`

Avoid:
- `verified`
- `boundary_access`
- `publish_flag`

---

## Code Patterns

### Validation-first pattern

Validate external or untrusted input at the boundary before transformation or persistence.

Preferred flow:
1. receive raw input
2. parse into structured form
3. validate schema
4. validate trust/policy/integrity
5. persist or act

Example naming sequence:
- `raw_event`
- `parsed_event`
- `validated_event`
- `verified_event`

### Boundary wrapping pattern

At every subsystem boundary:
- validate inputs
- convert foreign errors into subsystem errors
- emit audit events if required by TRD/security model
- return typed domain results

### Explicit policy evaluation pattern

Policy decisions should not be hidden inside generic methods.

Prefer:
- `decision = policy_evaluator.evaluate_policy_bundle(request)`
- `recommendation = decision_resolver.build_enforcement_recommendation(decision)`

Avoid:
- `service.process(request)` if policy evaluation is the true action

### Replay-safe deterministic pattern

For replayable systems:
- isolate time sources
- isolate randomness
- inject clocks, ID generators, and sequence providers
- name deterministic helpers explicitly:
  - `DeterministicClock`
  - `ReplaySequenceProvider`

### Audit-safe logging pattern

Operational logs and audit events are not the same.

- Use logging for diagnostics.
- Use TrustFlow event models for auditable actions.
- Never substitute one for the other.

---

## Imports and Dependency Rules

### Import style

- Prefer absolute imports rooted at subsystem package boundaries.
- Avoid deep relative imports when they obscure ownership.
- Do not import across subsystem internals unless the interface is explicitly public.

Prefer:
```python
from src.dtl.models.trust_label import TrustLabel
from src.mcp.policies.policy_evaluator import PolicyEvaluator
```

Avoid:
```python
from ..models.trust_label import TrustLabel
from src.dtl.validators.trust_label_validator import SomeInternalHelper
```

### Dependency direction

Preferred dependency shape:
- `models` are dependency-light
- `validators`, `serializers`, `policies` depend on `models`
- `services` orchestrate lower-level components
- `adapters` isolate external systems
- `sdk/connector` depends only on documented public contracts, not internal private modules

Avoid cyclical dependencies between subsystems.

---

## Testing Conventions

### Test layout

Tests must mirror source structure exactly.

Example:
```text
src/mcp/policies/policy_evaluator.py
tests/mcp/policies/test_policy_evaluator.py
```

### Test naming

- Test functions use `test_<behavior>`.
- Name tests after observable behavior, not implementation detail.

Prefer:
- `test_rejects_untrusted_label_without_provenance()`
- `test_advances_replay_cursor_after_checkpoint_restore()`

Avoid:
- `test_helper_1()`
- `test_internal_branch_b()`

### Test categories

Where needed, separate by suffix or directory:
- unit
- integration
- contract
- replay
- security

Examples:
```text
tests/trustlock/crypto/test_attestation_verifier.py
tests/trustlock/crypto/test_attestation_verifier_integration.py
tests/rewind/runtime/test_replay_engine_replay.py
```

### Security test naming

Security-relevant tests should make the threat or invariant obvious.

Examples:
- `test_rejects_modified_attestation_quote()`
- `test_prevents_cross_zone_transition_without_policy()`
- `test_redacts_secret_material_from_audit_error()`

---

## Documentation and Comment Conventions

### Comments

Comment only when:
- documenting non-obvious security rationale
- explaining protocol or TRD-mandated behavior
- clarifying invariants
- documenting edge-case intent

Avoid comments that restate code.

Good:
```python
# TRD-11: raw attestation material must never be persisted before verification.
```

Bad:
```python
# Increment the counter
counter += 1
```

### Docstrings

Public classes and functions should have concise docstrings when they:
- form part of a subsystem boundary
- implement protocol contracts
- enforce trust/security behavior
- are consumed by SDK users or other subsystems

Docstrings should describe:
- purpose
- key inputs/outputs
- notable side effects
- security or determinism constraints when relevant

---

## Constants, Configuration, and Schemas

### Constants

- Constants use `UPPER_SNAKE_CASE`.
- Group subsystem constants in dedicated files only if they are truly shared.
- Prefer typed config objects over scattered magic strings.

Examples:
- `MAX_AUDIT_BATCH_SIZE`
- `DEFAULT_REPLAY_WINDOW`
- `ATTESTATION_QUOTE_VERSION`

### Configuration naming

Use suffixes:
- `Config`
- `Settings`
- `Options`

Examples:
- `TrustFlowConfig`
- `ReplaySettings`
- `ConnectorClientOptions`

### Schema naming

Use explicit names for validation or transport schemas:
- `TrustLabelSchema`
- `PolicyDecisionRequestSchema`
- `AuditEventEnvelopeSchema`

---

## Anti-Patterns

Do not introduce:

- generic `utils` modules for domain logic
- cross-subsystem “shared” packages without explicit ownership
- hidden policy checks inside unrelated service methods
- untyped dict-based APIs where stable DTOs are expected
- silent exception swallowing
- names that conceal trust state
- names that blur audit logs with audit events
- replay logic that depends on ambient time or randomness
- public SDK symbols that expose internal implementation structure

---

## Minimum Naming Checklist

Before merging, confirm:

- file path matches the owning subsystem
- file name is snake_case and specific
- class names are PascalCase and role-accurate
- function names are verb-led and side-effect-aware
- typed errors exist for expected failure modes
- trusted/untrusted data is named explicitly
- tests mirror source layout exactly
- subsystem terminology matches the canonical terms in this document
- comments reference TRDs where security or protocol behavior is non-obvious

---

## Canonical Terminology Summary

Use these exact subsystem terms consistently:

- **CAL:** conversation, message, envelope, interaction, context
- **DTL:** trust_label, provenance, classification, derivation
- **TrustFlow:** audit_event, envelope, stream, batch, cursor, checkpoint
- **VTZ:** zone, boundary, transition, enforcement, session
- **TrustLock:** identity, attestation, quote, anchor, verifier, signer
- **MCP:** policy, rule, bundle, decision, evaluator, resolver
- **Rewind:** replay, timeline, snapshot, cursor, checkpoint, consistency
- **Connector SDK:** connector, client, manifest, session, transport, request, response

---

## Final Rule

If a name is shorter but less precise, choose the more precise name.  
In Forge, clarity, auditability, and trust semantics are always more important than brevity.