# CLAUDE.md - Forge Platform

Forge is a trust enforcement platform where every agent action is cryptographically identified, policy-gated, and audit-logged — it enforces identity (CTX-ID), zone boundaries (VTZ), data classification (DTL), and tamper-evident telemetry (TrustFlow) across endpoint, network, cloud, and AI runtime environments.

## Critical Rules - Read Before Writing Any Code

1. Validate CTX-ID first at every enforcement entry point and reject immediately on validation failure with no partial processing, no fallback, no retry.
2. Treat missing, expired, invalid, rotated, or unverifiable CTX-ID as `UNTRUSTED` and deny by default.
3. Check VTZ policy before executing any action, tool call, cross-boundary operation, or data movement; implicit cross-VTZ calls are denied.
4. Bind every agent session to exactly one VTZ at CTX-ID issuance and deny implicit cross-VTZ access.
5. Emit a synchronous TrustFlow event for every action outcome (`allow`, `restrict`, `block`) — async buffering is forbidden in the enforcement path; never silently skip emission failure.
6. Assign DTL labels at data ingestion; labels are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data is `CONFIDENTIAL` until explicitly reclassified.
7. Fail closed on all trust, identity, policy, cryptographic, and path-validation errors — reject the action, log the event, surface to the caller; never silently continue.
8. Never log or return secrets, keys, tokens, credentials, cleartext sensitive payloads, or HTTP response bodies in logs, error messages, audit records, or generated code.
9. All external input (documents, PR comments, CI output, XPC messages, user prompts, generated content) is untrusted — validate strictly before use; external document context goes in USER prompt, never SYSTEM prompt.
10. Never execute generated code or external content via `eval()`, `exec()`, dynamic interpretation, `subprocess` of generated artifacts, or `shell=True`.
11. Validate every file write path with `path_security.validate_write_path()` before performing the write — no exceptions.
12. Gates wait indefinitely for operator input — no auto-approve, ever.
13. If output contains `SECURITY_REFUSAL`, stop, gate, and log — never bypass the refusal by retrying, rephrasing, or provider fallback.

## Architecture Overview

Consensus Dev Agent is a two-process native macOS application: a Swift shell (UI, auth, Keychain, XPC) and a Python backend (consensus engine, build pipeline, GitHub integration). The 12 TRDs in `forge-docs/` are the source of truth — code MUST match them.

### Subsystem Map

| Directory | Component | Enforces | Must NOT Do |
|---|---|---|---|
| `src/cal/` | Conversation Abstraction Layer | CTX-ID validation at every entry point; action routing through VTZ policy; execution gating | Never process an action without validated CTX-ID; never execute before VTZ policy evaluation |
| `src/dtl/` | Data Trust Labels | Label assignment at ingestion; label inheritance on derivation; label verification at trust boundaries | Never strip or downgrade a label without audited policy authorization; never allow unlabeled outbound data without treating it as `CONFIDENTIAL` |
| `src/trustflow/` | TrustFlow Audit Stream | Synchronous emission of tamper-evident audit events for every action outcome with immutable audit fields | Never buffer asynchronously in the enforcement path; never skip or silently drop emission |
| `src/vtz/` | Virtual Trust Zones | Zone boundary enforcement; cross-zone authorization gating; session-to-VTZ binding | Never permit implicit cross-VTZ access; never allow mid-session policy mutation without re-authorization |
| `src/trustlock/` | TrustLock | CTX-ID validation against TrustLock public key; machine identity anchoring | Never accept software-only validation in place of TrustLock verification |
| `src/mcp/` | MCP Policy Engine | Policy decisions for tools, sessions, and boundaries | Never suggest policy when enforcement is required; never allow unevaluated policy pass-through |
| `src/rewind/` | Forge Rewind | State reconstruction and replay from append-only audit stream | Never mutate or delete audit records; never replay without full TrustFlow chain verification |

## CTX-ID Validation Contract

- Every public function in `src/cal/`, `src/vtz/`, `src/dtl/`, `src/mcp/` MUST accept a `ctx_id` parameter.
- Validation MUST verify: signature against TrustLock public key, expiry timestamp, VTZ binding, and revocation status.
- On failure: return `UNTRUSTED`, emit a `TrustFlow` event with `action: block`, and halt processing.

## VTZ Enforcement Contract

- A session is bound to exactly one VTZ at CTX-ID issuance.
- Cross-VTZ access requires explicit policy authorization checked via `src/mcp/`.
- Unauthorized cross-VTZ calls MUST be denied and logged as `TrustFlow` events with `action: block`.

## DTL Inheritance Contract

- Labels: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`.
- Derived data inherits `max(source_labels)`.
- Label downgrade requires audited policy authorization through `src/mcp/` and emits a `TrustFlow` event.
- Unlabeled data at any trust boundary MUST be treated as `CONFIDENTIAL`.

## TrustFlow Event Contract

- Every enforcement decision emits a TrustFlow event synchronously before returning.
- Required fields: `ctx_id`, `timestamp`, `vtz_id`, `action` (`allow` | `restrict` | `block`), `component`, `detail`.
- Events are append-only and immutable — no updates, no deletes.
- Emission failure MUST fail the enforcement action closed — never silently drop.

## File and Path Security

- All file writes MUST pass `path_security.validate_write_path()` before execution.
- Path traversal, symlink escape, and writes outside designated directories MUST be rejected and logged.

## Operator Gate Policy

- Gates wait indefinitely for operator input.
- No auto-approve, no timeout-based approval, no fallback approval — ever.

## Security Refusal Policy

- `SECURITY_REFUSAL` is terminal for the current action.
- Never retry, rephrase, use provider fallback, or attempt to bypass.
- Log the refusal as a `TrustFlow` event with `action: block` and surface to the operator.