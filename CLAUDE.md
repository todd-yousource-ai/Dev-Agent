

# CLAUDE.md — Forge Platform

Forge is a zero-trust runtime identity and authorization platform that binds every request to a cryptographically verified context (CTX-ID), enforces policy through TrustFlow evaluation, and fails closed on any ambiguity — no request proceeds without a validated trust chain.

## How to Use This File

This file is the authoritative baseline for all code generation, refactoring, and review across the Forge repository — read it fully before writing any code. For subsystem-specific detail, consult the TRDs in `forge-docs/` and the synthesised engineering standards in `forge-standards/`.

**Key reference files to load when you need deeper context:**

- `forge-standards/ARCHITECTURE.md` — full subsystem decomposition, dependency graph, deployment topology
- `forge-standards/INTERFACES.md` — every inter-subsystem contract with wire formats, error codes, and versioning rules
- `forge-standards/DECISIONS.md` — architectural decision records with rationale and constraints
- `forge-standards/ENGINEERING_STANDARDS.md` — complete coding standards, patterns, and anti-patterns

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Runtime TRD | TRD | `forge-docs/trd-ctx-id-runtime.md` | Context identity lifecycle: creation, binding, propagation, expiry, and revocation of CTX-IDs across all request paths |
| VTZ (Verified Trust Zone) TRD | TRD | `forge-docs/trd-vtz.md` | Trust zone boundary enforcement, zone admission, cross-zone request validation, and VTZ attestation protocol |
| TrustFlow Engine TRD | TRD | `forge-docs/trd-trustflow-engine.md` | Policy evaluation pipeline: rule ingestion, scoring, decision emission, audit logging, and cache invalidation |
| DTL (Distributed Trust Ledger) TRD | TRD | `forge-docs/trd-dtl.md` | Append-only trust event ledger: write path, replication, consistency guarantees, pruning, and query interface |
| Identity Provider Gateway TRD | TRD | `forge-docs/trd-idp-gateway.md` | External IdP integration, token exchange, claim normalization, and federation protocol handling |
| Policy Administration API TRD | TRD | `forge-docs/trd-policy-admin-api.md` | CRUD operations for TrustFlow rules, versioned policy sets, staging/promotion workflow, and rollback |
| Audit & Compliance TRD | TRD | `forge-docs/trd-audit-compliance.md` | Immutable audit trail generation, compliance report queries, retention policies, and export formats |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements: user stories, acceptance criteria, SLAs, and non-functional requirements for GA |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, deployment topology, scaling constraints, and failure domain isolation |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All inter-subsystem APIs: request/response schemas, error codes, versioning strategy, and backward-compatibility rules |
| Architectural Decisions | Standard | `forge-standards/DECISIONS.md` | ADRs covering crypto choices, storage engine selection, cache strategy, wire format, and fail-closed semantics |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Coding conventions, review checklist, dependency policy, performance budgets, and banned patterns |

## Critical Rules — Non-Negotiable

1. **Fail closed on every ambiguity.** If CTX-ID validation, TrustFlow evaluation, or VTZ attestation returns an indeterminate result, deny the request — never default to allow.
2. **Bind every inbound request to exactly one CTX-ID before any business logic executes.** No code path may skip CTX-ID resolution; extract it in the outermost middleware layer.
3. **Never cache a TrustFlow DENY decision.** Only ALLOW decisions with an explicit TTL may be cached; a stale DENY cache creates a liveness failure that masks a security state change.
4. **TrustFlow policy evaluation must be idempotent and side-effect-free.** The engine reads policy and context, emits a decision and audit event — it never mutates state.
5. **All writes to the DTL are append-only.** No update or delete operation may exist on the DTL write path; implement corrections as compensating append entries with back-references.
6. **Every cross-VTZ request must carry a fresh zone attestation token.** Do not reuse attestation tokens across zone boundaries; generate a new attestation at each zone ingress.
7. **Cryptographic operations use only the algorithms in `forge-standards/DECISIONS.md` § Crypto.** Do not introduce new cipher suites, hash functions, or signature schemes without an ADR amendment.
8. **All inter-subsystem calls use the versioned wire format defined in `forge-standards/INTERFACES.md`.** Do not add fields to a published schema version — create a new version.
9. **Secrets must never appear in logs, error messages, traces, or HTTP response bodies.** CTX-ID tokens, signing keys, and attestation material are classified as secrets.
10. **Every subsystem must expose a `/healthz` endpoint that returns unhealthy when it cannot reach its critical dependencies.** Health checks must be transitive — if TrustFlow cannot reach DTL, TrustFlow reports unhealthy.
11. **Audit events are non-optional.** Every TrustFlow decision, CTX-ID lifecycle event, VTZ admission, and policy mutation must emit a structured audit event to the audit subsystem before returning a response.
12. **Request timeout budgets are hierarchical.** The gateway enforces a global timeout; each downstream subsystem call must use a sub-budget allocated from the remaining time — never use a hardcoded timeout that exceeds the caller's budget.
13. **No direct database access outside the owning subsystem.** DTL data is accessed only through the DTL query interface; TrustFlow policy data is accessed only through the Policy Administration API. No shared databases.
14. **All public API endpoints require mutual TLS or VTZ-scoped bearer tokens.** No plaintext HTTP. No API key-only auth.
15. **Feature flags that weaken security controls (bypass TrustFlow, skip VTZ attestation, disable audit) must not exist in production builds.** Gate them behind a compile-time flag that is stripped in release builds.

