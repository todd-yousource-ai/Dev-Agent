# AGENTS.md - Forge Platform

Forge is a native macOS AI coding agent platform that enforces cryptographic machine identity, trust-zone–scoped policy, and auditable action streams across every agent operation — rejecting anything that cannot be verified.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST call CTX-ID validation FIRST; validation failure MUST immediately reject the request — no partial processing, no fallback.
2. Every action outcome (allow, restrict, block) MUST emit a TrustFlow event synchronously in the enforcement path — async buffering is forbidden.
3. VTZ policy MUST be checked BEFORE execution of any agent action; cross-VTZ tool calls without explicit policy authorization are denied.
4. DTL labels are assigned at data ingestion and are immutable; derived data inherits the HIGHEST classification of any source; unlabeled data is CONFIDENTIAL.
5. Missing CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from session context, process state, or caller location.
6. All trust, identity, policy, authentication, and cryptographic failures MUST fail closed: reject the action, log the event, surface to the caller — never silently continue, never degrade into permissive behavior.
7. Secrets, keys, tokens, and credentials MUST never appear in logs, error messages, generated code, or cleartext payloads.
8. Generated code is never executed by the agent — no `eval`, no `exec`, no subprocess of generated content, under any circumstances.
9. Gates wait indefinitely for operator input — no auto-approve ever. `SECURITY_REFUSAL` output is terminal and is never bypassed by rephrasing.
10. All file writes MUST be path-validated via `path_security.validate_write_path()` before execution.
11. Context from external documents goes in the USER prompt — never the SYSTEM prompt.
12. Build memory and build rules are never cleared automatically — they are persistent learning systems; per-PR stage checkpoints prevent re-running completed work after a crash.
13. XPC unknown message types are discarded and logged — never raised as exceptions; XPC wire format is line-delimited JSON, nonce-authenticated, max 16 MB per message.
14. Validate all external input strictly — documents, PR comments, CI output, XPC messages, and filesystem paths — before use.
15. DTL labels MUST be verified before any trust-boundary crossing; data with stripped or downgraded labels MUST NOT cross trust boundaries without audited policy authorization.

## Architecture Overview

Enforcement order: **CTX-ID validation → VTZ policy check → action execution → TrustFlow emission → DTL label verification on output**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; routes agent actions through policy; binds actions to policy context | Never process an action without validated CTX-ID; never execute agent actions before identity and policy checks |
| **DTL** (Data Trust Labels) | `src/dtl/` | Immutable classification labels on all data at ingestion; label inheritance (highest classification); verification before trust-boundary crossing | Never strip or downgrade a label without audited policy authorization; never permit unlabeled or stripped data to cross trust boundaries unnoticed |
| **TrustFlow** | `src/trustflow/` | Append-only audit event stream with globally unique event IDs; each event includes `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, and `payload_hash` | Never buffer asynchronously in the enforcement path; never silently skip emission or drop failures |
| **VTZ** (Virtual Trust Zones) | `src/vtz/` | Structural session boundaries; one VTZ per session at CTX-ID issuance; policy evaluated before execution | Never allow implicit cross-VTZ access; never apply policy changes mid-session |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity and CTX-ID validation rooted in TrustLock public-key verification; hardware-backed identity material | Never accept software-only identity validation; never issue CTX-ID without verified machine identity |
| **MCP** (MCP Policy Engine) | `src/mcp/` | Explicit policy decisions for all actions and cross-boundary operations; policy resolution is authoritative | Never provide advisory-only outcomes; never allow action execution without a resolved policy decision |

## TrustFlow Event Schema

Every TrustFlow event MUST contain these fields:

| Field | Type | Description |
|---|---|---|
| `event_id` | `String` (UUID) | Globally unique identifier for this event |
| `session_id` | `String` (UUID) | Session in which the event occurred |
| `ctx_id` | `String` | Validated CTX-ID of the actor |
| `ts` | `String` (ISO 8601) | Timestamp of event emission |
| `event_type` | `String` (enum: `allow`, `restrict`, `block`, `error`) | Outcome classification |
| `payload_hash` | `String` (SHA-256) | Integrity hash of the event payload |

## XPC Wire Format

- Line-delimited JSON
- Nonce-authenticated per message
- Maximum 16 MB per message
- Unknown message types: discard and log, never raise exceptions

## Swift Package Workspace — Eight Module Targets

The workspace is organized as a single Swift package with eight module targets corresponding to the core subsystems and shared infrastructure:


Package.swift
Sources/
  ForgeCore/           # Shared types, CTX-ID types, error types, DTL label enums
  ForgeCAL/            # Conversation Abstraction Layer enforcement
  ForgeDTL/            # Data Trust Label assignment, inheritance, verification
  ForgeTrustFlow/      # Synchronous audit event emission
  ForgeVTZ/            # Virtual Trust Zone boundary enforcement
  ForgeTrustLock/      # Cryptographic machine identity, CTX-ID validation
  ForgeMCP/            # MCP Policy Engine resolution
  ForgeXPC/            # XPC transport: line-delimited JSON, nonce auth, message validation
Tests/
  ForgeCoreTests/
  ForgeCALTests/
  ForgeDTLTests/
  ForgeTrustFlowTests/
  ForgeVTZTests/
  ForgeTrustLockTests/
  ForgeMCPTests/
  ForgeXPCTests/


### Module Dependency Rules

- **ForgeCore** has no internal dependencies — it is the leaf.
- **ForgeCAL** depends on ForgeCore, ForgeVTZ, ForgeTrustFlow, ForgeTrustLock.
- **ForgeDTL** depends on ForgeCore, ForgeTrustFlow.
- **ForgeTrustFlow** depends on ForgeCore only.
- **ForgeVTZ** depends on ForgeCore, ForgeMCP.
- **ForgeTrustLock** depends on ForgeCore only.
- **ForgeMCP** depends on ForgeCore only.
- **ForgeXPC** depends on ForgeCore, ForgeTrustFlow.
- No circular dependencies are permitted.
- Every module MUST enforce the critical rules within its domain — enforcement is never deferred to a caller.