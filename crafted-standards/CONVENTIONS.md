# Code Conventions

These conventions are derived from the provided TRD materials and repository guidance. They apply across the codebase and must be followed wherever the relevant subsystem exists.

## File and Directory Naming (exact `src/` layout)

### Repository structure

Use a two-process layout:

- Swift shell code for UI, authentication, secrets, and IPC-facing shell concerns
- Python backend code for intelligence, generation, consensus, pipeline, and remote service operations

Subsystem directories must follow the established naming prefixes exactly:

- `src/cal/` — Conversation Abstraction Layer components
- `src/dtl/` — Data Trust Label components
- `src/trustflow/` — TrustFlow audit stream components
- `src/vtz/` — Virtual Trust Zone enforcement
- `src/trustlock/` — Cryptographic machine identity
- `src/mcp/` — MCP Policy Engine
- `src/rewind/` — replay engine
- `sdk/connector/` — Connector SDK
- `tests/<subsystem>/` — tests mirror `src/` structure exactly

### Directory rules

- Directory names are lowercase.
- Use the exact subsystem directory names above; do not alias, pluralize, or rename them.
- New files must be placed under the subsystem that owns the behavior defined by the relevant TRD.
- Tests must mirror source layout exactly. Example:
  - `src/dtl/label_parser.py`
  - `tests/dtl/test_label_parser.py`

### File naming by language

#### Python

- Use `snake_case.py` for module filenames.
- Prefer descriptive names tied to the owned behavior:
  - `provider_adapter.py`
  - `consensus_engine.py`
  - `socket_protocol.py`
  - `audit_emitter.py`

#### Swift

- Use `PascalCase.swift` for type-centered files.
- Name the file after the primary type in the file.
- SwiftUI view files should be named after the view:
  - `SessionPanelView.swift`
  - `TrustStatusCard.swift`

### Protocol and transport files

For authenticated Unix socket and line-delimited JSON related code:

- Use names that clearly indicate transport and framing:
  - `socket_client.py`
  - `socket_server.py`
  - `jsonl_protocol.py`
  - `IPCEnvelope.swift`

Avoid generic names like `utils.py` or `helpers.swift` for protocol-critical code.

---

## Class and Function Naming

### General principles

- Name by responsibility, not implementation detail.
- Names must reflect TRD-defined concepts exactly where those concepts are specified.
- Prefer stable domain nouns over temporary task-oriented names.
- Avoid hardcoded product naming in identifiers unless already part of a required protocol or external API contract.

### Python naming

#### Classes

- Use `PascalCase`.
- Use role-based suffixes where applicable:
  - `Engine` for orchestration or decision systems
  - `Adapter` for provider or API boundary translation
  - `Client` for outbound service communication
  - `Server` for inbound service handling
  - `Policy` for rule evaluation
  - `Emitter` for append-only event output
  - `Recorder` / `Replayer` for replay systems
  - `Label` / `Classifier` / `Validator` for trust and labeling components

Examples:

- `ConsensusEngine`
- `ProviderAdapter`
- `PolicyEngine`
- `TrustLabelValidator`
- `AuditStreamEmitter`

#### Functions and methods

- Use `snake_case`.
- Start with a verb.
- Prefer explicit domain terms:
  - `open_authenticated_socket`
  - `encode_jsonl_message`
  - `validate_trust_label`
  - `append_audit_event`
  - `replay_session_frame`

Boolean-returning functions should read as predicates:

- `is_ready_for_review`
- `has_valid_signature`
- `can_merge_pull_request`

#### Constants

- Use `UPPER_SNAKE_CASE`.
- Group protocol constants near the owning subsystem.

### Swift naming

#### Types

- Use `PascalCase`.
- Suffix by role when useful:
  - `View` for SwiftUI screens/components
  - `Controller` only where imperative control exists
  - `Manager` only when lifecycle/resource ownership is the real responsibility
  - `Store` for state containers
  - `Client` for service/API interfaces
  - `Envelope` / `Message` for IPC payload models

Examples:

- `AuthenticationStore`
- `UnixSocketClient`
- `SessionPanelView`
- `TrustStatusCard`
- `IPCMessageEnvelope`

#### Properties and methods

