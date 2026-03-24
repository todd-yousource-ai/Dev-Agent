# Code Conventions

This document defines coding conventions derived from the provided technical requirements and repository guidance. The specification documents are the source of truth; code, interfaces, error handling, and tests must conform to them.

## File and Directory Naming (exact `src/` layout)

Use the repository structure exactly as defined by subsystem ownership.

```text
src/
  cal/            # Conversation Abstraction Layer components
  dtl/            # Data Trust Label components
  trustflow/      # TrustFlow audit stream components
  vtz/            # Virtual Trust Zone enforcement
  trustlock/      # Cryptographic machine identity
  mcp/            # Policy engine
  rewind/         # Replay engine

sdk/
  connector/      # Connector SDK

tests/
  <subsystem>/    # Mirrors src/ structure exactly
```

### Directory rules

- Subsystem directories are lowercase.
- Directory names are stable API boundaries; do not invent alternate aliases.
- Tests must mirror source layout exactly.
- Swift shell code and Python backend code must remain separated by process ownership and responsibility.
- Files should be placed under the subsystem that owns the behavior, not under a generic shared folder unless that shared contract is explicitly cross-cutting.

### File naming rules

- Use lowercase `snake_case` for Python source files.
- Use feature-oriented names, not vague utility names.
- Prefer names that reflect the owning concept or protocol boundary:
  - `consensus_engine.py`
  - `provider_adapter.py`
  - `audit_stream.py`
  - `policy_evaluator.py`
- Avoid:
  - `utils.py`
  - `helpers.py`
  - `misc.py`
  - `temp.py`

### Test file naming

- Test files must mirror the source module name:
  - `src/cal/conversation_router.py` → `tests/cal/test_conversation_router.py`
  - `src/trustflow/audit_stream.py` → `tests/trustflow/test_audit_stream.py`
- Use `test_<module>.py` naming consistently.
- Keep subsystem ownership identical between implementation and tests.

---

## Class and Function Naming

### General naming

- Classes: `PascalCase`
- Protocols, interfaces, abstract types: `PascalCase` with role-based names
- Functions and methods:
  - Python: `snake_case`
  - Swift: `lowerCamelCase`
- Constants:
  - Python module constants: `UPPER_SNAKE_CASE`
  - Swift static constants: `lowerCamelCase` unless platform convention requires otherwise
- Enum cases:
  - Python: lowercase symbolic values
  - Swift: `lowerCamelCase`

### Naming intent

Names must describe responsibility, not implementation detail.

Prefer:

- `ConsensusEngine`
- `ProviderAdapter`
- `AuditEvent`
- `TrustLabelEncoder`
- `ReplaySession`
- `SocketAuthenticator`

Avoid:

- `Manager`
- `Handler`
- `Processor`
- `Service`
- `Thing`
- `Data`

Use broad suffixes only when the TRD-defined role is truly generic.

### Function naming rules

Use verbs for actions and nouns for accessors.

Good examples:

- `build_request_payload`
- `validate_machine_identity`
- `append_audit_event`
- `mark_ready_for_review`
- `load_keychain_secret`
- `evaluate_policy`

Bad examples:

- `do_build`
- `handle_it`
- `run_data`
- `process`
- `thing_for_pr`

### Boolean naming

Boolean properties and functions should read as predicates.

Examples:

- `is_authenticated`
- `is_draft`
- `has_required_scope`
- `can_merge`
- `should_retry`

Avoid ambiguous names like:

- `auth`
- `draft`
- `mergeable_check`

### Asynchronous naming

If a function is asynchronous, name it by the operation, not by implementation detail. Add `async` only where required by language or existing API conventions, not as a naming crutch.

Prefer:

- `fetch_pull_request`
- `stream_audit_events`

Avoid:

- `async_fetch_pull_request`
- `threaded_stream_audit_events`

---

## Error and Exception Patterns

Error handling must match documented contracts. Do not invent silent fallbacks where a subsystem requires explicit failure.

### Core rules

- Use explicit, typed errors.
- Preserve subsystem boundaries in error naming.
- Include actionable context, but never leak secrets, tokens, machine identity material, or untrusted generated content into logs or user-facing errors.
- Never swallow security-relevant or contract-relevant failures.
- Distinguish:
  - validation errors
  - transport errors
  - authentication/authorization errors
  - policy denial
  - protocol violations
  - external API contract failures
  - replay/audit integrity failures

### Python exception naming

Use `PascalCase` and suffix with `Error` unless the exception represents a policy or protocol category with a stronger TRD-defined meaning.

