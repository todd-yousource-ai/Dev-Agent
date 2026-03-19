

# CLAUDE.md — Forge Platform

Forge is a trust-enforced runtime platform where every request is gated by cryptographic identity verification (CTX-ID), continuous trust scoring (TrustFlow), and policy-driven access control — no operation executes without passing all three checks.

## How to Use This File

This file is the authoritative baseline for all code generation, review, and refactoring in the Forge repository; read it completely before writing any code. For subsystem-specific implementation detail, see `forge-docs/` for the full TRDs and PRDs, and `forge-standards/` for synthesised architecture decisions and interface contracts.

**Key reference files to load when you need depth:**
- `forge-standards/ARCHITECTURE.md` — canonical subsystem map and dependency graph
- `forge-standards/INTERFACES.md` — every inter-subsystem contract with wire formats
- `forge-standards/DECISIONS.md` — architectural decision records with rationale
- `forge-standards/SECURITY.md` — threat model, cryptographic requirements, audit rules
- `forge-standards/TESTING.md` — coverage rules, fuzz targets, negative-test mandates

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| TRD-001: CTX-ID Subsystem | TRD | `forge-docs/TRD-001-CTX-ID.md` | Cryptographic context identity generation, validation, rotation, and revocation |
| TRD-002: VTZ (Verification Trust Zone) | TRD | `forge-docs/TRD-002-VTZ.md` | Runtime trust boundary enforcement, zone isolation, and cross-zone call gates |
| TRD-003: TrustFlow Engine | TRD | `forge-docs/TRD-003-TrustFlow.md` | Continuous trust score computation, decay functions, and score propagation |
| TRD-004: DTL (Distributed Trust Ledger) | TRD | `forge-docs/TRD-004-DTL.md` | Immutable audit log, trust event journaling, and consensus protocol |
| TRD-005: Policy Engine | TRD | `forge-docs/TRD-005-PolicyEngine.md` | Policy authoring, evaluation pipeline, and enforcement semantics |
| TRD-006: Gateway Layer | TRD | `forge-docs/TRD-006-Gateway.md` | Ingress routing, rate limiting, CTX-ID extraction, and TLS termination |
| TRD-007: Credential Store | TRD | `forge-docs/TRD-007-CredentialStore.md` | Secret storage, key derivation, credential lifecycle, and HSM integration |
| TRD-008: Session Manager | TRD | `forge-docs/TRD-008-SessionManager.md` | Session binding to CTX-ID, timeout enforcement, and re-authentication triggers |
| PRD-001: Forge Platform Overview | PRD | `forge-docs/PRD-001-Platform.md` | Product requirements, user stories, and acceptance criteria for Forge v1 |
| PRD-002: Trust Observability | PRD | `forge-docs/PRD-002-Observability.md` | Metrics, dashboards, alerting, and trust-score visibility requirements |
| Architecture Standard | Standard | `forge-standards/ARCHITECTURE.md` | Canonical subsystem map, dependency graph, deployment topology |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All inter-subsystem RPC/event contracts with field-level schemas |
| Decision Records | Standard | `forge-standards/DECISIONS.md` | ADRs for cryptographic choices, protocol selections, storage engines |
| Security Standard | Standard | `forge-standards/SECURITY.md` | Threat model, cryptographic requirements, key management, audit rules |
| Testing Standard | Standard | `forge-standards/TESTING.md` | Coverage mandates, fuzz targets, negative-test catalog, CI gates |

## Critical Rules — Non-Negotiable