- Use `camelCase`.
- Methods should start with a verb:
  - `sendMessage()`
  - `loadSession()`
  - `persistCredential()`
  - `renderTrustState()`

Boolean properties should read naturally:

- `isAuthenticated`
- `hasPendingReview`
- `canRetry`

### Acronyms and abbreviations

- Keep subsystem abbreviations as defined by directory and TRD usage:
  - `CAL`
  - `DTL`
  - `MCP`
- In Python filenames, use lowercase forms:
  - `dtl_parser.py`
- In Swift type names, preserve acronym capitalization if the acronym is a defined domain term:
  - `DTLLabel`
  - `MCPPolicyEngine`

Do not invent new abbreviations for established subsystems.

---

## Error and Exception Patterns

### General error rules

- Error behavior must match the owning TRD’s error contract.
- Errors must be explicit, typed where possible, and stable at subsystem boundaries.
- Never silently ignore failures that affect trust, auth, IPC integrity, policy enforcement, replay integrity, or remote state transitions.
- Do not invent success semantics for unsupported operations.

### Python exceptions

#### Naming

- Use `PascalCase` and end with `Error` for exception classes.
- Prefix with subsystem or domain where ambiguity is possible.

Examples:

- `IPCAuthenticationError`
- `DTLValidationError`
- `TrustFlowWriteError`
- `PolicyEvaluationError`
- `ReplayIntegrityError`
- `GitHubTransitionError`

#### Usage patterns

- Raise domain-specific exceptions at subsystem boundaries.
- Wrap third-party exceptions into subsystem-specific errors before crossing layers.
- Preserve original exception context.

Example pattern:

```python
try:
    response = client.mark_ready_for_review(pr_id)
except GraphQLError as exc:
    raise GitHubTransitionError("failed to mark pull request ready for review") from exc
```

#### Messages

Error messages should be:

- concise
- actionable
- free of secrets
- specific about the failed operation

Good:

- `failed to authenticate unix socket peer`
- `invalid trust label: missing classification`
- `draft pull request cannot be undrafted via REST`

Bad:

- `something broke`
- `auth failed with token abc123`
- `request error`

### Swift errors

- Prefer typed `Error` conforming enums for finite failure domains.
- Use structs only when associated context is substantial and structured.
- Name error enums after the owned domain.

Examples:

- `AuthenticationError`
- `KeychainError`
- `SocketTransportError`
- `IPCDecodingError`

Example:

```swift
enum SocketTransportError: Error {
    case peerAuthenticationFailed
    case invalidFrame
    case writeFailed
}
```

### Boundary error handling

At process and transport boundaries:

- Validate before deserialize/use when possible.
- Convert internal errors into stable transport-safe error payloads.
- Never leak credentials, secrets, machine identity material, or raw provider payloads in surfaced errors.
- Log enough detail for diagnosis without exposing protected data.

### Unsupported API behavior

Where external API behavior is known to be non-obvious, encode that as convention:

- Do not rely on REST field mutation for draft-to-ready transitions if the platform ignores it silently.
- Use the supported API path defined by the implementation guidance for lifecycle transitions.
- Treat silent no-op API responses as failures when state transition was required.

---

## Per-Subsystem Naming Rules

## `src/cal/` — Conversation Abstraction Layer

Purpose: conversation state, message abstraction, session-level exchange modeling.

### Naming rules

- Use `Conversation`, `Session`, `Turn`, `Message`, `Transcript`, `Exchange` for core abstractions.
- Adapters to model/provider layers should be suffixed with `Adapter`.
- Serialization/framing helpers should use `Encoder`, `Decoder`, or `Serializer`.

Examples:

- `ConversationSession`
- `TurnMessage`
- `TranscriptSerializer`
- `ConversationAdapter`

### Preferred function names

- `append_message`
- `start_session`
- `close_session`
- `serialize_transcript`
- `load_conversation_state`

---

## `src/dtl/` — Data Trust Label

Purpose: trust labels, validation, classification, and integrity of labeled data.

### Naming rules

- Include `Label`, `Classification`, `Trust`, `Source`, `Integrity`, or `Provenance` in type names where relevant.
- Validators must be named `*Validator`.
- Parsing components must be named `*Parser`.
- Normalization components must be named `*Normalizer`.

Examples:

- `DTLLabel`
- `TrustClassification`
- `LabelParser`
- `LabelValidator`
- `ProvenanceNormalizer`

### Preferred function names

- `parse_label`
- `validate_label`
- `normalize_provenance`
- `classify_source`
- `verify_integrity`

### Error names

- `DTLValidationError`
- `ProvenanceError`
- `IntegrityVerificationError`

---

## `src/trustflow/` — TrustFlow audit stream

Purpose: append-only audit/event stream and trust-relevant event recording.

### Naming rules

- Use `Audit`, `Event`, `Stream`, `Record`, `Envelope`, `Entry` for data structures.
- Writers should be `Emitter`, `Writer`, or `Appender`.
- Readers should be `Reader` or `Scanner`.

Examples:

- `AuditEvent`
- `AuditEnvelope`
- `TrustFlowEmitter`
- `AuditStreamReader`
- `RecordAppender`

### Preferred function names

- `append_event`
- `emit_audit_record`
- `read_stream`
- `scan_entries`
- `verify_stream_integrity`

### Error names

- `AuditWriteError`
- `StreamIntegrityError`
- `AuditEncodingError`

---

## `src/vtz/` — Virtual Trust Zone enforcement

Purpose: isolation, enforcement, trust boundary checks, and execution safety controls.

### Naming rules

- Use `Zone`, `Boundary`, `Guard`, `Enforcer`, `Policy`, `Isolation` in type names.
- Enforcement classes should end with `Enforcer` or `Guard`.
- Boundary-checking helpers should include `Boundary` or `Isolation`.

Examples:

- `VirtualTrustZone`
- `BoundaryGuard`
- `ExecutionEnforcer`
- `IsolationPolicy`

### Preferred function names

- `enforce_boundary`
- `validate_zone_access`
- `block_execution`
- `isolation_context_for`
- `check_trust_boundary`

### Error names

- `BoundaryViolationError`
- `ExecutionBlockedError`
- `IsolationPolicyError`

### Special rule

Because generated code must not be executed, names related to code handling should distinguish clearly between:

- generation
- validation
- storage
- display

Do not use ambiguous verbs like `run` or `execute` for generated artifacts unless the code is specifically enforcing a prohibition.

---

## `src/trustlock/` — Cryptographic machine identity

Purpose: machine identity, hardware-anchored identity material, and cryptographic binding.

### Naming rules

- Use `Identity`, `Attestation`, `Binding`, `Key`, `Signature`, `Challenge`, `Verifier`.
- Verifying components should end in `Verifier`.
- Signing components should end in `Signer`.

Examples:

- `MachineIdentity`
- `AttestationVerifier`
- `ChallengeSigner`
- `KeyBindingRecord`

### Preferred function names

- `load_machine_identity`
- `sign_challenge`
- `verify_attestation`
- `bind_key_material`
- `rotate_identity_if_needed`

### Error names

- `AttestationError`
- `IdentityBindingError`
- `SignatureVerificationError`

### Security naming rule

Do not name secrets or sensitive values with misleading generic names like `data` or `value`. Use explicit names such as:

- `private_key_ref`
- `attestation_blob`
- `challenge_nonce`

---

## `src/mcp/` — MCP Policy Engine

Purpose: policy evaluation and rule-based authorization/enforcement.

### Naming rules

- Use `Policy`, `Rule`, `Decision`, `Evaluator`, `Engine`, `Context`.
- Policies should be nouns; evaluators should be role-based.
- Decision outputs should use `Decision` in the type name.

Examples:

- `MCPPolicyEngine`
- `PolicyRule`
- `PolicyContext`
- `AuthorizationDecision`
- `RuleEvaluator`

### Preferred function names

- `evaluate_policy`
- `resolve_rules`
- `build_policy_context`
- `deny_with_reason`
- `is_action_permitted`

### Error names

- `PolicyEvaluationError`
- `RuleResolutionError`
- `DecisionEncodingError`

### Result naming

Where policy evaluation returns a structured result, prefer fields like:

- `decision`
- `reason`
- `matched_rules`
- `obligations`

Avoid vague result fields like `status` when a policy decision is intended.

---

## `src/rewind/` — replay engine

Purpose: deterministic replay, reconstruction, and inspection of prior flows.

### Naming rules