Examples:

- `SocketAuthenticationError`
- `PolicyEvaluationError`
- `DraftLifecycleError`
- `AuditIntegrityError`
- `TrustZoneViolationError`
- `ReplayMismatchError`

### Swift error naming

Use `Error`-conforming enums or structs named for the domain:

- `AuthError`
- `KeychainError`
- `XPCError`
- `SocketProtocolError`

Enum cases should be specific and stable:

- `invalidResponse`
- `authenticationFailed`
- `missingEntitlement`
- `malformedMessage`

### Error message rules

Error messages should be:

- concise
- deterministic
- redact-safe
- actionable

Good:

- `failed to authenticate socket peer`
- `policy denied repository write operation`
- `pull request remained draft after REST update attempt`

Bad:

- `something went wrong`
- `GitHub failed`
- `token abc123 was rejected`
- `raw provider output: ...`

### Wrapping and propagation

When rethrowing or translating errors:

- preserve the original cause where possible
- translate across process boundaries into the documented wire contract
- do not expose implementation-only stack details over line-delimited JSON IPC
- map external API quirks into stable internal error categories

Example pattern:

- external GraphQL mutation failure → internal `DraftLifecycleError`
- invalid line-delimited JSON message → `SocketProtocolError`
- audit hash mismatch → `AuditIntegrityError`

### Retry semantics

Only retry when the owning contract allows it.

- Retry transient transport failures with bounded policy.
- Do not retry:
  - authentication failures
  - policy denials
  - protocol violations
  - integrity check failures
- Retry logic must be explicit in name and scope:
  - `retry_fetch_pull_request`
  - `with_retry_on_transient_failure`

### Logging and errors

- Never log secrets from Keychain-backed storage, auth tokens, machine identity material, or generated code content if prohibited by security controls.
- Errors crossing trust boundaries must be sanitized.
- Audit stream entries must preserve integrity and traceability without exposing sensitive material beyond the contract.

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Use names centered on conversation structure, turns, routing, and context.

### Preferred nouns

- `Conversation`
- `Turn`
- `Message`
- `Context`
- `Transcript`
- `Router`
- `Session`

### Preferred class and module patterns

- `conversation_session.py`
- `message_router.py`
- `turn_state.py`
- `context_window.py`

### Function patterns

- `append_turn`
- `route_message`
- `build_context_window`
- `truncate_transcript`

### Avoid

- vague conversational names like `chat_stuff.py`
- generic state names like `data_store.py` unless the TRD explicitly defines that role

---

## `src/dtl/` — Data Trust Label

Use names centered on classification, provenance, trust labeling, and enforcement metadata.

### Preferred nouns

- `TrustLabel`
- `Classification`
- `Provenance`
- `SourceKind`
- `Sensitivity`
- `LabelPolicy`

### Preferred module names

- `trust_label.py`
- `provenance_encoder.py`
- `classification_rules.py`

### Function patterns

- `assign_trust_label`
- `encode_provenance`
- `validate_label_transition`
- `derive_sensitivity`

### Error names

- `TrustLabelError`
- `InvalidProvenanceError`
- `LabelTransitionError`

---

## `src/trustflow/` — TrustFlow Audit Stream

Use names centered on append-only audit behavior, integrity, sequencing, and event emission.

### Preferred nouns

- `AuditEvent`
- `AuditStream`
- `Sequence`
- `Envelope`
- `Checkpoint`
- `IntegrityChain`

### Preferred module names

- `audit_stream.py`
- `audit_event.py`
- `integrity_chain.py`
- `stream_checkpoint.py`

### Function patterns

- `append_audit_event`
- `verify_integrity_chain`
- `load_checkpoint`
- `emit_envelope`

### Error names

- `AuditIntegrityError`
- `SequenceGapError`
- `CheckpointLoadError`

### Special rule

Names in this subsystem should imply immutability and append-only semantics where applicable. Avoid names suggesting in-place mutation for audit records.

Prefer:

- `append_audit_event`

Avoid:

- `update_audit_event`

---

## `src/vtz/` — Virtual Trust Zone

Use names centered on boundary enforcement, isolation, allowed actions, and violations.

### Preferred nouns

- `TrustZone`
- `Boundary`
- `IsolationPolicy`
- `Guard`
- `Enforcer`
- `Violation`

### Preferred module names

- `trust_zone.py`
- `boundary_guard.py`
- `isolation_policy.py`
- `zone_enforcer.py`

### Function patterns

- `enforce_boundary`
- `validate_zone_access`
- `deny_untrusted_operation`
- `assert_isolated_execution`

