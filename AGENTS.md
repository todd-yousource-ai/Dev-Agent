# AGENTS.md

Crafted Dev Agent is a native macOS AI coding agent built on Forge principles. Forge is the enforcement-first architecture and engineering contract: it enforces explicit trust, identity, policy, telemetry, audit, and fail-closed security behavior across the Swift shell and Python backend. The agent decomposes plain-language build intents into ordered pull requests, generates code via dual-LLM consensus, and enforces security, identity, and policy contracts at every stage.

## Critical Rules — Read Before Writing Any Code

1. Every enforcement entry point MUST validate CTX-ID FIRST — validation failure causes immediate rejection with zero partial processing.
2. VTZ policy MUST be checked BEFORE execution of any agent action, tool call, cross-boundary operation, or sensitive workflow step — implicit cross-VTZ access is denied.
3. Every action outcome (allow, restrict, block) MUST emit a synchronous TrustFlow event in the enforcement path containing `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash` — async buffering is forbidden.
4. Missing CTX-ID MUST be treated as `UNTRUSTED` — never infer identity, trust, or authorization from ambient context.
5. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance — cross-VTZ tool calls require explicit policy authorization.
6. CTX-ID tokens are IMMUTABLE once issued — rotation creates a new token and immediately invalidates the old one; expired CTX-IDs MUST be rejected.
7. DTL labels MUST be assigned at data ingestion and are immutable — derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as `CONFIDENTIAL`; label stripping without policy control and audit is forbidden.
8. All trust, identity, policy, cryptographic, credential, and generated-code safety failures MUST fail closed: reject the action, log the event, surface to caller — never silently continue.
9. Generated code is NEVER executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content.
10. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution — traversal attempts return a safe default.
11. All external input (documents, PR comments, CI output, XPC messages, retrieved context) is untrusted — validate strictly before use; context from external documents goes in the USER prompt, NEVER the SYSTEM prompt.
12. Gates wait indefinitely for operator input — no auto-approve ever; `SECURITY_REFUSAL` output is never bypassed by rephrasing — stop, gate, log.
13. Secrets, keys, tokens, and credentials MUST NEVER appear in logs, error messages, audit records, generated code, or cleartext payloads.
14. TrustFlow event emission failure is a WARN-level audit event that MUST be logged and surfaced — never a silent skip; `try/except/pass` is BANNED in enforcement code.

## Architecture Overview

Crafted Dev Agent is a two-process architecture: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus, pipeline, GitHub).

### Swift Shell

| Path | Enforces | Must NOT Do |
|---|---|---|
| `Crafted/` | Native macOS Swift/SwiftUI shell: UI, auth, Keychain access, XPC boundary handling | Never implement backend consensus, retrieval, or GitHub policy logic |
| `CraftedTests/` | XCTest regression coverage for TRD-owned shell behavior | Never replace runtime enforcement with test-only assumptions |

### Python Backend

| Path | Enforces | Must NOT Do |
|---|---|---|
| `src/agent.py` | Backend entry point and REPL; startup and orchestration entry behavior | Never bypass pipeline gates or call generation without required context and language |
| `src/build_director.py` | Pipeline orchestrator: stage order, confidence gate, `pr_type` routing, checkpoints, operator gating | Never re-run completed per-PR stages after crash recovery; never auto-approve gates |
| `src/consensus.py` | `ConsensusEngine`: parallel provider generation, Claude arbitration, self-correction, fix-loop strategy selection | Never use length-based arbitration; never omit `language` parameter |
| `src/providers.py` | Provider adapters for Claude and OpenAI: provider isolation, request shaping | Never leak credentials; never mix provider contracts; never weaken system prompt boundaries |
| `src/build_ledger.py` | `BuildLedger`: multi-PR state persistence, checkpoint writes, crash recovery reads | Never allow partial writes to corrupt ledger state; never skip checkpoint validation on read |

