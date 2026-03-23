# AGENTS.md

Forge is the enforcement-first architecture for Crafted Dev Agent. It enforces explicit trust, identity, policy, audit, and fail-closed execution across every agent action. Crafted decomposes plain-language build intent into ordered pull requests via consensus AI, enforcing security, correctness, and operator-gated approval at every stage — no auto-approve, no silent failures.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point and reject immediately on validation failure with no partial processing.
2. Treat missing CTX-ID as `UNTRUSTED` and never infer identity from session state, UI context, transport context, or prior actions.
3. Bind every agent session to exactly one VTZ at CTX-ID issuance and deny cross-VTZ tool calls unless explicit policy authorizes them.
4. Check VTZ policy before executing any agent action and emit a `VTZEnforcementDecision` with `verdict=block` on denial.
5. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is not permitted and emission failures must never be silently skipped.
6. Assign DTL labels at data ingestion, keep them immutable, and treat unlabeled data as `CONFIDENTIAL` until explicitly reclassified. Derived data inherits the HIGHEST classification of any source.
7. Fail closed on all trust, identity, policy, and cryptographic errors: reject the action, log the event, surface the failure to the caller, and never silently continue.
8. Never log or return secrets, keys, tokens, credentials, or cleartext sensitive payloads in audit records, logs, errors, generated code, or error messages.
9. Validate all external input strictly, including documents, PR comments, CI output, XPC messages, and user-supplied file paths. Context from external documents goes in the USER prompt — never the SYSTEM prompt. All external input is untrusted.
10. Never execute generated code inside the agent: no `eval`, no `exec`, no shell execution of generated content, and no subprocess of generated payloads.
11. Validate every file write with `path_security.validate_write_path()` before performing the write; traversal attempts return a safe default.
12. Gates wait indefinitely for explicit operator input; never auto-approve, never bypass `SECURITY_REFUSAL` (including by rephrasing), and never convert policy enforcement into policy suggestion. `SECURITY_REFUSAL` output triggers stop, gate, and log.
13. Build memory and build rules are never cleared automatically — they are persistent learning systems. Per-PR stage checkpoints prevent re-running completed work after a crash.

## Architecture Overview

- **`Crafted/`** — Swift shell for native macOS UI, auth, Keychain, and XPC transport. It must enforce shell-side trust boundaries and must NOT make implicit backend trust assumptions.
- **`CraftedTests/`** — XCTest coverage for the Swift shell defined by TRD-9. It must verify security and protocol behavior and must NOT rely on force unwraps or hidden UI side effects.
- **`src/agent.py`** — Python backend entry point and REPL/version surface. It must orchestrate validated flows and must NOT bypass pipeline gates, execute generated code, or skip security checks.
- **`src/build_director.py`** — Build pipeline orchestration for confidence gate, `pr_type` routing, and staged execution. It must enforce phase order (never skip scoping phase), must NOT skip checkpoints, must NOT rerun completed work after recovery, and must NOT auto-merge without operator approval.
- **`src/consensus.py`** — `ConsensusEngine` for parallel generation (Claude + OpenAI) and arbitration via `_score_fix()`. It must call providers with explicit `language` parameter and must NOT use length-based arbitration or select a provider without scoring.
- **`src/providers.py`** — `ClaudeProvider` and `OpenAIProvider`. They must isolate provider interactions and must NOT leak API keys, embed secrets in prompts, or weaken generation policy.
- **`src/build_ledger.py`** — Multi-engineer coordination state. It must enforce serialized access and must NOT allow conflicting concurrent writes without lock.
- **`src/github_tools.py`** — All GitHub API calls (TRD-5). It must enforce token handling via Keychain/secure storage and must NOT store tokens outside secure subsystems or expose them in logs.

## Enforcement Subsystem Contracts

### CTX-ID
- Every enforcement function receives CTX-ID as its first parameter.
- CTX-ID validation is the first operation — before any policy check, any tool call, any data access.
- Invalid or missing CTX-ID → immediate rejection, TrustFlow event emitted, no partial processing.

### VTZ (Virtual Trust Zone)
- Session-to-VTZ binding is immutable after CTX-ID issuance.
- Cross-VTZ access requires explicit policy entry — implicit access is denied.
- Every VTZ enforcement decision emits `VTZEnforcementDecision` with fields: `ctx_id`, `vtz_id`, `action`, `verdict` (`allow` | `restrict` | `block`), `timestamp`.

### TrustFlow
- Every action outcome emits a TrustFlow event synchronously.
- Event fields: `ctx_id`, `action`, `outcome` (`allow` | `restrict` | `block`), `subsystem`, `timestamp`, `reason`.
- Emission failure must itself be logged and must halt the action — never fire-and-forget.

### DTL (Data Trust Label)
- Labels: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`.
- Assigned at ingestion, immutable thereafter.
- Derived data inherits the highest classification of all sources.
- Unlabeled data defaults to `CONFIDENTIAL`.
- Reclassification requires explicit operator action with audit trail.

### Path Security
- All file write paths validated via `path_security.validate_write_path()` before any I/O.
- Traversal attempts (`../`, symlink escapes) return safe default — never partial write.

### Operator Gates
- All gates block indefinitely until explicit operator input.
- No timeout, no auto-approve, no fallback.
- Gate decisions are logged with CTX-ID, timestamp, and operator identity.

## Build Pipeline Invariants

- Build phases execute in strict order: scope → plan → generate → test → review → merge.
- No phase may be skipped or reordered.
- Completed phase checkpoints persist — crash recovery resumes from last completed checkpoint, never re-executes.
- Merge requires explicit operator gate approval.
- Consensus arbitration uses `_score_fix()` scoring — never length, never recency, never provider preference.