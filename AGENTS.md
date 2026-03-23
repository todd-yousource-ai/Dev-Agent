

# AGENTS.md — Forge Platform

Forge is a trust-aware distributed execution platform that enforces identity verification, context integrity, and policy compliance at every runtime boundary through CTX-ID propagation, VTZ isolation zones, and the TrustFlow authorization pipeline.

## How to Use This File

This file is the baseline contract for all code changes in the Forge repository — read it completely before writing or modifying any code. For subsystem-specific implementation detail, see `forge-docs/` for the full Technical Reference Documents (TRDs) and Product Requirements Documents (PRDs), and `forge-standards/` for synthesised architecture decisions, interface contracts, and engineering standards.

Key reference files:
- `forge-standards/ARCHITECTURE.md` — canonical subsystem map and dependency graph
- `forge-standards/INTERFACES.md` — all inter-subsystem wire formats, RPC contracts, and schema definitions
- `forge-standards/DECISIONS.md` — architectural decision log with rationale
- `forge-standards/ENGINEERING_STANDARDS.md` — coding rules, testing thresholds, and review gates
- `forge-docs/` — source TRDs and PRDs (see Document Index below)

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| TRD: CTX-ID Subsystem | TRD | `forge-docs/trd-ctx-id.md` | Context identity token generation, propagation, validation, and lifecycle management across service boundaries |
| TRD: VTZ Isolation Zones | TRD | `forge-docs/trd-vtz.md` | Virtual Trust Zone creation, enforcement boundaries, resource isolation, and zone lifecycle |
| TRD: TrustFlow Pipeline | TRD | `forge-docs/trd-trustflow.md` | Authorization pipeline stages, policy evaluation, trust score computation, and decision caching |
| TRD: DTL (Distributed Trust Ledger) | TRD | `forge-docs/trd-dtl.md` | Append-only trust event ledger, replication protocol, consistency model, and audit query interface |
| TRD: Policy Engine | TRD | `forge-docs/trd-policy-engine.md` | Policy definition language, rule compilation, runtime evaluation, and hot-reload mechanics |
| TRD: Forge Gateway | TRD | `forge-docs/trd-gateway.md` | Ingress routing, CTX-ID injection, rate limiting, TLS termination, and upstream trust negotiation |
| TRD: Observability Stack | TRD | `forge-docs/trd-observability.md` | Structured logging, distributed tracing with CTX-ID correlation, metric emission, and alert routing |
| PRD: Forge Platform | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user personas, trust model goals, and compliance targets |
| PRD: Multi-Tenant Trust Domains | PRD | `forge-docs/prd-multi-tenant.md` | Tenant isolation requirements, cross-tenant trust delegation, and domain boundary enforcement |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Canonical subsystem map, dependency graph, deployment topology, and runtime invariants |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All RPC definitions, wire formats, protobuf schemas, and inter-subsystem contracts |
| Architectural Decisions | Standard | `forge-standards/DECISIONS.md` | ADR log: every significant design choice with context, decision, and consequences |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Coding conventions, testing thresholds, CI gates, dependency rules, and review requirements |
| Security Model | Standard | `forge-standards/SECURITY_MODEL.md` | Threat model, trust boundaries, cryptographic requirements, and secret management |
| Runbook | Ops | `docs/RUNBOOK.md` | Operational procedures, incident response, rollback steps, and escalation paths |

## Critical Rules — Non-Negotiable

1. **Propagate CTX-ID on every inter-service call.** No RPC, message, or HTTP request may cross a service boundary without a valid CTX-ID in the request context. Drop the request if CTX-ID is absent or malformed.

2. **Validate CTX-ID signature before any processing.** Every receiving service must cryptographically verify the CTX-ID HMAC-SHA256 signature against the shared trust root before reading the payload. Never parse an unverified CTX-ID.

3. **Fail closed on all trust decisions.** If TrustFlow cannot reach a policy decision within the configured timeout (default 500ms), deny the request. Never fall back to allow-by-default.

4. **Never mutate DTL entries.** The Distributed Trust Ledger is append-only. Any code path that updates or deletes an existing DTL record is a critical bug. Corrections are new append events with back-references.

5. **Enforce VTZ boundary checks at the kernel level.** VTZ isolation must use OS-level namespace and cgroup enforcement. Application-layer-only isolation is forbidden — every VTZ must have a corresponding kernel-enforced boundary.

6. **Never log secrets, CTX-ID signing keys, or raw trust tokens.** All structured log output must pass through the `forge-redactor` filter. Log the CTX-ID fingerprint (first 8 hex chars), never the full token.

