

# AGENTS.md — Forge Platform

Forge is a trust-enforcement runtime that validates every context identity (CTX-ID), virtualisation boundary (VTZ), and data-transit lineage (DTL) operation at the point of execution, rejecting any request that violates TrustFlow policy before side effects occur.

## How to Use This File

This file is the authoritative baseline for every code change in this repository — read it completely before writing any code. For subsystem-specific design rationale, protocol detail, and decision records, consult the full documents in `forge-docs/` (source TRDs and PRDs) and `forge-standards/` (synthesised architecture, interface contracts, and decision logs).

Key reference files to load when you need deeper context:

- `forge-standards/ARCHITECTURE.md` — canonical subsystem map, dependency graph, and deployment topology
- `forge-standards/INTERFACES.md` — every inter-subsystem contract with wire formats, error codes, and versioning rules
- `forge-standards/DECISIONS.md` — architectural decision records with rationale and trade-off analysis
- `forge-standards/ENGINEERING_STANDARDS.md` — complete coding standards, review gates, and CI policy

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| TrustFlow TRD | TRD | `forge-docs/trd-trustflow.md` | TrustFlow engine policy evaluation, rule grammar, chaining semantics, and fail-closed enforcement |
| CTX-ID TRD | TRD | `forge-docs/trd-ctx-id.md` | Context Identity lifecycle — issuance, rotation, revocation, and propagation across service boundaries |
| VTZ TRD | TRD | `forge-docs/trd-vtz.md` | Virtualisation Zones — boundary enforcement, resource isolation, cross-zone call gating |
| DTL TRD | TRD | `forge-docs/trd-dtl.md` | Data Transit Lineage — provenance tracking, hash-chain integrity, lineage query API |
| Forge Platform PRD | PRD | `forge-docs/prd-platform.md` | Product requirements, user personas, success metrics, and release milestones |
| Integration PRD | PRD | `forge-docs/prd-integration.md` | Third-party integration surface, SDK requirements, webhook contracts |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency DAG, deployment topology, scaling constraints |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All RPC/event schemas, wire formats, versioning policy, backward-compatibility rules |
| Decision Records | Standard | `forge-standards/DECISIONS.md` | ADRs for every major architectural choice with status, context, and consequences |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Code style, review gates, CI pipeline configuration, dependency policy |
| API Reference | Docs | `docs/api-reference.md` | Public API surface — REST and gRPC endpoints, auth headers, rate limits |
| Runbook | Docs | `docs/runbook.md` | Operational procedures — incident response, rollback, key rotation |
| Threat Model | Docs | `docs/threat-model.md` | Attack surfaces, mitigations, trust boundary diagram |

## Critical Rules — Non-Negotiable

1. **Fail closed on every TrustFlow evaluation.** If the TrustFlow engine cannot reach a definitive ALLOW decision, the request MUST be rejected — never default to permissive.
2. **Never skip CTX-ID validation.** Every inbound request — external or inter-service — MUST carry a valid CTX-ID that is cryptographically verified before any handler logic executes.
3. **Treat VTZ boundaries as hard isolation.** No pointer, file descriptor, shared-memory segment, or ambient credential may leak across a VTZ boundary; all cross-zone communication goes through the gated VTZ API.
4. **Append to the DTL chain before returning success.** Any operation that creates, transforms, or moves data MUST write a signed DTL record to the lineage store *before* the response is sent to the caller.
5. **Never log CTX-ID secrets, private keys, or raw authentication tokens.** Mask or omit these fields in every log path, error message, and diagnostic payload.
6. **Version every wire format with an explicit `schema_version` field.** Deserialise by dispatching on this field; never infer version from payload shape.
7. **Enforce the 90 % line-coverage minimum per subsystem.** CI blocks merge on any PR that drops a subsystem below this threshold.
8. **Write a negative test for every access-control branch.** Every TrustFlow rule, VTZ gate check, and CTX-ID validation path MUST have a test that asserts denial for an unauthorized input.
9. **Sign every DTL record with the originating service's Ed25519 key.** Do not use HMAC for DTL; only asymmetric signatures are acceptable for non-repudiation.
10. **Rotate CTX-IDs on a maximum 24-hour cadence.** Any CTX-ID older than its TTL MUST be rejected even if the signature is otherwise valid.
11. **Never introduce a circular dependency between subsystems.** The dependency DAG is: `CTX-ID → TrustFlow → VTZ → DTL`. Violations break startup ordering and are not mergeable.
12. **Use structured logging (JSON) with mandatory fields: `timestamp`, `ctx_id` (masked), `subsystem`, `trace_id`, `level`.** Unstructured log calls are rejected in review.
13. **Pin every third-party dependency to an exact version with a verified checksum.** Floating ranges and unpinned dependencies are forbidden.
14. **Gate all database schema changes behind a reviewed migration file in `migrations/`.** Never modify schema via ad-hoc SQL or ORM auto-migration in production.
15. **Run `forge lint`, `forge test`, and `forge security-scan` locally before pushing.** CI will reject the push if any of these fail; don't waste pipeline minutes.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────┐     ┌─────────┐
│   CTX-ID    │────▶│  TrustFlow   │────▶│   VTZ   │────▶│   DTL   │
│  Service    │     │   Engine     │     │ Manager │     │  Store  │
└─────────────┘     └──────────────┘     └─────────┘     └─────────┘
       │                   │                  │                │
       ▼                   ▼                  ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Forge Control Plane                          │
