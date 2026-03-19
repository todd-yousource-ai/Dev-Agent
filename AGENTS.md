

# AGENTS.md — Forge Platform

Forge is a trust-enforcing runtime platform that binds every operation to a cryptographically verified context identity (CTX-ID), routes all data through Verified Trust Zones (VTZ), and rejects any request that cannot satisfy its TrustFlow policy chain at the point of execution.

## How to Use This File

This file is the authoritative baseline for all code generation, review, and refactoring in this repository — read it completely before writing any code. For subsystem-specific implementation detail, consult the full TRDs in `forge-docs/` and the synthesised architectural standards in `forge-standards/`; the key reference files are:

- `forge-standards/ARCHITECTURE.md` — canonical subsystem map, dependency graph, and runtime invariants
- `forge-standards/INTERFACES.md` — every inter-subsystem contract, wire format, and schema definition
- `forge-standards/DECISIONS.md` — architectural decision log with rationale and constraints
- `forge-standards/ENGINEERING_STANDARDS.md` — complete coding standards, error handling, testing, and security rules

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, runtime invariants, deployment topology |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All inter-subsystem APIs, wire formats, schemas, versioning rules |
| Decision Log | Standard | `forge-standards/DECISIONS.md` | Architectural decisions, trade-off rationale, constraint records |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Coding conventions, error handling, testing requirements, security rules |
| CTX-ID Service TRD | TRD | `forge-docs/trd-ctx-id-service.md` | Context identity issuance, validation, rotation, revocation lifecycle |
| VTZ Runtime TRD | TRD | `forge-docs/trd-vtz-runtime.md` | Verified Trust Zone instantiation, boundary enforcement, attestation |
| TrustFlow Engine TRD | TRD | `forge-docs/trd-trustflow-engine.md` | Policy chain evaluation, rule composition, decision caching, audit hooks |
| DTL (Distributed Trust Ledger) TRD | TRD | `forge-docs/trd-dtl.md` | Append-only trust event log, replication, consistency model, pruning |
| Gateway Service TRD | TRD | `forge-docs/trd-gateway-service.md` | Ingress authentication, CTX-ID binding, rate limiting, request routing |
| Policy Admin API TRD | TRD | `forge-docs/trd-policy-admin-api.md` | Policy CRUD, versioning, staged rollout, audit trail |
| Attestation Service TRD | TRD | `forge-docs/trd-attestation-service.md` | Hardware/software attestation collection, verification, evidence storage |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user stories, acceptance criteria, release milestones |
| Threat Model | Reference | `forge-docs/threat-model.md` | Attack surfaces, trust boundaries, mitigations, residual risk register |
| Runbook | Operations | `docs/runbook.md` | Incident response, rollback procedures, operational playbooks |
| Branch Context | Reference | `docs/CONTEXT.md` | Current branch objectives, in-flight work, known tech debt |

## Critical Rules — Non-Negotiable

