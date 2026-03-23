# CLAUDE.md - Forge Platform

Forge is a trust-enforcement platform for AI agent operations that binds every agent action to a cryptographic identity (CTX-ID), confines it within a Virtual Trust Zone (VTZ), labels all data via DTL classification, and emits an append-only TrustFlow audit stream — enforcing policy before execution, never after.

## Critical Rules - Read Before Writing Any Code

1. Every enforcement entry point MUST validate CTX-ID **first** — before any other processing occurs; validation failure means immediate rejection with no partial processing.
2. Every agent action outcome (allow, restrict, block) MUST emit a synchronous TrustFlow event containing `event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash` — async buffering is forbidden in the enforcement path.
3. VTZ policy MUST be checked **before** execution of any action; cross-VTZ tool calls require explicit policy authorization — implicit access is denied.
4. All trust, identity, policy, and cryptographic failures MUST fail **closed**: reject the action, log the event, surface to caller — never silently continue or degrade into permissive behavior.
5. Never hardcode secrets, tokens, credentials, or cryptographic material; secrets MUST NOT appear in logs, error messages, audit records, or generated code.
6. All external input (documents, PR comments, CI output, XPC messages, file paths) is **untrusted** — validate strictly before use; all parsing MUST be bounds-checked and fail safely.
7. Generated code is never executed by the agent — no `eval`, no `exec`, no subprocess of generated content.
8. DTL labels are assigned at data ingestion and are **immutable**; derived data inherits the **highest** classification of any source; unlabeled data MUST be treated as `CONFIDENTIAL`.
9. CTX-ID tokens are **immutable** once issued; expired CTX-ID MUST be rejected; missing CTX-ID MUST be treated as `UNTRUSTED` — never infer identity from context, session state, or transport metadata.
10. Gates wait indefinitely for operator input — no auto-approve, no auto-bypass, ever.
11. Build memory and build rules are never cleared automatically — they are persistent learning systems.
12. `try/except/pass` (or Swift `try?` with discarded result) is **banned** in any enforcement path — every error MUST include `component`, `operation`, `failure_reason`, and `ctx_id` if available.
13. Every file write MUST be validated with `path_security.validate_write_path()` before execution — reject path traversal, symlink escape, and out-of-root writes.
14. Every agent session MUST be bound to exactly one VTZ at CTX-ID issuance — this binding is immutable for the session lifetime.

## Architecture Overview

Enforcement order for every agent action: **CTX-ID validation → VTZ policy check → Action execution → TrustFlow emission → DTL label verification on output**.

| Subsystem | Path | Enforces | Must NOT |
|---|---|---|---|
| **CAL** (Conversation Abstraction Layer) | `src/cal/` | CTX-ID validation at every entry point; orchestrates the enforcement sequence | Never process an action without CTX-ID validation first |
| **VTZ** (Virtual Trust Zone) | `src/vtz/` | Structural session boundaries; policy authorization for cross-zone calls; binds sessions to exactly one VTZ | Never treat boundaries as advisory; never allow bypass by application code; never allow implicit cross-VTZ access |
| **TrustFlow** | `src/trustflow/` | Append-only audit event emission for every action outcome; synchronous recording with required fields (`event_id`, `session_id`, `ctx_id`, `ts`, `event_type`, `payload_hash`) | Never silently buffer, drop, mutate, or omit failed emissions; never emit asynchronously in the enforcement path |
| **DTL** (Data Trust Labeling) | `src/dtl/` | Classification labels assigned at ingestion; immutable labels; highest-label inheritance for derived data | Never permit unlabeled cross-boundary data transfer without treating as `CONFIDENTIAL`; never downgrade or remove labels |
| **TrustLock** | `src/trustlock/` | Cryptographic machine identity; CTX-ID issuance and validation anchored to TrustLock public key material; token immutability and expiration enforcement | Never issue a CTX-ID without cryptographic binding; never accept an expired or malformed token; never infer identity without validated CTX-ID |

