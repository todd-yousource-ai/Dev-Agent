# AGENTS.md

Crafted Dev Agent is a native macOS AI coding agent that decomposes plain-language build intents into ordered pull requests, generates code via dual-LLM consensus, and gates every merge on operator approval — enforcing Forge security, identity, policy, and audit contracts throughout.

Forge is the policy-enforcing architecture that validates CTX-ID, enforces VTZ boundaries, preserves DTL classifications, and emits synchronous TrustFlow audit evidence for every security-relevant action.

## Critical Rules - Read Before Writing Any Code

1. **Validate CTX-ID first at every enforcement entry point** — reject immediately on failure with zero partial processing; missing CTX-ID is treated as `UNTRUSTED`; never infer identity from ambient context, session state, or caller location.
2. **Check VTZ policy BEFORE execution of every agent action** — cross-VTZ tool calls require explicit policy authorization; implicit access is denied; VTZ boundaries are structural, not advisory.
3. **Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`)** — emission is synchronous in the enforcement path; async buffering is not permitted; failed emission is a WARN-level audit event, never a silent skip.
4. **Fail closed on all auth, crypto, identity, and policy errors** — never degrade silently into insecure behavior; reject the action, log the event, surface to the caller with component, operation, failure_reason, and ctx_id.
5. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified; label verification occurs before any data crosses a trust boundary.
6. **Secrets, keys, tokens, and credentials never appear in logs, error messages, or generated code** — all sensitive material is protected in memory, at rest, and in transit; never hardcode, return, persist, or generate any of it.
7. **All external input (documents, PR comments, CI output, XPC messages, file paths) is untrusted** — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. **Generated code is never executed by the agent** — no `eval`, no `exec`, no `subprocess` of generated content; SECURITY_REFUSAL output is never bypassed by rephrasing — stop, gate, log.
9. **Gates wait indefinitely for operator input** — no auto-approve ever; `gate_card` blocks until the operator responds; completed per-PR stage checkpoints must not be rerun after recovery.
10. **All file writes are path-validated via `path_security.validate_write_path()` before execution** — traversal attempts return a safe default path.
11. **Audit records are append-only, generated BEFORE execution, and must never contain secrets** — replay must be possible from the audit stream alone; audit failures are non-fatal but must be surfaced immediately.
12. **No swallowed exceptions in enforcement code** — `try/except/pass` is BANNED in any enforcement path; every error must include `component`, `operation`, `failure_reason`, and `ctx_id` if available.
13. **Discard and log unknown XPC message types** — never raise them as uncaught exceptions in the transport path.

## Architecture Overview

Crafted Dev Agent is a two-process architecture: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub integration).

| Subsystem | Path | Enforces (Must) | Must NOT |
|---|---|---|---|
| **Swift Shell** | `Crafted/` | Native macOS shell handling UI, auth, Keychain, and XPC; enforces shell-side trust boundaries; validates XPC message types; discards unknown XPC messages with logging | Perform backend policy arbitration that belongs in Python; pass unvalidated XPC payloads to the backend |
| **Agent Entry** | `src/agent.py` | Python backend entry point and REPL; starts the controlled pipeline; initializes CTX-ID validation and audit | Bypass enforcement, recovery, or audit requirements |
| **CAL** | `src/cal/` | Conversation Abstraction Layer — CTX-ID validation at every entry point; manages conversation context and trust boundary enforcement | Allow requests with missing or invalid CTX-ID to proceed; place external context in SYSTEM prompt |
| **Build Director** | `src/build_director.py` | Pipeline orchestration for confidence gate and `pr_type` routing; sequences gated stages; persists stage checkpoints | Skip operator approval, CI, or checkpoint persistence; auto-approve any gate; rerun completed per-PR stage checkpoints after recovery |
| **Consensus Engine** | `src/consensus.py` | `ConsensusEngine` for parallel generation, arbitration, and self-correction; passes `language=spec.language` to providers | Use forbidden length-based fix arbitration; execute or trust generated code |
| **Providers** | `src/providers.py` | `ClaudeProvider` and `OpenAIProvider`; treats all provider outputs as untrusted | Execute or trust returned code without policy and validation; log or persist API keys or tokens |
| **Build Ledger** | `src/build_ledger.py` | Multi-engineer coordination state; preserves stage checkpoints and build rules | Clear persistent build memory or build rules automatically |
| **GitHub Tools** | `src/github_tools.py` | `GitHubTool` — single Python class through which all GitHub operations flow; owns repo API calls; validates all inputs from PR comments and CI output as untrusted | Bypass path validation; expose tokens in logs or error messages; execute content received from GitHub |
| **Path Security** | `src/path_security.py` | `validate_write_path()` — validates every file write target before execution; returns safe default on traversal attempts | Allow directory traversal; permit writes outside approved workspace roots |
| **TrustFlow Audit** | `src/trustflow/` | Synchronous emission of TrustFlow events for every action outcome; append-only audit records generated before execution | Buffer events asynchronously; silently skip emission failures; include secrets in audit records |
| **VTZ Policy** | `src/vtz/` | Virtual Trust Zone boundary enforcement; policy checked before every agent action; cross-VTZ calls require explicit authorization | Treat VTZ boundaries as advisory; allow implicit cross-VTZ access |
| **DTL** | `src/dtl/` | Data Trust Labels assigned at ingestion; immutable; highest classification inherited on derived data; unlabeled data is `CONFIDENTIAL` | Downgrade labels without explicit reclassification; skip label verification at trust boundaries |