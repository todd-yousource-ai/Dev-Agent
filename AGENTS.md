

# AGENTS.md — Forge Platform

Forge is a trust-aware runtime platform that enforces identity verification, contextual authorization, and data lineage tracking across every request path, rejecting any operation that cannot produce a valid CTX-ID, VTZ clearance, and TrustFlow score at the point of execution.

## How to Use This File

This file is the authoritative baseline for all code generation, review, and refactoring in the Forge repository — read it fully before writing any code. For subsystem-specific detail, see `forge-docs/` for the full Technical Reference Documents (TRDs) and Product Requirements Documents (PRDs), and `forge-standards/` for synthesised architecture decisions and interface contracts.

**Key reference files to load when you need deeper context:**

- `forge-standards/ARCHITECTURE.md` — canonical subsystem map and dependency graph
- `forge-standards/INTERFACES.md` — all inter-subsystem wire formats and contracts
- `forge-standards/DECISIONS.md` — architectural decision log with rationale
- `forge-standards/SECURITY.md` — threat model, invariants, and hardening rules
- `forge-standards/TESTING.md` — coverage policy, fuzz targets, negative-test catalog

---

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Service TRD | TRD | `forge-docs/trd-ctx-id-service.md` | Context identity issuance, validation, propagation rules, and token lifecycle |
| VTZ Authorization TRD | TRD | `forge-docs/trd-vtz-authorization.md` | Vertical trust zone enforcement, clearance levels, zone boundary checks |
| TrustFlow Engine TRD | TRD | `forge-docs/trd-trustflow-engine.md` | Trust score computation, decay model, signal aggregation, threshold enforcement |
| DTL (Data Trust Lineage) TRD | TRD | `forge-docs/trd-dtl.md` | Data lineage graph construction, provenance tracking, tamper detection |
| Gateway & Ingress TRD | TRD | `forge-docs/trd-gateway-ingress.md` | Request admission, CTX-ID injection, rate limiting, TLS termination |
| Policy Engine TRD | TRD | `forge-docs/trd-policy-engine.md` | OPA/Rego policy evaluation, policy bundle management, audit logging |
| Audit Subsystem TRD | TRD | `forge-docs/trd-audit.md` | Immutable audit log, event schema, retention policy, tamper-evident sealing |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user stories, acceptance criteria, milestone plan |
| Identity & Access PRD | PRD | `forge-docs/prd-identity-access.md` | End-user and service identity requirements, federation, credential rotation |
| Architecture Overview | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, deployment topology |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All gRPC/REST contracts, protobuf schemas, event envelopes |
| Architectural Decisions | Standard | `forge-standards/DECISIONS.md` | ADR log — every major design choice with context and consequences |
| Security Standards | Standard | `forge-standards/SECURITY.md` | Threat model, cryptographic requirements, secret handling, hardening rules |
| Testing Standards | Standard | `forge-standards/TESTING.md` | Coverage policy, fuzz targets, integration test topology, negative-test catalog |

---

## Critical Rules — Non-Negotiable

1. **Never process a request without a valid CTX-ID.** Every inbound request must carry a CTX-ID issued by the CTX-ID Service; reject with `403` and audit-log the attempt if missing or malformed.

2. **Propagate CTX-ID on every outbound call.** Any service-to-service or service-to-datastore call must forward the originating CTX-ID in the `X-Ctx-Id` header (HTTP) or `ctx_id` metadata field (gRPC) — no exceptions.

3. **Enforce VTZ clearance at every zone boundary.** Before a request crosses a Vertical Trust Zone boundary, the calling service must present a VTZ token with a clearance level ≥ the target zone's minimum; fail closed with `403`.

4. **Compute TrustFlow score before authorization.** The TrustFlow Engine must return a score for the (identity, action, resource) tuple before the Policy Engine evaluates access; if TrustFlow is unreachable, deny the request.

5. **TrustFlow scores below threshold always deny.** If `TrustFlowScore < zone.min_trust_threshold`, the request is denied regardless of other policy outcomes — the Policy Engine must not override this.

6. **Record every state-changing operation in DTL.** Every write, update, delete, or permission change must produce a DTL lineage event containing `ctx_id`, `actor_id`, `resource_urn`, `operation`, `timestamp`, and `parent_hash`.