### Error names

- `TrustZoneViolationError`
- `BoundaryEnforcementError`
- `IsolationPolicyError`

### Special rule

Use deny-by-default naming where behavior is security-sensitive. Favor names that make enforcement explicit.

Prefer:

- `allowlisted_operation`
- `deny_untrusted_operation`

Avoid:

- `maybe_run`
- `soft_check_access`

---

## `src/trustlock/` — Cryptographic Machine Identity

Use names centered on machine identity, attestation, key material handling, and secure anchoring.

### Preferred nouns

- `MachineIdentity`
- `Attestation`
- `KeyMaterial`
- `Anchor`
- `Signer`
- `Verifier`

### Preferred module names

- `machine_identity.py`
- `attestation_verifier.py`
- `key_material_store.py`
- `identity_anchor.py`

### Function patterns

- `load_machine_identity`
- `verify_attestation`
- `sign_challenge`
- `rotate_key_material`

### Error names

- `MachineIdentityError`
- `AttestationVerificationError`
- `KeyMaterialAccessError`

### Special rule

Never use names that imply raw secret exposure.

Prefer:

- `load_signing_key_reference`

Avoid:

- `get_private_key_plaintext`

---

## `src/mcp/` — Policy Engine

Use names centered on policy definition, evaluation, decisioning, and enforcement outcomes.

### Preferred nouns

- `Policy`
- `Rule`
- `Decision`
- `Evaluator`
- `Constraint`
- `Effect`

### Preferred module names

- `policy_evaluator.py`
- `decision_record.py`
- `rule_set.py`
- `constraint_graph.py`

### Function patterns

- `evaluate_policy`
- `apply_rule_set`
- `record_decision`
- `resolve_constraints`

### Error names

- `PolicyEvaluationError`
- `RuleConfigurationError`
- `ConstraintResolutionError`

### Special rule

Decision-returning APIs should use clear outcome terminology:

- `allow`
- `deny`
- `require_review`

Avoid ambiguous result names like:

- `ok`
- `pass`
- `green`

---

## `src/rewind/` — Replay Engine

Use names centered on replay, determinism, event reconstruction, and verification.

### Preferred nouns

- `Replay`
- `Frame`
- `Snapshot`
- `Timeline`
- `Cursor`
- `Reconstructor`

### Preferred module names

- `replay_session.py`
- `timeline_cursor.py`
- `snapshot_loader.py`
- `event_reconstructor.py`

### Function patterns

- `replay_from_checkpoint`
- `advance_cursor`
- `load_snapshot`
- `reconstruct_event_sequence`

### Error names

- `ReplayMismatchError`
- `SnapshotLoadError`
- `TimelineCorruptionError`

### Special rule

Names should distinguish live execution from replayed execution.

Prefer:

- `replay_session`
- `reconstructed_event`

Avoid:

- `run_session`
- `normal_event`

---

## `sdk/connector/` — Connector SDK

Use names centered on external integration contracts, client boundaries, and stable SDK surface area.

### Preferred nouns

- `Connector`
- `Client`
- `Request`
- `Response`
- `Capability`
- `Session`

### Preferred module names

- `connector_client.py`
- `capability_registry.py`
- `request_builder.py`
- `response_decoder.py`

### Function patterns

- `build_request`
- `decode_response`
- `negotiate_capabilities`
- `open_connector_session`

### Error names

- `ConnectorProtocolError`
- `CapabilityNegotiationError`
- `ResponseDecodingError`

### Special rule

SDK names form part of a public contract. Prefer explicit, version-stable names and avoid internal implementation terms.

---

## Cross-Process and Interface Conventions

The architecture is two-process: shell process and backend process. Naming must preserve ownership and trust boundaries.

### IPC naming

For authenticated Unix socket and line-delimited JSON communication:

- use names like:
  - `SocketMessage`
  - `SocketAuthenticator`
  - `JsonLineCodec`
  - `MessageEnvelope`
- avoid vague names like:
  - `PipeHelper`
  - `CommStuff`

### Message shape naming

Use contract terms consistently:

- `request`
- `response`
- `event`
- `error`
- `envelope`

Do not mix synonyms such as `packet`, `blob`, and `payload` unless the TRD distinguishes them.

### Serialization functions

Prefer:

- `encode_message`
- `decode_envelope`
- `parse_json_line`
- `serialize_response`

Avoid:

- `pack`
- `unpack`
- `marshal_stuff`

---

## External API Integration Conventions