## Architecture Overview

### CTX-ID Runtime
- **Enforces:** Every request is bound to a unique, cryptographically signed context identity with bounded lifetime.
- **Called by:** API Gateway (on every inbound request), all downstream subsystems (to propagate context).
- **Calls:** Identity Provider Gateway (for initial claim resolution), DTL (to record CTX-ID issuance/revocation).
- **Must NEVER:** Issue a CTX-ID without verifying the upstream identity claim. Must NEVER extend a CTX-ID beyond its maximum TTL.

### VTZ (Verified Trust Zone)
- **Enforces:** Zone boundary integrity — only requests with valid zone attestation tokens cross zone boundaries.
- **Called by:** API Gateway (at zone ingress), inter-zone service mesh proxies.
- **Calls:** CTX-ID Runtime (to validate the bound context), DTL (to record zone admission events).
- **Must NEVER:** Admit a request with an expired or replayed attestation token. Must NEVER allow cross-zone traffic without fresh attestation.

### TrustFlow Engine
- **Enforces:** Authorization policy — evaluates rules against CTX-ID claims and request attributes, emits ALLOW/DENY decisions.
- **Called by:** API Gateway (inline on every request), Policy Administration API (for policy dry-run/test).
- **Calls:** DTL (to read trust history for adaptive scoring), Audit subsystem (to emit decision events).
- **Must NEVER:** Mutate policy state during evaluation. Must NEVER return a default-allow when rule evaluation fails.

### DTL (Distributed Trust Ledger)
- **Enforces:** Immutable, append-only record of all trust-relevant events across the platform.
- **Called by:** CTX-ID Runtime, VTZ, TrustFlow Engine, Audit subsystem.
- **Calls:** Storage backend (internal only — no external dependencies from DTL write path).
- **Must NEVER:** Expose a delete or update API. Must NEVER accept writes without the caller's CTX-ID and subsystem attestation.

### Identity Provider Gateway
- **Enforces:** Normalized identity claims from heterogeneous external IdPs, ensuring Forge-internal code never handles raw external tokens.
- **Called by:** CTX-ID Runtime (during initial context creation).
- **Calls:** External IdPs (OIDC, SAML, custom federation), DTL (to record federation events).
- **Must NEVER:** Pass raw external tokens downstream. Must NEVER trust an external claim without signature verification.

### Policy Administration API
- **Enforces:** Versioned, staged lifecycle for TrustFlow rules — all policy changes are auditable and reversible.
- **Called by:** Platform operators (via CLI/UI), CI/CD pipelines (for policy-as-code deployments).
- **Calls:** TrustFlow Engine (for dry-run validation), DTL (to record policy change events), Audit subsystem.
- **Must NEVER:** Apply a policy version that has not passed dry-run validation. Must NEVER allow deletion of policy versions referenced by active deployments.

### Audit & Compliance Subsystem
- **Enforces:** Complete, tamper-evident audit trail with compliance-grade query and export capabilities.
- **Called by:** All subsystems (for event emission), compliance operators (for query/export).
- **Calls:** DTL (as the backing store for audit events).
- **Must NEVER:** Drop audit events silently — if the audit sink is unavailable, the calling subsystem must block or fail the operation. Must NEVER expose audit data without CTX-ID-scoped access control.

## Interface Contracts — All Subsystems