7. **Audit log entries are append-only and tamper-evident.** Never update or delete an audit record. Every entry must include a chained hash (`prev_hash`) linking to the prior entry; broken chains trigger a `TAMPER_ALERT`.

8. **Fail closed on every ambiguous state.** If any subsystem returns an error, timeout, or unexpected response during an authorization path, deny the request and emit a structured error event to the audit log.

9. **Never log secrets, tokens, or raw credentials.** Logging must redact all fields listed in `forge-standards/SECURITY.md § Redaction List`. Use the `forge/pkg/redact` package — do not hand-roll redaction.

10. **All cryptographic operations use `forge/pkg/crypto`.** Do not import `crypto/*` directly in application code. The `forge/pkg/crypto` wrapper enforces algorithm allowlists (Ed25519 for signing, AES-256-GCM for symmetric, Argon2id for hashing).

11. **Every protobuf and JSON schema must be backward-compatible.** Add fields only. Never remove or rename fields. Never change field numbers. Run `buf breaking` in CI on every PR that touches `.proto` files.

12. **All inter-service communication uses mTLS.** Plaintext HTTP between services is forbidden. The Gateway terminates external TLS; internal mesh traffic must use mTLS with certificates from the Forge CA.

13. **Policy bundles are signed and versioned.** The Policy Engine must verify the Ed25519 signature on every OPA bundle before loading. Unsigned or signature-invalid bundles must be rejected and the rejection audit-logged.

14. **Test coverage must meet or exceed 90% line coverage per package.** PRs that drop any package below 90% must not merge. Negative tests (malformed input, expired tokens, revoked clearances) are mandatory for every public API.

15. **Every error returned to a caller must include a Forge error code.** Use the canonical error codes in `forge/pkg/errors` (e.g., `FORGE-4010: CTX_ID_MISSING`, `FORGE-4031: VTZ_CLEARANCE_INSUFFICIENT`). Never return raw library errors to callers.

---

## Architecture Overview

### Subsystem Map

```
┌─────────────┐     ┌───────────────┐     ┌─────────────────┐
│   Gateway    │────▶│  CTX-ID Svc   │────▶│  TrustFlow Eng  │
│  & Ingress   │     └───────────────┘     └─────────────────┘
└──────┬───────┘              │                      │
       │                      ▼                      ▼
       │              ┌───────────────┐     ┌─────────────────┐
       └─────────────▶│ Policy Engine │◀────│  VTZ Authz Svc  │
                      └───────┬───────┘     └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             ┌────────────┐     ┌─────────────┐
             │ Audit Log  │     │  DTL Engine  │
             └────────────┘     └─────────────┘
```

**Gateway & Ingress** — Terminates external TLS, injects CTX-ID via CTX-ID Service call, applies rate limits. Calls: CTX-ID Service, Policy Engine. Called by: external clients. NEVER: bypass CTX-ID injection, forward requests without rate-limit evaluation.

**CTX-ID Service** — Issues, validates, and revokes context identity tokens. Calls: nothing (leaf service; reads from its own store). Called by: Gateway, all internal services for validation. NEVER: issue a CTX-ID without verifying the upstream TLS client certificate, cache a revoked CTX-ID as valid.

**TrustFlow Engine** — Computes a trust score from behavioral signals, credential age, device posture, and historical access patterns. Calls: signal stores (read-only). Called by: Policy Engine. NEVER: mutate signal stores, return a default score on internal error (must return error).

**VTZ Authorization Service** — Evaluates whether an identity's clearance level satisfies a target zone's minimum. Calls: CTX-ID Service (for identity lookup). Called by: Policy Engine. NEVER: grant clearance higher than what the identity's token asserts.

**Policy Engine** — Evaluates OPA/Rego policies combining VTZ clearance and TrustFlow score to produce allow/deny decisions. Calls: TrustFlow Engine, VTZ Authorization Service, Audit Log. Called by: Gateway, application services. NEVER: override a TrustFlow denial, load an unsigned policy bundle, cache a deny decision as allow.

**Audit Log** — Receives structured events from all subsystems, persists them in append-only tamper-evident storage. Calls: nothing (sink). Called by: all subsystems. NEVER: expose a delete or update API, accept events without a valid CTX-ID.

**DTL Engine** — Constructs and queries data lineage graphs. Each node is a data operation; each edge links parent to child via `parent_hash`. Calls: Audit Log (to emit lineage events). Called by: application services, Policy Engine (for provenance queries). NEVER: allow a lineage node without a valid `parent_hash` (except genesis nodes), serve lineage queries without CTX-ID validation.

