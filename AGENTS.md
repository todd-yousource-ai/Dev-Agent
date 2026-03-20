# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform where every AI agent action is cryptographically identified, policy-gated, and audit-logged — the Consensus Dev Agent is a native macOS two-process (Swift shell + Python backend) implementation that decomposes build intents into ordered PRs, generates code via parallel LLM consensus, and gates every merge on human operator approval.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure is immediate rejection with no partial processing.
2. Every agent action MUST be checked against VTZ policy BEFORE execution — implicit cross-VTZ tool calls are denied by default when authorization is absent.
3. Every action outcome (`allow`, `restrict`, `block`) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is not permitted; emission failures MUST never be silently skipped.
4. Missing CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from session context, transport state, or prior actions.
5. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to caller with safe context — never silently continue.
6. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, audit records, or cleartext payloads — Python never reads Keychain; only Swift reads Keychain and delivers via XPC.
7. All external input (documents, PR comments, CI output, XPC messages, LLM responses) is untrusted — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
8. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
9. Gates wait indefinitely for explicit operator input — no auto-approve, no auto-merge ever; `/continue` resumes from current thread state. `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log; never retry with a different provider.
10. All file writes MUST pass `path_security.validate_write_path()` before any write operation — reject invalid or out-of-scope paths.
11. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified. Label stripping MUST NOT occur without explicit policy control and audit.
12. XPC unknown message types are discarded and logged — never raised as exceptions; wire format is line-delimited JSON, nonce-authenticated, max 16MB per message.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action routing through VTZ policy | Must NOT process any action before CTX-ID is validated |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural boundary enforcement; one VTZ per session bound at CTX-ID issuance; decides authorization before execution | Must NOT allow cross-VTZ calls without explicit policy authorization; must NOT apply policy changes mid-session |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable label assignment at ingestion; classification propagation (derived data inherits highest source label) | Must NOT downgrade or strip labels without policy control and audit; must NOT leave data unlabeled without defaulting to `CONFIDENTIAL` |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome; every event record MUST include: `event_id` (string, UUID), `session_id` (string), `ctx_id` (string), `ts` (string, ISO-8601), `event_type` (string, one of `allow`, `restrict`, `block`), `payload_hash` (string, SHA-256 hex) | Must NOT buffer events asynchronously in the enforcement path; must NOT silently drop emission failures |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity binding; CTX-ID verification against TrustLock public key | Must NOT rely on software-only validation; must NOT accept unverified CTX-IDs |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explicit policy decisions tied to identity and VTZ; authoritative deny/allow for every gated action | Must NOT act as advisory-only logic; must NOT return ambiguous policy results |
| **Rewind** (Forge Rewind) | `src/rewind/` | Deterministic replay of audit-logged sessions from TrustFlow event stream | Must NOT replay without validating event chain integrity; must NOT modify events during replay |
| **Path Security** | `src/path_security/` | Write-path validation for all file operations | Must NOT allow any write without `validate_write_path()` call; must NOT permit path traversal or out-of-scope writes |

## Repository Directory Structure


forge/
├── CLAUDE.md                    # This file — platform rules and conventions
├── src/
│   ├── cal/                     # Conversation Abstraction Layer
│   │   ├── __init__.py
│   │   ├── ctx_id.py            # CTX-ID validation and issuance
│   │   ├── entry.py             # Enforcement entry points
│   │   └── router.py            # Action routing through VTZ policy
│   ├── vtz/                     # Virtual Trust Zones
│   │   ├── __init__.py
│   │   ├── zone.py              # Zone lifecycle and session binding
│   │   ├── policy.py            # Cross-VTZ authorization rules
│   │   └── boundary.py          # Structural boundary enforcement
│   ├── dtl/                     # Data Trust Labels
│   │   ├── __init__.py
│   │   ├── labels.py            # Label assignment and immutability
│   │   ├── propagation.py       # Classification inheritance rules
│   │   └── reclassify.py        # Policy-controlled reclassification
│   ├── trustflow/               # TrustFlow audit emission
│   │   ├── __init__.py
│   │   ├── emitter.py           # Synchronous event emission
│   │   ├── schema.py            # Event schema (event_id, session_id, ctx_id, ts, event_type, payload_hash)
│   │   └── store.py             # Audit record persistence
│   ├── trustlock/               # Cryptographic identity
│   │   ├── __init__.py
│   │   ├── identity.py          # Machine identity binding
│   │   └── verify.py            # CTX-ID verification against public key
│   ├── mcp/                     # MCP Policy Engine
│   │   ├── __init__.py
│   │   ├── engine.py            # Policy decision entry point
│   │   └── rules.py             # Identity- and VTZ-scoped policy rules
│   ├── rewind/                  # Forge Rewind replay engine
│   │   ├── __init__.py
│   │   ├── replay.py            # Deterministic session replay
│   │   └── integrity.py         # Event chain integrity validation
│   ├── path_security/           # Write-path enforcement
│   │   ├── __init__.py
│   │   └── validate.py          # validate_write_path() implementation
│   └── xpc/                     # XPC bridge (Swift ↔ Python)
│       ├── __init__.py
│       ├── protocol.py          # Line-delimited JSON, nonce auth, 16MB max
│       └── handler.py           # Message dispatch; unknown types discarded and logged
├── swift_shell/                 # Native macOS Swift shell process
│   ├── Package.swift
│   └── Sources/
│       ├── KeychainAccess.swift # Keychain reads — only Swift touches Keychain
│       ├── XPCBridge.swift      # XPC transport to Python backend
│       └── Main.swift           # Shell entry point
├── tests/
│   ├── test_cal/
│   ├── test_vtz/
│   ├── test_dtl/
│   ├── test_trustflow/
│   ├── test_trustlock/
│   ├── test_mcp/
│   ├── test_rewind/
│   ├── test_path_security/
│   └── test_xpc/
└── config/
    ├── vtz_policies.json        # VTZ policy definitions
    └── dtl_defaults.json        # Default DTL classification rules


## Path Namespace Conventions

- All Python source MUST reside under `src/` with one directory per subsystem matching the subsystem abbreviation in lowercase: `cal`, `vtz`, `dtl`, `trustflow`, `trustlock`, `mcp`, `rewind`, `path_security`, `xpc`.
- All Swift source MUST reside under `swift_shell/Sources/`.
- All tests MUST reside under `tests/` with one directory per subsystem prefixed with `test_`.
- Configuration files MUST reside under `config/`.
- Import paths MUST match directory structure: `from src.cal.ctx_id import validate_ctx_id`.
- No subsystem directory MUST import from another subsystem except through the explicitly defined interfaces in `__init__.py` — cross-subsystem coupling MUST go through CAL routing or MCP policy.
- Generated artifacts, build outputs, and temporary files MUST NOT be committed and MUST be listed in `.gitignore`.
- Every new subsystem directory MUST contain an `__init__.py` that exports only the public interface.

## Wire Format

XPC messages between Swift shell and Python backend:
- Format: line-delimited JSON (one JSON object per line, `\n`-terminated)
- Authentication: nonce-authenticated per message
- Max message size: 16 MB
- Unknown message types: discard and log, never raise exceptions

TrustFlow event record fields (all required):
- `event_id`: string, UUID v4
- `session_id`: string
- `ctx_id`: string
- `ts`: string, ISO-8601 with timezone
- `event_type`: string, one of `allow`, `restrict`, `block`
- `payload_hash`: string, SHA-256 hex digest

## Enforcement Checklist for Every PR

1. Does every new entry point validate CTX-ID before any processing?
2. Does every action check VTZ policy before execution?
3. Does every action outcome emit a synchronous TrustFlow event?
4. Are all failures fail-closed with no silent continuation?
5. Are secrets absent from all logs, errors, and generated output?
6. Is all external input validated before use?
7. Is no generated code executed?
8. Do all file writes pass `path_security.validate_write_path()`?
9. Are DTL labels assigned at ingestion and never stripped without policy and audit?
10. Are all XPC unknown message types discarded and logged?