# AGENTS.md

Forge is the security-first enforcement architecture underlying Crafted Dev Agent. It enforces explicit trust validation, VTZ policy decisions, immutable CTX-ID identity, DTL data labeling, synchronous TrustFlow audit emission, and fail-closed execution across every agent action.

Crafted Dev Agent is a native macOS AI coding agent that decomposes plain-language build intents into ordered pull requests, generates and tests implementations via dual-LLM consensus, and gates on human operator approval before merging — all governed by Forge's trust, identity, policy, and audit enforcement contracts.

## Critical Rules - Read Before Writing Any Code

1. **Validate CTX-ID at every enforcement entry point FIRST** — validation failure results in immediate rejection with no partial processing; missing CTX-ID is `UNTRUSTED`, never inferred from session context, transport context, or prior actions.
2. **Check VTZ policy BEFORE execution of every agent action** — cross-VTZ tool calls require explicit policy authorization; implicit access is denied; VTZ boundaries are structural, not advisory. Every agent session is bound to exactly one VTZ at CTX-ID issuance.
3. **Emit a TrustFlow event for every action outcome (allow, restrict, block)** — every event must include `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash`; emission is synchronous in the enforcement path; async buffering is not permitted; failed emission is a WARN-level audit event, never a silent skip.
4. **Fail closed on all trust, identity, policy, cryptographic, and credential errors** — never degrade silently into insecure behavior; reject the action, log the event, surface to the caller with safe context.
5. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified; label verification occurs before any trust boundary crossing; labels are never stripped or downgraded without audited policy control.
6. **Secrets, keys, tokens, and credentials never appear in logs, error messages, audit records, prompts, generated code, or XPC messages** — never hardcode secrets or cryptographic material; all secrets are protected in memory, at rest, and in transit via Keychain (TRD-1).
7. **All external input is untrusted** — this includes documents, PR comments, CI output, XPC messages, file paths, and repository content; validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. **Generated code is never executed by the agent** — no `eval`, no `exec`, no `subprocess` of generated content.
9. **Validate every file write path with `path_security.validate_write_path()` before execution** — returns a safe default on traversal attempts; never write to an unvalidated user-supplied path.
10. **Gates wait indefinitely for operator input** — no auto-approve ever; `SECURITY_REFUSAL` is terminal and never bypassed by rephrasing; unknown XPC message types are discarded and logged.
11. **Audit records are append-only, generated BEFORE execution** — they must not contain secrets, keys, tokens, or cleartext sensitive data; replay must be possible from the audit stream alone.
12. **No swallowed exceptions in enforcement paths** — `try/except/pass` is BANNED in any code touching trust, identity, policy, or cryptography; every error must include `component`, `operation`, `failure_reason`, and `ctx_id` if available.

## Architecture Overview

Crafted Dev Agent is a **two-process architecture**: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub).

### Subsystem Map

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **Swift Application Shell** | `Crafted/` | UI rendering, Keychain auth, XPC transport (TRD-1), local platform security boundaries | Must NOT execute backend logic, store secrets outside Keychain, implement backend consensus, or bypass backend policy decisions |
| **Swift Shell Tests** | `CraftedTests/` | XCTest suites for shell-side security and protocol behavior | Must NOT replace backend enforcement testing |
| **Agent Entry Point** | `src/agent.py` | Python backend entry point and REPL; routes work into controlled pipeline stages | Must NOT perform unchecked direct execution of generated artifacts |
| **Build Director** | `src/build_director.py` | Pipeline orchestration, confidence gate, `pr_type` routing; preserves stage ordering, checkpoints, and operator gates | Must NOT auto-approve or skip completed-stage bookkeeping |
| **Consensus Engine** | `src/consensus.py` | `ConsensusEngine` for parallel provider generation and arbitration; must call `run(..., language=spec.language)` | Must NOT use length-based fix arbitration |
| **LLM Providers** | `src/providers.py` | Provider abstraction for LLM calls; must enforce token limits, timeout, and error surfacing | Must NOT leak API keys or provider credentials into logs or audit |
| **GitHub Integration** | `src/github_*.py` | PR creation, branch management, CI status polling | Must NOT merge without operator gate approval; must NOT trust CI output without validation |
| **Path Security** | `src/path_security.py` | Write-path validation, traversal prevention | Must NOT allow writes outside validated directories |
| **Audit / TrustFlow** | `src/audit.py` | Append-only audit emission with required TrustFlow fields | Must NOT buffer asynchronously; must NOT omit required fields; must NOT log secrets |
| **Configuration** | `src/config.py` | Runtime configuration loading and validation | Must NOT contain secrets; must NOT override security policy at runtime without audited control |
| **Tests (Python)** | `tests/` | Unit and integration tests for all backend enforcement paths | Must NOT mock away security enforcement; must NOT skip trust/identity/policy validation in test fixtures |
