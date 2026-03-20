# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all enforced locally on macOS via a two-process Swift/Python architecture where the human is in the loop at every gate.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing.
2. Every agent action MUST be checked against VTZ policy BEFORE execution — implicit cross-VTZ access is always denied.
3. Every action outcome (allow, restrict, block) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is forbidden. If emission fails, fail closed.
4. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller with context — never silently continue.
5. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or XPC payloads beyond the initial `credentials` delivery — Python stores credentials in memory only.
6. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
7. All external input (documents, PR comments, CI output) is untrusted — validate strictly, place in USER prompt only (never SYSTEM prompt), scan for injection before inclusion.
8. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
9. Gates wait indefinitely for operator input — no auto-approve, no timeout-to-approve, no synthesized operator consent, ever.
10. DTL labels are assigned at data ingestion, are immutable thereafter, and derived data inherits the HIGHEST classification of any source — unlabeled data is CONFIDENTIAL until explicitly reclassified. Labels MUST be verified before any trust-boundary crossing.
11. `SECURITY_REFUSAL` output is terminal — never retry with rephrasing, never bypass; stop, gate, log.
12. XPC unknown message types are discarded and logged — never raised as exceptions, never processed, never inferred from malformed messages.

## Architecture Overview

**Two-process architecture. Always. No exceptions.**

### Swift Shell (macOS App)
- **Owns:** SwiftUI (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.
- **MUST NOT:** call LLM APIs, read Keychain for the backend's use outside XPC delivery, execute generated code.

### Python Backend
- **Owns:** ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter.
- **MUST NOT:** read Keychain directly, access the UI, persist credentials to disk or env vars.

### Credential Flow (strict order)
Touch ID → Swift reads Keychain → delivers via XPC `credentials` message → Python stores in memory only.

## Subsystem Map and Enforcement Order

| Directory | Subsystem | Enforces | MUST | MUST NOT |
|-----------|-----------|----------|------|----------|
| `src/cal/` | Conversation Abstraction Layer | Enforcement entry points | Validate CTX-ID first, enforce VTZ before action execution, emit TrustFlow after decision | Perform silent fallback or bypass enforcement |
| `src/vtz/` | Virtual Trust Zone | Policy boundary enforcement | Decide boundary access before cross-zone operations, deny by default | Allow implicit cross-VTZ tool calls |
| `src/dtl/` | Data Trust Labels | Classification at ingestion | Assign labels at ingestion, preserve immutable classification, enforce highest-label inheritance | Permit unlabeled or stripped data to cross boundaries unaudited |
| `src/trustflow/` | TrustFlow Audit Stream | Append-only enforcement event stream | Synchronously emit auditable events in the enforcement path, fail closed on emission failure | Buffer asynchronously in a way that hides failure |
| `src/trustlock/` | TrustLock Identity | Cryptographic machine identity and CTX-ID validation | Validate immutable CTX-ID tokens anchored to TrustLock public key material | Accept software-only validation when hardware attestation is available |
| `src/mcp/` | MCP Policy Engine | Deterministic policy evaluation | Evaluate explicit policy inputs deterministically | Infer policy from ambient context |

## TrustFlow Event Wire Format

Every TrustFlow event MUST contain these fields:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `string (UUID)` | Unique identifier for this event |
| `timestamp` | `string (ISO 8601)` | Time of event emission |
| `ctx_id` | `string` | CTX-ID of the acting agent identity |
| `vtz_id` | `string` | VTZ boundary in which the action occurred |
| `action` | `string` | The action attempted |
| `outcome` | `enum: allow \| restrict \| block` | Enforcement decision |
| `dtl_label` | `string` | Data classification label at time of action |
| `reason` | `string` | Human-readable enforcement rationale |
| `policy_ref` | `string` | Reference to the policy rule that produced this outcome |

Events are append-only. No event is ever modified or deleted after emission.

## CTX-ID Validation Contract

1. Every CTX-ID token MUST be validated against TrustLock public key material before any action proceeds.
2. Expired, malformed, or revoked CTX-ID tokens MUST result in immediate rejection.
3. CTX-ID validation MUST occur before VTZ policy check, DTL label assignment, or TrustFlow emission.
4. CTX-ID MUST be immutable for the lifetime of an agent session.

## VTZ Policy Enforcement Contract

1. Every cross-VTZ operation MUST have an explicit policy grant — no implicit access.
2. VTZ boundary decisions MUST be logged to TrustFlow before the action executes.
3. A missing policy entry for a (ctx_id, vtz_id, action) tuple MUST be treated as `block`.
4. VTZ policy evaluation MUST be deterministic: same inputs produce same outcome.

## DTL Label Contract

1. Labels are assigned at ingestion and are immutable.
2. Derived data inherits the HIGHEST classification of any source input.
3. Unlabeled data is classified as `CONFIDENTIAL` until explicitly reclassified by an operator.
4. Label verification MUST occur before data crosses any trust boundary.
5. Label stripping or downgrade without operator gate approval is forbidden.

## Gate Card Contract

1. A `gate_card` blocks execution until an operator provides explicit input.
2. Gates MUST wait indefinitely — no timeout, no auto-approve.
3. Operator input is cryptographically attributed to the operator's identity.
4. Gate decisions are logged to TrustFlow with the operator's identity and decision.

## XPC Message Contract

1. All XPC messages MUST have a `type` field.
2. Known types: `credentials`, `gate_card`, `trustflow_event`, `action_request`, `action_response`.
3. Unknown types are discarded and logged — never processed, never raised as exceptions.
4. The `credentials` message is the ONLY message that carries secrets; secrets MUST NOT appear in any other message type.

## Build Pipeline Contract

1. BuildPipeline orchestrates through ConsensusEngine for multi-agent decisions.
2. BuildLedger records every build step outcome immutably.
3. HolisticReview validates cross-cutting concerns before merge approval.
4. TRDWorkflow gates Technical Review Documents through operator approval.
5. All pipeline steps MUST enforce the full chain: CTX-ID → VTZ → Action → TrustFlow.

## Shared Contract Base Classes

All enforcement contracts inherit from base classes in `src/contracts/`:

- `BaseEnforcementContract` — requires `validate(ctx_id, vtz_id, action) -> EnforcementResult`
- `EnforcementResult` — contains `outcome: allow | restrict | block`, `reason: str`, `policy_ref: str`, `trustflow_event: TrustFlowEvent`
- `TrustFlowEvent` — typed dataclass matching the wire format above
- `DTLLabel` — immutable label with classification level and provenance
- `GateCard` — blocks until operator resolution; contains `gate_id`, `prompt`, `ctx_id`, `status: pending | approved | rejected`

## Registry

All subsystem contracts MUST be registered in `src/contracts/registry.py`:

- `ContractRegistry.register(subsystem: str, contract: BaseEnforcementContract)` — registers a contract for a subsystem.
- `ContractRegistry.get(subsystem: str) -> BaseEnforcementContract` — retrieves the registered contract; raises `ContractNotFoundError` if missing.
- `ContractRegistry.validate_all()` — validates all registered contracts have required enforcement methods.

## Schema Export

All wire formats MUST be exportable via `src/contracts/schema_export.py`:

- `export_json_schema(contract: BaseEnforcementContract) -> dict` — returns JSON Schema for the contract's wire format.
- `export_all_schemas() -> dict` — returns all registered contract schemas keyed by subsystem name.
- Schemas MUST be generated from the typed dataclasses, not hand-maintained.