### CTX-ID Issuance
```
POST /v1/ctx-id/issue
Request:  { "identity_claims": NormalizedClaims, "requested_ttl_seconds": uint32, "zone_id": string }
Response: { "ctx_id": string, "token": string, "expires_at": ISO8601, "zone_scope": string }
Errors:   401 InvalidClaims | 403 ZoneDenied | 429 RateLimited | 500 IssuanceFailure
```

### CTX-ID Validation
```
POST /v1/ctx-id/validate
Request:  { "token": string }
Response: { "valid": bool, "ctx_id": string, "claims": NormalizedClaims, "expires_at": ISO8601, "zone_scope": string }
Errors:   401 InvalidToken | 410 Expired | 500 ValidationFailure
```

### TrustFlow Evaluation
```
POST /v1/trustflow/evaluate
Request:  { "ctx_id": string, "resource": string, "action": string, "environment": map<string, string> }
Response: { "decision": "ALLOW" | "DENY", "score": float64, "policy_version": string, "reasons": []string, "audit_ref": string }
Errors:   400 MalformedRequest | 401 InvalidCtxId | 500 EvaluationFailure (→ treated as DENY)
```

### VTZ Attestation
```
POST /v1/vtz/attest
Request:  { "ctx_id": string, "source_zone": string, "target_zone": string }
Response: { "attestation_token": string, "expires_at": ISO8601, "target_zone": string }
Errors:   403 ZoneCrossing Denied | 401 InvalidCtxId | 500 AttestationFailure
```

### DTL Append
```
POST /v1/dtl/append
Request:  { "event_type": string, "ctx_id": string, "subsystem": string, "payload": bytes, "idempotency_key": string }
Response: { "sequence_id": uint64, "timestamp": ISO8601, "hash": string }
Errors:   400 MalformedEvent | 401 Unauthorized | 409 DuplicateIdempotencyKey | 500 WriteFailure
```

### DTL Query
```
POST /v1/dtl/query
Request:  { "ctx_id"?: string, "event_type"?: string, "after_sequence": uint64, "limit": uint32 }
Response: { "events": []DTLEvent, "next_cursor": string, "has_more": bool }
Errors:   400 MalformedQuery | 401 Unauthorized | 500 QueryFailure
```

### Policy Mutation
```
POST /v1/policy/stage
Request:  { "policy_set": PolicySet, "parent_version": string }
Response: { "staged_version": string, "dry_run_result": DryRunReport, "audit_ref": string }
Errors:   400 InvalidPolicy | 409 VersionConflict | 500 StagingFailure
```

For the complete contract catalog including pagination, streaming, and webhook interfaces, see `forge-standards/INTERFACES.md`.

## Wire Formats and Schemas

### CTX-ID Token Structure (JWT-like, Forge-specific)
```
{
  "ctx":    string,       // Unique CTX-ID (UUIDv7)
  "sub":    string,       // Normalized subject from IdP
  "iss":    string,       // Forge CTX-ID Runtime issuer URI
  "iat":    uint64,       // Issued-at (Unix seconds)
  "exp":    uint64,       // Expiry (Unix seconds, max TTL enforced)
  "vtz":    string,       // Zone scope identifier
  "claims": map<string, string>,  // Normalized identity claims
  "sig":    bytes         // Ed25519 signature over canonical form
}
```

### TrustFlow Decision Record
```
{
  "decision_id":    string,       // UUIDv7
  "ctx_id":         string,       // Bound CTX-ID
  "resource":       string,       // Target resource URI
  "action":         string,       // Requested action
  "decision":       enum,         // ALLOW | DENY
  "score":          float64,      // Trust score [0.0, 1.0]
  "policy_version": string,       // Evaluated policy version hash
  "reasons":        []string,     // Human-readable rule match reasons
  "timestamp":      ISO8601,
  "audit_ref":      string        // DTL sequence reference
}
```

### DTL Event Envelope
```
{
  "sequence_id":     uint64,      // Monotonically increasing
  "event_type":      string,      // e.g., "ctx_id.issued", "trustflow.decision", "vtz.admission"
  "ctx_id":          string,      // Originating context
  "subsystem":       string,      // Emitting subsystem identifier
  "timestamp":       ISO8601,
  "payload":         bytes,       // Subsystem-specific, schema-versioned
  "payload_version": uint32,      // Schema version for payload
  "prev_hash":       string,      // Hash of previous entry (chain integrity)
  "hash":            string,      // SHA-256 of this entry's canonical form
  "idempotency_key": string       // Caller-provided dedup key
}
```

