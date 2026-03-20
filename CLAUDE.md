

# CLAUDE.md — Forge Platform

Forge is a distributed trust-enforcement platform that validates every operation against cryptographic identity (CTX-ID), temporal authorization (VTZ), and policy-driven trust propagation (TrustFlow), failing closed at runtime on any violation.

## How to Use This File

This file is the authoritative baseline for all code changes in the Forge repository — read it completely before writing any code. For subsystem-specific implementation detail, see `forge-docs/` for full TRDs and PRDs, and `forge-standards/` for synthesised architecture documents, interface contracts, and decision records.

**Key reference files to load when working on specific areas:**
- `forge-standards/ARCHITECTURE.md` — canonical subsystem map and dependency graph
- `forge-standards/INTERFACES.md` — every public interface contract with types and preconditions
- `forge-standards/DECISIONS.md` — architectural decision log with rationale
- `forge-standards/SECURITY.md` — threat model, trust boundaries, and mitigation catalog

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Technical Reference | TRD | `forge-docs/trd-ctx-id.md` | Cryptographic identity lifecycle: key generation, rotation, revocation, binding to sessions |
| VTZ Technical Reference | TRD | `forge-docs/trd-vtz.md` | Temporal authorization tokens: issuance, scoping, expiration, clock-skew tolerance |
| TrustFlow Technical Reference | TRD | `forge-docs/trd-trustflow.md` | Trust propagation engine: policy evaluation, chain validation, delegation rules |
| DTL Technical Reference | TRD | `forge-docs/trd-dtl.md` | Distributed Trust Ledger: append-only audit log, consistency protocol, compaction |
| Policy Engine Technical Reference | TRD | `forge-docs/trd-policy-engine.md` | Policy definition language, evaluation order, conflict resolution, caching |
| Gateway Technical Reference | TRD | `forge-docs/trd-gateway.md` | Ingress/egress enforcement: request validation, rate limiting, circuit breaking |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements: use cases, SLAs, compliance mandates, deployment targets |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, deployment topology, scaling constraints |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All public APIs: method signatures, wire formats, preconditions, error codes |
| Decision Log | Standard | `forge-standards/DECISIONS.md` | Numbered ADRs with context, decision, consequences for every architectural choice |
| Security Standard | Standard | `forge-standards/SECURITY.md` | Threat model, trust boundaries, required mitigations, penetration test schedule |
| Testing Standard | Standard | `forge-standards/TESTING.md` | Coverage requirements, fuzz targets, integration test topology, CI gate criteria |

## Critical Rules — Non-Negotiable

1. **Fail closed on every authorization check.** If CTX-ID validation, VTZ verification, or TrustFlow evaluation returns an error or timeout, deny the operation — never default to allow.
2. **Validate CTX-ID before reading the request body.** Identity binding happens at the transport layer; no subsystem may process payload bytes from an unverified identity.
3. **Treat VTZ tokens as immutable after issuance.** Never mutate a VTZ token in place — issue a new token with a new expiration and revoke the old one atomically.
4. **Enforce VTZ clock-skew tolerance of ≤ 5 seconds.** Reject any token whose `nbf` or `exp` falls outside this window relative to the local monotonic clock.
5. **Write to the DTL before returning success to the caller.** Every state-changing operation must be durably logged in the Distributed Trust Ledger; if the DTL write fails, roll back and return an error.
6. **Never bypass TrustFlow evaluation with hardcoded role checks.** All authorization decisions route through the TrustFlow policy engine — no inline `if role == "admin"` patterns.
7. **Rotate CTX-ID signing keys on the schedule defined in `trd-ctx-id.md`.** Key rotation is automated; manual key management code is forbidden.
8. **Scope every VTZ token to exactly one resource and one action.** Wildcard scopes (`resource: "*"`) are banned in production token issuance paths.
9. **Propagate trace context (CTX-ID, VTZ reference, span ID) on every inter-service call.** Missing trace headers cause the receiving service to reject the request.
10. **Never log secret material.** CTX-ID private keys, VTZ signing secrets, TrustFlow policy-engine secrets, and DTL encryption keys must never appear in log output at any level including DEBUG.
11. **Pin all cryptographic algorithm identifiers.** Do not accept algorithm negotiation from callers — the server dictates `alg` in every cryptographic operation.
12. **Return structured error responses with Forge error codes.** Every error response includes `forge_error_code`, `subsystem`, `message`, and `trace_id` — never return raw stack traces.
13. **Gate every PR on ≥ 90% line coverage and zero failing tests.** CI must block merge if coverage drops or any test — unit, integration, or fuzz — fails.
14. **Enforce schema validation at subsystem boundaries.** Every inbound payload is validated against the canonical schema before deserialization into domain types.
15. **Never introduce circular dependencies between subsystems.** The dependency graph is a DAG: Gateway → TrustFlow → Policy Engine → DTL; CTX-ID and VTZ are leaf dependencies consumed by all.