7. **Every TrustFlow policy change requires a DTL audit entry.** When a policy is created, modified, enabled, or disabled, emit a `POLICY_MUTATION` event to the DTL before the change takes effect. The DTL write must succeed or the policy change must abort.

8. **Use the Forge protobuf schemas as the single source of truth for wire formats.** Do not define ad-hoc JSON structures for inter-subsystem communication. All new fields require a schema migration in `proto/forge/` and a version bump.

9. **Pin all cryptographic algorithms explicitly.** Never use library defaults for hashing, signing, or encryption. Specify the algorithm (e.g., `ECDSA-P256-SHA256`, `AES-256-GCM`) at every call site. Banned: MD5, SHA-1, RSA-1024, DES, RC4.

10. **Gate every deployment on the full test suite passing at ≥90% line coverage per subsystem.** No subsystem may merge to `main` below this threshold. Integration tests between subsystems are mandatory, not optional.

11. **Scope VTZ resource quotas at creation time.** Every VTZ must declare CPU, memory, network, and storage limits in its manifest. A VTZ without explicit quotas must be rejected by the VTZ controller.

12. **Implement idempotency on all DTL append operations.** Every DTL event carries a client-generated idempotency key. The DTL must deduplicate within a 24-hour window. Callers must retry with the same key on transient failure.

13. **Never bypass the TrustFlow pipeline with hardcoded allow-lists.** Emergency access uses the `BREAK_GLASS` policy path, which still traverses TrustFlow, emits a DTL event with severity `CRITICAL`, and triggers an alert.

14. **Enforce schema validation at every ingress point.** The Forge Gateway, every gRPC server interceptor, and every message consumer must validate payloads against the registered protobuf schema before dispatching. Reject malformed payloads with a `FORGE_INVALID_SCHEMA` error code.

15. **Carry the VTZ zone identifier in every CTX-ID.** The `vtz_zone_id` field is mandatory in the CTX-ID claims. If a request's CTX-ID references a VTZ that does not match the executing zone, reject the request immediately with `FORGE_VTZ_MISMATCH`.

## Architecture Overview

### Subsystem Map

**Forge Gateway** (`src/gateway/`)
- **Enforces:** TLS termination, CTX-ID injection for external requests, rate limiting, request routing, schema validation at ingress.
- **Called by:** External clients, partner APIs, load balancers.
- **Calls:** TrustFlow (authorization check), CTX-ID Service (token minting), Observability (trace initiation).
- **Must NEVER:** Perform policy evaluation directly — always delegate to TrustFlow. Must never cache authorization decisions beyond a single request lifecycle.

**CTX-ID Service** (`src/ctx-id/`)
- **Enforces:** Identity token minting, signature generation, token validation, CTX-ID lifecycle (creation, propagation, revocation).
- **Called by:** Forge Gateway (mint on ingress), all internal services (validate on receive).
- **Calls:** DTL (audit trail for token events), Policy Engine (claim enrichment rules).
- **Must NEVER:** Store private signing keys in application memory beyond the signing operation. Must never issue a CTX-ID without a valid VTZ zone binding.

**TrustFlow Pipeline** (`src/trustflow/`)
- **Enforces:** Multi-stage authorization pipeline — authentication, policy evaluation, trust scoring, decision rendering.
- **Called by:** Forge Gateway, all internal services at trust boundaries.
- **Calls:** Policy Engine (rule evaluation), DTL (decision audit logging), CTX-ID Service (claims extraction).
- **Must NEVER:** Cache a DENY decision and later serve it as ALLOW. Must never skip pipeline stages — all stages execute in order even if an early stage is sufficient.

**Policy Engine** (`src/policy-engine/`)
- **Enforces:** Policy rule compilation, runtime evaluation, hot-reload without downtime, policy versioning.
- **Called by:** TrustFlow (rule evaluation), CTX-ID Service (claim enrichment).
- **Calls:** DTL (policy mutation audit), Observability (evaluation metrics).
- **Must NEVER:** Evaluate a policy that has not been compiled and checksum-verified. Must never execute policies from untrusted sources without signature verification.

**VTZ Controller** (`src/vtz/`)
- **Enforces:** Virtual Trust Zone lifecycle — creation, quota enforcement, namespace isolation, teardown.
- **Called by:** Orchestration layer, TrustFlow (zone verification), Forge Gateway (zone routing).
- **Calls:** DTL (zone lifecycle events), Observability (zone health metrics), kernel isolation APIs (cgroups, namespaces).
- **Must NEVER:** Create a zone without kernel-enforced isolation. Must never allow cross-zone memory access or network traffic outside explicit trust delegation rules.

