# CLAUDE.md

Forge is the enforcement-first architecture and engineering standard for Crafted Dev Agent. It enforces explicit trust validation, deny-by-default policy control, synchronous auditability, and fail-closed handling across every agent action and repository write. Crafted is a two-process system: a native macOS Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub integration) that decomposes plain-language build intents into ordered pull requests, generates and tests code via dual-LLM consensus, and gates every merge on human operator approval.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point and reject immediately on any validation failure — no partial processing, no fallback.
2. Treat missing CTX-ID as UNTRUSTED and never infer identity from ambient context, session state, or UI state.
3. Check VTZ policy before execution of every agent action and never allow implicit cross-VTZ access; cross-VTZ tool calls require explicit policy authorization.
4. Emit a synchronous TrustFlow event for every action outcome (allow, restrict, block) in the enforcement path — async buffering is forbidden; never silently skip emission on failure.
5. Assign DTL labels at data ingestion; labels are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data is CONFIDENTIAL until explicitly reclassified.
6. Fail closed on all trust, identity, policy, cryptographic, and authorization errors — reject the action, log the event, surface the failure to the caller. Never silently continue.
7. Validate every file write path with `path_security.validate_write_path()` before any write, commit, scaffold, or generated file operation.
8. Treat all external input as untrusted, including documents, PR comments, CI output, XPC messages, user-supplied paths, and generated code. Validate strictly.
9. Never execute generated code — no `eval`, no `exec`, no shell execution, no subprocess invocation of generated content.
10. Never auto-approve gates; gate workflows MUST wait indefinitely for explicit operator input.
11. Never log secrets, keys, tokens, credentials, cleartext sensitive payloads, or CTX-ID material in logs, error messages, generated code, or audit records.
12. Preserve persistent build memory and build rules; never clear them automatically after crashes, retries, or stage completion. Per-PR stage checkpoints prevent re-running completed work after a crash.
13. Context from external documents goes in the USER prompt — never the SYSTEM prompt; SECURITY_REFUSAL output is never bypassed by rephrasing.
14. XPC unknown message types MUST be discarded and logged — never raised as exceptions. XPC messages are line-delimited JSON, nonce-authenticated, max 16 MB.

## Architecture Overview

### Swift Shell — `Crafted/`

Native macOS Swift/SwiftUI shell handling UI, authentication, Keychain access, and XPC transport. It MUST NOT perform backend consensus, GitHub orchestration, or bypass enforcement contracts.

### Python Backend

| File / Path | Responsibility | Enforces | Must NOT |
|---|---|---|---|
| `src/agent.py` | Backend entry point and REPL | Startup contracts, work routing | Bypass `build_director.py` sequencing or direct-write unsafe paths |
| `src/build_director.py` | Pipeline orchestration: confidence gate, PR decomposition, PR type routing | Stage order and checkpointing | Rerun completed stages after crash recovery |
| `src/consensus.py` | `ConsensusEngine`: parallel provider generation, arbitration, self-correction | Always pass `language` to `_consensus.run(...)` | Use length-based arbitration |
| `src/providers.py` | Provider adapters for Claude and OpenAI | Security/system prompt boundaries | Move external document context into the system prompt |
| `src/build_ledger.py` | Multi-engineer coordination and persistent build state | Checkpoint integrity | Clear build memory or build rules automatically |
| `src/github_tools.py` | `GitHubTool`: single Python class for all GitHub operations | All GitHub API calls route through this class | Perform GitHub operations outside this class |

### Enforcement Subsystems

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point, action lifecycle management | Process any action without CTX-ID validation |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Session-bound policy boundaries, cross-zone authorization checks | Allow implicit cross-VTZ access or mid-session policy changes without re-authorization |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome | Buffer events asynchronously or silently skip failed emissions |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable classification labels assigned at ingestion, highest-label inheritance for derived data | Downgrade labels, strip labels from derived data, or treat unlabeled data as anything other than CONFIDENTIAL |

## Build & Test

bash
# Python backend
python -m pytest tests/ -v

# Swift shell
xcodebuild -scheme Crafted -destination 'platform=macOS' test


## Key Conventions

- Every PR corresponds to one decomposed build intent — no multi-intent PRs.
- Dual-LLM consensus is required for all code generation; single-provider output is never merged.
- All enforcement boundaries (CAL, VTZ, TrustFlow, DTL) are structural — they are not advisory and cannot be bypassed by configuration.
- Operator identity is cryptographically verified; ambient or inferred identity is never accepted.