## Swift Package Workspace Structure

The Forge workspace is organized as a Swift package with eight module targets:


forge/
├── Package.swift
├── CLAUDE.md
├── Sources/
│   ├── ForgeCore/          # Shared types, error definitions, CTX-ID types, DTL label enums
│   ├── ForgeCAL/           # Conversation Abstraction Layer — enforcement entry points
│   ├── ForgeVTZ/           # Virtual Trust Zone — session binding and policy evaluation
│   ├── ForgeTrustFlow/     # Append-only audit stream — synchronous event emission
│   ├── ForgeDTL/           # Data Trust Labeling — ingestion labels, inheritance, verification
│   ├── ForgeTrustLock/     # Cryptographic identity — CTX-ID issuance, validation, key material
│   ├── ForgePolicy/        # Policy engine — rule evaluation, cross-VTZ authorization decisions
│   └── ForgeGate/          # Operator gate — indefinite wait for human approval, no auto-approve
└── Tests/
    ├── ForgeCoreTests/
    ├── ForgeCALTests/
    ├── ForgeVTZTests/
    ├── ForgeTrustFlowTests/
    ├── ForgeDTLTests/
    ├── ForgeTrustLockTests/
    ├── ForgePolicyTests/
    └── ForgeGateTests/


### Module Dependency Graph

- **ForgeCore** — no internal dependencies; all other modules depend on ForgeCore
- **ForgeTrustLock** → ForgeCore
- **ForgeDTL** → ForgeCore
- **ForgeTrustFlow** → ForgeCore
- **ForgePolicy** → ForgeCore, ForgeVTZ
- **ForgeVTZ** → ForgeCore, ForgeTrustLock
- **ForgeCAL** → ForgeCore, ForgeTrustLock, ForgeVTZ, ForgeTrustFlow, ForgeDTL, ForgePolicy
- **ForgeGate** → ForgeCore, ForgeTrustFlow

### Package.swift Requirements

- Swift tools version: 6.0
- All targets MUST specify explicit dependencies — no implicit module imports
- All targets MUST include corresponding test targets
- All modules MUST use strict concurrency checking (`SwiftSetting.strictConcurrency`)
- No external dependencies in initial bootstrap — all enforcement logic is internal

## TrustFlow Event Wire Format

swift
struct TrustFlowEvent: Sendable, Codable {
    let event_id: String      // UUID v4, generated at emission time
    let session_id: String    // VTZ-scoped session identifier
    let ctx_id: String        // Validated CTX-ID of the acting agent
    let ts: String            // ISO 8601 timestamp with timezone
    let event_type: String    // One of: "allow", "restrict", "block", "gate_pending", "gate_approved", "gate_denied"
    let payload_hash: String  // SHA-256 hex digest of the action payload
}


All six fields are **required** — a TrustFlow event missing any field MUST NOT be emitted; the emission failure MUST be logged and the originating action MUST be blocked.

## DTL Classification Levels

swift
enum DTLClassification: String, Sendable, Codable, Comparable {
    case PUBLIC        = "PUBLIC"
    case INTERNAL      = "INTERNAL"
    case CONFIDENTIAL  = "CONFIDENTIAL"
    case RESTRICTED    = "RESTRICTED"
}


Ordering: `PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED`. Derived data MUST inherit the **maximum** classification of all sources. Unlabeled data MUST default to `CONFIDENTIAL`.

## Error Handling Contract

Every error in an enforcement path MUST include:

swift
struct ForgeError: Error, Sendable {
    let component: String       // e.g., "CAL", "VTZ", "TrustFlow", "DTL", "TrustLock"
    let operation: String       // e.g., "validateCTXID", "checkPolicy", "emitEvent"
    let failure_reason: String  // Human-readable description
    let ctx_id: String?         // CTX-ID if available; nil only if CTX-ID itself is missing
}


Swift `try?` with a discarded result is **banned** in enforcement paths. All `catch` blocks MUST handle the error explicitly with logging and appropriate rejection.