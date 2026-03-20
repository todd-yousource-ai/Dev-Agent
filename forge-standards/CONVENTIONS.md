# Code Conventions — Forge Platform

This document defines coding conventions, naming rules, and required code patterns for the full Forge platform.

Forge is a multi-subsystem platform with strict naming and structure requirements. These conventions apply across all source code, tests, SDKs, automation, and generated repository layout unless a subsystem-specific rule below is stricter.

---

## Source of Truth and Priority

When implementing or modifying code:

1. TRDs in `forge-docs/` are the source of truth.
2. Security requirements in TRD-11 override convenience or local patterns.
3. This file defines repository-wide naming and implementation conventions.
4. Subsystem-specific rules in this file override general rules for that subsystem.
5. Do not invent new top-level naming patterns if an existing one fits.

If conventions conflict with a TRD, follow the TRD and update this file.

---

## Repository Identity

Forge platform includes the following major subsystems:

- `cal` — Conversation Abstraction Layer
- `dtl` — Data Trust Label
- `trustflow` — TrustFlow audit stream
- `vtz` — Virtual Trust Zone enforcement
- `trustlock` — Cryptographic machine identity
- `mcp` — MCP Policy Engine
- `rewind` — Forge Rewind replay engine
- `sdk/connector` — Forge Connector SDK

Tests must mirror subsystem structure exactly.

---

# File and Directory Naming

## File and Directory Naming (exact src/ layout)

The `src/` layout is fixed:

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

### Required rules

- Directory names must be lowercase.
- Directory names must use a single canonical subsystem name.
- Do not introduce aliases for subsystem directories.
- Tests must mirror production structure exactly.
- Shared helpers must live in an explicit shared module, never in an arbitrary subsystem.

### Allowed naming forms

- Python packages/modules: `snake_case`
- Swift file names: `PascalCase.swift`
- JSON/YAML fixtures: `snake_case.json`, `snake_case.yaml`
- Shell scripts: `verb_noun.sh`
- Markdown docs: `UPPERCASE.md` for repository authority files, otherwise `snake_case.md`

### Disallowed forms

- Mixed-case directories under `src/`
- Abbreviations not already standardized by the platform
- Generic filenames like `utils.py`, `helpers.py`, `misc.py`, `temp.py`, `new.py`
- Version suffixes in filenames such as `_v2`, `_new`, `_final`

Use purpose-specific names instead.

---

## General Naming Principles

All names must be:

- Specific
- Stable
- Searchable
- Unambiguous
- Consistent with subsystem terminology from TRDs

Prefer names that encode role rather than implementation detail.

### Good examples

- `policy_evaluator.py`
- `TrustZoneEnforcer.swift`
- `audit_stream_writer.py`
- `connector_session.py`

### Bad examples

- `manager.py`
- `common.py`
- `service.py` when multiple services exist
- `data_handler.py`
- `thing.py`

---

# Class and Function Naming

## Classes, Structs, Enums, Protocols, and Types

### Python

- Classes: `PascalCase`
- Exceptions: `PascalCaseError` or `PascalCaseException`
- Enums: `PascalCase`
- Protocol-like ABCs: `PascalCase` with suffix matching role:
  - `Provider`
  - `Adapter`
  - `Client`
  - `Store`
  - `Policy`
  - `Evaluator`

Examples:

- `TrustLabel`
- `AuditEvent`
- `ReplaySession`
- `PolicyEvaluator`
- `MachineIdentityProvider`

### Swift

- Types: `PascalCase`
- Protocols: `PascalCase`, preferably capability-oriented
- Error enums: `PascalCaseError`
- View types: suffix `View`
- View models: suffix `ViewModel`
- Coordinators: suffix `Coordinator`
- Stores: suffix `Store`

Examples:

- `ConversationRouter`
- `TrustFlowView`
- `ConnectorSessionViewModel`
- `VirtualTrustZoneError`

## Functions and Methods

### Python

- Functions and methods: `snake_case`
- Boolean-returning functions should begin with:
  - `is_`
  - `has_`
  - `can_`
  - `should_`
- Factory functions should begin with:
  - `build_`
  - `create_`
  - `make_`
- Conversion functions should begin with:
  - `to_`
  - `from_`
  - `parse_`
