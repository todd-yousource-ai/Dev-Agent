# CLAUDE.md

Crafted Dev Agent is a native macOS AI coding agent built on the Forge platform — a two-process architecture (Swift shell + Python backend) that decomposes plain-language build intents into ordered pull requests, generates and tests code via parallel LLM consensus, and gates on operator approval before merging.

Forge is the security-first enforcement architecture and it enforces explicit identity, policy, labeling, audit, and fail-closed execution across every agent action.

## Critical Rules - Read Before Writing Any Code

1. All trust, identity, policy, and cryptographic failures MUST fail closed — reject the action, log the event, surface to caller, never silently continue.
2. CTX-ID tokens are immutable once issued; expired or missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from context.
3. Every enforcement entry point MUST call CTX-ID validation FIRST; validation failure results in immediate rejection with zero partial processing.
4. Every action outcome (allow, restrict, block) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is not permitted.
5. VTZ boundaries are structural, not advisory — enforcement cannot be bypassed by application code; cross-VTZ tool calls require explicit policy authorization.
6. DTL labels are assigned at data ingestion and are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data is CONFIDENTIAL until explicitly reclassified.
7. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or error payloads — protect in memory, at rest, and in transit.
8. Generated code is never executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content.
9. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution — traversal attempts return a safe default.
10. Context from external documents goes in the USER prompt — never the SYSTEM prompt; all external input (documents, PR comments, CI output) is untrusted and validated.
11. Gates wait indefinitely for operator input — no auto-approve ever; `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
12. Audit records are append-only, MUST NOT contain secrets, and replay MUST be possible from the audit stream alone with no external state required.
13. Discard and log unknown XPC message types; never raise them as uncaught exceptions in the message path.
14. Preserve persistent build memory, build rules, and per-PR stage checkpoints; never clear or rerun completed work automatically after a crash.

## Architecture Overview

Crafted is a two-process system: a Swift/SwiftUI shell (UI, authentication, Keychain, XPC) and a Python backend (consensus engine, build pipeline, GitHub integration).

### Subsystem Enforcement Map

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL (Conversation Abstraction Layer)** | `src/cal/` | CTX-ID validation at every entry point; action routing through VTZ policy | Never process an action without CTX-ID validation first |
| **TrustFlow** | `src/trustflow/` | Synchronous audit event emission for every action outcome | Never buffer asynchronously; never silently skip failed emissions |
| **VTZ (Virtual Trust Zone)** | `src/vtz/` | Structural boundary enforcement; policy checks before cross-boundary operations | Never allow application code to bypass enforcement; never permit implicit cross-VTZ access |
| **DTL (Data Trust Labels)** | `src/dtl/` | Label assignment at ingestion; immutability of labels; highest-classification inheritance for derived data | Never allow relabeling to a lower classification; never process unlabeled data as PUBLIC |
| **PathSecurity** | `src/path_security/` | Write-path validation before every file operation; traversal detection | Never write without validation; never permit path traversal |
| **AuditLog** | `src/audit/` | Append-only record creation; secret-free payloads; replayable event stream | Never delete or mutate records; never include secrets in audit entries |

### Module Responsibilities

- **`Crafted/`** — Native macOS Swift shell for UI, auth, Keychain access, and XPC transport; it enforces operator interaction, local credential handling, and shell/backend boundary control. It MUST NOT implement backend policy bypasses or infer trust implicitly.
- **`src/agent.py`** — Python backend entry point and REPL; it enforces top-level orchestration startup and versioned backend behavior. It MUST NOT bypass validation, policy, or audit paths.
- **`src/build_director.py`** — Pipeline orchestration for confidence gate, `pr_type` routing, staged PR execution, and checkpointing; it enforces ordered build progression and human gates. It MUST NOT auto-approve or rerun completed stages without checkpoint logic.
- **`src/consensus.py`** — `ConsensusEngine` for parallel LLM generation, arbitration, and self-correction; it enforces multi-provider generation with explicit `language` routing. It MUST NOT use length-based fix arbitration.
- **`src/providers.py`** — Provider adapters for `ClaudeProvider` and `OpenAIProvider`; they enforce provider isolation and normalized result handling. They MUST NOT leak credentials or provider-specific unsafe behavior upward.
- **`src/build_ledger.py`** — `BuildLedger` for multi-engineer coordination and persistent build state; it enforces stage persistence and crash recovery continuity. It MUST NOT lose or silently rewrite build history.
- **`src/github_tools.py`** — GitHub API integration for PR creation, branch management, and merge operations; it enforces authenticated API access and operator-gated merge. It MUST NOT merge without explicit operator approval.
- **`src/path_security.py`** — Path validation utilities; it enforces `validate_write_path()` for every file write. It MUST NOT return success for traversal attempts.
- **`src/trustflow/`** — TrustFlow event emission; it enforces synchronous event recording for every action outcome. It MUST NOT drop events or buffer asynchronously.

## Repo Structure


.
├── CLAUDE.md                  # This file — agent instructions and enforcement rules
├── README.md                  # Project overview and setup instructions
├── LICENSE                    # License file
├── Makefile                   # Build, test, lint targets
├── pyproject.toml             # Python project configuration
├── requirements.txt           # Python dependencies
├── .github/
│   └── workflows/             # CI/CD pipeline definitions
├── Crafted/                   # Swift/SwiftUI macOS shell
│   ├── App/                   # Application entry point
│   ├── Views/                 # SwiftUI views
│   ├── XPC/                   # XPC service definitions and transport
│   └── Keychain/              # Credential storage
├── src/
│   ├── __init__.py
│   ├── agent.py               # Backend entry point and REPL
│   ├── build_director.py      # Pipeline orchestration
│   ├── consensus.py           # ConsensusEngine
│   ├── providers.py           # LLM provider adapters
│   ├── build_ledger.py        # BuildLedger persistence
│   ├── github_tools.py        # GitHub API integration
│   ├── path_security.py       # Path validation
│   ├── cal/                   # Conversation Abstraction Layer
│   │   └── __init__.py
│   ├── trustflow/             # TrustFlow audit events
│   │   └── __init__.py
│   ├── vtz/                   # Virtual Trust Zone enforcement
│   │   └── __init__.py
│   ├── dtl/                   # Data Trust Labels
│   │   └── __init__.py
│   └── audit/                 # Append-only audit log
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_cal.py
    ├── test_trustflow.py
    ├── test_vtz.py
    ├── test_dtl.py
    ├── test_path_security.py
    ├── test_consensus.py
    ├── test_build_director.py
    └── test_build_ledger.py