1. **Bind every request to a CTX-ID before any business logic executes.** A request without a validated CTX-ID must be rejected at the Gateway with a `401` — never pass it downstream.
2. **Validate CTX-ID signatures using the current key material from the CTX-ID Service on every call.** Never cache a "valid" boolean across requests; cache only the verified claims with a TTL ≤ 30 seconds.
3. **Enforce TrustFlow policy chains synchronously in the request path.** Do not defer policy evaluation to an async worker or background job — the response must not be sent until the full chain resolves.
4. **Fail closed on every error.** If the TrustFlow Engine is unreachable, the DTL is unavailable, or attestation cannot be verified, deny the request. Never fall back to an allow-by-default mode.
5. **Never mutate DTL entries.** The Distributed Trust Ledger is append-only. Any code that updates or deletes a DTL record is a critical defect. Corrections are modeled as new compensating entries.
6. **Enforce VTZ boundary isolation at the network and process level.** Code in one VTZ must not directly call code in another VTZ — all cross-zone communication transits the Gateway and re-evaluates TrustFlow policy.
7. **Sign all inter-subsystem messages with the originating service's CTX-ID.** Unsigned internal calls are forbidden; the receiving service must verify the signature before processing.
8. **Never log, serialize, or include raw cryptographic key material in error messages, traces, or API responses.** Log only key identifiers (fingerprints).
9. **Version every API and wire format using the `Forge-API-Version` header.** Breaking changes require a new major version; the previous version must remain operational for a minimum of two release cycles.
10. **Write DTL entries for every trust-relevant state change** — CTX-ID issuance, revocation, policy evaluation result, attestation verdict, VTZ creation, and VTZ destruction.
11. **Enforce idempotency on all mutating Gateway endpoints** using the `Forge-Idempotency-Key` header. Replayed requests must return the original response, not re-execute side effects.
12. **Run the full TrustFlow policy chain in a deterministic, sandboxed evaluator.** Policy rules must not perform I/O, spawn threads, or access the filesystem — they receive only the immutable request context and policy data.
13. **Require attestation evidence to be fresh.** Attestation results older than the `max_attestation_age` configuration value (default: 300 seconds) must be re-fetched before a VTZ can be instantiated or renewed.
14. **Maintain ≥ 90% line coverage on every subsystem, with 100% coverage on all CTX-ID validation and TrustFlow evaluation code paths.** PRs that reduce coverage below threshold must not merge.
15. **Never import a dependency that has not been reviewed, pinned to an exact version, and recorded in the dependency allowlist** (`forge-standards/approved-deps.lock`). No floating version ranges.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Gateway Service                           │
│  Ingress point. Authenticates external requests, binds CTX-ID,   │
│  enforces rate limits, routes to internal subsystems.            │
│  Calls: CTX-ID Service, TrustFlow Engine                        │
│  Called by: External clients                                     │
│  NEVER: bypass TrustFlow evaluation; forward unvalidated CTX-IDs │
└──────────────┬──────────────────────┬────────────────────────────┘
               │                      │
       ┌───────▼───────┐      ┌───────▼────────┐
       │  CTX-ID       │      │  TrustFlow     │
       │  Service      │      │  Engine        │
       │               │      │                │
       │ Issues,       │      │ Evaluates      │
       │ validates,    │      │ policy chains  │
       │ rotates,      │      │ synchronously. │
       │ revokes       │      │ Returns allow/ │
       │ context IDs.  │      │ deny + reason. │
       │               │      │                │
       │ Calls: DTL    │      │ Calls: DTL,    │
       │ Called by:     │      │  Policy Admin  │
       │  Gateway,     │      │  API           │
       │  all services │      │ Called by:     │
       │ NEVER: issue  │      │  Gateway, VTZ  │
       │  a CTX-ID     │      │  Runtime       │
       │  without      │      │ NEVER: perform │
       │  writing DTL  │      │  I/O inside    │
       │  entry        │      │  policy eval   │
       └───────┬───────┘      └───────┬────────┘
               │                      │
       ┌───────▼──────────────────────▼────────┐
       │              DTL                       │
       │  Append-only trust event ledger.       │
       │  Records all trust-relevant events.    │
       │  Replicated across availability zones. │
       │  Calls: nothing (leaf node)            │
       │  Called by: all subsystems              │
       │  NEVER: allow mutation or deletion      │
       └───────────────────┬───────────────────┘
                           │
       ┌───────────────────▼───────────────────┐
       │          VTZ Runtime                   │
       │  Instantiates Verified Trust Zones.    │
       │  Enforces process + network isolation. │
       │  Requires fresh attestation.           │
       │  Calls: Attestation Service,           │
       │         TrustFlow Engine, DTL          │
       │  Called by: Gateway (zone creation),    │
       │            Orchestrator                │
       │  NEVER: allow cross-zone direct calls  │
       └───────────────────┬───────────────────┘
                           │
       ┌───────────────────▼───────────────────┐
       │       Attestation Service              │
       │  Collects and verifies HW/SW evidence. │
       │  Returns signed attestation verdicts.  │
       │  Calls: DTL                            │
       │  Called by: VTZ Runtime                 │
       │  NEVER: cache verdicts beyond           │
       │         max_attestation_age             │
       └───────────────────────────────────────┘

       ┌───────────────────────────────────────┐
       │       Policy Admin API                 │
       │  CRUD for TrustFlow policy rules.      │
       │  Enforces versioning + staged rollout. │
       │  Calls: DTL, TrustFlow Engine (reload) │
       │  Called by: Operators (admin UI/CLI)    │
       │  NEVER: allow policy activation without │
       │         a DTL audit entry               │
       └───────────────────────────────────────┘
