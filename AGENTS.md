# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all enforced locally on macOS via a native agent (ConsensusDevAgent) that decomposes build intents into gated PR sequences with human approval at every gate.

## Critical Rules — Read Before Writing Any Code

1. **CTX-ID first.** Validate CTX-ID at every enforcement entry point — validation failure is immediate rejection with no partial processing, no fallback. Missing CTX-ID MUST be treated as `UNTRUSTED`. Never infer identity from ambient context, session state, or caller location.
2. **VTZ before execution.** Check VTZ policy BEFORE any agent action executes. Cross-VTZ tool calls require explicit policy authorization; implicit access is denied. On denial, emit a `VTZEnforcementDecision` with `verdict=block`.
3. **TrustFlow synchronous emission.** Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`). Every event MUST include: `event_id` (UUID), `session_id`, `ctx_id`, `ts` (ISO-8601), `event_type`, `payload_hash` (SHA-256). Async buffering is forbidden in the enforcement path. Failed emission is a WARN-level audit event that MUST be surfaced.
4. **Fail closed.** All trust, identity, policy, and cryptographic failures MUST fail closed: reject the action, log the event, surface to the caller — never silently continue.
5. **No secrets in output.** Never hardcode secrets, tokens, credentials, API keys, or cryptographic material. Secrets MUST never appear in logs, error messages, audit records, generated code, or comments.
6. **Untrusted input.** All external input (documents, PR comments, CI output, user prompts) is untrusted. Validate strictly, scan for injection before inclusion, and never place external content in the SYSTEM prompt.
7. **No execution of generated content.** Generated code is never executed by the agent — no `eval()`, no `exec()`, no subprocess execution of generated content, no `shell=True` in subprocess calls.
8. **Gates wait forever.** Gates wait indefinitely for operator input — no auto-approve, no auto-merge, ever. If a component emits `SECURITY_REFUSAL`, do not retry, rephrase, or bypass — stop, gate, log.
9. **Path security.** All file writes MUST pass `path_security.validate_write_path()` before execution — no exceptions, no writes to unvalidated paths.
10. **DTL immutability.** DTL labels are assigned at data ingestion and are immutable. Derived data inherits the HIGHEST classification of any source. Unlabeled data MUST be treated as `CONFIDENTIAL` until explicitly reclassified. Labels MUST never be stripped or downgraded without a policy-authorized reclassification event.
11. **CTX-ID immutability.** CTX-ID tokens are IMMUTABLE once issued. Rotation creates a new token and immediately invalidates the old one. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance.
12. **XPC wire discipline.** Discard and log unknown XPC message types. Enforce line-delimited JSON with a 16 MB maximum message size. Never raise uncaught exceptions for unknown wire messages.

## Architecture Overview

Enforcement order: **CTX-ID validation → VTZ policy check → Action execution → DTL label verification → TrustFlow emission → Audit record**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; action-level policy gating; calls VTZ policy second, executes action third, emits TrustFlow last | Never process an action without CTX-ID validation first; never perform partial action processing before trust validation |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural session boundaries; policy-based cross-zone authorization; emits `VTZEnforcementDecision` with `verdict` field | Never allow implicit cross-VTZ access; never apply policy changes mid-session |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation anchored to TrustLock public key / TPM-backed identity | Never accept software-only identity validation when hardware attestation is available; never issue a CTX-ID without cryptographic proof |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every enforcement outcome; each event contains `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Never buffer asynchronously in the enforcement path; never silently drop emission failures |
| **DTL** (Data Trust Labeling) | `src/dtl/` | Ingestion-time data classification; immutable label assignment; derived-data inheritance at highest source classification | Never strip, downgrade, or omit labels; never allow unlabeled data to pass as unclassified |
| **ConsensusDevAgent** | `src/consensus_dev_agent/` | Decomposes build intents into gated PR sequences; enforces human approval at every gate; coordinates with CAL for CTX-ID-bound operations | Never auto-approve a gate; never execute generated code; never bypass `SECURITY_REFUSAL` |
| **Path Security** | `src/path_security/` | Write-path validation for all file operations via `validate_write_path()` | Never allow a file write to an unvalidated path |

## Repository Structure


forge/
├── CLAUDE.md                          # This file — platform contract
├── README.md                          # Project overview and setup
├── LICENSE
├── pyproject.toml                     # Build and dependency config
├── Makefile                           # Common dev commands
├── .github/
│   └── workflows/
│       ├── ci.yml                     # CI pipeline
│       └── security-audit.yml         # Security-focused checks
├── src/
│   ├── cal/
│   │   ├── __init__.py
│   │   ├── entry.py                   # Enforcement entry points
│   │   ├── ctx_id_validator.py        # CTX-ID validation logic
│   │   └── policy_gate.py            # Action-level policy gating
│   ├── vtz/
│   │   ├── __init__.py
│   │   ├── zone.py                    # VTZ definition and lifecycle
│   │   ├── policy.py                  # Cross-zone authorization policy
│   │   └── enforcement.py            # VTZEnforcementDecision emission
│   ├── trustlock/
│   │   ├── __init__.py
│   │   ├── identity.py                # Machine identity and key management
│   │   ├── ctx_id.py                  # CTX-ID issuance and rotation
│   │   └── attestation.py            # Hardware attestation interface
│   ├── trustflow/
│   │   ├── __init__.py
│   │   ├── emitter.py                 # Synchronous event emission
│   │   ├── event.py                   # Event schema (event_id, session_id, ctx_id, ts, event_type, payload_hash)
│   │   └── store.py                   # Immutable audit record persistence
│   ├── dtl/
│   │   ├── __init__.py
│   │   ├── labeler.py                 # Ingestion-time label assignment
│   │   ├── inheritance.py            # Derived-data classification inheritance
│   │   └── validator.py              # Label immutability enforcement
│   ├── consensus_dev_agent/
│   │   ├── __init__.py
│   │   ├── decomposer.py             # Build intent → gated PR decomposition
│   │   ├── gate.py                    # Human approval gate (waits indefinitely)
│   │   └── pr_sequence.py            # PR sequencing and dependency tracking
│   ├── path_security/
│   │   ├── __init__.py
│   │   └── validator.py              # validate_write_path() implementation
│   └── xpc/
│       ├── __init__.py
│       ├── wire.py                    # Line-delimited JSON, 16MB max, unknown-type discard
│       └── handler.py                # XPC message dispatch
├── tests/
│   ├── test_cal/
│   ├── test_vtz/
│   ├── test_trustlock/
│   ├── test_trustflow/
│   ├── test_dtl/
│   ├── test_consensus_dev_agent/
│   ├── test_path_security/
│   └── test_xpc/
└── docs/
    ├── architecture.md
    ├── enforcement-order.md
    ├── ctx-id-lifecycle.md
    ├── vtz-policy-model.md
    ├── trustflow-event-schema.md
    └── dtl-classification-rules.md


## Enforcement Invariants

These invariants MUST hold at all times. Any violation is a security incident.

- No action executes without a validated CTX-ID.
- No cross-VTZ access occurs without explicit policy authorization.
- No TrustFlow event is dropped silently.
- No DTL label is downgraded or removed.
- No file is written without path validation.
- No gate is passed without human approval.
- No generated content is executed.
- No secret appears outside secure storage.