### Enforcement Subsystems

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point, VTZ policy check before execution, TrustFlow emission for every outcome | Never process an action without validating CTX-ID first; never skip TrustFlow emission |
| **DTL** (Data Trust Labels) | `src/dtl/` | Label assignment at ingestion, label inheritance (highest classification), label verification before trust boundary crossing | Never strip labels without audit; never allow unlabeled data to pass as unclassified |
| **TrustFlow** | `src/trustflow/` | Append-only audit stream with globally unique `event_id` per event; synchronous emission on every enforcement outcome; wire format: `event_id` (UUID), `session_id` (UUID), `ctx_id` (string), `ts` (ISO-8601), `event_type` (enum: `ALLOW`, `RESTRICT`, `BLOCK`, `GATE`, `SECURITY_REFUSAL`), `payload_hash` (SHA-256 hex) | Never emit asynchronously; never drop events; never omit required fields; never use `try/except/pass` around emission |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Zone boundary enforcement, one-session-one-VTZ binding at CTX-ID issuance, cross-VTZ policy authorization gate | Never allow implicit cross-VTZ access; never rebind a session to a different VTZ without new CTX-ID issuance |
| **Path Security** | `src/path_security.py` | Write-path validation via `validate_write_path()`; traversal detection and safe-default return | Never allow unvalidated file writes; never trust caller-supplied paths without validation |

## Naming Conventions and Identifier Registry

### Canonical Names

All Forge subsystem names, token names, and event types MUST use the exact canonical forms listed below. Aliases, abbreviations, and alternative spellings are forbidden in code, logs, config, documentation, and generated output.

| Canonical Name | Type | Description |
|---|---|---|
| `CTX-ID` | Identity token | Context identity token; immutable once issued; validated first at every enforcement entry point |
| `VTZ` | Trust boundary | Virtual Trust Zone; one session binds to exactly one VTZ at CTX-ID issuance |
| `TrustFlow` | Audit subsystem | Append-only synchronous audit event stream |
| `DTL` | Data classification | Data Trust Labels; assigned at ingestion, immutable, inherited at highest classification |
| `CAL` | Abstraction layer | Conversation Abstraction Layer; mediates all enforcement entry points |
| `BuildLedger` | State store | Multi-PR pipeline state persistence and crash-recovery checkpoint store |
| `ConsensusEngine` | Generation subsystem | Dual-LLM parallel generation with Claude arbitration |
| `SECURITY_REFUSAL` | Output type | Terminal refusal output; never bypassable by rephrasing |

### TrustFlow Event Type Enum

| Value | Meaning |
|---|---|
| `ALLOW` | Action permitted by policy |
| `RESTRICT` | Action permitted with constraints |
| `BLOCK` | Action denied by policy |
| `GATE` | Action held pending operator approval |
| `SECURITY_REFUSAL` | Action permanently refused on security grounds |

### TrustFlow Event Wire Format

| Field | Type | Constraint |
|---|---|---|
| `event_id` | UUID v4 | Globally unique; generated at emission time |
| `session_id` | UUID v4 | Bound to the active agent session |
| `ctx_id` | string | The validated CTX-ID for the current context |
| `ts` | ISO-8601 string | UTC timestamp at emission time |
| `event_type` | enum string | One of: `ALLOW`, `RESTRICT`, `BLOCK`, `GATE`, `SECURITY_REFUSAL` |
| `payload_hash` | string | SHA-256 hex digest of the action payload |

### DTL Classification Levels (Ascending)

| Label | Meaning |
|---|---|
| `PUBLIC` | No restrictions |
| `INTERNAL` | Organization-internal |
| `CONFIDENTIAL` | Default for unlabeled data; restricted access |
| `RESTRICTED` | Highest classification; strictest controls |

### Identifier Format Rules

- `CTX-ID` tokens: opaque strings; format is issuer-defined; MUST be validated, never parsed for semantics.
- `event_id` and `session_id`: UUID v4, lowercase hex with hyphens (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`).
- `payload_hash`: lowercase hex SHA-256 (64 characters).
- `ts`: ISO-8601 with timezone designator (`2025-01-15T09:30:00Z`); UTC MUST be used.
- DTL labels: uppercase exact strings as listed above; no aliases.
- TrustFlow event types: uppercase exact strings as listed above; no aliases.

## Code Hygiene

- `try/except/pass` is BANNED in any enforcement, audit, or security code path.
- Every `except` block MUST log, surface, or re-raise — never silently swallow.
- All enforcement functions MUST be synchronous in the enforcement path; background/async emission of TrustFlow events is forbidden.
- All tests MUST assert TrustFlow event emission for the specific action under test.
- All new subsystems MUST register their canonical names in this document before merge.