```

## Interface Contracts — All Subsystems

### Gateway → CTX-ID Service

```
POST /internal/ctx-id/validate
Forge-API-Version: 1
Content-Type: application/json

Request:
{
  "raw_token": "<opaque CTX-ID token>",
  "request_origin": "<IP or service name>",
  "timestamp_utc": "<ISO-8601>"
}

Response 200:
{
  "valid": true,
  "ctx_id": "<canonical CTX-ID string>",
  "claims": { "sub": "...", "scope": [...], "vtz": "...", "exp": <unix_ts> },
  "key_fingerprint": "<hex>"
}

Response 401:
{
  "valid": false,
  "error_code": "CTX_EXPIRED | CTX_REVOKED | CTX_SIGNATURE_INVALID",
  "message": "<human-readable>"
}
```

### Gateway → TrustFlow Engine

```
POST /internal/trustflow/evaluate
Forge-API-Version: 1
Content-Type: application/json

Request:
{
  "ctx_id": "<canonical CTX-ID>",
  "claims": { ... },
  "action": "<operation name>",
  "resource": "<resource identifier>",
  "environment": { "ip": "...", "vtz_id": "...", "timestamp_utc": "..." }
}

Response 200:
{
  "decision": "ALLOW | DENY",
  "policy_chain": ["policy-a:v3", "policy-b:v1"],
  "reason": "<human-readable if DENY>",
  "dtl_entry_id": "<UUID of the recorded evaluation>"
}
```

### Any Subsystem → DTL

```
POST /internal/dtl/append
Forge-API-Version: 1
Content-Type: application/json

Request:
{
  "event_type": "CTX_ISSUED | CTX_REVOKED | POLICY_EVALUATED | VTZ_CREATED | VTZ_DESTROYED | ATTESTATION_VERIFIED | POLICY_ACTIVATED",
  "actor_ctx_id": "<CTX-ID of originating service>",
  "actor_signature": "<base64 detached signature over payload>",
  "timestamp_utc": "<ISO-8601>",
  "payload": { ... event-specific fields ... },
  "idempotency_key": "<UUID>"
}

Response 201:
{
  "entry_id": "<UUID>",
  "sequence_number": <monotonic uint64>,
  "hash": "<SHA-256 chain hash>"
}

Response 409: (duplicate idempotency_key)
{
  "entry_id": "<UUID of original>",
  "sequence_number": <original>,
  "hash": "<original>"
}
```

### VTZ Runtime → Attestation Service

```
POST /internal/attestation/verify
Forge-API-Version: 1
Content-Type: application/json

Request:
{
  "vtz_id": "<target VTZ identifier>",
  "evidence": "<base64-encoded attestation evidence>",
  "evidence_type": "TPM2_QUOTE | SEV_ATTESTATION | SGX_REPORT | SW_MEASUREMENT",
  "nonce": "<base64 anti-replay nonce>",
  "collected_at_utc": "<ISO-8601>"
}

Response 200:
{
  "verdict": "TRUSTED | UNTRUSTED",
  "measurements": { ... },
  "expires_at_utc": "<ISO-8601>",
  "dtl_entry_id": "<UUID>"
}
```

### Policy Admin API → TrustFlow Engine

```
POST /internal/trustflow/reload
Forge-API-Version: 1

Request:
{
  "policy_id": "<policy identifier>",
  "version": <uint32>,
  "activated_by_ctx_id": "<admin CTX-ID>",
  "dtl_entry_id": "<UUID of the activation audit record>"
}

Response 200:
{
  "loaded": true,
  "policy_id": "...",
  "version": <uint32>,
  "active_chain_hash": "<SHA-256>"
}
```

See `forge-standards/INTERFACES.md` for the complete contract catalog, including error schemas, pagination, streaming DTL queries, and health check endpoints.

## Wire Formats and Schemas

### CTX-ID Token Structure (JWT-like, Forge-specific)

```
Header:
{
  "alg": "EdDSA",
  "typ": "FORGE-CTX",
  "kid": "<key fingerprint hex>"
}

