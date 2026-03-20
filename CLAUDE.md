

# CLAUDE.md — Forge Platform

Forge is a trust-aware distributed platform that enforces identity verification, contextual authorization, and cryptographic audit integrity at runtime through its CTX-ID, VTZ, TrustFlow, and DTL subsystems — every request that cannot be verified is rejected.

## How to Use This File

This file is the baseline context for all LLM-assisted development on the Forge platform; read it completely before writing any code. For subsystem-specific detail, see `forge-docs/` for the full TRDs and PRDs, and `forge-standards/` for synthesised architecture, interface contracts, and decision records — the exact paths are listed below.

**Key reference files to load when you need deeper context:**

- `forge-standards/ARCHITECTURE.md` — canonical subsystem map and dependency graph
- `forge-standards/INTERFACES.md` — all inter-subsystem wire formats and contracts
- `forge-standards/DECISIONS.md` — architectural decision records with rationale
- `forge-standards/ENGINEERING_STANDARDS.md` — complete coding and review standards
- `forge-standards/SECURITY.md` — threat model, control matrix, crypto requirements

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Technical Requirements | TRD | `forge-docs/trd-ctx-id.md` | Context-identity binding, token lifecycle, CTX-ID issuance and validation |
| VTZ Technical Requirements | TRD | `forge-docs/trd-vtz.md` | Verification Trust Zones — zone definitions, boundary enforcement, zone transitions |
| TrustFlow Technical Requirements | TRD | `forge-docs/trd-trustflow.md` | Trust propagation engine — scoring model, decay rules, delegation chains |
| DTL Technical Requirements | TRD | `forge-docs/trd-dtl.md` | Distributed Trust Ledger — append-only audit log, Merkle proofs, replication |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user personas, acceptance criteria, launch gates |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, deployment topology |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All RPC/event schemas, wire formats, versioning rules |
| Decision Records | Standard | `forge-standards/DECISIONS.md` | ADRs — why each architectural choice was made |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Code style, review gates, CI/CD rules, dependency policy |
| Security Reference | Standard | `forge-standards/SECURITY.md` | Threat model, control matrix, cryptographic requirements |
| API Reference | Docs | `docs/api-reference.md` | Public API surface, authentication flows, rate limits |
| Deployment Guide | Docs | `docs/deployment.md` | Infrastructure requirements, configuration, rollout procedures |
| Runbook | Docs | `docs/runbook.md` | Incident response, operational procedures, escalation paths |

## Critical Rules — Non-Negotiable

1. **Never skip CTX-ID validation.** Every inbound request must carry a valid CTX-ID; reject requests with missing, expired, or malformed CTX-IDs with a `401` before any business logic executes.
2. **Fail closed on all trust decisions.** If TrustFlow scoring returns an error or timeout, deny the operation — never default to a permissive trust score.
3. **Never mutate a DTL record.** The Distributed Trust Ledger is append-only; any code path that updates or deletes an existing DTL entry is a critical defect.
4. **Enforce VTZ boundaries at the service mesh layer.** Cross-zone calls must present a valid zone-transition token issued by CTX-ID; do not rely on application-level checks alone.
5. **Sign every DTL entry with the originating service's private key.** Unsigned or self-signed entries must be rejected by all DTL replicas.
6. **Validate Merkle proofs on DTL reads.** Consumers of DTL data must verify the Merkle inclusion proof before trusting any audit record.
7. **Never log CTX-ID tokens, private keys, or raw trust scores to stdout, files, or external logging services.** Emit only token fingerprints (first 8 chars of SHA-256).
8. **Use exactly the schemas defined in `forge-standards/INTERFACES.md` for all inter-subsystem communication.** Do not invent ad-hoc payloads.
9. **Apply TrustFlow decay on every score read.** Trust scores are time-decayed; never cache a score without reapplying the decay function at read time.
10. **Reject unknown fields in all inbound payloads.** Forge APIs use strict deserialization — unknown fields cause a `400`, not silent ignoring.
11. **Gate every PR on passing the full test suite with ≥ 90% line coverage for the changed subsystem.** No merge without green CI.
12. **Pin all cryptographic dependencies to exact versions.** No semver ranges for any library that touches key material, hashing, or signatures.
13. **Propagate trace context (OpenTelemetry `traceparent`) through every inter-subsystem call.** Broken traces are a P2 bug.
14. **Never embed secrets in source.** All key material loads from the secrets manager at runtime; environment variable fallback is permitted only in local-dev profile.
15. **Run `forge lint` and `forge typecheck` before committing.** Both must pass with zero warnings; `--fix` is acceptable but the diff must be reviewed.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                      API Gateway                         │
│  Terminates TLS, extracts CTX-ID, enforces rate limits   │
└──────────┬──────────────────────────────────┬────────────┘
           │                                  │
     ┌─────▼─────┐                    ┌───────▼───────┐
     │   CTX-ID   │◄────────────────►│   TrustFlow    │
     │  Service   │                   │    Engine      │
     └─────┬─────┘                    └───────┬───────┘
           │                                  │
     ┌─────▼─────┐                    ┌───────▼───────┐
     │    VTZ     │                   │     DTL        │
     │  Enforcer  │                   │    Ledger      │
     └───────────┘                    └───────────────┘