## Architecture Overview

```
┌──────────┐     ┌───────────┐     ┌──────────────┐     ┌─────┐
│  Gateway  │────▶│ TrustFlow │────▶│ Policy Engine│────▶│ DTL │
└──────────┘     └───────────┘     └──────────────┘     └─────┘
     │                │                    │
     ▼                ▼                    ▼
  ┌───────┐       ┌─────┐            ┌─────────┐
  │CTX-ID │       │ VTZ │            │ Schema  │
  └───────┘       └─────┘            │ Registry│
                                     └─────────┘
```

### Gateway
- **Enforces:** Transport-layer identity binding, request validation, rate limiting, circuit breaking.
- **Called by:** External clients, internal service-mesh sidecars.
- **Calls:** CTX-ID (identity verification), VTZ (token validation), TrustFlow (authorization).
- **Must NEVER:** Forward a request with an unverified CTX-ID or expired VTZ token.

### CTX-ID
- **Enforces:** Cryptographic identity lifecycle — key generation, binding, rotation, revocation.
- **Called by:** Gateway, TrustFlow, any subsystem performing identity verification.
- **Calls:** DTL (audit logging of key events), Hardware Security Module (HSM) interface for key storage.
- **Must NEVER:** Export private key material, accept externally-supplied key IDs without re-derivation.

### VTZ
- **Enforces:** Temporal authorization — token issuance, expiration, scope binding, revocation.
- **Called by:** Gateway (token validation), TrustFlow (scope checking during policy eval).
- **Calls:** CTX-ID (identity verification of token requestor), DTL (revocation list sync).
- **Must NEVER:** Issue a token without a bounded `exp`, reuse a revoked token ID (`jti`).

### TrustFlow
- **Enforces:** Trust propagation — evaluates policy chains, validates delegation depth, computes effective permissions.
- **Called by:** Gateway (per-request authorization), internal services (delegation checks).
- **Calls:** Policy Engine (rule evaluation), VTZ (scope verification), DTL (trust chain audit).
- **Must NEVER:** Cache authorization decisions beyond the TTL of the shortest-lived input token.

### Policy Engine
- **Enforces:** Policy evaluation — parses policy definitions, resolves conflicts (deny-overrides), returns deterministic decisions.
- **Called by:** TrustFlow exclusively.
- **Calls:** Schema Registry (policy schema validation), DTL (policy change audit).
- **Must NEVER:** Execute arbitrary code from policy definitions — the policy language is declarative only.

### DTL (Distributed Trust Ledger)
- **Enforces:** Append-only audit integrity — every trust-relevant event is recorded with cryptographic chaining.
- **Called by:** All subsystems for audit writes; compliance services for reads.
- **Calls:** Storage backend (pluggable: PostgreSQL, FoundationDB, or S3-compatible).
- **Must NEVER:** Delete or overwrite an existing ledger entry — compaction creates summary records but preserves originals.

### Schema Registry
- **Enforces:** Canonical schema definitions for all wire formats and internal types.
- **Called by:** Gateway (request validation), Policy Engine (policy schema validation), all subsystems at boundaries.
- **Calls:** Nothing — it is a leaf service serving static schemas.
- **Must NEVER:** Accept schema registrations that break backward compatibility without a version bump.

## Interface Contracts — All Subsystems

### CTX-ID

```
CtxIdService.Verify(request: VerifyRequest) -> VerifyResponse
  VerifyRequest  { ctx_id: string, signature: bytes, payload_hash: bytes }
  VerifyResponse { valid: bool, identity: Identity, error: ForgeError? }
  Precondition: ctx_id is non-empty, signature length matches algorithm.
  Postcondition: if valid==true, identity is fully populated.
  Failure: returns valid=false with forge_error_code; never throws.

CtxIdService.Rotate(request: RotateRequest) -> RotateResponse
  RotateRequest  { ctx_id: string, rotation_proof: bytes }
  RotateResponse { new_ctx_id: string, effective_at: timestamp, error: ForgeError? }
  Precondition: rotation_proof is signed by the current active key.
  Postcondition: old key enters grace period; new key is immediately valid.
```