---

## Interface Contracts — All Subsystems

### CTX-ID Service

```protobuf
service CtxIdService {
  rpc Issue(IssueCtxIdRequest) returns (IssueCtxIdResponse);
  rpc Validate(ValidateCtxIdRequest) returns (ValidateCtxIdResponse);
  rpc Revoke(RevokeCtxIdRequest) returns (RevokeCtxIdResponse);
}
```

- `IssueCtxIdRequest`: `actor_id (string)`, `source_zone (string)`, `client_cert_fingerprint (bytes)`, `requested_ttl_seconds (int32)`
- `IssueCtxIdResponse`: `ctx_id (string)`, `issued_at (google.protobuf.Timestamp)`, `expires_at (google.protobuf.Timestamp)`, `zone (string)`
- `ValidateCtxIdResponse`: `valid (bool)`, `actor_id (string)`, `zone (string)`, `remaining_ttl_seconds (int32)`, `revoked (bool)`

### TrustFlow Engine

```protobuf
service TrustFlowEngine {
  rpc ComputeScore(TrustFlowRequest) returns (TrustFlowResponse);
}
```

- `TrustFlowRequest`: `ctx_id (string)`, `actor_id (string)`, `action (string)`, `resource_urn (string)`
- `TrustFlowResponse`: `score (float)`, `confidence (float)`, `signals_used (repeated string)`, `computed_at (google.protobuf.Timestamp)`
- Score range: `[0.0, 1.0]`. Confidence range: `[0.0, 1.0]`. A score of `0.0` with confidence `0.0` means computation failed — treat as deny.

### VTZ Authorization Service

```protobuf
service VtzAuthzService {
  rpc CheckClearance(VtzCheckRequest) returns (VtzCheckResponse);
}
```

- `VtzCheckRequest`: `ctx_id (string)`, `actor_id (string)`, `target_zone (string)`, `requested_operation (string)`
- `VtzCheckResponse`: `allowed (bool)`, `actor_clearance_level (int32)`, `zone_min_clearance (int32)`, `denial_reason (string)`

### Policy Engine

```protobuf
service PolicyEngine {
  rpc Evaluate(PolicyEvalRequest) returns (PolicyEvalResponse);
}
```

- `PolicyEvalRequest`: `ctx_id (string)`, `actor_id (string)`, `action (string)`, `resource_urn (string)`, `context (google.protobuf.Struct)`
- `PolicyEvalResponse`: `decision (Decision)`, `trust_flow_score (float)`, `vtz_clearance_met (bool)`, `matched_policies (repeated string)`, `denial_reasons (repeated string)`
- `Decision` enum: `ALLOW = 0; DENY = 1; DENY_TRUST_SCORE = 2; DENY_VTZ_CLEARANCE = 3; DENY_POLICY = 4; ERROR = 5`

### DTL Engine

```protobuf
service DtlEngine {
  rpc RecordEvent(DtlEvent) returns (DtlEventAck);
  rpc QueryLineage(LineageQuery) returns (LineageGraph);
}
```

- `DtlEvent`: `ctx_id (string)`, `actor_id (string)`, `resource_urn (string)`, `operation (string)`, `timestamp (google.protobuf.Timestamp)`, `parent_hash (bytes)`, `payload_hash (bytes)`, `metadata (map<string, string>)`
- `DtlEventAck`: `event_hash (bytes)`, `sequence_number (int64)`, `accepted (bool)`
- `LineageQuery`: `resource_urn (string)`, `max_depth (int32)`, `since (google.protobuf.Timestamp)`

### Audit Log

```protobuf
service AuditLog {
  rpc Append(AuditEntry) returns (AuditAck);
  rpc Query(AuditQuery) returns (stream AuditEntry);
}
```

- `AuditEntry`: `entry_id (string)`, `ctx_id (string)`, `actor_id (string)`, `subsystem (string)`, `event_type (string)`, `timestamp (google.protobuf.Timestamp)`, `payload (google.protobuf.Struct)`, `prev_hash (bytes)`, `entry_hash (bytes)`
- `AuditAck`: `entry_id (string)`, `sequence_number (int64)`, `chain_valid (bool)`