- Async functions must still use normal `snake_case`; do not prefix with `async_` unless it clarifies meaning.

Examples:

- `evaluate_policy`
- `is_trusted_source`
- `build_replay_plan`
- `parse_audit_record`

### Swift

- Functions and methods: `lowerCamelCase`
- Boolean properties/functions:
  - `isTrusted`
  - `hasEntitlement`
  - `canReplay`
  - `shouldEscalate`
- Factory methods:
  - `makeSession()`
  - `buildEnvelope()`
- Do not use Objective-C-style verbose labels unless required for clarity.

Examples:

- `evaluatePolicy()`
- `parseTrustLabel()`
- `buildReplaySession()`

---

## Variables, Constants, and Properties

### Python

- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private/internal attributes: leading underscore only when meaningful
- Avoid single-letter names outside tight loop indices

### Swift

- Variables/properties: `lowerCamelCase`
- Static constants: `lowerCamelCase` unless bridged or externally constrained
- Enum cases: `lowerCamelCase`

### General

Use full domain terms:

- `trust_label` not `tl`
- `audit_event` not `evt`
- `machine_identity` not `mid`
- `conversation_message` not `msg` unless scope is tiny and obvious

---

# Error and Exception Patterns

## General Rules

Errors must be:

- Typed
- Explicit
- Actionable
- Sanitized
- Mapped to subsystem error contracts from TRDs

Do not raise or propagate raw generic exceptions across subsystem boundaries unless immediately wrapped.

## Python Error Patterns

### Naming

Use:

- `XxxError` for recoverable or domain errors
- `XxxProtocolError` for interface/contract violations
- `XxxValidationError` for input validation failures
- `XxxSecurityError` for security policy violations
- `XxxTimeoutError` for timeout cases
- `XxxUnavailableError` for temporary dependency issues

Examples:

- `PolicyEvaluationError`
- `TrustLabelValidationError`
- `AuditStreamUnavailableError`
- `ReplayProtocolError`

### Structure

Prefer a small typed hierarchy per subsystem:

```python
class DtlError(Exception):
    pass

class TrustLabelValidationError(DtlError):
    pass
```

### Requirements

- Preserve original exception cause using `raise ... from exc`
- Sanitize secrets, tokens, keys, prompts, raw credentials, and sensitive payloads from error text
- Include stable machine-readable error codes where required by a TRD
- Separate user-displayable messages from internal diagnostics

## Swift Error Patterns

- Use typed `enum` errors conforming to `Error`
- Prefer narrow error domains over one giant error enum
- Add localized descriptions only when they are actually surfaced
- Never include secrets in `localizedDescription`

Example:

```swift
enum TrustLockError: Error {
    case keyNotFound
    case attestationFailed(reason: String)
    case invalidIdentityState
}
```

## Boundary Mapping

At process, network, IPC, SDK, CLI, or UI boundaries:

- Map internal errors into stable boundary error types
- Preserve diagnostics in logs or telemetry only if allowed by security rules
- Avoid leaking stack traces or provider internals to end users
- Convert unknown failures into subsystem-specific fallback errors

---

# Code Patterns

## Module Design

- One module/file should have one primary responsibility.
- Prefer cohesive modules over broad utility modules.
- Keep public surface area minimal.
- Internal helpers should stay internal to the subsystem.

## Dependency Direction

- Lower-level modules must not depend on higher-level orchestration modules.
- Security enforcement modules must not import presentation-layer code.
- Replay/audit code must not bypass trust labeling or policy evaluation where required.
- SDK code must not depend on internal application-only modules.

## Data Models

- Use explicit typed models for boundary payloads.
- Validate all external input at ingress.
- Avoid passing raw dictionaries/maps through multiple layers when a typed model is appropriate.
- Naming of models should reflect meaning:
  - `TrustLabel`
  - `AuditRecord`
  - `PolicyDecision`
  - `ReplayFrame`
  - `ConnectorRequest`

## State and Mutability

- Prefer immutable value objects for records, envelopes, labels, and events.
- Centralize mutable state behind explicit stores, coordinators, or controllers.
- Name mutable state holders clearly:
  - `SessionStore`
  - `ReplayStateStore`
  - `AuditCursorStore`

## Logging and Telemetry