```

### CTX-ID Service
- **Enforces:** Identity binding — issues, validates, and revokes context-identity tokens.
- **Called by:** API Gateway (on every request), TrustFlow (for identity resolution during scoring).
- **Calls:** DTL (to log issuance/revocation events), VTZ (to determine zone affinity of the identity).
- **Must NEVER:** Issue a CTX-ID without verifying the upstream authentication credential. Must NEVER extend token expiry beyond the configured maximum TTL.

### VTZ Enforcer
- **Enforces:** Zone boundaries — validates that a request is authorized to operate within or transition between Verification Trust Zones.
- **Called by:** API Gateway (pre-routing), CTX-ID (zone affinity lookup), application services (for zone-scoped operations).
- **Calls:** CTX-ID (to validate zone-transition tokens), DTL (to audit zone transitions).
- **Must NEVER:** Allow a cross-zone call without a valid zone-transition token. Must NEVER cache zone policy beyond the configured refresh interval.

### TrustFlow Engine
- **Enforces:** Trust scoring — computes, propagates, and decays trust scores across entities and delegation chains.
- **Called by:** API Gateway (authorization decisions), application services (trust-gated features).
- **Calls:** CTX-ID (identity resolution), DTL (to read historical trust events and write score change events).
- **Must NEVER:** Return a cached score without applying time-decay. Must NEVER propagate trust through a revoked CTX-ID.

### DTL (Distributed Trust Ledger)
- **Enforces:** Audit integrity — provides an append-only, Merkle-tree-backed ledger of all trust-relevant events.
- **Called by:** CTX-ID, VTZ, TrustFlow (all write audit events), any service (reads with proof verification).
- **Calls:** Peer DTL replicas (for replication and consistency).
- **Must NEVER:** Accept an unsigned entry. Must NEVER delete, update, or compact existing entries. Must NEVER serve a record without an accompanying Merkle inclusion proof.

### API Gateway
- **Enforces:** TLS termination, CTX-ID extraction, rate limiting, request routing.
- **Called by:** External clients.
- **Calls:** CTX-ID (validation), VTZ (zone routing), TrustFlow (authorization).
- **Must NEVER:** Forward a request with an invalid or missing CTX-ID to any downstream service.

## Interface Contracts — All Subsystems

### CTX-ID ↔ API Gateway
- **Protocol:** gRPC over mTLS
- **Method:** `ValidateCTXID(ValidateCTXIDRequest) → ValidateCTXIDResponse`
- **Timeout:** 50ms hard, 30ms soft (p99 target)
- **Retry:** 1 retry with 10ms jitter; fail closed on second failure
- **Idempotency:** Safe (read-only validation)

### CTX-ID ↔ TrustFlow
- **Protocol:** gRPC over mTLS
- **Method:** `ResolveIdentity(ResolveIdentityRequest) → ResolveIdentityResponse`
- **Timeout:** 100ms hard
- **Retry:** 0 retries; fail closed immediately
- **Contract:** TrustFlow must not call `ResolveIdentity` for identities it has resolved within the last 5s (local cache with decay-aware invalidation)

### TrustFlow ↔ DTL
- **Protocol:** gRPC over mTLS
- **Methods:** `AppendTrustEvent(TrustEvent) → AppendResponse`, `QueryTrustHistory(HistoryQuery) → HistoryResponse`
- **Timeout:** 200ms hard for writes, 500ms for reads
- **Contract:** Every `TrustEvent` must include the originating service signature and the CTX-ID that triggered it

### VTZ ↔ CTX-ID
- **Protocol:** gRPC over mTLS
- **Method:** `ValidateZoneTransition(ZoneTransitionRequest) → ZoneTransitionResponse`
- **Timeout:** 50ms hard
- **Contract:** Transition tokens are single-use; CTX-ID must mark them consumed atomically

### All Services → DTL (Audit Write)
- **Protocol:** Async via event bus (Kafka/NATS) with gRPC fallback
- **Schema:** `AuditEntry` protobuf (see Wire Formats below)
- **Delivery guarantee:** At-least-once; DTL deduplicates by `entry_id`
- **Contract:** Every audit entry must include `entry_id` (UUIDv7), `ctx_id`, `service_signature`, `timestamp_utc`, and `event_type`

Refer to `forge-standards/INTERFACES.md` for the complete protobuf definitions, field-level validation rules, and backwards-compatibility policy.

## Wire Formats and Schemas

### CTX-ID Token (JWT-based)
```
{
  "header": {
    "alg": "EdDSA",             // Ed25519 only; no RSA, no ECDSA
    "typ": "CTX-ID",
    "kid": "<key-id>"           // references signing key in key registry
  },
  "payload": {
    "sub":      "<entity-id>",        // UUIDv7
    "ctx":      "<context-hash>",     // SHA-256 of the request context
    "vtz_zone": "<zone-id>",          // VTZ zone the identity is bound to
    "trust":    <float64>,            // TrustFlow score snapshot (decay-applied)
    "iat":      <unix-epoch-seconds>,
    "exp":      <unix-epoch-seconds>, // max TTL: 3600s
    "jti":      "<token-id>"          // UUIDv7, unique per issuance
  }
}
```

### DTL AuditEntry (Protobuf)
```protobuf
message AuditEntry {
  string entry_id = 1;            // UUIDv7
  string ctx_id = 2;              // the CTX-ID token ID (jti)
  string event_type = 3;          // enum: ISSUANCE | REVOCATION | ZONE_TRANSITION | TRUST_CHANGE | ACCESS_DECISION
  string source_service = 4;      // service name emitting the event
  bytes  service_signature = 5;   // Ed25519 signature over fields 1-4,6-8
  int64  timestamp_utc = 6;       // Unix epoch millis
  bytes  payload = 7;             // event-type-specific protobuf, max 64KB
  bytes  merkle_proof = 8;        // populated on read, empty on write
}
```

### TrustFlow Score Record
```protobuf
message TrustScore {
  string entity_id = 1;           // UUIDv7
  double raw_score = 2;           // 0.0–1.0, pre-decay
  double decayed_score = 3;       // 0.0–1.0, post-decay at query time
  int64  last_updated_utc = 4;    // Unix epoch millis
  double decay_rate = 5;          // per-second decay coefficient
  repeated string delegation_chain = 6; // ordered list of entity IDs
}
```

Refer to `forge-standards/INTERFACES.md` for the complete set of protobuf definitions, enum values, and field validation constraints.

## Error Handling Rules

### Fail-Closed Requirement
Every trust-critical code path must fail closed. If a subsystem is unreachable, returns an error, or times out, the calling service must deny the operation. There is no "degrade to open" mode in Forge.

### Error Classification and Response

| Failure Type | Action | HTTP Status | Log Level |
|---|---|---|---|
| CTX-ID validation failure | Reject request immediately | 401 | WARN |
| CTX-ID expired | Reject; do not auto-renew server-side | 401 | INFO |
| VTZ zone-transition denied | Reject; audit to DTL | 403 | WARN |
| TrustFlow score below threshold | Reject; include `X-Trust-Decision: denied` header | 403 | INFO |
| TrustFlow timeout | Reject (fail closed) | 503 | ERROR |
| DTL write failure | Retry once, then reject the originating operation | 503 | ERROR |
| DTL Merkle proof invalid | Discard record; raise alert | — | CRITICAL |
| Unknown/unexpected error | Reject; do not expose internal details | 500 | ERROR |

### Banned Patterns
- **Never catch and swallow errors.** Every error must be logged, propagated, or explicitly converted to a typed Forge error.
- **Never return `200 OK` with an error in the body.** Use appropriate HTTP status codes.
- **Never retry indefinitely.** All retries have a hard cap (specified per-interface in the contracts above).
- **Never expose stack traces, internal service names, or infrastructure details in client-facing error responses.**
- **Never use string matching on error messages for control flow.** Use typed error codes from the Forge error enum.

### Error Response Schema
```json
{
  "error": {
    "code": "FORGE_CTX_ID_EXPIRED",
    "message": "Context identity token has expired.",
    "trace_id": "<OpenTelemetry trace ID>",
    "timestamp": "<ISO 8601>"
  }
}
```

## Testing Requirements

### Coverage Rules
- **90% line coverage minimum** for every subsystem on every PR. CI blocks merge if any subsystem drops below this threshold.
- **100% branch coverage** for all code paths in CTX-ID validation, VTZ boundary enforcement, and TrustFlow scoring.
- Coverage is measured per-subsystem, not globally — a high-coverage utility module does not offset a low-coverage security module.

### Mandatory Test Categories

| Category | Requirement | Where |
|---|---|---|
| Unit tests | Every public function; every error branch | `src/<subsystem>/tests/unit/` |
| Integration tests | Every inter-subsystem contract | `tests/integration/` |
| Negative tests | Every rejection path (expired token, invalid zone, revoked identity, low trust score, malformed payload) | Alongside unit tests |
| Boundary tests | Max TTL, score range [0.0, 1.0], payload size 64KB limit, delegation chain max depth | Alongside unit tests |
| Fuzz targets | CTX-ID token parsing, DTL entry deserialization, TrustFlow score computation | `tests/fuzz/` |
| Chaos tests | DTL replica failure, TrustFlow timeout, CTX-ID service unavailable | `tests/chaos/` |

### Fuzz Testing
- Maintain fuzz targets for all deserialization paths and all cryptographic verification paths.
- Fuzz targets run nightly in CI for a minimum of 10 minutes each.
- Any fuzz finding is a P1 bug.

### Test Naming Convention
```
test_<subsystem>_<function>_<scenario>_<expected_outcome>
```
Example: `test_ctxid_validate_expired_token_returns_401`

## File Naming and Directory Layout

```
forge/
├── CLAUDE.md                          # This file
├── forge-docs/                        # Source TRDs and PRDs
│   ├── trd-ctx-id.md
│   ├── trd-vtz.md
│   ├── trd-trustflow.md
│   ├── trd-dtl.md
│   └── prd-forge-platform.md
├── forge-standards/                   # Synthesised architecture & standards
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   ├── DECISIONS.md
│   ├── ENGINEERING_STANDARDS.md
│   └── SECURITY.md
├── docs/                              # Operational and API documentation
│   ├── api-reference.md
│   ├── deployment.md
│   └── runbook.md
├── proto/                             # Protobuf definitions (source of truth)
│   ├── ctx_id.proto
│   ├── vtz.proto
│   ├── trustflow.proto
│   ├── dtl.proto
│   └── common.proto
├── src/
│   ├── gateway/                       # API Gateway
│   │   ├── middleware/                # CTX-ID extraction, rate limiting
│   │   ├── routing/                   # VTZ-aware request routing
│   │   └── tests/
│   ├── ctx-id/                        # CTX-ID Service
│   │   ├── issuance/                  # Token creation
│   │   ├── validation/                # Token verification
│   │   ├── revocation/                # Token revocation
│   │   ├── keys/                      # Key management and rotation
│   │   └── tests/
│   ├── vtz/                           # VTZ Enforcer
│   │   ├── zones/                     # Zone definitions and policy
│   │   ├── transitions/               # Zone-transition validation
│   │   └── tests/
│   ├── trustflow/                     # TrustFlow Engine
│   │   ├── scoring/                   # Score computation
│   │   ├── decay/                     # Time-decay functions
│   │   ├── delegation/                # Delegation chain resolution
│   │   └── tests/
│   ├── dtl/                           # Distributed Trust Ledger
│   │   ├── ledger/                    # Append-only storage
│   │   ├── merkle/                