│  (Config, Key Management, Observability, Health)                 │
└──────────────────────────────────────────────────────────────────┘
```

### CTX-ID Service (`src/ctx-id/`)
- **Enforces:** Identity issuance, cryptographic verification, TTL-based expiration, and revocation list checks.
- **Called by:** Every inbound gateway and inter-service call as the first middleware.
- **Calls:** Key Management (for signing keys), Observability (for audit events).
- **NEVER:** Issue a CTX-ID without verifying the caller's authentication credential. NEVER extend a CTX-ID's TTL after issuance.

### TrustFlow Engine (`src/trustflow/`)
- **Enforces:** Policy evaluation against the rule set, decision caching, and audit trail of every ALLOW/DENY.
- **Called by:** VTZ Manager (before gating a cross-zone call), API Gateway (for request-level authorization), DTL Store (for lineage-query access control).
- **Calls:** CTX-ID Service (to resolve identity attributes for rule evaluation), Policy Store (for rule retrieval).
- **NEVER:** Cache a DENY decision beyond the current request. NEVER evaluate rules against a stale policy version — always check policy revision before evaluation.

### VTZ Manager (`src/vtz/`)
- **Enforces:** Zone boundary creation, resource quota assignment, cross-zone call gating, and zone lifecycle (create, freeze, destroy).
- **Called by:** Deployment orchestrator, TrustFlow (to query zone membership), application services (to request cross-zone calls).
- **Calls:** TrustFlow Engine (for authorization of every cross-zone call), CTX-ID Service (to validate zone-scoped identities).
- **NEVER:** Allow a direct memory or filesystem path between zones. NEVER destroy a zone with active DTL lineage records that have not been archived.

### DTL Store (`src/dtl/`)
- **Enforces:** Append-only lineage recording, hash-chain integrity verification, signed provenance records, and lineage query with access control.
- **Called by:** Every data-mutating service (to record lineage), audit tools (to query provenance), compliance exports.
- **Calls:** TrustFlow Engine (for query-access authorization), Key Management (for signature verification).
- **NEVER:** Mutate or delete an existing DTL record. NEVER return lineage data without a TrustFlow authorization check on the querying CTX-ID.

### Forge Control Plane (`src/control-plane/`)
- **Enforces:** Configuration distribution, key rotation orchestration, health checks, and observability aggregation.
- **Called by:** All subsystems (for config, keys, health reporting).
- **Calls:** External KMS, monitoring backends.
- **NEVER:** Serve stale configuration after a confirmed config update. NEVER expose raw key material over any non-mTLS channel.

## Interface Contracts — All Subsystems

### CTX-ID ↔ TrustFlow
- **Protocol:** gRPC over mTLS (port 9401).
- **Request:** `ResolveIdentity { ctx_id: string, requested_attributes: []string, schema_version: uint32 }`
- **Response:** `IdentityAttributes { attributes: map<string, string>, valid_until: timestamp, schema_version: uint32 }`
- **Timeout:** 50 ms hard deadline. On timeout, TrustFlow MUST treat identity as unresolved and DENY.
- **Idempotency:** Safe (read-only).

### TrustFlow ↔ VTZ
- **Protocol:** gRPC over mTLS (port 9402).
- **Request:** `AuthorizeCrossZone { ctx_id: string, source_zone: string, target_zone: string, action: string, schema_version: uint32 }`
- **Response:** `AuthzDecision { allowed: bool, reason: string, policy_revision: uint64, schema_version: uint32 }`
- **Timeout:** 100 ms. On timeout, VTZ MUST reject the cross-zone call.
- **Idempotency:** Safe (read-only, no side effects).

### VTZ ↔ DTL
- **Protocol:** gRPC over mTLS (port 9403).
- **Request (record):** `AppendLineage { ctx_id: string, zone_id: string, operation: string, data_hash: bytes, parent_record_id: string, signature: bytes, schema_version: uint32 }`
- **Response:** `LineageReceipt { record_id: string, chain_hash: bytes, timestamp: timestamp, schema_version: uint32 }`
- **Timeout:** 200 ms. On timeout, the calling service MUST retry with exponential backoff (max 3 attempts) before failing the operation.
- **Idempotency:** Idempotent by `(ctx_id, data_hash, parent_record_id)` tuple — duplicate appends return the existing receipt.

### DTL ↔ TrustFlow (Query Authorization)
- **Protocol:** gRPC over mTLS (port 9404).
- **Request:** `AuthorizeLineageQuery { ctx_id: string, query_scope: string, target_record_ids: []string, schema_version: uint32 }`
- **Response:** `AuthzDecision { allowed: bool, reason: string, policy_revision: uint64, schema_version: uint32 }`
- **Timeout:** 100 ms. On timeout, DTL MUST reject the query.

### All Subsystems ↔ Control Plane
- **Config pull:** HTTP GET over mTLS, `GET /config/{subsystem}?revision={last_seen}` — returns config blob + revision number. Poll every 10 s.
- **Health reporting:** gRPC `ReportHealth { subsystem: string, status: enum(HEALTHY, DEGRADED, UNHEALTHY), detail: string }` every 5 s.
- **Key retrieval:** gRPC `GetSigningKey { subsystem: string, key_purpose: string }` — returns wrapped key material, never plaintext outside the enclave boundary.

See `forge-standards/INTERFACES.md` for the complete protobuf definitions, all error codes, and backward-compatibility rules.

## Wire Formats and Schemas

### CTX-ID Token (JWT-like, Ed25519-signed)
```
{
  "schema_version": 3,
  "ctx_id": "ctxid-a3f8...",       // UUIDv7, globally unique
  "issuer": "ctxid-service-01",
  "subject": "svc:order-processor",
  "zone_id": "vtz-prod-us-east-1",
  "issued_at": 1719500000,          // Unix epoch seconds
  "expires_at": 1719586400,         // Max 24h from issued_at
  "attributes": {
    "role": "data-writer",
    "clearance": "L2"
  },
  "signature": "<Ed25519 signature over all preceding fields>"
}
```

### DTL Lineage Record
```
{
  "schema_version": 2,
  "record_id": "dtl-rec-b7c2...",   // UUIDv7
  "ctx_id": "ctxid-a3f8...",
  "zone_id": "vtz-prod-us-east-1",
  "operation": "TRANSFORM",          // CREATE | TRANSFORM | MOVE | DELETE_MARKER
  "data_hash": "<SHA-256 of data payload>",
  "parent_record_id": "dtl-rec-a1e0...",  // null for CREATE
  "chain_hash": "<SHA-256(parent.chain_hash + record_id + data_hash)>",
  "timestamp": 1719500042,
  "signature": "<Ed25519 signature by originating service>"
}
```

### TrustFlow Policy Rule
```
{
  "schema_version": 1,
  "rule_id": "tf-rule-0042",
  "priority": 100,                   // Lower number = higher priority
  "match": {
    "subject.role": "data-writer",
    "source_zone": "vtz-prod-*",
    "action": "CROSS_ZONE_WRITE"
  },
  "decision": "ALLOW",               // ALLOW | DENY — no other values
  "conditions": [
    { "field": "subject.clearance", "op": "gte", "value": "L2" }
  ],
  "expires_at": null                  // null = does not expire
}
```

Reference `forge-standards/INTERFACES.md` for the full protobuf/JSON schema catalog, all enum values, and field validation rules.

## Error Handling Rules

### Fail-Closed Requirement
Every subsystem MUST fail closed. If an authorization check, signature verification, or policy lookup cannot complete (timeout, network partition, internal error), the operation is DENIED. There is no "open" or "permissive" fallback mode anywhere in Forge.

### Error Categories and Required Responses

| Error Type | Required Action | Retry Allowed | Log Level |
|---|---|---|---|
| CTX-ID validation failure | Reject request, return `401 UNAUTHENTICATED` | No | WARN |
| CTX-ID expired | Reject request, return `401 UNAUTHENTICATED`, include `expired_at` in error detail | No — caller must obtain new CTX-ID | WARN |
| TrustFlow DENY | Reject request, return `403 PERMISSION_DENIED` with `rule_id` | No | INFO |
| TrustFlow timeout | Reject request, return `503 UNAVAILABLE` | Yes, caller may retry once | ERROR |
| VTZ boundary violation | Reject request, return `403 PERMISSION_DENIED` | No | WARN |
| DTL append failure | Fail the parent operation, return `500 INTERNAL` | Yes, up to 3 retries with exponential backoff | ERROR |
| DTL chain integrity mismatch | Halt all writes to affected chain, alert on-call, return `500 INTERNAL` | No — requires manual investigation | CRITICAL |
| Config fetch failure | Continue with last-known config for up to 60 s; after 60 s enter DEGRADED state and reject new requests | Yes, continuous retry | ERROR |
| Key retrieval failure | Reject all operations requiring that key, return `503 UNAVAILABLE` | Yes, continuous retry | CRITICAL |

### Banned Patterns
- **Never catch and swallow errors.** Every error MUST be logged and propagated or explicitly handled with a defined recovery path.
- **Never return a generic `200 OK` when an internal subsystem call failed.** Map internal failures to appropriate HTTP/gRPC error codes.
- **Never retry DENY decisions.** A TrustFlow DENY is authoritative for the evaluated policy revision.
- **Never use panic/abort for recoverable errors.** Reserve panics for invariant violations that indicate memory corruption or logic bugs.
- **Never embed error strings in conditional logic.** Use typed error codes (`FORGE_ERR_CTX_EXPIRED`, `FORGE_ERR_TF_TIMEOUT`, etc.) defined in `src/common/errors.rs`.

## Testing Requirements

### Coverage Rules
- **Minimum 90 % line coverage per subsystem.** CI blocks merge on any PR that drops below this. Measure with `forge test --coverage`.
- **100 % branch coverage on all TrustFlow rule evaluation paths.** Every match arm, condition operator, and priority-ordering branch must be exercised.
- **100 % branch coverage on CTX-ID validation and VTZ boundary checks.** These are security-critical paths.

### Mandatory Negative Tests
- Every TrustFlow rule MUST have at least one test asserting DENY for an unauthorized subject.
- Every CTX-ID validation function MUST have tests for: expired token, invalid signature, malformed payload, revoked CTX-ID, and missing required fields.
- Every VTZ gate MUST have a test with a cross-zone call where source and target zones are the same (self-loop — must be denied unless explicitly allowed by policy).
- Every DTL append MUST have a test with an invalid `parent_record_id` (broken chain) and a test with a forged signature.

### Fuzz Targets
- Maintain fuzz targets in `src/{subsystem}/fuzz/` for all deserialization paths.
- TrustFlow policy parser: fuzz the rule grammar with arbitrary byte inputs.
- CTX-ID token parser: fuzz with malformed JWTs, truncated signatures, oversized payloads.
- DTL record parser: fuzz `chain_hash` recomputation with corrupted inputs.
- Run fuzz targets in CI nightly for a minimum of 10 minutes per target. Track crash count in `forge-standards/fuzz-report.md`.

### Integration Tests
- `tests/integration/` contains end-to-end tests that spin up all subsystems via Docker Compose (`tests/docker-compose.yml`).
- Every cross-subsystem contract in the Interface Contracts section above MUST have a corresponding integration test.
- Integration tests run on every PR that touches more than one subsystem directory.

### Performance Tests
- Maintain latency benchmarks in `tests/perf/`. TrustFlow evaluation MUST complete in < 5 ms at p99 for a 1000-rule policy set.
- CTX-ID validation MUST complete in < 2 ms at p99.
- DTL append MUST complete in < 50 ms at p99 (excluding network).

## File Naming and Directory Layout

```
forge/
├── CLAUDE.md                          # This file