Refer to `forge-standards/INTERFACES.md` for the full contract definitions, including HTTP/REST equivalents, header propagation rules, and event envelope schemas.

---

## Wire Formats and Schemas

### CTX-ID Token (JWT-like, Ed25519-signed)

```json
{
  "ctx_id": "forge-ctx-a1b2c3d4e5f6",
  "actor_id": "svc:payment-service",
  "zone": "vtz-financial",
  "clearance_level": 3,
  "issued_at": 1719849600,
  "expires_at": 1719853200,
  "trust_score_at_issue": 0.87,
  "sig": "<Ed25519 signature over canonical JSON of all other fields>"
}
```

### TrustFlow Signal Envelope

```json
{
  "signal_id": "string (UUID v7)",
  "signal_type": "enum: DEVICE_POSTURE | CREDENTIAL_AGE | BEHAVIOR_ANOMALY | GEO_VELOCITY | ACCESS_PATTERN",
  "actor_id": "string",
  "value": "float [0.0, 1.0]",
  "weight": "float [0.0, 1.0]",
  "observed_at": "ISO-8601 timestamp",
  "source": "string (emitting subsystem)"
}
```

### DTL Lineage Node

```json
{
  "event_hash": "bytes (SHA-256)",
  "ctx_id": "string",
  "actor_id": "string",
  "resource_urn": "string (forge:resource:<type>:<id>)",
  "operation": "enum: CREATE | UPDATE | DELETE | GRANT | REVOKE",
  "timestamp": "ISO-8601 timestamp",
  "parent_hash": "bytes (SHA-256, null for genesis)",
  "payload_hash": "bytes (SHA-256 of operation payload)",
  "metadata": "map<string, string>"
}
```

### Forge Error Response (all APIs)

```json
{
  "error": {
    "code": "FORGE-4031",
    "message": "VTZ clearance insufficient for target zone",
    "subsystem": "vtz-authz",
    "ctx_id": "forge-ctx-a1b2c3d4e5f6",
    "timestamp": "ISO-8601",
    "details": {}
  }
}
```

Refer to `forge-standards/INTERFACES.md` for the complete schema catalog, field validation rules, and versioning conventions.

---

## Error Handling Rules

### Failure Mode Matrix

| Failure Type | Action | HTTP Code | Forge Error Code |
|---|---|---|---|
| CTX-ID missing from request | Reject. Audit log. | `403` | `FORGE-4010` |
| CTX-ID expired | Reject. Audit log. | `403` | `FORGE-4011` |
| CTX-ID revoked | Reject. Audit log. Emit `REVOKED_ACCESS_ATTEMPT` event. | `403` | `FORGE-4012` |
| TrustFlow score below threshold | Reject. Audit log with score and threshold. | `403` | `FORGE-4031` |
| TrustFlow Engine unreachable | Reject (fail closed). Emit `SUBSYSTEM_UNAVAILABLE` event. | `503` | `FORGE-5031` |
| VTZ clearance insufficient | Reject. Audit log. | `403` | `FORGE-4032` |
| VTZ Authorization Service unreachable | Reject (fail closed). Emit `SUBSYSTEM_UNAVAILABLE` event. | `503` | `FORGE-5032` |
| Policy Engine error | Reject (fail closed). Audit log. | `500` | `FORGE-5020` |
| Policy bundle signature invalid | Reject bundle load. Alert. Continue serving with last valid bundle. | N/A (internal) | `FORGE-5021` |
| DTL parent_hash mismatch | Reject write. Emit `LINEAGE_INTEGRITY_VIOLATION`. | `409` | `FORGE-4090` |
| Audit log chain broken | Emit `TAMPER_ALERT` to ops channel. Halt writes to affected partition. | N/A (internal) | `FORGE-5090` |
| Downstream service timeout | Reject (fail closed). Audit log. Retry only if idempotent and within retry budget. | `504` | `FORGE-5040` |

### Banned Patterns

- **Never swallow errors.** Every error must be either handled (with audit event) or propagated. Empty `catch` / `recover` blocks are forbidden.
- **Never return `200 OK` with an error body.** Use appropriate HTTP status codes.
- **Never retry non-idempotent operations.** The `forge/pkg/retry` package enforces this — pass the idempotency flag.
- **Never fall back to "allow" on error.** There is no "soft fail" mode in Forge. If you cannot determine authorization state, deny.
- **Never construct