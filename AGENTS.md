# AGENTS.md - Forge Platform

Forge is a security-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL, and emits an immutable TrustFlow audit stream — all enforced, never advisory.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing.
2. Every agent action MUST be checked against VTZ policy BEFORE execution — implicit cross-VTZ access is denied, always.
3. Every action outcome (`allow`, `restrict`, `block`) MUST emit a synchronous TrustFlow event — async buffering is not permitted in enforcement paths.
4. All trust, identity, policy, and cryptographic failures MUST fail closed — reject the action, log the event, surface to caller, never silently continue.
5. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads.
6. All external input (documents, PR comments, CI output, XPC messages, agent prompts) is untrusted — validate strictly before use.
7. Generated code is never executed by the agent — no `eval()`, no `exec()`, no subprocess of generated content, no `shell=True`.
8. Gates wait indefinitely for operator input — no auto-approve, no auto-merge, no auto-resolve destructive or security-relevant actions, ever.
9. All file writes MUST pass `path_security.validate_write_path()` before opening, creating, moving, or overwriting any file.
10. Unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified — DTL labels are immutable after ingestion and derived data inherits the highest classification of any source.
11. CTX-ID tokens are immutable once issued — rotation creates a new token and invalidates the old one immediately; expired or missing CTX-ID MUST be rejected as `UNTRUSTED`. Never infer identity from session context, transport context, or prior requests.
12. TrustFlow emission failure is a WARN-level audit event that MUST be logged and surfaced — never a silent skip; `try/except/pass` is BANNED in all enforcement code.
13. `SECURITY_REFUSAL` is terminal for that operation: stop, gate, and log it; never bypass it by retrying, rephrasing, or provider failover.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → DTL label verification on output**.

| Directory | Subsystem | Enforces | MUST NOT Do |
|---|---|---|---|
| `src/cal/` | Conversation Abstraction Layer | CTX-ID validation at every entry point; action dispatch to VTZ; enforcement sequencing | Process any action before CTX-ID is validated and VTZ policy is checked |
| `src/vtz/` | Virtual Trust Zone | Structural session boundaries; per-VTZ policy evaluation; each agent session bound to exactly one VTZ | Allow cross-VTZ calls without explicit policy authorization; permit mid-session policy mutation |
| `src/trustflow/` | TrustFlow Audit Stream | Synchronous, append-only audit event emission for every action outcome with required fields | Buffer events asynchronously; modify or delete audit records; silently drop failed emissions |
| `src/dtl/` | Data Trust Labels | Label assignment at ingestion; label verification at every trust boundary crossing; highest-label inheritance on derived data | Strip or mutate labels without audit; pass unlabeled data as trusted; downgrade labels without audited policy control |
| `src/trustlock/` | TrustLock (TPM-anchored identity) | Cryptographic machine identity; CTX-ID validation against TrustLock public key with hardware-anchored assurance | Rely on software-only validation when hardware anchoring is available; issue CTX-ID without cryptographic binding |
| `src/mcp/` | MCP Policy Engine | Policy evaluation prior to execution; policy-driven gating for destructive and security-relevant actions | Execute actions before policy evaluation completes; auto-approve gated actions |

## Repository Structure


