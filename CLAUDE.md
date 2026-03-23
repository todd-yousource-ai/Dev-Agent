# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographically verified identity (CTX-ID), constrains execution within Virtual Trust Zones (VTZ), labels all data with immutable Data Trust Labels (DTL), and emits a complete TrustFlow audit stream — failing closed on any violation.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST — before any other processing occurs; validation failure means immediate rejection with zero partial execution.
2. CTX-ID tokens are IMMUTABLE after issuance; rotation creates a new token and invalidates the old one immediately; expired or missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from context.
3. Every agent action MUST be checked against VTZ policy BEFORE execution; VTZ boundaries are structural, not advisory — application code cannot bypass enforcement; cross-VTZ tool calls require explicit policy authorization or they are denied.
4. Every action outcome (allow, restrict, block) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is forbidden; failed emission is a WARN-level audit event, never a silent skip.
5. All trust, identity, policy, and cryptographic failures MUST fail CLOSED: reject the action, log the event, surface to the caller — never silently continue; `try/except/pass` is BANNED in enforcement code.
6. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads; all secrets MUST be protected in memory, at rest, and in transit.
7. DTL labels are assigned at data ingestion and are IMMUTABLE; derived data inherits the HIGHEST classification of any source; unlabeled data MUST be treated as CONFIDENTIAL until explicitly reclassified.
8. Generated code is NEVER executed by the agent — no `eval`, no `exec`, no `subprocess` of generated content.
9. All external input (documents, PR comments, CI output, XPC messages) is UNTRUSTED and MUST be validated strictly; context from external documents goes in the USER prompt, never the SYSTEM prompt.
10. Gates wait indefinitely for operator input — no auto-approve ever; SECURITY_REFUSAL output is never bypassed by rephrasing — stop, gate, log.
11. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution; XPC unknown message types are discarded and logged, never raised as exceptions.
12. Build memory and build rules are NEVER cleared automatically — they are persistent learning systems; per-PR stage checkpoints prevent re-running completed work after a crash.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → DTL label verification (if data crosses boundary) → TrustFlow event emission → Audit record write**.

| Subsystem | Path | Enforces | Must NOT Do |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | Processes agent actions; calls CTX-ID validation first, VTZ policy second, emits TrustFlow on every outcome | Must NOT execute any action before CTX-ID validation completes; must NOT swallow VTZ denials |
| **DTL** (Data Trust Labels) | `src/dtl/` | Assigns immutable classification labels at ingestion; enforces label inheritance on derived data; verifies labels at trust boundaries | Must NOT allow label modification after assignment; must NOT pass unlabeled data across trust boundaries without treating it as CONFIDENTIAL |
| **TrustFlow** | `src/trustflow/` | Emits synchronous audit events for every enforcement decision with `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` | Must NOT buffer events asynchronously; must NOT omit events on failure — log the emission failure instead |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Binds each agent session to exactly one VTZ at CTX-ID issuance; enforces structural boundaries on all tool calls | Must NOT allow cross-VTZ calls without explicit policy authorization; must NOT apply policy changes mid-session |
| **TrustLock** | `src/trustlock/` | Provides TPM-anchored cryptographic machine identity; validates CTX-ID against TrustLock public key | Must NOT accept software-only validation; must NOT degrade to unsigned identity |
| **MCP Policy Engine** | `src/mcp/` | Evaluates and enforces agent action policies | Must NOT suggest policy — must enforce it; must NOT allow bypass from application code |
| **Rewind** | `src/rewind/` | Replays enforcement decisions from audit stream alone | Must NOT depend on external state for replay; must NOT modify audit records |
| **Connector SDK** | `sdk/connector/` | Provides integration interface for external systems | Must NOT trust connector input without validation; must NOT expose internal enforcement state |
| **Consensus Engine** | `src/consensus.py` | Runs dual-LLM generation with Claude arbitration; routes by `language` parameter | Must NOT use length-based fix arbitration — use `_score_fix()` |
| **Build Director** | `src/build_director.py` | Orchestrates build pipeline, confidence gates, PR-type routing | Must NOT auto-approve gates; must NOT skip stage checkpoints |
| **GitHub Tools** | `src/github_tools.py` | Manages GitHub operations, webhook receiving | Must NOT expose tokens in logs; must NOT trust webhook payloads without validation |
| **Build Ledger** | `src/build_ledger.py` | Tracks build state and stage checkpoints | Must NOT clear state automatically |
| **Tests** | `tests/<subsystem>/` | Mirrors `src/` structure exactly | Must NOT mock enforcement decisions — may mock external calls but logic must run |

## Interface Contracts - Mandatory Implementation Rules

