# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) for every decision — defaulting to deny on any failure.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing. Missing, expired, rotated, invalid, or software-only-validated CTX-ID is `UNTRUSTED` and MUST fail closed.
2. TrustFlow events MUST be emitted synchronously in the enforcement path for every action outcome (allow, restrict, block). Every event MUST include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`. Async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
3. VTZ policy MUST be checked BEFORE execution of any agent action — every agent session is bound to exactly one VTZ at CTX-ID issuance. Cross-VTZ tool calls require explicit policy authorization; implicit access is denied.
4. DTL labels are assigned at data ingestion and are IMMUTABLE — derived data inherits the HIGHEST classification of any source; unlabeled data is treated as CONFIDENTIAL. Labels MUST be verified before any trust-boundary crossing; silent label stripping is forbidden.
5. All trust, identity, policy, and cryptographic failures MUST fail CLOSED — reject the action, log the event, surface to caller, never silently continue.
6. Secrets, keys, tokens, and credentials MUST NEVER appear in logs, error messages, generated code, or error payloads.
7. All external input (documents, PR comments, CI output, XPC messages, user prompts) is UNTRUSTED — validate strictly before use; external document context goes in the USER prompt, never the SYSTEM prompt.
8. Generated code is NEVER executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
9. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions. This applies to open, create, replace, and move operations.
10. Gate cards wait indefinitely for operator input — no auto-approve, ever.
11. If a component emits `SECURITY_REFUSAL`, the refusal is final — never retry with rephrasing, never route to another provider, stop and gate and log.
12. XPC unknown message types are discarded and logged — never raised as exceptions, never processed.
13. An audit record MUST be generated before every security-relevant action. Audit records are append-only.
14. Never swallow exceptions or silently continue in trust, identity, policy, cryptographic, XPC, CI, or file-write paths.

## Architecture Overview

Forge is a two-process architecture. Always. No exceptions.

### Swift Shell (macOS App)
- **Owns:** SwiftUI interface (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain storage for all credentials, XPC channel, Python process lifecycle.
- **MUST NOT:** call LLM APIs, read Keychain for the backend's use outside XPC delivery, execute generated code, perform policy enforcement logic.

### Python Backend
- **Owns:** ConsensusEngine, BuildPipeline, GitHubTool, BuildLedger, DocumentStore, HolisticReview, TRDWorkflow, CommandRouter.
- **MUST NOT:** read Keychain directly, access the UI, persist credentials to disk, store credentials in env vars.

### Credential Flow (inviolable)
Touch ID → Swift reads Keychain → delivers via XPC `credentials` message → Python stores in memory only.

## Python Naming Rules

### Branch Names
- Format: `<type>/<ticket>-<slug>` — e.g. `feat/FORGE-42-ctx-id-rotation`, `fix/FORGE-99-trustflow-emit`
- `<type>` MUST be one of: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `ci`
- All lowercase, hyphens only, no underscores, no trailing hyphens.

### Commit Prefixes
- Format: `<type>(scope): <imperative summary>` — e.g. `feat(vtz): add cross-zone deny-by-default`, `fix(trustflow): emit sync before response`
- `<type>` MUST be one of: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `ci`
- `scope` MUST name the subsystem: `ctx-id`, `vtz`, `dtl`, `trustflow`, `trustlock`, `mcp`, `rewind`, `cal`, `connector`, `pipeline`, `xpc`
- Summary MUST be imperative mood, lowercase start, no trailing period, ≤72 characters.

### Labels
- CI and issue labels use `snake_case` with namespace prefix — e.g. `trust/ctx_id_failure`, `vtz/cross_zone_denied`, `dtl/label_missing`, `audit/trustflow_emit`, `security/refusal`
- Every PR MUST carry at least one subsystem label and one status label (`ready_for_review`, `blocked`, `wip`).

### Artifacts
- Build artifacts: `forge-<subsystem>-<semver>-<sha8>.<ext>` — e.g. `forge-trustflow-1.2.0-a3b4c5d6.whl`
- Audit artifacts: `trustflow-<session_id>-<ts_iso>.jsonl`
- Test reports: `test-<subsystem>-<date_iso>-<sha8>.xml`
- All lowercase, hyphens between segments, no spaces, no underscores in artifact names.

### Python Source Naming
- Modules and packages: `snake_case` — e.g. `ctx_id_validator.py`, `trust_flow_emitter.py`
- Classes: `PascalCase` — e.g. `CTXIDValidator`, `VTZPolicyEngine`, `DTLLabelStore`, `TrustFlowEmitter`
- Functions and methods: `snake_case` — e.g. `validate_ctx_id()`, `check_vtz_policy()`, `emit_trust_event()`
- Constants: `UPPER_SNAKE_CASE` — e.g. `DEFAULT_VTZ_POLICY`, `MAX_CTX_ID_TTL_SECONDS`, `DTL_CONFIDENTIAL`
- No abbreviations except established Forge terms (CTX-ID → `ctx_id`, VTZ → `vtz`, DTL → `dtl`).

## Subsystem Map and Enforcement

| Path | Subsystem | MUST | MUST NOT |
|---|---|---|---|
| `src/cal/` | Conversation Abstraction Layer | Validate CTX-ID first; enforce VTZ before execution | Partially process actions before trust checks |
| `src/vtz/` | Virtual Trust Zone | Decide allow/restrict/block before execution | Allow implicit cross-VTZ access |
| `src/dtl/` | Data Trust Labels | Assign labels at ingestion; verify labels before trust-boundary crossing | Permit silent label stripping |
| `src/trustflow/` | TrustFlow Audit Stream | Synchronously emit enforcement-path events with all required fields | Async-buffer or silently skip emission failures |
| `src/trustlock/` | TrustLock Crypto Identity | Validate against TrustLock public key | Accept software-only validation |
| `src/mcp/` | MCP Policy Engine | Evaluate policy before action execution; return binding decisions | Act as advisory-only logic |
| `src/rewind/` | Replay and Reconstruction | Support replay from append-only audit state | Depend on hidden mutable state |
| `sdk/connector/` | Forge Connector SDK | Preserve Forge trust and audit invariants across integrations | Weaken CTX-ID, VTZ, DTL, or TrustFlow guarantees |