forge/
├── CLAUDE.md                    # This file — platform rules and conventions
├── pyproject.toml               # Project metadata, dependencies, build config
├── src/
│   ├── cal/                     # Conversation Abstraction Layer
│   │   ├── __init__.py
│   │   ├── entry.py             # Entry-point validation; CTX-ID-first enforcement
│   │   ├── dispatch.py          # Action dispatch to VTZ after policy check
│   │   └── types.py             # CAL-specific types and enums
│   ├── vtz/                     # Virtual Trust Zone
│   │   ├── __init__.py
│   │   ├── zone.py              # VTZ lifecycle, session binding
│   │   ├── policy.py            # Per-VTZ policy evaluation
│   │   └── boundary.py          # Cross-VTZ authorization checks
│   ├── trustflow/               # TrustFlow Audit Stream
│   │   ├── __init__.py
│   │   ├── emitter.py           # Synchronous event emission
│   │   ├── schema.py            # Event schema with required fields
│   │   └── store.py             # Append-only audit storage
│   ├── dtl/                     # Data Trust Labels
│   │   ├── __init__.py
│   │   ├── labels.py            # Label assignment and immutability enforcement
│   │   ├── classify.py          # Classification logic and inheritance
│   │   └── boundary.py          # Label verification at trust boundaries
│   ├── trustlock/               # TrustLock cryptographic identity
│   │   ├── __init__.py
│   │   ├── identity.py          # CTX-ID issuance and validation
│   │   ├── tpm.py               # TPM-anchored key operations
│   │   └── rotation.py          # Token rotation with immediate invalidation
│   ├── mcp/                     # MCP Policy Engine
│   │   ├── __init__.py
│   │   ├── engine.py            # Policy evaluation engine
│   │   ├── gates.py             # Operator gate enforcement (wait indefinitely)
│   │   └── rules.py             # Policy rule definitions
│   └── common/                  # Shared utilities
│       ├── __init__.py
│       ├── path_security.py     # validate_write_path() and path validation
│       ├── errors.py            # Fail-closed error types
│       └── types.py             # Shared enums, constants, base types
├── tests/
│   ├── unit/                    # Unit tests mirroring src/ structure
│   ├── integration/             # Cross-subsystem enforcement tests
│   └── conftest.py              # Shared fixtures
└── docs/                        # Design docs and subsystem specifications


## Path Namespace Conventions

- All source code lives under `src/` — never at repository root.
- Each subsystem owns exactly one top-level directory under `src/` matching its acronym in lowercase: `cal`, `vtz`, `trustflow`, `dtl`, `trustlock`, `mcp`.
- Shared utilities live in `src/common/` — subsystem code MUST NOT import laterally between peer subsystems except through explicitly defined interface modules (`__init__.py` public API).
- Test paths mirror source paths: `tests/unit/cal/`, `tests/unit/vtz/`, etc.
- No file outside `src/common/path_security.py` may implement write-path validation — all file writes MUST route through `path_security.validate_write_path()`.

## Import Conventions

- Subsystem public API is defined in `src/<subsystem>/__init__.py` — internal modules are private.
- Cross-subsystem imports MUST use the public API: `from src.vtz import check_policy`, never `from src.vtz.policy import _internal_check`.
- `src/common/` is the only package importable by all subsystems.

## Enforcement Contracts

- **CTX-ID**: Every public function in `src/cal/entry.py` MUST accept a `ctx_id: str` parameter and call `trustlock.validate(ctx_id)` before any other logic. Return type on failure: `SecurityRefusal`.
- **VTZ**: Every action dispatch in `src/cal/dispatch.py` MUST call `vtz.check_policy(ctx_id, action)` and MUST NOT proceed if the result is `deny`.
- **TrustFlow**: Every action outcome MUST call `trustflow.emit(event)` synchronously before returning. The `event` object MUST include: `ctx_id: str`, `vtz_id: str`, `action: str`, `outcome: Literal['allow', 'restrict', 'block']`, `timestamp: str` (ISO 8601), `dtl_label: str`.
- **DTL**: Every data object crossing a trust boundary MUST have a `dtl_label` field. If absent, the system MUST assign `CONFIDENTIAL` and emit a TrustFlow event recording the assignment.
- **TrustLock**: `trustlock.validate(ctx_id)` MUST verify the CTX-ID signature against the TPM-anchored public key. On failure, return `UNTRUSTED` — never fall back to software-only validation.
- **MCP Gates**: Any action classified as destructive or security-relevant by MCP policy MUST enter an operator gate that blocks indefinitely until explicit operator approval.

## Code Style and Testing

- Python 3.11+ required.
- Type annotations on all public functions — `mypy --strict` MUST pass.
- All enforcement paths MUST have unit tests that verify fail-closed behavior.
- Integration tests MUST verify the full enforcement chain: CTX-ID → VTZ → Action → TrustFlow → DTL.
- No `# type: ignore` without an inline comment explaining why.
- No `try/except/pass` anywhere in the codebase — caught exceptions MUST be logged and surfaced.