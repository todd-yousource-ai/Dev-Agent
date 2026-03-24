# AGENTS.md

Forge is the enforcement-first architecture for Crafted Dev Agent — a native macOS AI coding agent that decomposes plain-language build intents into ordered, tested, CI-passing pull requests via a two-process architecture (Swift shell + Python backend) with consensus AI arbitration. Forge enforces explicit identity, policy, labeling, auditability, and fail-closed execution across every agent action.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID at the first enforcement entry point and reject immediately on validation failure with no partial processing.
2. Check VTZ policy before executing any agent action and record `VTZEnforcementDecision` with `verdict=block` on denial.
3. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is forbidden; failed emission is a WARN-level audit event that MUST be surfaced, never silently skipped.
4. Treat missing CTX-ID as `UNTRUSTED` and never infer identity from session state, UI context, or prior requests.
5. Bind every agent session to exactly one VTZ at CTX-ID issuance and deny cross-VTZ tool calls unless explicit policy authorizes them. VTZ boundaries are structural, not advisory — enforcement cannot be bypassed by application code.
6. Assign DTL labels at data ingestion, keep them immutable, and make derived data inherit the highest source classification.
7. Treat unlabeled data as `CONFIDENTIAL` until explicitly reclassified through a policy-controlled path.
8. Fail closed on all trust, identity, policy, cryptographic, and label-verification errors: reject, log, and surface the failure — never silently continue.
9. Never log or return secrets, keys, tokens, credentials, CTX-ID material, or cleartext sensitive payloads in errors, audit data, generated code, or logs — protect in memory, at rest, and in transit.
10. Validate every external input as untrusted, including documents, PR comments, CI output, XPC messages, and user-supplied file paths.
11. Never execute generated code, never use `eval` or `exec`, and never run generated content through subprocess execution.
12. Validate every file write with `path_security.validate_write_path()` before the write occurs and never bypass this path check.
13. Context from external documents goes in the USER prompt — never the SYSTEM prompt. SECURITY_REFUSAL output is never bypassed by rephrasing — stop, gate, log.
14. Gates wait indefinitely for operator input — no auto-approve ever.
15. Fix arbitration uses `_score_fix()` based on assertion token overlap — never length-based selection (`max(..., key=len)` is BANNED). Fix loop strategy uses `_choose_strategy(failure_type, attempt, records)` — never a static lookup table.
16. `try/except/pass` is BANNED in all enforcement code paths — every exception MUST be caught, logged with `component`, `operation`, `failure_reason`, and `ctx_id`, then surfaced.

## Architecture Overview

- `Crafted/` — Swift shell for UI, auth, Keychain, and XPC; it enforces native macOS boundary handling and credential custody. MUST NOT implement backend policy decisions, store secrets outside Keychain, or make GitHub API calls directly.
- `src/agent.py` — Python backend entry point and REPL/version surface; it enforces startup wiring and session orchestration. MUST NOT bypass pipeline gates or direct enforcement checks.
- `src/build_director.py` — Pipeline orchestrator for confidence gate, PRD decomposition, PR routing, and staged execution; it enforces ordered build progression and checkpointed recovery. MUST NOT auto-approve operator gates.
- `src/consensus.py` — `ConsensusEngine` for parallel generation and arbitration; it enforces language-specific generation routing and scored fix arbitration. MUST NOT use length-based winner selection.
- `src/providers.py` — LLM provider implementations; it enforces provider isolation and prompt routing. MUST NOT place external document context in the system prompt.
- `src/build_ledger.py` — `BuildLedger` for multi-engineer coordination and persistent execution state; it enforces stage checkpoints and durable progress tracking. MUST NOT clear or overwrite ledger state without explicit operator gate.
- `src/trust/` — TrustFlow event emission, CTX-ID validation, VTZ boundary enforcement, and DTL label propagation. MUST NOT allow implicit cross-VTZ authorization or silent emission failures.
- `src/security/path_security.py` — File-write path validation. Every write in the agent MUST call `path_security.validate_write_path()` before proceeding.

### Enforcement Order

1. CTX-ID validation
2. VTZ boundary check
3. DTL label verification
4. Policy evaluation
5. Action execution
6. TrustFlow event emission (synchronous, in enforcement path)
7. Audit log persistence

### TrustFlow Event Contract

Every TrustFlow event MUST include:
- `ctx_id` (string) — the validated CTX-ID for the session
- `vtz_id` (string) — the bound Virtual Trust Zone identifier
- `action` (string) — the action being evaluated
- `verdict` (enum: `allow`, `restrict`, `block`) — the enforcement outcome
- `dtl_label` (enum: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) — the data classification in effect
- `timestamp` (ISO 8601 string) — when the event was emitted
- `component` (string) — the subsystem that emitted the event
- `failure_reason` (string, nullable) — populated on `restrict` or `block`

### VTZEnforcementDecision Contract

Every VTZ enforcement decision MUST include:
- `ctx_id` (string)
- `source_vtz` (string)
- `target_vtz` (string, nullable — null for same-zone actions)
- `tool` (string) — the tool or operation requested
- `verdict` (enum: `allow`, `block`)
- `policy_ref` (string) — the policy rule that produced the verdict
- `timestamp` (ISO 8601 string)