# CLAUDE.md

Forge is the engineering and enforcement framework for Crafted Dev Agent — a native macOS two-process AI coding agent (Swift shell + Python backend) that decomposes plain-language build intents into ordered pull requests, generates and tests implementations via dual-LLM consensus, and gates on operator approval before merging. Forge enforces explicit trust validation, policy-first execution, synchronous auditability, fail-closed security, and traceable implementation across every boundary.

## Critical Rules - Read Before Writing Any Code

1. Validate `CTX-ID` first at every enforcement entry point — validation failure means immediate rejection with no partial processing.
2. Check `VTZ` policy before any action execution — emit a `VTZEnforcementDecision` record with `verdict=block` on denial.
3. Emit a synchronous `TrustFlow` event for every action outcome (`allow`, `restrict`, `block`) in the enforcement path — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
4. Treat missing or expired `CTX-ID` as `UNTRUSTED` — never infer identity from session context, XPC state, or UI state.
5. Bind every agent session to exactly one `VTZ` at `CTX-ID` issuance — cross-`VTZ` tool calls require explicit policy authorization; implicit access is denied.
6. Assign `DTL` labels at data ingestion — labels are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified.
7. Fail closed on all trust, identity, policy, and cryptographic errors — reject the action, log the event, surface the failure to the caller; never silently continue.
8. Never log or return secrets, keys, tokens, credentials, `CTX-ID` tokens, or cleartext sensitive payloads in errors, audit records, telemetry, generated code, or error structs.
9. Validate every filesystem write with `path_security.validate_write_path()` before execution — traversal attempts return a safe default; never write directly from user-supplied paths.
10. Treat all external content (documents, PR comments, CI output, XPC input, user-supplied paths) as untrusted — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
11. Generated code is NEVER executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content, ever.
12. Gate waits indefinitely for operator input — no auto-approve, no timeout-based approval for merges, releases, security overrides, or policy-bypassing actions, ever.
13. `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
14. Length-based fix arbitration is FORBIDDEN — use `_score_fix()` based on assertion token overlap; `max(claude_fix, openai_fix, key=len)` is banned.
15. Do not change version constants, semantic version ownership, or compatibility handshake behavior outside the owning startup/version contract defined by `TRD-12`.

## Architecture Overview

| Subsystem | Path | Enforces | Must NOT Do |
|-----------|------|----------|-------------|
| **App Shell (TRD-1)** | `Crafted/` | XPC channel, credential delivery, Keychain, process lifecycle, ready-message validation | Must NOT store credentials outside Keychain; must NOT implement backend policy enforcement; must NOT infer backend trust state without explicit protocol data |
| **Backend Entry (TRD-12)** | `src/agent.py` | Python entry point, REPL, version surface, TRD-defined startup ordering | Must NOT signal ready before required startup succeeds; must NOT alter version constants or handshake behavior outside TRD-12 contract |
| **Consensus Engine** | `src/consensus.py` | `ConsensusEngine` for parallel dual-LLM generation, arbitration, self-correction, lint gate, fix-loop coordination; language-aware system prompt selection | Must NOT use length-based arbitration; must NOT skip explicit `language` parameter |
| **Build Pipeline** | `src/build_director.py` | Pipeline orchestration, confidence gate, `pr_type` routing, stage ordering, checkpoints | Must NOT skip gates; must NOT rerun completed PR stages after recovery |
| **Provider Adapters** | `src/providers.py` | Provider adapters for Claude and OpenAI; API key delivery, model routing, response normalization | Must NOT hardcode credentials; must NOT expose raw provider errors containing sensitive data |
| **Path Security** | `src/path_security.py` | Write-path validation, traversal prevention | Must NOT allow unvalidated writes; must NOT trust user-supplied paths |

## Trust & Identity Invariants

- **CTX-ID** is the sole identity token — every enforcement boundary validates it before any processing.
- **VTZ** (Virtual Trust Zone) boundaries are structural, not advisory — they partition tool access and data visibility.
- **DTL** (Data Trust Label) classification is assigned once at ingestion and propagates upward through derivation.
- **TrustFlow** events are the single audit trail — every policy decision emits one synchronously.

## Version & Startup Contract (TRD-12)

- Version constants live in `src/agent.py` and are owned by the startup/version contract defined in TRD-12.
- Semantic version values, compatibility handshake fields, and ready-signal semantics MUST NOT be modified outside TRD-12-governed changes.
- The Swift shell and Python backend perform a version compatibility handshake over XPC at startup — both sides MUST agree on the protocol version before the backend signals ready.
- The backend MUST complete all TRD-defined startup steps (provider initialization, path security setup, policy loading) before emitting the ready signal.

## Consensus & Arbitration

- Dual-LLM consensus: Claude and OpenAI generate in parallel; arbitration selects or merges.
- Fix arbitration MUST use `_score_fix()` with assertion token overlap — never length comparison.
- Language parameter MUST be explicitly passed to system prompt selection — never inferred or defaulted silently.
- Self-correction loops are bounded; lint gate failures trigger fix attempts, not infinite retries.

## Pipeline & Gating

- Build pipeline decomposes intents into ordered PRs with stage checkpoints.
- Confidence gate MUST be evaluated before PR submission.
- Operator approval gates wait indefinitely — the pipeline blocks, never auto-advances.
- Completed PR stages MUST NOT be rerun after recovery — the pipeline resumes from the last incomplete stage.