1. **Never execute any operation without a validated CTX-ID.** Every request handler must call `ctx_id::validate()` before any business logic; there are zero exceptions.
2. **Fail closed on every trust check.** If TrustFlow scoring is unavailable, the VTZ gate must deny the request — never default to allow.
3. **Never log, serialize, or expose raw cryptographic keys.** All key material must pass through the Credential Store's redaction layer before touching any I/O boundary.
4. **Every cross-subsystem call must pass through a VTZ call gate.** Direct function calls between subsystems that bypass VTZ boundary enforcement are forbidden.
5. **TrustFlow scores are non-transferable.** Never copy a trust score from one CTX-ID to another; each identity computes its own score from its own event history.
6. **All DTL writes are append-only and cryptographically chained.** Never mutate or delete a DTL entry; every record must include the hash of the previous record.
7. **Policy Engine evaluation must be pure and deterministic.** Given identical policy definitions and identical request context, the engine must return identical decisions on every invocation.
8. **Session tokens must be bound to their originating CTX-ID and VTZ zone.** A session created in one trust zone must never be accepted in a different trust zone without explicit re-authentication.
9. **All TLS connections must use TLS 1.3 or higher with approved cipher suites only.** See `forge-standards/SECURITY.md` for the exact cipher suite allowlist.
10. **Every public API endpoint must enforce rate limiting at the Gateway layer before the request reaches any downstream subsystem.**
11. **CTX-ID rotation must complete atomically.** A partially rotated identity is a revoked identity; if rotation fails midway, the old CTX-ID must be invalidated immediately.
12. **Never use string concatenation to build policy expressions.** All policy construction must use the Policy Engine's typed AST builder.
13. **All errors returned to callers must use Forge's canonical error type with a machine-readable error code.** Never return raw strings or untyped error objects across subsystem boundaries.
14. **Every DTL-persisted event must include a monotonic timestamp, the originating CTX-ID, and the VTZ zone identifier.** Omitting any field makes the record invalid.
15. **Unit tests for any trust-boundary code must include at least one test with an expired CTX-ID, one with a revoked CTX-ID, one with an insufficient TrustFlow score, and one with a malformed policy.** All four negative cases are mandatory.

## Architecture Overview

```
┌─────────────┐
│   Gateway    │ ← All external traffic enters here
└──────┬──────┘
       │ CTX-ID extracted, rate limits enforced
       ▼
┌─────────────┐     ┌──────────────┐
│     VTZ     │◄───►│  TrustFlow   │
│ (Trust Zone)│     │   Engine     │
└──────┬──────┘     └──────┬───────┘
       │                    │ score queries
       ▼                    ▼
┌─────────────┐     ┌──────────────┐
│   Policy    │     │     DTL      │
│   Engine    │     │  (Ledger)    │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│  Session    │◄───►│  Credential  │
│  Manager    │     │    Store     │
└─────────────┘     └──────────────┘
```

### Subsystem Responsibilities

**Gateway** — Terminates TLS, extracts CTX-ID from request headers, enforces rate limits, routes to VTZ. Calls: VTZ. Called by: external clients. NEVER: perform trust scoring or policy evaluation.

**VTZ (Verification Trust Zone)** — Enforces trust boundaries between zones, validates that the CTX-ID is active and the TrustFlow score meets the zone's minimum threshold. Calls: TrustFlow, Policy Engine, CTX-ID validator. Called by: Gateway. NEVER: persist state or write to the DTL directly.

**TrustFlow Engine** — Computes continuous trust scores from DTL event history using configurable decay functions and scoring models. Calls: DTL (read-only). Called by: VTZ. NEVER: modify DTL records or cache scores beyond the configured TTL.

**DTL (Distributed Trust Ledger)** — Append-only, hash-chained audit log of all trust-relevant events. Calls: Credential Store (for signing keys). Called by: TrustFlow (reads), Session Manager (writes), VTZ (writes). NEVER: allow record mutation, deletion, or out-of-order insertion.

**Policy Engine** — Evaluates typed policy expressions against request context to produce allow/deny decisions. Calls: nothing (pure evaluation). Called by: VTZ. NEVER: perform I/O, access the network, or maintain mutable state between evaluations.

**Session Manager** — Creates, validates, and invalidates sessions bound to CTX-ID and VTZ zone. Calls: Credential Store, DTL (for audit writes). Called by: VTZ. NEVER: issue a session without a validated CTX-ID and passing TrustFlow score.

**Credential Store** — Manages all cryptographic material including keys, certificates, and derived secrets. Integrates with HSM when available. Calls: HSM driver (optional). Called by: CTX-ID subsystem, DTL, Session Manager. NEVER: expose raw key bytes outside its own process boundary.

**CTX-ID Subsystem** — Generates, validates, rotates, and revokes cryptographic context identities. Calls: Credential Store. Called by: Gateway, VTZ. NEVER: reuse a revoked identity or allow a CTX-ID without a valid cryptographic proof.

## Interface Contracts — All Subsystems