Payload:
{
  "sub": "<subject identifier>",          // string, required
  "iss": "forge-ctx-id-service",          // string, constant
  "iat": <unix_timestamp_seconds>,        // uint64, required
  "exp": <unix_timestamp_seconds>,        // uint64, required, max lifetime 3600s
  "jti": "<UUID>",                        // string, unique token ID
  "scope": ["read", "write", "admin"],    // string[], required, non-empty
  "vtz": "<VTZ identifier or null>",      // string|null
  "trust_level": <uint8>,                 // 0-255, computed by TrustFlow
  "attestation_ref": "<DTL entry UUID>"   // string|null
}

Signature: Ed25519 detached signature over `base64url(header).base64url(payload)`
```

### DTL Entry Schema

```
{
  "entry_id": "<UUID v7>",                // string, server-assigned
  "sequence_number": <uint64>,            // monotonically increasing, gapless
  "prev_hash": "<SHA-256 hex>",           // hash of previous entry
  "hash": "<SHA-256 hex>",               // SHA-256(prev_hash || canonical(payload))
  "event_type": "<enum string>",          // see DTL append contract
  "actor_ctx_id": "<string>",            // CTX-ID of writer
  "actor_signature": "<base64>",          // Ed25519 over canonical(payload)
  "timestamp_utc": "<ISO-8601>",          // server-validated, max skew 5s
  "payload": { ... },                     // event-specific, schema per event_type
  "idempotency_key": "<UUID>"             // client-provided
}
```

### TrustFlow Policy Rule Schema

```
{
  "policy_id": "<string>",                // unique identifier
  "version": <uint32>,                    // monotonically increasing
  "priority": <uint16>,                   // lower = evaluated first
  "effect": "ALLOW | DENY",              // terminal decision
  "conditions": [
    {
      "field": "claims.scope | claims.trust_level | environment.vtz_id | ...",
      "operator": "eq | neq | gt | lt | gte | lte | in | not_in | matches",
      "value": <any>
    }
  ],
  "description": "<human-readable>",
  "created_by_ctx_id": "<string>",
  "created_at_utc": "<ISO-8601>",
  "dtl_entry_id": "<UUID>"               // DTL record of creation
}
```

Reference `forge-standards/INTERFACES.md` for the full schema catalog including VTZ manifests, attestation evidence formats, and health check responses.

## Error Handling Rules

### Mandatory Patterns

1. **Fail closed.** Every subsystem defaults to DENY when an error, timeout, or unknown state occurs. There is no safe open state.
2. **Return structured errors.** All error responses use the Forge error envelope:
   ```json
   {
     "error_code": "<SUBSYSTEM_ERROR_NAME>",
     "message": "<human-readable, no secrets>",
     "request_id": "<trace ID>",
     "timestamp_utc": "<ISO-8601>"
   }
   ```
3. **Map all internal exceptions to a defined `error_code`.** Unhandled exceptions must be caught at the subsystem boundary, logged with full context, and returned as `INTERNAL_ERROR` with HTTP 500.
4. **Propagate `request_id` across all inter-subsystem calls.** Generate at the Gateway; never overwrite downstream.
5. **Set timeouts on every outbound call.** Default: 2 seconds for CTX-ID validation, 5 seconds for TrustFlow evaluation, 3 seconds for DTL append, 5 seconds for attestation verification. These are configurable but must never be infinite.
6. **Retry only on transient failures** (network timeout, 503). Retry at most 2 times with exponential backoff (base 100ms, jitter ±50ms). Never retry 4xx responses.
7. **Circuit-break on cascading failures.** If a downstream subsystem returns 3 consecutive 5xx responses within 10 seconds, open the circuit for 30 seconds. While the circuit is open, fail closed immediately — do not queue.

### Banned Patterns

- **Never catch and swallow exceptions silently.** Every catch block must log or propagate.
- **Never return HTTP 200 with an error in the body.** Use appropriate 4xx/5xx status codes.
- **Never include stack traces, file paths, or internal IPs in client-facing error responses.**
- **Never use generic string matching on