### VTZ

```
VtzService.Issue(request: IssueRequest) -> IssueResponse
  IssueRequest  { ctx_id: string, resource: string, action: string, ttl_seconds: uint32 }
  IssueResponse { token: string, jti: string, exp: timestamp, error: ForgeError? }
  Precondition: ctx_id is verified, resource != "*", action != "*", ttl_seconds ≤ MAX_VTZ_TTL.
  Postcondition: token is signed, DTL entry written.

VtzService.Validate(request: ValidateRequest) -> ValidateResponse
  ValidateRequest  { token: string }
  ValidateResponse { valid: bool, claims: VtzClaims, error: ForgeError? }
  Precondition: token is non-empty.
  Postcondition: if valid==true, claims.exp > now - CLOCK_SKEW_TOLERANCE.

VtzService.Revoke(request: RevokeRequest) -> RevokeResponse
  RevokeRequest  { jti: string, reason: string }
  RevokeResponse { revoked: bool, error: ForgeError? }
  Precondition: jti exists in the issuance log.
  Postcondition: token is immediately invalid; revocation propagated to all VTZ caches within 2 seconds.
```

### TrustFlow

```
TrustFlowService.Evaluate(request: EvalRequest) -> EvalResponse
  EvalRequest  { ctx_id: string, vtz_token: string, resource: string, action: string, context: map<string,string> }
  EvalResponse { decision: ALLOW|DENY, reasons: []string, policy_ids: []string, error: ForgeError? }
  Precondition: ctx_id verified, vtz_token validated, resource and action non-empty.
  Postcondition: DTL audit entry written for decision. decision is DENY if any input validation fails.
```

### DTL

```
DtlService.Append(request: AppendRequest) -> AppendResponse
  AppendRequest  { subsystem: string, event_type: string, payload: bytes, prev_hash: bytes }
  AppendResponse { entry_id: string, hash: bytes, timestamp: timestamp, error: ForgeError? }
  Precondition: prev_hash matches the current head; payload ≤ MAX_DTL_ENTRY_SIZE.
  Postcondition: entry is durable and hash-chained before response is sent.

DtlService.Query(request: QueryRequest) -> QueryResponse
  QueryRequest  { subsystem: string?, event_type: string?, from: timestamp, to: timestamp, limit: uint32 }
  QueryResponse { entries: []DtlEntry, has_more: bool, error: ForgeError? }
```

See `forge-standards/INTERFACES.md` for the complete contract catalog including Gateway, Policy Engine, Schema Registry, and all internal helper interfaces.

## Wire Formats and Schemas

### ForgeError (universal error envelope)
```json
{
  "forge_error_code": "string — e.g. VTZ_EXPIRED, CTX_ID_REVOKED, TRUSTFLOW_DENY",
  "subsystem": "string — e.g. gateway, ctx-id, vtz, trustflow, dtl",
  "message": "string — human-readable, no secrets",
  "trace_id": "string — 32-hex-char trace identifier",
  "timestamp": "string — RFC 3339 with nanoseconds"
}
```

### VtzClaims
```json
{
  "jti": "string — unique token ID, UUIDv7",
  "sub": "string — CTX-ID of the subject",
  "resource": "string — fully qualified resource URN",
  "action": "string — one of: read, write, delete, admin",
  "iss": "string — issuing VTZ node ID",
  "iat": "uint64 — issued-at, Unix epoch seconds",
  "nbf": "uint64 — not-before, Unix epoch seconds",
  "exp": "uint64 — expiration, Unix epoch seconds",
  "sig": "bytes — Ed25519 or ES256 signature over canonical JSON"
}
```

### DtlEntry
```json
{
  "entry_id": "string — UUIDv7",
  "subsystem": "string",
  "event_type": "string",
  "payload": "bytes — opaque, schema-validated by subsystem",
  "prev_hash": "bytes — SHA-256 of the previous entry",
  "hash": "bytes — SHA-256 of this entry (entry_id || subsystem || event_type || payload || prev_hash || timestamp)",
  "timestamp": "string — RFC 3339 with nanoseconds, server-assigned"
}
```