### Gateway → VTZ
```
rpc AuthenticateRequest(GatewayRequest) → VTZDecision

GatewayRequest {
  ctx_id:        bytes(32)       // Raw CTX-ID extracted from X-Forge-CTX-ID header
  request_path:  string          // Normalized URI path
  method:        HttpMethod      // Enum: GET, POST, PUT, DELETE, PATCH
  source_ip:     bytes(16)       // IPv6-mapped address
  tls_fingerprint: bytes(32)     // SHA-256 of client certificate (if mTLS)
  timestamp:     int64           // Unix epoch nanoseconds
}

VTZDecision {
  allowed:       bool
  denial_reason: ErrorCode       // Set only when allowed=false
  zone_id:       string          // VTZ zone the request was evaluated against
  trust_score:   float64         // Score at time of evaluation (0.0–1.0)
  session_token: bytes(64)       // Issued only when allowed=true
}
```

### VTZ → TrustFlow
```
rpc GetTrustScore(TrustScoreRequest) → TrustScoreResponse

TrustScoreRequest {
  ctx_id:        bytes(32)
  zone_id:       string
  evaluation_ts: int64           // Timestamp for point-in-time scoring
}

TrustScoreResponse {
  score:         float64         // 0.0 (no trust) to 1.0 (full trust)
  confidence:    float64         // 0.0 to 1.0 — data sufficiency indicator
  last_event_ts: int64           // Timestamp of most recent DTL event used
  decay_model:   string          // Name of decay function applied
}
```

### VTZ → Policy Engine
```
rpc EvaluatePolicy(PolicyRequest) → PolicyDecision

PolicyRequest {
  ctx_id:        bytes(32)
  zone_id:       string
  resource:      string          // Resource identifier being accessed
  action:        string          // Action being performed
  trust_score:   float64         // Current TrustFlow score
  attributes:    map<string, string>  // Additional context attributes
}

PolicyDecision {
  effect:        Effect          // Enum: ALLOW, DENY, NOT_APPLICABLE
  matched_policy: string         // Policy ID that produced this decision
  obligations:   []Obligation    // Post-decision actions (e.g., log, notify)
}
```

### Session Manager → DTL
```
rpc AppendTrustEvent(TrustEvent) → AppendResult

TrustEvent {
  event_id:      bytes(16)       // UUID v7
  ctx_id:        bytes(32)
  zone_id:       string
  event_type:    EventType       // Enum: SESSION_CREATE, SESSION_REVOKE, AUTH_SUCCESS, AUTH_FAILURE, TRUST_CHANGE
  timestamp:     int64           // Monotonic nanosecond timestamp
  prev_hash:     bytes(32)       // SHA-256 of previous DTL record
  payload:       bytes           // Event-specific data, max 4096 bytes
  signature:     bytes(64)       // Ed25519 signature over all preceding fields
}

AppendResult {
  record_hash:   bytes(32)       // SHA-256 of the newly appended record
  sequence_num:  uint64          // Monotonically increasing sequence number
}
```

### CTX-ID → Credential Store
```
rpc DeriveKey(KeyDerivationRequest) → DerivedKey
rpc GetSigningKey(KeyRequest) → SigningKeyHandle

KeyDerivationRequest {
  master_key_id: string          // Reference to the master key in HSM/store
  derivation_path: string        // Hierarchical derivation path
  purpose:       KeyPurpose      // Enum: SIGNING, ENCRYPTION, IDENTITY
}

DerivedKey {
  key_handle:    string          // Opaque handle — NEVER raw bytes
  algorithm:     string          // e.g., "Ed25519", "X25519", "AES-256-GCM"
  created_at:    int64
  expires_at:    int64
}
```

See `forge-standards/INTERFACES.md` for the complete contract catalog including all error response types and streaming interfaces.

## Wire Formats and Schemas

### CTX-ID Wire Format
```
CTX-ID (32 bytes):
  [0..1]   version:    uint16     // Current: 0x0001
  [2..5]   issued_at:  uint32     // Unix epoch seconds
  [6..9]   expires_at: uint32     // Unix epoch seconds
  [10..11] zone_flags: uint16     // Bitfield of authorized VTZ zones
  [12..31] identity:   bytes(20)  // SHA-1 of the public key (truncated identifier)
```

### TrustFlow Score Record
```
ScoreRecord {
  ctx_id:        bytes(32)
  score:         float64         // IEEE 754 double, clamped to [0.0, 1.0]
  computed_at:   int64           // Nanosecond timestamp
  input_events:  uint32          // Number of DTL events consumed
  decay_fn:      string          // "exponential" | "linear" | "step"
  half_life_sec: uint32          // Decay half-life (exponential only)
}
```

