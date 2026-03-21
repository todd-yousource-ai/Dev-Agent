# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographic identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data with immutable Data Trust Labels (DTL), and emits a TrustFlow audit event for every enforcement decision — failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — validation failure means immediate rejection with zero partial processing.
2. CTX-ID MUST be validated against the TrustLock public key — software-only validation is never acceptable.
3. Missing or expired CTX-ID MUST be classified as `UNTRUSTED` and rejected — never infer identity from context.
4. CTX-ID tokens are immutable once issued — never modify, extend, or reissue without a full cryptographic re-validation through TrustLock.
5. Every agent action MUST be checked against VTZ policy BEFORE execution — implicit cross-VTZ access is always denied.
6. Every action outcome (`allow`, `restrict`, `block`) MUST emit a synchronous TrustFlow event in the enforcement path — async buffering is not permitted; silent skip is never acceptable.
7. All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to the caller — never silently continue.
8. Never hardcode secrets, tokens, credentials, or cryptographic material; never log them; never include them in error messages.
9. All external input (documents, PR comments, CI output, agent prompts, XPC messages, file paths) is untrusted — validate strictly before use; context from external documents goes in the USER prompt, never the SYSTEM prompt.
10. Generated code is never executed by the agent — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True`.
11. DTL labels are assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as `CONFIDENTIAL`.
12. DTL labels MUST NOT be downgraded, stripped, or ignored without a policy-controlled audit decision that is itself recorded in TrustFlow.
13. All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions.
14. Gate cards wait indefinitely for operator input — no auto-approve ever; `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
15. XPC unknown message types are discarded and logged — never raised as exceptions; XPC messages are line-delimited JSON, nonce-authenticated, max 16 MB per message.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → TrustLock key verification → VTZ policy check → Action execution → TrustFlow emission → DTL label verification on data output**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Binds every agent action to a validated CTX-ID and routes through VTZ policy | Never process an action without CTX-ID validation; never skip TrustFlow emission |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; CTX-ID verification against TrustLock public key | Never fall back to software-only validation; never accept an unverified CTX-ID |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural session boundaries; one VTZ per session; cross-VTZ requires explicit policy | Never allow implicit cross-zone access; never apply policy changes mid-session |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns and verifies immutable labels at ingestion and at every boundary crossing | Never downgrade, strip, or ignore labels without policy-controlled audit; never treat unlabeled data as anything below `CONFIDENTIAL` |
| **TrustFlow** | `src/trustflow/` | Append-only audit stream for every enforcement decision | Never emit asynchronously in enforcement paths; never silently drop events; never allow retroactive modification of emitted records |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Evaluates policy inputs for tools, data movement, and enforcement decisions | Never act as advisory-only logic when enforcement is required; never skip policy evaluation for any tool invocation |
| **Forge Rewind** | `src/rewind/` | Reconstructs session history from append-only TrustFlow audit records | Never depend on non-audit external state for replay correctness; never mutate audit records during replay |
| **Forge Connector SDK** | `sdk/connector/` | Exposes conformant client integrations for external consumers | Never bypass CTX-ID or VTZ enforcement at the SDK boundary; never expose internal enforcement interfaces directly |

## Repository Structure