- Log with structured fields where supported.
- Event/log names must be stable and domain-specific.
- Never log secrets, raw credentials, unredacted tokens, private keys, or protected content.
- Redaction helpers must be named clearly, e.g.:
  - `redact_token`
  - `redactedPayload`
  - `sanitize_error_context`

## Concurrency and Async Code

- Async boundaries must be explicit.
- Methods performing blocking I/O must not masquerade as pure compute helpers.
- Queue/task ownership should be evident from names:
  - `enqueue_audit_event`
  - `drain_replay_buffer`
  - `run_policy_evaluation`

## Testing Patterns

- Test modules must mirror source layout exactly.
- Test file names:
  - Python: `test_<module_name>.py`
  - Swift: `<TypeName>Tests.swift`
- Name tests by behavior, not implementation:
  - `test_rejects_untrusted_label`
  - `test_replay_stops_on_corrupt_frame`
- Include subsystem prefix in fixtures only when needed to avoid collisions.

---

# Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation and interaction abstraction, message normalization, routing, session semantics.

### File naming

Use names such as:

- `conversation_session.py`
- `message_router.py`
- `interaction_context.py`
- `conversation_adapter.py`

### Type naming

Prefer domain terms:

- `ConversationSession`
- `ConversationMessage`
- `MessageEnvelope`
- `InteractionContext`
- `ConversationRouter`
- `ProviderConversationAdapter`

### Function naming

Use verbs that reflect message flow and normalization:

- `normalize_message`
- `route_conversation`
- `append_turn`
- `serialize_envelope`
- `parse_provider_response`

### Avoid

- `chat.py`
- `bot.py`
- `llm_utils.py`
- `prompt_handler.py` unless it is specifically prompt handling

---

## `src/dtl/` — Data Trust Label

Purpose: trust classification, label issuance, validation, propagation, and verification.

### File naming

Use names such as:

- `trust_label.py`
- `label_validator.py`
- `label_issuer.py`
- `label_propagation.py`
- `trust_label_codec.py`

### Type naming

Preferred types:

- `TrustLabel`
- `TrustLabelIssuer`
- `TrustLabelValidator`
- `TrustClassification`
- `LabelVerificationResult`
- `TrustLabelCodec`

### Function naming

- `issue_label`
- `validate_label`
- `verify_signature`
- `propagate_label`
- `parse_label_claims`

### Error naming

- `DtlError`
- `TrustLabelValidationError`
- `TrustLabelSignatureError`
- `TrustClassificationError`

### Avoid

- `tag`
- `stamp`
- `marker`

Use `label` consistently unless the TRD defines a narrower term.

---

## `src/trustflow/` — TrustFlow Audit Stream

Purpose: append-only audit/event stream, evidence capture, event lineage, and traceability.

### File naming

Use names such as:

- `audit_event.py`
- `audit_stream.py`
- `audit_writer.py`
- `event_lineage.py`
- `evidence_bundle.py`

### Type naming

Preferred types:

- `AuditEvent`
- `AuditStream`
- `AuditStreamWriter`
- `AuditCursor`
- `EventLineage`
- `EvidenceBundle`

### Function naming

- `append_event`
- `read_from_cursor`
- `build_evidence_bundle`
- `resolve_lineage`
- `seal_stream_segment`

### Error naming

- `TrustFlowError`
- `AuditStreamUnavailableError`
- `AuditIntegrityError`
- `EvidenceBundleError`

### Avoid

- `log` when the object is a durable audit stream
- `trace` when the concept is actually lineage or evidence
- `history` for append-only stream primitives

Use `audit`, `event`, `lineage`, `evidence`, and `stream` precisely.

---

## `src/vtz/` — Virtual Trust Zone

Purpose: trust boundary enforcement, isolation policy, execution restrictions, and containment.

### File naming

Use names such as:

- `trust_zone.py`
- `zone_enforcer.py`
- `boundary_policy.py`
- `isolation_controller.py`
- `execution_guard.py`

### Type naming

Preferred types:

- `VirtualTrustZone`
- `TrustZoneEnforcer`
- `BoundaryPolicy`
- `IsolationController`
- `ExecutionGuard`
- `ZoneDecision`

### Function naming

- `enforce_boundary`
- `validate_zone_transition`
- `deny_execution`
- `allow_resource_access`
- `compute_zone_decision`