### DTL Record On-Disk Format
```
DTLRecord (variable length, max 4352 bytes):
  [0..15]   event_id:    bytes(16)   // UUID v7
  [16..47]  ctx_id:      bytes(32)
  [48..55]  sequence:    uint64      // Big-endian
  [56..63]  timestamp:   int64       // Big-endian, nanoseconds
  [64..95]  prev_hash:   bytes(32)   // SHA-256
  [96..97]  payload_len: uint16      // Big-endian, max 4096
  [98..N]   payload:     bytes       // Variable
  [N..N+64] signature:   bytes(64)   // Ed25519
```

### Policy Expression AST Node Types
```
PolicyNode = 
  | And(children: []PolicyNode)
  | Or(children: []PolicyNode)
  | Not(child: PolicyNode)
  | TrustThreshold(min_score: float64)
  | ZoneMembership(zone_id: string)
  | AttributeMatch(key: string, pattern: string)
  | TimeWindow(after: int64, before: int64)
```

See `forge-standards/INTERFACES.md` for the complete schema catalog.

## Error Handling Rules

### Canonical Error Structure
```
ForgeError {
  code:       uint32          // Machine-readable, see error code registry
  subsystem:  string          // "gateway", "vtz", "trustflow", "dtl", "policy", "session", "credential", "ctx_id"
  message:    string          // Human-readable, never contains secrets
  request_id: bytes(16)       // Correlation ID for tracing
  timestamp:  int64
}
```

### Error Code Ranges
| Range | Subsystem |
|---|---|
| 1000–1099 | Gateway |
| 1100–1199 | VTZ |
| 1200–1299 | TrustFlow |
| 1300–1399 | DTL |
| 1400–1499 | Policy Engine |
| 1500–1599 | Session Manager |
| 1600–1699 | Credential Store |
| 1700–1799 | CTX-ID |

### Failure Handling by Type

- **CTX-ID validation failure** → Return error code 1700, deny the request, log to DTL with `AUTH_FAILURE` event. Do not retry.
- **TrustFlow unavailable** → Fail closed. Return error code 1200, deny the request. Never assume a default trust score.
- **DTL write failure** → Retry exactly 3 times with exponential backoff (100ms, 400ms, 1600ms). If all retries fail, deny the originating request and emit a critical alert. Never silently drop a trust event.
- **Policy Engine returns NOT_APPLICABLE** → Treat as DENY. Log a warning including the policy request for debugging. Never treat missing policy as implicit allow.
- **Credential Store HSM timeout** → Fail closed. Return error code 1600. Queue the operation for retry only if it is non-interactive (e.g., key rotation). Interactive requests must fail immediately.
- **Session token expired** → Return error code 1500, force re-authentication. Never extend an expired session silently.
- **Malformed wire format** → Return error code specific to the subsystem, drop the message. Never attempt partial parsing of a malformed message.

### Banned Patterns
- **Catching and swallowing errors.** Every error must be either handled with explicit recovery logic or propagated to the caller.
- **Using generic exception types.** All thrown/returned errors must be `ForgeError` with a valid code.
- **Logging error details that include key material, tokens, or trust scores.** Use the `ForgeError.message` field which is guaranteed redacted.
- **Retry loops without bounded iteration.** Every retry must have a max attempt count and a backoff ceiling.

## Testing Requirements

### Coverage Rules
- **Minimum 90% line coverage** on all subsystem code. CI blocks merge below this threshold.
- **100% branch coverage** on all VTZ gate logic, CTX-ID validation, and Policy Engine evaluation paths.
- **Every public function** must have at least one positive test and one negative test.

### Mandatory Negative Tests
For every trust-boundary function, the following four negative test cases are required:
1. Expired CTX-ID
2. Revoked CTX-ID
3. TrustFlow score below zone threshold
4. Malformed or missing policy

### Fuzz Targets
Maintain active fuzz targets for:
- CTX-ID wire format parser (`src/ctx_id/fuzz/`)
- DTL record deserializer (`src/dtl/fuzz/`)
- Policy expression parser (`src/policy/fuzz/`)
- Gateway header extractor (`src/gateway/fuzz/`)

Fuzz targets must run for a minimum of 10 minutes in CI on every PR that touches the