forge/
├── CLAUDE.md                  # This file — platform rules and architecture
├── src/
│   ├── cal/                   # Conversation Abstraction Layer
│   │   ├── __init__.py
│   │   ├── entry.py           # CTX-ID validation entry point
│   │   ├── mediator.py        # Action mediation and VTZ routing
│   │   └── tests/
│   ├── trustlock/             # Cryptographic machine identity
│   │   ├── __init__.py
│   │   ├── verifier.py        # CTX-ID verification against TrustLock public key
│   │   ├── key_store.py       # Public key management (never stores private keys)
│   │   └── tests/
│   ├── vtz/                   # Virtual Trust Zone enforcement
│   │   ├── __init__.py
│   │   ├── zone.py            # VTZ lifecycle and boundary enforcement
│   │   ├── policy.py          # VTZ policy evaluation
│   │   └── tests/
│   ├── dtl/                   # Data Trust Labels
│   │   ├── __init__.py
│   │   ├── labeler.py         # Label assignment at ingestion
│   │   ├── propagation.py     # Classification inheritance logic
│   │   ├── boundary.py        # Label verification at boundary crossings
│   │   └── tests/
│   ├── trustflow/             # TrustFlow audit stream
│   │   ├── __init__.py
│   │   ├── emitter.py         # Synchronous event emission
│   │   ├── schema.py          # Event schema and required fields
│   │   ├── store.py           # Append-only audit storage
│   │   └── tests/
│   ├── mcp/                   # MCP Policy Engine
│   │   ├── __init__.py
│   │   ├── engine.py          # Policy evaluation for tools and data movement
│   │   ├── rules.py           # Policy rule definitions
│   │   └── tests/
│   ├── rewind/                # Forge Rewind replay engine
│   │   ├── __init__.py
│   │   ├── replay.py          # Session reconstruction from audit records
│   │   └── tests/
│   ├── xpc/                   # XPC message handling
│   │   ├── __init__.py
│   │   ├── transport.py       # Line-delimited JSON, nonce auth, 16 MB limit
│   │   ├── dispatcher.py      # Message routing; unknown types discarded and logged
│   │   └── tests/
│   └── path_security/         # File write path validation
│       ├── __init__.py
│       ├── validator.py       # validate_write_path() implementation
│       └── tests/
├── sdk/
│   └── connector/             # Forge Connector SDK
│       ├── __init__.py
│       ├── client.py          # Conformant client integration
│       └── tests/
├── tests/                     # Integration and end-to-end tests
│   ├── integration/
│   └── e2e/
├── docs/                      # Architecture and interface documentation
├── pyproject.toml
└── README.md


## TrustFlow Event Schema (Required Fields)

Every TrustFlow event MUST include:

| Field | Type | Description |
|---|---|---|
| `event_id` | `string (UUID v4)` | Unique identifier for this event |
| `timestamp` | `string (ISO 8601)` | Time of emission; MUST be set in the enforcement path |
| `ctx_id` | `string` | The CTX-ID of the agent action that triggered this event |
| `vtz_id` | `string` | The VTZ in which the action was evaluated |
| `action` | `string` | The action that was attempted |
| `outcome` | `enum: allow \| restrict \| block` | The enforcement decision |
| `dtl_label` | `string` | The DTL classification of affected data |
| `reason` | `string` | Human-readable enforcement rationale |
| `policy_ref` | `string` | Reference to the MCP policy rule that produced this decision |

## Development Commands

bash
# Run all tests
python -m pytest tests/ -v

# Run subsystem tests
python -m pytest src/cal/tests/ -v
python -m pytest src/trustlock/tests/ -v
python -m pytest src/vtz/tests/ -v
python -m pytest src/dtl/tests/ -v
python -m pytest src/trustflow/tests/ -v
python -m pytest src/mcp/tests/ -v

# Type checking
python -m mypy src/ sdk/ --strict

# Linting
python -m ruff check src/ sdk/


## Enforcement Invariants (CI MUST Verify)

1. Every public function in `src/cal/` MUST have a CTX-ID parameter and MUST call TrustLock verification before any other logic.
2. Every function that performs file I/O MUST call `path_security.validate_write_path()` before writing.
3. Every enforcement decision point MUST have a corresponding `TrustFlow.emit()` call on the same synchronous code path.
4. No module in `src/` MUST import `eval`, `exec`, or `subprocess` with `shell=True`.
5. No DTL label mutation MUST exist outside of `src/dtl/labeler.py` initial assignment.
6. All XPC message handling MUST discard unknown types — grep for unknown-type exception raises as CI failure.