### Identity
```json
{
  "ctx_id": "string — the public identity handle",
  "public_key": "bytes — DER-encoded public key",
  "algorithm": "string — Ed25519 | ES256 (server-pinned, never negotiated)",
  "created_at": "string — RFC 3339",
  "rotation_generation": "uint32 — monotonically increasing"
}
```

Reference `forge-standards/INTERFACES.md` for the full schema catalog including Policy definitions, Gateway request/response envelopes, and Schema Registry metadata.

## Error Handling Rules

1. **Fail closed.** Any error during CTX-ID verification, VTZ validation, TrustFlow evaluation, or DTL append results in denial of the operation. There is no "soft fail" mode.
2. **Classify errors into three categories:**
   - **Client errors (4xx / `FORGE_CLIENT_*`):** Invalid input, expired tokens, revoked identities. Return immediately with the structured `ForgeError` envelope.
   - **Upstream errors (5xx / `FORGE_UPSTREAM_*`):** A dependent subsystem is unavailable. Apply circuit-breaker logic; do not retry inline on the request path. Return `503` with `retry_after`.
   - **Internal errors (5xx / `FORGE_INTERNAL_*`):** Bugs, assertion failures, OOM. Log at ERROR with full trace context, return generic `500` with trace_id — no stack trace in the response.
3. **Banned patterns:**
   - `catch (Exception e) { return ok(); }` — swallowing errors is a fireable offense.
   - Returning HTTP `200` with an error payload in the body.
   - Using string matching on error messages for control flow — use `forge_error_code` exclusively.
   - Logging and re-throwing without adding context — wrap with subsystem and operation.
4. **Timeout defaults:** All inter-subsystem calls enforce a 2-second deadline. If a subsystem does not respond, treat as `FORGE_UPSTREAM_TIMEOUT` and fail closed.
5. **Circuit breaker thresholds:** 5 consecutive failures or >50% error rate in a 10-second window opens the circuit. Half-open after 30 seconds with a single probe request.
6. **DTL write failures:** If the DTL append fails after 2 retries (exponential backoff, max 500ms total), the originating operation MUST fail. Do not proceed without an audit record.

## Testing Requirements

1. **Minimum 90% line coverage on every subsystem.** CI blocks merge on any drop below this threshold.
2. **Every public interface method has:**
   - At least one positive test (happy path with valid inputs).
   - At least one negative test per documented precondition (e.g., expired VTZ, revoked CTX-ID, wildcard scope).
   - At least one boundary test (e.g., `ttl_seconds == 0`, `ttl_seconds == MAX_VTZ_TTL`, clock skew at exactly ±5s).
3. **Fuzz targets are mandatory for:**
   - VTZ token parsing (`VtzService.Validate` with arbitrary byte input).
   - CTX-ID signature verification (`CtxIdService.Verify` with malformed signatures).
   - DTL entry deserialization (`DtlService.Query` response parsing).
   - Policy Engine rule evaluation (random policy + random request context).
4. **Integration tests run against the full subsystem graph.** Use `docker-compose.test.yml` to spin up all services. Integration tests must exercise:
   - Full request flow: Gateway → CTX-ID → VTZ → TrustFlow → Policy Engine → DTL.
   - Failure injection: kill each subsystem one at a time and verify fail-closed behavior.
   - Clock skew simulation: offset VTZ validation node by 6 seconds and verify rejection.
5. **No test may depend on execution order.** All tests run in parallel by default.
6. **Mocks are allowed only at subsystem boundaries.** Never mock internal functions within a subsystem — test the real implementation.
7. **Performance benchmarks run nightly.** Regressions >10% on p99 latency trigger an automatic alert and block the next release.

Reference `forge-standards/TESTING.md` for the complete test matrix and CI pipeline configuration.

## File Naming and Directory Layout

```
forge/
├── CLAUDE.md                          # THIS FILE — read first
├── forge-docs/                        # Source TRDs and PRDs (authoritative specs)
│   ├── trd-ctx-id.md
│   ├── trd-vtz.md
│   ├── trd-trustflow.md
│   ├── trd-dtl.md
│   ├── trd-policy-engine.md
│   ├── trd-gateway.md
│   └── prd-forge-platform.md
├── forge-standards/                   # Synthesised engineering standards
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   ├── DECISIONS.md
│   ├── SECURITY.md
│   └── TESTING.md
├── src/
│   ├── gateway/                       # Ingress/egress enforcement
│   │