### CTX-ID Contract
- Tokens are **IMMUTABLE** after issuance — no field modification.
- Rotation creates a new token; old token is invalidated **immediately**.
- Expired CTX-ID MUST be rejected; clock skew tolerance is defined per deployment.
- CTX-ID MUST be validated against **TrustLock public key** — software-only validation is rejected.
- Missing CTX-ID MUST be treated as **UNTRUSTED**.

### CAL Enforcement Contract
- Every entry point processing an agent action MUST call CTX-ID validation **FIRST**.
- CTX-ID validation failure → immediate rejection, no partial processing.
- Every action MUST be checked against VTZ policy **BEFORE** execution.
- VTZ denial MUST produce a `VTZEnforcementDecision` record with `verdict=block`.
- Every action outcome MUST emit a TrustFlow event.
- TrustFlow emission failure MUST NOT silently continue — log and surface.

### TrustFlow Emission Contract
- Required fields: `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`.
- `event_id`: globally unique via CSPRNG (not sequential).
- `ts`: UTC Unix timestamp, **millisecond precision**.
- `payload_hash`: SHA-256 of the serialized action payload.
- Emission MUST be **synchronous** in the enforcement path.
- Failed emission → WARN-level audit event, not silent skip.

### VTZ Enforcement Contract
- Each agent session bound to **exactly one** VTZ at CTX-ID issuance.
- Cross-VTZ tool calls require **explicit** policy authorization — implicit is denied.
- VTZ boundaries are **structural** — application code cannot bypass.
- Policy changes take effect at **next CTX-ID issuance**, not mid-session.

### DTL Label Contract
- Labels assigned at **data ingestion**, immutable thereafter.
- Derived data inherits the **HIGHEST** classification of any source.
- Unlabeled data → **CONFIDENTIAL** until explicitly reclassified.
- Label verification MUST occur **before** any data crosses a trust boundary.
- Label stripping is a security event — MUST be audited and policy-controlled.

### Audit Contract
- Every security-relevant action MUST generate an audit record **BEFORE** execution.
- Audit records are **APPEND-ONLY** — no modification or deletion.
- Audit failures are **NON-FATAL** to agent operation but MUST be surfaced immediately.
- Audit records MUST NOT contain secrets, keys, tokens, or cleartext sensitive data.
- Replay MUST be possible from the audit stream alone (no external state required).

### Consensus Engine Contract
- Always pass `language` parameter: `"python"` | `"swift"` | `"go"` | `"typescript"` | `"rust"`.
- `language="swift"` → `SWIFT_GENERATION_SYSTEM` + `SWIFT_UI_ADDENDUM` (when UI keywords detected).
- `language="python"` → `GENERATION_SYSTEM` (security-focused Python rules).
- Fix arbitration uses `_score_fix()` based on assertion token overlap — **NEVER** `max(..., key=len)`.
- Fix loop strategy via `_choose_strategy(failure_type, attempt, records)` — not a static lookup table.

### XPC Wire Contract
- Line-delimited JSON, nonce-authenticated, max **16 MB** per message.
- `ready`: `{ agent_version, min_swift_version, capabilities[], doc_store_status }`
- `build_card`: `{ card_type, stage, content, progress }` — streamed to `BuildStreamView`.
- `gate_card`: `{ gate_type, options[], description }` — blocks until operator responds.
- `credentials`: `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`
- `doc_status`: `{ doc_id, doc_name, status, chunk_count, embedded_count }`
- Unknown message types: **discard and log** — never raise as exceptions.

## Wire Formats and Schemas

### TrustFlow Event Schema
```json
{
  "event_id": "string (CSPRNG-generated, globally unique)",
  "session_id": "string",
  "ctx_id": "string (validated CTX-ID token reference)",
  "ts": "integer (UTC Unix timestamp, millisecond precision)",
  "event_type": "string (allow | restrict | block | audit)",
  "payload_hash": "string (SHA-256 hex of serialized action payload)"
}
```

### VTZEnforcementDecision Schema
```json
{
  "verdict": "allow | restrict | block",
  "ctx_id": "string",
  "vtz_id": "string",
  "policy_ref": "string",
  "reason": "string (no secrets)",
  "ts": "integer (UTC Unix ms)"
}
```

### XPC Message Schemas
See Interface Contracts above. All XPC messages are line-delimited JSON, nonce-authenticated. Maximum payload: 16 MB.

### Keychain Item Schema (KeychainKit)
```
kSecClass:            kSecClassGenericPassword
kSecAttrService:      "ai.yousource.crafted.<service_identifier>"
kSecAttrAccount:      "<credential_key>"
kSecValueData:        <encrypted bytes>
kSecAttrAccessible:   kSecAttrAccessibleWhenUnlockedThisDeviceOnly
kSecAttrAccessControl: biometry + device passcode (SecAccessControlCreateFlags)
```

Note: Additional TRD-specific schemas (beyond TRD-1) are not yet loaded. Add them to this section as TRDs are integrated.