External API behavior must be encoded in stable internal names that reflect real contract semantics, not assumptions.

### Pull request lifecycle naming

Because draft lifecycle behavior has specific API constraints, use precise names:

- `create_draft_pull_request`
- `mark_pull_request_ready_for_review`
- `merge_pull_request`
- `refresh_pull_request_state`

Avoid misleading names such as:

- `undraft_pull_request_via_rest`

If implementation must account for API quirks, keep that detail inside the adapter layer and expose the correct domain action name.

### Adapter naming

For external providers and service integrations:

- `<Domain>Adapter`
- `<Domain>Client`
- `<Domain>Mutation`
- `<Domain>Query`

Examples:

- `PullRequestClient`
- `GraphqlMutationBuilder`
- `RepositoryAdapter`

### Error mapping

Map provider-specific failures into stable domain errors.

Prefer:

- `DraftLifecycleError`
- `RepositoryPermissionError`

Avoid surfacing raw provider-only terminology outside the adapter layer unless contractually required.

---

## Security-Sensitive Naming Rules

Security-relevant code must make trust level and operation intent obvious.

### Required patterns

Use names that indicate:

- trust state
- validation step
- enforcement point
- redaction behavior
- boundary crossing

Examples:

- `validate_external_content`
- `sanitize_error_payload`
- `redact_sensitive_fields`
- `authenticate_socket_peer`
- `verify_generated_artifact_metadata`

### Forbidden style patterns

Avoid names that obscure sensitive behavior:

- `check_data`
- `clean_output`
- `safe_mode`
- `fix_auth`

### Secrets and credentials

Use references, handles, or descriptors in names rather than raw material terms when possible.

Prefer:

- `credential_reference`
- `token_handle`
- `secret_metadata`

Avoid:

- `raw_token`
- `plaintext_secret`

---

## Testing Naming Conventions

Tests must mirror subsystem ownership and contract names.

### File layout

- `tests/cal/`
- `tests/dtl/`
- `tests/trustflow/`
- `tests/vtz/`
- `tests/trustlock/`
- `tests/mcp/`
- `tests/rewind/`

### Test function naming

Use:

- `test_<action>_<expected_outcome>`
- `test_<condition>_<behavior>`

Examples:

- `test_append_audit_event_increments_sequence`
- `test_verify_attestation_rejects_invalid_signature`
- `test_mark_pull_request_ready_for_review_uses_supported_transition`
- `test_evaluate_policy_denies_untrusted_write`

### Test class naming

If grouping is needed, use:

- `TestAuditStream`
- `TestPolicyEvaluator`
- `TestReplaySession`

Avoid generic names like `TestUtils`.

---

## Code Pattern Conventions

### Single-responsibility modules

Each file should expose one primary concept or tightly related contract set.

### Boundary adapters

Put external system quirks behind adapter classes or modules.

- Keep provider-specific behavior out of domain logic.
- Keep transport details out of policy logic.
- Keep UI/auth/secrets ownership separate from backend intelligence logic.

### Deterministic interfaces

For replay, audit, and policy-sensitive systems:

- prefer deterministic function signatures
- avoid hidden global state
- make time, randomness, and external I/O injectable where needed

### Explicit trust transitions

Whenever data crosses a trust boundary, name the transition explicitly.

Examples:

- `label_external_input`
- `sanitize_before_render`
- `verify_before_replay`
- `enforce_policy_before_write`

### No execution-implying names for generated content

Because generated code is not executed, do not use names that imply direct execution of generated artifacts.

Avoid:

- `execute_generated_code`
- `run_suggested_patch`

Prefer:

- `render_generated_patch`
- `validate_generated_output`
- `stage_generated_changes`

---

## Naming Anti-Patterns

Do not introduce:

- `utils`, `helpers`, `common`, `misc` as catch-all modules
- abbreviations not already established by subsystem names
- product-specific names in code identifiers unless required by an existing public contract
- implementation-detail names exposed at domain boundaries
- names that hide security significance

Bad examples:

- `src/mcp/utils.py`
- `src/vtz/helper.py`
- `src/trustflow/common.py`
- `AuthThing`
- `process_data`

Good replacements:

- `constraint_graph.py`
- `boundary_guard.py`
- `integrity_chain.py`
- `SocketAuthenticator`
- `assign_trust_label`

---

## Final Rule

If a name, file placement, or error pattern is ambiguous:

1. follow subsystem ownership,
2. prefer explicit domain terminology,
3. preserve trust and process boundaries,
4. match documented interfaces and contracts,
5. do not invent new conventions that conflict with the specification.