**Distributed Trust Ledger (DTL)** (`src/dtl/`)
- **Enforces:** Append-only event storage, causal ordering, replication consistency (eventual with bounded staleness ≤ 2s), audit query interface.
- **Called by:** Every subsystem (audit events), compliance tooling (queries).
- **Calls:** Observability (replication lag metrics), storage backend.
- **Must NEVER:** Mutate or delete records. Must never serve reads from a replica with staleness exceeding the configured bound without marking the response as `STALE`.

**Observability Stack** (`src/observability/`)
- **Enforces:** Structured logging with CTX-ID correlation, distributed trace propagation, metric aggregation, alert routing.
- **Called by:** Every subsystem.
- **Calls:** External monitoring backends (Prometheus, Jaeger, log aggregators).
- **Must NEVER:** Emit unredacted secrets or full trust tokens. Must never drop CTX-ID correlation from traces.

## Interface Contracts — All Subsystems

### CTX-ID Token Structure
```protobuf
message CtxId {
  string token_id = 1;          // UUIDv7, globally unique
  string vtz_zone_id = 2;       // Bound VTZ zone identifier
  string subject = 3;           // Authenticated principal
  int64 issued_at = 4;          // Unix epoch millis
  int64 expires_at = 5;         // Unix epoch millis, max TTL 3600s
  map<string, string> claims = 6; // Policy-enriched claims
  bytes signature = 7;          // HMAC-SHA256 over fields 1-6
}
```

### TrustFlow Decision
```protobuf
message TrustFlowDecision {
  string request_id = 1;
  string ctx_id_fingerprint = 2; // First 8 hex chars of token_id
  Decision decision = 3;         // ALLOW, DENY, CHALLENGE
  float trust_score = 4;         // 0.0 – 1.0
  string policy_version = 5;
  repeated string matched_rules = 6;
  int64 evaluated_at = 7;
  string dtl_event_id = 8;      // Back-reference to audit entry
}

enum Decision {
  DENY = 0;
  ALLOW = 1;
  CHALLENGE = 2;
}
```

### DTL Event
```protobuf
message DtlEvent {
  string event_id = 1;          // UUIDv7
  string idempotency_key = 2;   // Client-generated, unique within 24h window
  string event_type = 3;        // e.g., TRUST_DECISION, POLICY_MUTATION, VTZ_LIFECYCLE, CTX_ID_ISSUED
  string ctx_id_fingerprint = 4;
  string vtz_zone_id = 5;
  int64 timestamp = 6;          // Unix epoch millis
  bytes payload = 7;            // Serialized event-specific protobuf
  string causal_parent = 8;     // event_id of causal predecessor, empty for root events
}
```

### VTZ Manifest
```protobuf
message VtzManifest {
  string zone_id = 1;
  string tenant_id = 2;
  ResourceQuota quota = 3;
  repeated TrustDelegation delegations = 4;
  int64 created_at = 5;
  string policy_binding = 6;    // Policy Engine policy ID governing this zone
}

message ResourceQuota {
  int32 cpu_millicores = 1;
  int64 memory_bytes = 2;
  int64 storage_bytes = 3;
  int32 network_bandwidth_mbps = 4;
}
```

### Inter-Service RPC Contracts
All inter-subsystem calls use gRPC with mutual TLS. Every RPC method must:
- Accept a `CtxId` in the `forge-ctx-id` metadata header.
- Return a `ForgeError` on failure (see Error Handling Rules below).
- Complete within the subsystem-specific deadline (see `forge-standards/INTERFACES.md` for per-method deadlines).

Reference `forge-standards/INTERFACES.md` for the full list of service definitions, method signatures, and streaming contracts.

## Wire Formats and Schemas

All schemas live in `proto/forge/` and are the single source of truth:
- `proto/forge/ctx_id.proto` — CTX-ID token and validation messages
- `proto/forge/trustflow.proto` — TrustFlow pipeline request/response, Decision enum
- `proto/forge/dtl.proto` — DTL events, queries, replication messages
- `proto/forge/vtz.proto` — VTZ manifest, lifecycle RPCs, quota definitions
- `proto/forge/policy.proto` — Policy definitions, compilation results, evaluation requests
- `proto/forge/gateway.proto` — Gateway routing rules, rate limit configs
- `proto/forge/observability.proto` — Structured log entries, trace context, metric definitions
- `proto/forge/errors.proto` — Canonical `ForgeError` type with error codes