## Error Handling Rules

### Mandatory Behavior by Failure Type

| Failure Type | Action | Log Level | Continue? |
|---|---|---|---|
| CTX-ID validation failure | Reject immediately, zero partial processing | ERROR | NO — fail closed |
| CTX-ID expired | Reject, require re-issuance | ERROR | NO — fail closed |
| CTX-ID missing | Treat as UNTRUSTED, reject | ERROR | NO — fail closed |
| VTZ policy denial | Block action, produce `VTZEnforcementDecision(verdict=block)` | ERROR | NO — fail closed |
| Cross-VTZ call without explicit auth | Deny | ERROR | NO — fail closed |
| TrustFlow emission failure | Log WARN, surface to caller | WARN | YES — but audit the failure |
| Cryptographic operation failure | Reject, log, never degrade to insecure | ERROR | NO — fail closed |
| DTL label missing | Treat data as CONFIDENTIAL | WARN | YES — with CONFIDENTIAL enforcement |
| DTL label verification failure at boundary | Block data transfer | ERROR | NO — fail closed |
| Audit write failure | Surface immediately, do not block agent | WARN | YES — but surface |
| XPC unknown message type | Discard and log | WARN | YES — discard silently |
| SECURITY_REFUSAL from LLM | Stop, gate, log — never rephrase to bypass | ERROR | NO — gate for operator |
| Keychain read/write failure | Fail closed, surface to caller, never return stale/empty secret | ERROR | NO — fail closed |
| Path validation failure | Reject write operation | ERROR | NO — fail closed |

### Banned Patterns

```python
# BANNED — swallowed exception in enforcement path
try:
    enforce_policy(action)
except Exception:
    pass  # NEVER

# BANNED — silent continue on auth failure
if not validate_ctx_id(token):
    logger.debug("invalid token")
    # missing: return / raise — MUST reject

# BANNED — length-based fix arbitration
winner = max(claude_fix, openai_fix, key=len)  # Use _score_fix()

# BANNED — eval/exec of generated code
eval(generated_code)      # NEVER
exec(generated_code)      # NEVER
subprocess.run(generated) # NEVER

# BANNED — secrets in error messages
raise AuthError(f"Token {token} expired")  # Exposes token
# Correct:
raise AuthError(f"CTX-ID expired for session {session_id}")
```

### Required Error Structure
All errors MUST include: `component`, `operation`, `failure_reason`, `ctx_id` (if available).
All errors MUST NOT include: keys, tokens, secrets, or cleartext payloads.

## Testing Requirements

- **90% minimum coverage** for all enforcement paths (CTX-ID, VTZ, TrustFlow, DTL, audit).
- Every enforcement path MUST have at least **one negative test** (what happens on rejection).
- Every cryptographic operation MUST have a test with **invalid and expired** material.
- Every TrustFlow emission MUST be tested for **both success and failure** paths.
- Tests MUST NOT mock the enforcement decision — they may mock external calls but the enforcement logic MUST run.
- All parsing, policy, trust, and cryptographic logic MUST be tested against **malformed inputs**.
- **Regression tests** MUST be added for every material bug.
- **Benchmark tests** MUST exist for: network paths, crypto operations, policy evaluation, telemetry emission.
- **Fuzz testing** MUST be used where inputs are complex, attacker-controlled, or parser-driven (XPC messages, document import, webhook payloads).
- Run existing tests before making changes: `cd src && pytest ../tests/ -v --tb=short`

### KeychainKit-Specific Testing
- Test Keychain write → read round-trip with valid credentials.
- Test read of nonexistent key → must return explicit error, not empty/nil.
- Test write with invalid access control → must fail closed.
- Test behavior when Keychain is locked (biometry not satisfied) → must fail closed, never return stale data.
- Test concurrent access to the same Keychain item.
- Test migration path if `kSecAttrService` format changes.

## File Naming and Code Conventions

### Directory Structure
```
src/cal/           — Conversation Abstraction Layer components
src/dtl/           — Data Trust Label components
src/trustflow/     — TrustFlow audit stream components
src/vtz/           — Virtual Trust Zone enforcement
src/trustlock/     — Cryptographic machine identity (TPM-anchored)
src/mcp/           — MCP Policy Engine
src/rewind/        — Forge Rewind replay engine
sdk/connector/     — Forge Connector SDK
tests/<subsystem>/ — Tests mirror src/ structure exactly
```

### Python Backend Files
```
src/consensus.py       — ConsensusEngine, GENERATION_SYSTEM, SWIFT_GENERATION_SYSTEM + UI_ADDENDUM
src/build_director.py  — BuildPipeline orchestration, confidence gate, pr_type routing
src/github_tools.py    — GitHubTool, WebhookReceiver
src/build_ledger.py    —