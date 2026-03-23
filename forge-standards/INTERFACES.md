

# INTERFACES.md — Forge Platform Wire Format & API Contract Reference

**Version:** 1.0
**Status:** Normative — all implementations MUST conform
**Authority:** TRD-1 through TRD-12, CLAUDE.md, AGENTS.md, Forge Component Interface Contracts
**Scope:** Every subsystem, every wire format, every data structure, every protocol boundary

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Transport Layer](#2-transport-layer)
3. [CTX-ID — Context Identity Token](#3-ctx-id--context-identity-token)
4. [VTZ — Virtual Trust Zone](#4-vtz--virtual-trust-zone)
5. [CAL — Context Authority Layer](#5-cal--context-authority-layer)
6. [TrustFlow — Audit Event Stream](#6-trustflow--audit-event-stream)
7. [DTL — Data Trust Labels](#7-dtl--data-trust-labels)
8. [TrustLock — Cryptographic Identity](#8-trustlock--cryptographic-identity)
9. [Shell ↔ Backend IPC Protocol](#9-shell--backend-ipc-protocol)
10. [Consensus Engine](#10-consensus-engine)
11. [Pipeline — PRD / PR Lifecycle](#11-pipeline--prd--pr-lifecycle)
12. [GitHub Integration](#12-github-integration)
13. [Authentication & Session Lifecycle](#13-authentication--session-lifecycle)
14. [Provider Adapter Protocol](#14-provider-adapter-protocol)
15. [UI Data Contracts (SwiftUI ↔ Shell)](#15-ui-data-contracts-swiftui--shell)
16. [Auto-Update (Sparkle)](#16-auto-update-sparkle)
17. [Cross-Subsystem Enums & Constants](#17-cross-subsystem-enums--constants)
18. [Validation Rules](#18-validation-rules)
19. [Wire Format Examples](#19-wire-format-examples)

---

## 1. Design Principles

All interfaces in the Forge platform obey these non-negotiable rules:

| Principle | Rule |
|---|---|
| **Fail closed** | Every trust, identity, policy, and cryptographic failure rejects the action, logs the event, and surfaces to the caller. Silent continuation is forbidden. |
| **TRD authority** | When this document and a TRD disagree, the TRD wins. When two TRDs disagree, TRD-11 (Security) wins. |
| **No invented requirements** | If a field, state, or contract is not in a TRD, it does not exist. |
| **Immutable tokens** | CTX-ID, DTL labels, and audit records are immutable after creation. |
| **Explicit over implicit** | No inferred identity, no implicit trust, no advisory-only boundaries. |

---

## 2. Transport Layer

### 2.1 Shell ↔ Backend: Unix Domain Socket

| Property | Value |
|---|---|
| Type | Authenticated Unix domain socket (UDS) |
| Path | `$XDG_RUNTIME_DIR/forge/ipc.sock` or `~/Library/Application Support/Forge/ipc.sock` |
| Permissions | `0600`, owner = current user |
| Framing | Line-delimited JSON (newline = `\n`, U+000A) |
| Encoding | UTF-8, no BOM |
| Max message size | 16 MiB per line |
| Authentication | Peer credential verification (SO_PEERCRED / LOCAL_PEERCRED) + session token |
| Concurrency | Single multiplexed connection, request-response with `msg_id` correlation |

### 2.2 Message Envelope

Every IPC message — request or response — uses this envelope:

```
Field           Type        Required  Constraints
─────────────────────────────────────────────────────────────────
msg_id          string      YES       UUIDv4, unique per message
msg_type        string      YES       One of MessageType enum
session_id      string      YES       UUIDv4, bound to active session
ctx_id          string      COND      Required for all non-auth messages
ts              integer     YES       UTC Unix millis
payload         object      YES       Type-specific, see subsystem sections
hmac            string      YES       HMAC-SHA256 of canonical payload
```

**Canonical serialization for HMAC:** JSON with keys sorted lexicographically, no whitespace, UTF-8 encoded. HMAC key is the session-scoped shared secret derived during authentication.

### 2.3 MessageType Enum

```
MessageType = {
  // Authentication
  "auth.request"
  "auth.response"
  "auth.session_refresh"
  "auth.session_revoke"

  // Pipeline
  "pipeline.plan_request"
  "pipeline.plan_response"
  "pipeline.pr_generate"
  "pipeline.pr_status"
  "pipeline.pr_complete"
  "pipeline.abort"

  // Consensus
  "consensus.submit"
  "consensus.provider_result"
  "consensus.arbitration_result"
  "consensus.error"

  // GitHub
  "github.pr_open"
  "github.pr_update"
  "github.pr_status"
  "github.ci_status"
  "github.merge"

  // Trust & Policy
  "ctx.validate"
  "ctx.rotate"
  "ctx.revoke"
  "vtz.policy_check"
  "vtz.enforcement_decision"
  "trustflow.event"
  "dtl.label_assign"
  "dtl.label_verify"

  // UI Sync
  "ui.state_update"
  "ui.progress"
  "ui.error"
  "ui.card_update"

  // System
  "system.health"
  "system.shutdown"
  "system.error"
}
```

---

## 3. CTX-ID — Context Identity Token

### 3.1 Data Structure

```
CTXIDToken {
  ctx_id          string      UUIDv4, CSPRNG-generated
  session_id      string      UUIDv4, references parent session
  agent_id        string      UUIDv4, identifies the acting agent
  vtz_id          string      UUIDv4, bound VTZ — EXACTLY ONE per token
  issued_at       integer     UTC Unix millis
  expires_at      integer     UTC Unix millis, MUST be > issued_at
  ttl_seconds     integer     Positive integer, max 3600 (1 hour)
  scope           string[]    List of permitted action scopes (see CTXScope enum)
  trustlock_sig   string      Base64url-encoded Ed25519 signature over canonical token
  pubkey_fingerprint string   SHA-256 fingerprint of the TrustLock public key
  nonce           string      16 bytes, CSPRNG, Base64url-encoded
  version         integer     Token format version, currently 1
}
```

### 3.2 CTX-ID Lifecycle

```
States: ACTIVE → EXPIRED | REVOKED | ROTATED

Transitions:
  issuance      → ACTIVE     (new token created, signed by TrustLock)
  clock check   → EXPIRED    (current_time_ms > expires_at)
  explicit call → REVOKED    (ctx.revoke message processed)
  rotation      → ROTATED    (new CTX-ID issued, old invalidated immediately)
```

### 3.3 CTX-ID Validation Sequence

Every entry point that processes an agent action MUST execute this sequence **first**:

```
1. Parse ctx_id from message envelope
2. IF ctx_id is missing → REJECT as UNTRUSTED, emit TrustFlow, return error
3. Verify token signature against TrustLock public key
4. IF signature invalid → REJECT, emit TrustFlow(event_type=ctx_validation_failure)
5. Check expiry: current_time_utc_ms > expires_at → REJECT as EXPIRED
6. Verify nonce has not been seen (replay protection)
7. IF replay detected → REJECT, emit TrustFlow(event_type=replay_attempt)
8. Verify vtz_id matches expected zone for this operation
9. Return validated CTXIDToken for downstream use
```

### 3.4 CTXScope Enum

```
CTXScope = {
  "read:repo"           // Read repository contents
  "write:repo"          // Write/create files in repository
  "read:secrets"        // Read credentials from Keychain (Shell only)
  "execute:pipeline"    // Run pipeline operations
  "execute:consensus"   // Submit to consensus engine
  "write:github"        // Open/update PRs, push branches
  "read:github"         // Read PR status, CI results
  "admin:session"       // Session management operations
  "admin:vtz"           // VTZ policy management
  "audit:read"          // Read audit log
}
```

---

## 4. VTZ — Virtual Trust Zone

### 4.1 Data Structure

```
VTZDefinition {
  vtz_id            string      UUIDv4
  name              string      Human-readable, 1-128 chars, [a-zA-Z0-9_-]
  created_at        integer     UTC Unix millis
  policy_version    integer     Monotonically increasing, starts at 1
  boundary_type     string      One of VTZBoundaryType enum
  allowed_scopes    string[]    Subset of CTXScope enum
  denied_scopes     string[]    Subset of CTXScope enum (takes precedence)
  tool_whitelist    string[]    Fully qualified tool identifiers permitted
  tool_blacklist    string[]    Fully qualified tool identifiers denied (takes precedence)
  cross_vtz_policy  string      One of CrossVTZPolicy enum
  data_labels       string[]    DTL labels permitted within this zone
  max_ttl_seconds   integer     Maximum CTX-ID TTL issuable in this zone
}
```

### 4.2 VTZBoundaryType Enum

```
VTZBoundaryType = {
  "repository"      // Scoped to a single repository
  "organization"    // Scoped to a GitHub org
  "workspace"       // Scoped to a local workspace path
  "global"          // Platform-wide (admin only)
}
```

### 4.3 CrossVTZPolicy Enum

```
CrossVTZPolicy = {
  "deny"            // All cross-VTZ calls denied (default)
  "explicit_allow"  // Cross-VTZ calls allowed only with per-call authorization
  "audit_only"      // Allowed but every cross-VTZ call is audit-logged
}
```

### 4.4 VTZ Enforcement Decision

```
VTZEnforcementDecision {
  decision_id       string      UUIDv4, CSPRNG
  ctx_id            string      CTX-ID that triggered the check
  vtz_id            string      VTZ being enforced
  action            string      The action being evaluated
  tool_id           string      Tool being invoked (if applicable), nullable
  verdict           string      One of VTZVerdict enum
  reason            string      Human-readable explanation
  policy_version    integer     Version of VTZ policy applied
  ts                integer     UTC Unix millis
  trustflow_event_id string     Event ID of the TrustFlow record emitted
}
```

### 4.5 VTZVerdict Enum

```
VTZVerdict = {
  "allow"           // Action permitted
  "restrict"        // Action permitted with reduced scope
  "block"           // Action denied — caller receives rejection
}
```

**Contract:** `verdict=block` MUST produce a `VTZEnforcementDecision` record. This is not optional.

---

## 5. CAL — Context Authority Layer

### 5.1 Enforcement Sequence

The CAL is the orchestrator. Every agent action flows through this sequence:

```
┌─────────────┐
│ Agent Action │
└──────┬──────┘
       │