**Key conventions:**
- All timestamps are `int64` Unix epoch milliseconds.
- All identifiers are UUIDv7 strings unless explicitly documented otherwise.
- All byte fields use raw bytes, not base64 — encoding happens at the transport layer.
- Field numbering: reserve fields 1-15 for high-frequency fields (single-byte varint tag).
- Schema evolution: add fields only. Never remove or renumber. Deprecated fields get `[deprecated = true]` and a comment with the deprecation date and replacement.

## Error Handling Rules

### Canonical Error Type
```protobuf
message ForgeError {
  string error_code = 1;        // FORGE_* namespaced code
  string message = 2;           // Human-readable, never contains secrets
  string ctx_id_fingerprint = 3;
  string subsystem = 4;         // Originating subsystem name
  map<string, string> metadata = 5;
  bool retryable = 6;
}
```

### Error Code Registry
| Code | Subsystem | Meaning | Retryable |
|---|---|---|---|
| `FORGE_CTX_ID_INVALID` | CTX-ID | Signature verification failed | No |
| `FORGE_CTX_ID_EXPIRED` | CTX-ID | Token past `expires_at` | No (re-mint) |
| `FORGE_VTZ_MISMATCH` | VTZ | CTX-ID zone does not match executing zone | No |
| `FORGE_VTZ_QUOTA_EXCEEDED` | VTZ | Resource quota exhausted | No |
| `FORGE_TRUST_DENIED` | TrustFlow | Policy evaluation returned DENY | No |
| `FORGE_TRUST_TIMEOUT` | TrustFlow | Pipeline did not complete in deadline | Yes |
| `FORGE_POLICY_COMPILE_ERROR` | Policy Engine | Policy failed compilation | No |
| `FORGE_DTL_WRITE_FAILED` | DTL | Append failed after retries | Yes |
| `FORGE_DTL_STALE_READ` | DTL | Replica staleness exceeded bound | Yes |
| `FORGE_INVALID_SCHEMA` | Gateway/All | Payload failed schema validation | No |
| `FORGE_RATE_LIMITED` | Gateway | Client exceeded rate limit | Yes (with backoff) |
| `FORGE_INTERNAL` | Any | Unexpected internal error | Yes |

### Failure Behavior Rules
1. **Fail closed.** On any trust-related error or timeout, deny the operation. There is no "fail open" path.
2. **Propagate error context.** Every `ForgeError` must include the `ctx_id_fingerprint` and originating `subsystem`. Do not swallow errors — wrap and propagate.
3. **Retry policy.** Retryable errors use exponential backoff: base 100ms, max 5s, jitter ±50ms, max 3 attempts. Non-retryable errors must not be retried.
4. **Circuit breaker.** Every inter-subsystem client must implement a circuit breaker. Open the circuit after 5 consecutive failures. Half-open probe after 10s.
5. **Banned patterns:**
   - `catch (Exception e) { /* ignore */ }` — never swallow exceptions.
   - Returning HTTP 200 with an error body — use proper status codes.
   - Logging an error and continuing as if it didn't happen when the error affects trust state.
   - Using `null`/`nil` as a sentinel for "unknown trust state" — use the explicit `FORGE_TRUST_TIMEOUT` error.
6. **DTL failure is blocking.** If a mandatory DTL audit write fails, the triggering operation must abort. Do not complete a trust-affecting action without its audit record.

## Testing Requirements

### Coverage Thresholds
- **Line coverage per subsystem: ≥ 90%.** Enforced by CI. No merge to `main` below this threshold.
- **Branch coverage per subsystem: ≥ 80%.** Tracked and reported; regressions block merge.
- **Integration test coverage: every inter-subsystem RPC method must have at least one positive and one negative integration test.**

### Mandatory Test Categories
1. **Unit tests:** Every public function. Every error path. Mock external dependencies at the gRPC stub level.
2. **Negative tests (required):** Every subsystem must test:
   - Invalid CTX-ID (bad signature, expired, missing `vtz_zone_id`).
   - TrustFlow DENY path.
   - DTL write failure handling (verify the operation aborts).
   - VTZ quota exhaustion.
   - Schema validation rejection.
3. **Integration tests:** Run in CI against real (not mocked) subsystem instances in an ephemeral test VTZ. Located in `tests/integration/`.
4. **Fuzz targets:** Every protobuf deserialization path must have a fuzz target. Located in `tests/fuzz/`. Run nightly for 10 minutes per