### VTZ Attestation Token
```
{
  "att_id":      string,    // UUIDv7
  "ctx_id":      string,    // Bound context
  "src_zone":    string,    // Source VTZ identifier
  "tgt_zone":    string,    // Target VTZ identifier
  "iat":         uint64,    // Issued-at
  "exp":         uint64,    // Expiry (short-lived, max 30s)
  "nonce":       bytes,     // Replay prevention
  "sig":         bytes      // Zone-specific Ed25519 signature
}
```

For the complete schema catalog, enumerations, and backward-compatibility rules, see `forge-standards/INTERFACES.md`.

## Error Handling Rules

### Fail-Closed Requirement
Every subsystem must treat unhandled errors, timeouts, and indeterminate states as DENY/REJECT. The only path to an ALLOW decision is an explicit, validated success from TrustFlow.

### Error Classification and Required Behavior

| Error Class | Examples | Required Action |
|---|---|---|
| **Authentication Failure** | Invalid CTX-ID, expired token, bad signature | Return 401. Do not retry. Emit audit event. |
| **Authorization Failure** | TrustFlow DENY, VTZ zone crossing denied | Return 403. Do not retry. Emit audit event with full decision context. |
| **Validation Failure** | Malformed request, schema mismatch, missing required field | Return 400. Do not retry. Log at WARN with sanitized request shape (no secrets). |
| **Downstream Timeout** | DTL write timeout, TrustFlow evaluation timeout | Fail the request. Return 504. Emit audit event with timeout context. Do not return a cached stale result. |
| **Downstream Unavailable** | DTL unreachable, audit sink down | Fail the request. Return 503. Report health check failure. Do not silently skip the unavailable dependency. |
| **Internal Error** | Panic, nil dereference, OOM | Return 500. Emit structured error to logging pipeline. Trigger alerting. Never expose stack traces to callers. |
| **Idempotency Conflict** | DTL duplicate idempotency key | Return 409. Return the original response if available. Do not re-execute. |
| **Rate Limiting** | CTX-ID issuance rate exceeded | Return 429 with `Retry-After` header. Emit metric. |

### Banned Error Handling Patterns
- **Do not swallow errors.** Every `err != nil` must result in a return, log, or propagation — never `_ = err`.
- **Do not use generic catch-all error messages.** Every error response must include a Forge-specific error code (e.g., `FORGE-CTX-001`) that maps to runbook entries.
- **Do not retry authorization failures.** A DENY is a DENY. Retrying a TrustFlow evaluation with the same inputs is a bug.
- **Do not log-and-continue on audit emission failures.** If the audit event cannot be written, the originating operation must fail.
- **Do not return partial success.** Forge operations are atomic — either the full operation succeeds (CTX-ID issued AND DTL written AND audit emitted) or the entire operation fails.

### Circuit Breaker Configuration
All inter-subsystem clients must implement circuit breakers with the following defaults:
- **Failure threshold:** 5 consecutive failures or >50% failure rate in a 10-second window.
- **Open duration:** 30 seconds.
- **Half-open probe:** 1 request.
- **On open circuit:** Fail closed (DENY/503), do not queue.

## Testing Requirements

### Coverage Rules
- **Minimum line coverage: 90%** for all subsystems. Measured per-subsystem, not aggregate.
- **Minimum branch coverage: 85%.** Every conditional that touches security logic (CTX-ID validation, TrustFlow evaluation, VTZ attestation) must have both branches covered.
- **100% coverage on all error paths** listed in the Error Handling Rules section. Every error return must have a test that triggers it.

### Mandatory Test Categories

| Category | Requirement |
|---|---|
| **Unit tests** | Every public function. Every exported type's constructor and methods. Mock all external dependencies. |
| **Negative tests** | Every API endpoint must have tests for: invalid CTX-ID, expired token, malformed request, missing required fields, replay attacks, zone crossing violations. |
| **Fail-closed tests** | Every subsystem must have tests proving it denies requests when dependencies are unavailable, when evaluation is indeterminate, and when timeouts occur. |
| **Contract tests** | Every inter-subsystem interface must have consumer-driven contract tests validating request/response schemas against `forge-standards/INTERFACES.md`. |
| **Integration tests** | End-to-end request flow: IdP → CTX-ID issuance