- Use `Replay`, `Rewind`, `Frame`, `Checkpoint`, `Timeline`, `Cursor`.
- Replay-capable components should end with `Replayer`.
- Snapshot/state extraction components may use `Snapshot` or `Checkpoint`.

Examples:

- `ReplayFrame`
- `TimelineCursor`
- `SessionReplayer`
- `CheckpointStore`

### Preferred function names

- `replay_from_checkpoint`
- `load_timeline`
- `advance_cursor`
- `reconstruct_state`
- `verify_replay_integrity`

### Error names

- `ReplayIntegrityError`
- `CheckpointLoadError`
- `TimelineCorruptionError`

---

## `sdk/connector/` — Connector SDK

Purpose: SDK-facing connector abstractions and integration surfaces.

### Naming rules

- Use `Connector`, `Client`, `Session`, `Request`, `Response`, `Config`.
- Public SDK types should be stable, descriptive, and version-tolerant.
- Avoid exposing internal transport terminology in high-level SDK type names unless the transport is itself the public contract.

Examples:

- `ConnectorClient`
- `ConnectorSession`
- `ConnectorRequest`
- `ConnectorResponse`
- `ConnectorConfig`

### Preferred function names

- `create_session`
- `send_request`
- `close_session`
- `load_config`
- `validate_connector_input`

### Error names

- `ConnectorError`
- `ConnectorConfigurationError`
- `ConnectorProtocolError`

### SDK rule

Public names must optimize for external clarity and compatibility. Internal subsystem abbreviations should not leak into SDK-facing APIs unless explicitly part of the contract.

---

## Cross-Cutting Conventions

### IPC and message contracts

For authenticated Unix socket communication with line-delimited JSON:

- Name transport payloads with `Message`, `Envelope`, `Frame`, or `Event`.
- Encoding/decoding components must make framing explicit.
- Validation must occur before business handling.
- Keep request and response names symmetrical where applicable:
  - `AuthRequest` / `AuthResponse`
  - `PolicyDecisionRequest` / `PolicyDecisionResponse`

### UI naming

For SwiftUI views, cards, and panels:

- End reusable visual components with `View`, `Card`, `Panel`, or `Row` as appropriate.
- Match the dominant UI role:
  - `SessionPanelView`
  - `TrustStatusCard`
  - `AuditEventRow`

Avoid view names that hide user-facing purpose.

### Authentication, secrets, and key storage

- Swift shell owns UI, authentication, and secrets.
- Names for secret-handling types should be explicit:
  - `CredentialStore`
  - `KeychainClient`
  - `AuthenticationSession`
- Never name persistence methods ambiguously when handling secrets:
  - prefer `storeCredential` over `saveData`
  - prefer `loadTokenReference` over `readValue`

### Remote service integration conventions

For remote repository or pull request operations:

- Use names that reflect actual state transitions.
- Distinguish draft lifecycle operations from merge operations.
- If a platform requires a specific API modality for a transition, encode that in function naming.

Examples:

- `mark_ready_for_review`
- `enable_auto_merge`
- `merge_pull_request`
- `create_draft_pull_request`

Do not name a method as if it performs a transition through an API path known not to support it.

### Testing conventions

- Tests mirror `src/` structure exactly.
- Python test files use `test_<module>.py`.
- Test class names should describe the subject:
  - `TestLabelValidator`
  - `TestPolicyEngine`
- Test names should describe behavior and expected result:
  - `test_validate_label_rejects_missing_classification`
  - `test_mark_ready_for_review_uses_supported_api`
  - `test_generated_code_is_never_executed`

### Prohibited naming patterns

Do not use:

- `misc`, `helpers`, `stuff`, `temp`, `manager` without clear ownership
- `run_*` for generated code handling unless blocking/prohibition is the intent
- hardcoded product-name identifiers in new convention-driven code
- ambiguous transport names like `payload` when `message`, `frame`, or `envelope` is more precise

### Preference order when naming

When choosing between candidate names, prefer:

1. TRD-defined term
2. subsystem-defined domain noun
3. explicit role suffix (`Engine`, `Adapter`, `Validator`, `Emitter`, `View`)
4. implementation detail only if externally invisible

If a TRD term and an existing local term conflict, the TRD term wins.