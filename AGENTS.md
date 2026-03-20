# AGENTS.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), enforces policy boundaries (VTZ), labels all data at ingestion (DTL), and emits an immutable audit stream (TrustFlow) — all enforced locally on macOS through a two-process architecture (Swift shell + Python backend) connected via XPC.

## Critical Rules - Read Before Writing Any Code

1. **Fail closed on all auth, crypto, identity, and policy errors** — never degrade silently, never fall through to a permissive default; reject the action, log the event, and surface the failure to the caller.
2. **CTX-ID must be validated FIRST at every enforcement entry point** — validation failure means immediate rejection with no partial processing; missing CTX-ID means UNTRUSTED, never infer identity from context, session state, or prior requests.
3. **TrustFlow events must be emitted synchronously in the enforcement path for every action outcome** (`allow`, `restrict`, `block`) — async buffering is not permitted; failed emission is a WARN-level audit event, never a silent skip.
4. **VTZ policy must be checked BEFORE execution of any agent action** — cross-VTZ tool calls require explicit policy authorization; implicit access is denied; VTZ boundaries are structural, not advisory.
5. **DTL labels are assigned at data ingestion and are immutable** — derived data inherits the HIGHEST classification of any source; unlabeled data is CONFIDENTIAL until explicitly reclassified; label verification occurs before any data crosses a trust boundary.
6. **Secrets, keys, tokens, and credentials must never appear in logs, error messages, audit records, generated code, prompts, or environment variables** — Python receives credentials only via XPC `credentials` message and holds them in memory only.
7. **Generated code is never executed by the agent** — no `eval()`, no `exec()`, no `subprocess` of generated content, no `shell=True` in subprocess calls.
8. **All external input (documents, PR comments, CI output, XPC messages, filesystem paths) is untrusted** — must be validated strictly; external document context goes in the USER prompt, never the SYSTEM prompt; all loaded document chunks must pass injection scanning.
9. **Gates wait indefinitely for operator input** — no auto-approve, no auto-merge, ever; `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
10. **All file writes must pass `path_security.validate_write_path()` before execution** — no exceptions, no bypass paths.
11. **Audit records are append-only, generated BEFORE execution, and must never contain secrets** — replay must be possible from the audit stream alone with no external state required.
12. **XPC unknown message types are discarded and logged** — never raised as exceptions; XPC wire format is line-delimited JSON, nonce-authenticated, max 16MB per message.

## Architecture Overview

### Two-Process Architecture (No Exceptions)

| Process | Owns | Must NEVER |
|---------|------|------------|
| **Swift Shell** (macOS app) | SwiftUI (Navigator + BuildStream + ContextPanel), Touch ID biometric gate, Keychain credential storage, XPC listener, process lifecycle management | Import Python modules, execute agent logic, access GitHub API directly, mutate audit records |
| **Python Backend** (child process) | Consensus pipeline, CAL enforcement, VTZ policy evaluation, DTL labeling, TrustFlow emission, GitHub integration, ledger management, document processing, MCP policy engine, Forge Rewind replay | Access Keychain directly, display UI, call Touch ID, spawn additional child processes, hold credentials except via XPC `credentials` message |

### Canonical Directory Layout


forge/
├── CLAUDE.md                  # This file — platform rules and architecture
├── swift/                     # Swift Shell process
│   ├── ForgeApp/              # SwiftUI application entry point
│   │   ├── Navigator/         # Navigator panel UI
│   │   ├── BuildStream/       # BuildStream panel UI
│   │   ├── ContextPanel/      # Context panel UI
│   │   └── XPC/               # XPC listener and message dispatch
│   ├── Auth/                  # Touch ID biometric gate and Keychain access
│   └── Lifecycle/             # Process lifecycle and child process management
├── src/                       # Python Backend process
│   ├── cal/                   # Conversation Abstraction Layer enforcement entry points
│   │   └── Must validate CTX-ID FIRST; must NOT process agent actions before identity validation
│   ├── vtz/                   # Virtual Trust Zone policy enforcement
│   │   └── Must bind each session to exactly one VTZ; must NOT allow implicit cross-VTZ tool calls
│   ├── dtl/                   # Data Trust Label assignment and verification
│   │   └── Must assign labels at ingestion; must NOT permit post-ingestion mutation or unlabeled boundary crossing
│   ├── trustflow/             # TrustFlow audit stream emission
│   │   └── Must synchronously emit enforcement-path events; must NOT async-buffer or silently drop events
│   ├── trustlock/             # Cryptographic machine identity and TrustLock-backed CTX-ID validation
│   │   └── Must validate against TrustLock public key; must NOT accept software-only validation
│   ├── mcp/                   # MCP Policy Engine
│   │   └── Must evaluate explicit policy decisions; must NOT act as advisory-only logic in enforcement paths
│   ├── rewind/                # Forge Rewind replay engine
│   │   └── Must support replay from append-only audit records; must NOT require hidden external state
│   ├── consensus/             # Consensus pipeline orchestration
│   ├── github/                # GitHub API integration (tokens received via XPC only)
│   ├── ledger/                # Immutable ledger management
│   ├── documents/             # Document ingestion, chunking, and injection scanning
│   └── path_security/         # Path resolution and write-path validation utilities
│       ├── validate_write_path()   # Every file write must call this BEFORE execution
│       ├── resolve_canonical()     # Resolve symlinks and normalize to absolute path
│       └── check_boundary()        # Verify path is within allowed VTZ workspace boundary
├── tests/                     # Test suites
│   ├── unit/                  # Unit tests per module
│   ├── integration/           # Cross-module integration tests
│   └── audit/                 # Audit replay verification tests
├── config/                    # Policy and configuration files
│   ├── vtz_policies/          # VTZ boundary and authorization policy definitions
│   ├── dtl_schemas/           # DTL classification schemas
│   └── trustflow_schemas/     # TrustFlow event schemas
└── ledger/                    # Append-only audit ledger storage (immutable at rest)


### Path Resolution Utilities

All path operations in `src/path_security/` must enforce the following:

- `resolve_canonical(path: str) -> str` — Resolve all symlinks, normalize to absolute path, reject paths containing `..` traversal after resolution.
- `validate_write_path(path: str, vtz_id: str) -> bool` — Call `resolve_canonical()`, verify the resolved path is within the VTZ workspace boundary for the given `vtz_id`, reject writes outside the boundary. Must be called before every file write with no exceptions.
- `check_boundary(path: str, vtz_id: str) -> bool` — Verify the canonical path falls within the allowed workspace root for the specified VTZ. Cross-VTZ paths require explicit policy authorization verified via `src/vtz/`.

### XPC Wire Format

- Line-delimited JSON, one message per line
- Every message must include a `nonce` field for authentication
- Maximum message size: 16 MB
- Unknown message types: discard and log, never raise exceptions
- Credential delivery: Swift sends `{"type": "credentials", "nonce": "...", "payload": {...}}` — Python holds credentials in memory only, never writes to disk

### Enforcement Order (Every Request)

1. **CTX-ID validation** — reject immediately if invalid or missing
2. **VTZ policy check** — reject if action is not authorized for this VTZ
3. **DTL label verification** — reject if data crosses trust boundary without valid label
4. **TrustFlow audit event emission** — emit synchronously before execution
5. **Action execution** — only after steps 1–4 pass
6. **TrustFlow outcome event emission** — emit result synchronously after execution

Every step must fail closed. No step may be skipped. No step may proceed if a prior step failed.