### Error naming

- `VtzError`
- `TrustZoneViolationError`
- `BoundaryPolicyError`
- `IsolationEnforcementError`

### Avoid

- `sandbox` unless the TRD explicitly uses it
- `jail`
- `container` unless it truly refers to container technology

Use `zone`, `boundary`, `isolation`, and `enforcement`.

---

## `src/trustlock/` — Cryptographic Machine Identity

Purpose: machine identity, attestation, TPM-anchored or hardware-rooted trust, key material lifecycle.

### File naming

Use names such as:

- `machine_identity.py`
- `identity_attestor.py`
- `key_provider.py`
- `attestation_verifier.py`
- `identity_store.py`

### Type naming

Preferred types:

- `MachineIdentity`
- `IdentityAttestor`
- `AttestationDocument`
- `AttestationVerifier`
- `KeyProvider`
- `IdentityStore`

### Function naming

- `load_machine_identity`
- `generate_attestation`
- `verify_attestation`
- `rotate_identity_key`
- `bind_identity_claims`

### Error naming

- `TrustLockError`
- `MachineIdentityError`
- `AttestationVerificationError`
- `KeyProvisioningError`

### Avoid

- `device_id` when the concept is cryptographic identity
- `cert` when the concept is broader attestation material
- `token` for key identity artifacts unless the TRD does so

Use `identity`, `attestation`, `key`, `provisioning`, and `binding`.

---

## `src/mcp/` — MCP Policy Engine

Purpose: policy definition, evaluation, decisioning, enforcement coordination, and policy result explanation.

### File naming

Use names such as:

- `policy_engine.py`
- `policy_evaluator.py`
- `policy_bundle.py`
- `decision_context.py`
- `decision_explainer.py`

### Type naming

Preferred types:

- `PolicyEngine`
- `PolicyEvaluator`
- `PolicyBundle`
- `DecisionContext`
- `PolicyDecision`
- `DecisionExplainer`

### Function naming

- `evaluate_policy`
- `load_policy_bundle`
- `build_decision_context`
- `explain_decision`
- `resolve_policy_inputs`

### Error naming

- `McpError`
- `PolicyEvaluationError`
- `PolicyBundleError`
- `DecisionContextError`

### Avoid

- `rules` when the TRD distinguishes rules from policies
- `judge`
- `brain`
- `checker` if evaluator/enforcer is more precise

Use `policy`, `decision`, `context`, `bundle`, and `evaluation`.

---

## `src/rewind/` — Forge Rewind Replay Engine

Purpose: deterministic replay, event/frame reconstruction, debugging playback, historical execution tracing.

### File naming

Use names such as:

- `replay_engine.py`
- `replay_session.py`
- `frame_decoder.py`
- `timeline_builder.py`
- `checkpoint_store.py`

### Type naming

Preferred types:

- `ReplayEngine`
- `ReplaySession`
- `ReplayFrame`
- `ReplayTimeline`
- `FrameDecoder`
- `CheckpointStore`

### Function naming

- `start_replay`
- `decode_frame`
- `reconstruct_timeline`
- `load_checkpoint`
- `seek_to_timestamp`

### Error naming

- `RewindError`
- `ReplayFrameCorruptionError`
- `CheckpointLoadError`
- `TimelineReconstructionError`

### Avoid

- `undo` when the concept is replay
- `time_travel` unless it is a user-facing UX term
- `playback` if deterministic replay is the actual engine concept

Use `replay`, `frame`, `timeline`, `checkpoint`, and `reconstruction`.

---

## `sdk/connector/` — Forge Connector SDK

Purpose: external integration SDK, connector APIs, client sessions, request/response contracts, developer integration surface.

### File naming

Use names such as:

- `connector_client.py`
- `connector_session.py`
- `request_models.py`
- `response_models.py`
- `auth_strategy.py`

### Type naming

Preferred types:

- `ConnectorClient`
- `ConnectorSession`
- `ConnectorRequest`
- `ConnectorResponse`
- `AuthStrategy`
- `ConnectorConfiguration`

### Function naming

- `send_request`
- `open_session`
- `authenticate_client`
- `build_connector_request`
- `parse_connector_response`

### Error naming

