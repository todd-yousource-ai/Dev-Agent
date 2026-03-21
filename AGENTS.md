# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that cryptographically binds every agent action to a verified identity, policy boundary, and auditable event stream — rejecting anything that cannot be verified.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID FIRST at every enforcement entry point — validation failure means immediate rejection with zero partial processing.
2. Check VTZ policy BEFORE execution of any agent action — VTZ boundaries are structural and MUST NOT be bypassed by application code. Record a `VTZEnforcementDecision` with `verdict=block` on denial.
3. Emit a TrustFlow event synchronously in the enforcement path for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden. Emission failure is a WARN-level audit event that MUST be surfaced, never silently skipped.
4. Treat missing or expired CTX-ID as `UNTRUSTED` — never infer identity from ambient context, session state, or caller metadata. CTX-ID tokens are IMMUTABLE once issued.
5. Fail closed on ALL trust, identity, policy, and cryptographic errors — reject the action, log the event, surface to caller. Never silently continue.
6. Assign DTL labels at data ingestion; labels are IMMUTABLE. Derived data inherits the HIGHEST classification of any source. Unlabeled data MUST be treated as `CONFIDENTIAL` until explicit policy-controlled reclassification.
7. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads — no exceptions.
8. All external input (documents, PR comments, CI output, user prompts, XPC messages) is UNTRUSTED and MUST be validated strictly before use. Context from external documents goes in the USER prompt, never the SYSTEM prompt.
9. Generated code is never executed by the agent — no `eval()`, no `exec()`, no dynamic code loading, no subprocess execution of generated content. `shell=True` is banned in all subprocess calls.
10. Validate every file write path with `path_security.validate_write_path()` BEFORE writing to disk.
11. `SECURITY_REFUSAL` output is terminal — never bypass by rephrasing, retrying with another provider, or suppressing. Stop, gate, and log.
12. Audit records are APPEND-ONLY, generated BEFORE execution, and MUST NOT contain secrets. Replay MUST be possible from the audit stream alone.
13. Gates wait indefinitely for operator input — no auto-approve, no auto-merge, no auto-dismiss ever. The human is in the loop at every gate.
14. Discard and log unknown XPC message types — never raise them as uncaught exceptions across the process boundary.

## Architecture Overview

Forge is a two-process architecture: a **Swift shell** (UI, auth, Keychain, XPC) and a **Python backend** (consensus, pipeline, GitHub). Enforcement order for every agent action:

**CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → Audit record**

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action abstraction and enforcement sequencing over agent conversations | Execute any action before CTX-ID validation and VTZ policy check complete |
| **TrustLock** | `src/trustlock/` | TPM-anchored machine identity validation; CTX-ID signature verification against the TrustLock public key | Accept software-only validation; skip TPM binding |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural policy boundaries; each session bound to exactly one VTZ; cross-VTZ authorization evaluation | Permit implicit cross-VTZ access; allow application code to bypass boundaries |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable label assignment at ingestion; label verification before trust-boundary crossings; highest-classification inheritance for derived data | Downgrade or strip labels without policy-controlled audit; treat unlabeled data as anything other than CONFIDENTIAL |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome with full required event fields (`ctx_id`, `vtz_id`, `action`, `verdict`, `timestamp`, `dtl_label`) | Buffer events asynchronously; silently drop events on failure |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Policy decisions for tools, boundaries, and operations; enforcement-grade verdicts | Return advisory-only decisions where enforcement is required |
| **Forge Rewind** | `src/rewind/` | Deterministic replay from append-only audit history; full action reconstruction from TrustFlow stream | Require hidden state outside the audit stream for replay; mutate audit records |

## Naming Conventions

- **CTX-ID**: Contextual Trust Identity — the immutable, cryptographically issued token that identifies an agent session. Always hyphenated, always capitalized: `CTX-ID`. Never `ctx_id` in prose (use `ctx_id` only as a field name in code and wire formats).
- **VTZ**: Virtual Trust Zone — the structural policy boundary scoping agent actions. Always capitalized: `VTZ`. Reference specific zones as `VTZ:<zone_name>`.
- **TrustFlow**: The synchronous audit event subsystem. One word, PascalCase: `TrustFlow`. Never `Trust Flow`, `trust_flow` in prose.
- **DTL**: Data Trust Label — immutable classification labels. Always capitalized: `DTL`. Valid DTL values: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`.
- **TrustLock**: TPM-anchored identity verification. One word, PascalCase: `TrustLock`.
- **CAL**: Conversation Abstraction Layer. Always capitalized: `CAL`.
- **MCP**: MCP Policy Engine. Always capitalized: `MCP`.
- **Forge Rewind**: The replay subsystem. Two words, both capitalized: `Forge Rewind`.
- **Forge**: The platform name. Always capitalized. Never `forge` in prose. The full formal name is **Forge Platform**.

## Branding Rules

- The product name is **Forge**. Use **Forge Platform** for formal references.
- Subsystem names (CAL, TrustLock, VTZ, DTL, TrustFlow, MCP, Forge Rewind) MUST use the exact casing defined above in all documentation, comments, commit messages, and UI text.
- Never abbreviate subsystem names beyond their defined acronyms (e.g., never shorten TrustFlow to TF, never shorten TrustLock to TL).
- Code identifiers use `snake_case` for Python (`ctx_id`, `vtz_id`, `dtl_label`, `trust_flow`) and `camelCase` for Swift (`ctxId`, `vtzId`, `dtlLabel`, `trustFlow`).
- Wire format field names use `snake_case`: `ctx_id`, `vtz_id`, `dtl_label`, `verdict`, `timestamp`, `action`.
- Log messages and audit records MUST reference subsystems by their canonical names.
- Error codes follow the pattern `FORGE_<SUBSYSTEM>_<ERROR>` (e.g., `FORGE_VTZ_BOUNDARY_VIOLATION`, `FORGE_CTX_INVALID`, `FORGE_DTL_LABEL_MISSING`, `FORGE_TRUSTFLOW_EMISSION_FAILURE`).