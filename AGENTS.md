# AGENTS.md

Crafted Dev Agent is a native macOS two-process AI coding agent (Swift shell + Python backend) that decomposes build intents into ordered pull requests, generates and tests code via dual-LLM consensus, and gates on human approval before merging — enforcing Forge security, identity, and trust contracts at every boundary.

## Critical Rules — Read Before Writing Any Code

1. **Validate CTX-ID first at every enforcement entry point** — failure results in immediate rejection with zero partial processing; missing CTX-ID means `UNTRUSTED`; never infer identity from ambient context, session state, or caller location.
2. **Check VTZ policy BEFORE execution** — every agent session is bound to exactly one VTZ at CTX-ID issuance; cross-VTZ tool calls require explicit policy authorization; implicit cross-VTZ access is denied; emit a `VTZEnforcementDecision` with `verdict=block` on denial.
3. **Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`)** — emission is synchronous in the enforcement path; async buffering is not permitted; failed emission is a `WARN`-level audit event, never a silent skip.
4. **DTL labels are immutable after assignment at data ingestion** — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified; label stripping is audited.
5. **Fail closed on all auth, crypto, identity, and policy errors** — never degrade silently into insecure behavior; reject the action, log the event, surface to the caller.
6. **Secrets, keys, tokens, and credentials never appear in logs, error messages, or generated code** — protect in memory, at rest, and in transit; never hardcode.
7. **All external input (documents, PR comments, CI output) is untrusted** — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. **Generated code is never executed by the agent** — no `eval`, no `exec`, no `subprocess` of generated content.
9. **Gate cards wait indefinitely for operator input** — no auto-approve ever; `SECURITY_REFUSAL` output must halt processing and is never bypassed by rephrasing.
10. **All file writes must be path-validated via `path_security.validate_write_path()` before execution** — returns safe default on traversal attempt; never bypass path validation.
11. **XPC unknown message types are discarded and logged** — never raised as exceptions; wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.

## Architecture Overview

**Two-process architecture:** Swift shell (UI, auth, Keychain, XPC) → Python backend (consensus, pipeline, GitHub).

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **Swift Shell** | `Crafted/` | Process-boundary integrity, credential delivery via Keychain, XPC transport | Implement backend policy, consensus logic, or LLM calls |
| **Agent entry point** | `src/agent.py` | REPL, version reporting, startup sequencing | Signal ready before required initialization succeeds; accept commands before handshake completes |
| **Build Director** | `src/build_director.py` | Pipeline orchestration, confidence gate, `pr_type` routing, ordered build stages | Skip confidence gate, rerun completed per-PR checkpoints after recovery, or re-run completed stages |
| **Consensus Engine** | `src/consensus.py` | Parallel LLM generation + arbitration via `_score_fix()`, provider comparison, language-specific system prompt selection | Use length-based fix arbitration |
| **Providers** | `src/providers.py` | `ClaudeProvider` and `OpenAIProvider` isolation, request shaping, credential scoping | Leak credentials, execute returned code, or share state across providers |
| **Build Ledger** | `src/build_ledger.py` | `BuildLedger` multi-engineer coordination, persistent stage state | Clear build memory or build rules automatically |
| **GitHub Tools** | `src/github_tools.py` | PR creation, branch management, review gating | Merge without gate approval; push to protected branches without policy check |
| **Path Security** | `src/path_security.py` | Write-path validation, traversal prevention | Allow writes outside validated roots; raise on traversal (must return safe default) |

## Version and Semantic Ownership

- The canonical version constant lives in `src/agent.py` as `__version__`.
- The Swift shell reads version via XPC handshake; it must NOT maintain an independent version constant.
- Version bumps follow semver; major bumps require a gate card.

## TrustFlow Event Fields (required)

| Field | Type | Constraint |
|---|---|---|
| `actor_ctx_id` | `string` | Must be a validated CTX-ID; never null |
| `action` | `string` | The operation attempted |
| `resource` | `string` | Target of the action |
| `verdict` | `enum` | One of `allow`, `restrict`, `block` |
| `timestamp` | `ISO-8601` | UTC; set at emission time |
| `vtz_id` | `string` | Bound VTZ for the session |
| `dtl_label` | `string` | Classification of data involved |

## VTZEnforcementDecision Fields (on denial)

| Field | Type | Constraint |
|---|---|---|
| `actor_ctx_id` | `string` | Validated CTX-ID of requester |
| `resource` | `string` | Target resource or tool |
| `verdict` | `enum` | `block` |
| `reason` | `string` | Policy rule that triggered denial |
| `timestamp` | `ISO-8601` | UTC |

## XPC Wire Format

- Line-delimited JSON, one message per line.
- Every message includes a `nonce` field for replay prevention.
- Max message size: 16 MB; oversized messages are discarded and logged.
- Unknown `msg_type` values are discarded and logged; never raised as exceptions.