- `ConnectorError`
- `ConnectorAuthenticationError`
- `ConnectorRequestError`
- `ConnectorProtocolError`

### SDK-specific rules

- Public APIs must be stable and explicit.
- Avoid leaking internal subsystem terminology unless it is part of the SDK contract.
- Internal-only helpers must not be exposed through package root exports.
- Public names must optimize for integrator clarity over internal implementation symmetry.

### Avoid

- `internal_client` in public surface
- `raw_call` for stable SDK methods
- `do_request`
- `handle_response`

---

# Test Naming Conventions

## Directory rules

Tests mirror source exactly:

```text
src/cal/...            -> tests/cal/...
src/dtl/...            -> tests/dtl/...
src/trustflow/...      -> tests/trustflow/...
src/vtz/...            -> tests/vtz/...
src/trustlock/...      -> tests/trustlock/...
src/mcp/...            -> tests/mcp/...
src/rewind/...         -> tests/rewind/...
sdk/connector/...      -> tests/connector/...
```

## Test file naming

- Python:
  - `test_conversation_session.py`
  - `test_policy_evaluator.py`
- Swift:
  - `TrustZoneEnforcerTests.swift`

## Test function naming

Use `test_<behavior>` and prefer externally visible behavior:

- `test_issues_signed_trust_label`
- `test_rejects_invalid_attestation_document`
- `test_appends_audit_event_in_order`
- `test_denies_zone_transition_without_policy`
- `test_reconstructs_timeline_from_checkpoint`

Avoid:

- `test_helper`
- `test_basic`
- `test_works`
- `test_stuff`

---

# Prohibited Naming Patterns

Do not use these unless required by an external dependency or protocol:

- `util`, `utils`, `misc`, `common`, `base` as catch-all modules
- `manager` when a more exact noun exists
- `handler` when route/evaluator/validator/controller/enforcer is more precise
- `processor` unless processing is the actual domain abstraction
- `data` as a primary type name
- `info` for structured domain records
- `object`, `entity`, `item`, `thing`
- unexplained acronyms
- temporary suffixes:
  - `_new`
  - `_old`
  - `_tmp`
  - `_2`
  - `_final`

Replace broad names with exact domain terms.

---

# Cross-Language Consistency

When the same concept exists across Python, Swift, SDK, tests, or protocol payloads, keep the root domain term aligned.

Examples:

- Python: `TrustLabel`
- Swift: `TrustLabel`
- JSON field: `trust_label`
- Test: `test_trust_label.py`

Likewise:

- `PolicyDecision` / `policy_decision`
- `AuditEvent` / `audit_event`
- `MachineIdentity` / `machine_identity`
- `ReplaySession` / `replay_session`

Do not rename the same concept differently in adjacent layers without a clear boundary reason.

---

# Security-Sensitive Convention Rules

These apply across all subsystems:

- Secret-bearing variables must be named explicitly:
  - `api_token`
  - `session_secret`
  - `private_key_material`
- Redacted values should be marked in name where retained:
  - `redacted_token`
  - `sanitized_payload`
- Functions performing trust or security checks must be named as enforcement, validation, or verification operations:
  - `verify_attestation`
  - `validate_label`
  - `enforce_boundary`
  - `evaluate_policy`
- Never use vague names for security-critical decisions:
  - avoid `check()`
  - avoid `ok()`
  - avoid `safe()`

---

# Documentation and Authority Files

Repository-wide authority files use uppercase names:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONVENTIONS.md`

Other documentation should use `snake_case.md` unless externally required otherwise.

---

# Change Discipline

When adding new code:

1. Place it in the canonical subsystem directory.
2. Name files by precise responsibility.
3. Name types by domain noun.
4. Name functions by explicit action.
5. Add matching tests in mirrored structure.
6. Use typed errors with subsystem prefixes/root classes.
7. Re-check naming against the owning TRD.

When renaming code, prefer semantic improvement only if all references, tests, docs, and contracts are updated together.

---

# Summary

Forge naming and code conventions optimize for:

- exact subsystem ownership
- high signal names
- typed boundary contracts
- strong security clarity
- mirrored tests
- cross-language consistency

If a name is vague, overloaded, or generic, it is probably wrong. Use the subsystem’s domain language exactly and consistently.