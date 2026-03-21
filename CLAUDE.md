

# CLAUDE.md — Forge Platform

Forge is a distributed trust-enforcement platform that binds every request to a cryptographically verified context identity (CTX-ID), enforces policy through TrustFlow pipelines, and fail-closes on any violation at runtime.

## How to Use This File

This file is the authoritative baseline for all LLM-assisted development on the Forge platform — read it completely before generating or modifying any code. For subsystem-specific depth, consult the full TRDs in `forge-docs/` and the synthesised architecture documents in `forge-standards/`.

**Key reference files:**
- `forge-standards/ARCHITECTURE.md` — subsystem map, data flows, deployment topology
- `forge-standards/INTERFACES.md` — all inter-subsystem contracts, wire formats, schemas
- `forge-standards/DECISIONS.md` — architectural decision records with rationale
- `forge-standards/ENGINEERING_STANDARDS.md` — coding rules, testing, error handling, security

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Service TRD | TRD | `forge-docs/trd-ctx-id-service.md` | Context identity issuance, validation, lifecycle, cryptographic binding |
| VTZ (Verification Trust Zone) TRD | TRD | `forge-docs/trd-vtz.md` | Trust boundary enforcement, zone isolation, ingress/egress policy |
| TrustFlow Engine TRD | TRD | `forge-docs/trd-trustflow-engine.md` | Policy pipeline execution, rule evaluation, decision propagation |
| DTL (Distributed Trust Ledger) TRD | TRD | `forge-docs/trd-dtl.md` | Immutable audit log, trust event recording, replication, tamper detection |
| Policy Authority TRD | TRD | `forge-docs/trd-policy-authority.md` | Policy definition, versioning, distribution, conflict resolution |
| Gateway Service TRD | TRD | `forge-docs/trd-gateway-service.md` | Edge ingress, CTX-ID extraction, request routing, rate limiting |
| Credential Vault TRD | TRD | `forge-docs/trd-credential-vault.md` | Secret storage, key rotation, HSM integration, envelope encryption |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user stories, acceptance criteria, roadmap |
| Trust Scoring PRD | PRD | `forge-docs/prd-trust-scoring.md` | Dynamic trust score computation, decay model, escalation thresholds |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, data flows, deployment topology, scaling constraints |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All RPC/event contracts, wire formats, schema definitions, versioning |
| Decision Records | Standard | `forge-standards/DECISIONS.md` | ADRs: why each architectural choice was made, alternatives rejected |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Code style, testing, error handling, security, CI/CD, review process |

## Critical Rules — Non-Negotiable

1. **Attach a CTX-ID to every request.** No request may pass the Gateway without a valid, non-expired CTX-ID bound to the originating principal.
2. **Fail closed on all policy evaluation errors.** If TrustFlow cannot reach a PERMIT decision, the request is DENIED — never default-allow.
3. **Never log, serialize, or expose raw secret material.** Credential Vault handles all secrets; all other subsystems receive opaque references only.
4. **Validate CTX-ID signatures at every trust boundary.** VTZ ingress points must cryptographically verify the CTX-ID — never trust upstream validation alone.
5. **Write every trust-relevant decision to the DTL before returning a response.** The audit record must be durable before the action is permitted to proceed.
6. **Never mutate a DTL record.** The Distributed Trust Ledger is append-only; implement corrections as compensating entries with back-references.
7. **Version all Policy Authority rule sets with monotonically increasing sequence numbers.** Never overwrite a published policy version.
8. **Enforce schema validation on all inter-subsystem messages at the boundary.** Reject malformed payloads; do not coerce or silently fix fields.
9. **Set explicit TTLs on every CTX-ID.** Maximum TTL is 3600 seconds; re-issuance is required beyond that — never extend in place.
10. **Encrypt all data in transit with mutual TLS (mTLS) between every subsystem pair.** Plaintext inter-service communication is forbidden in all environments including local development.
11. **Run TrustFlow policy evaluation as a pure function.** Policy evaluation must produce no side effects — logging and DTL writes happen in the calling orchestration layer.
12. **Return structured error responses with a Forge error code, not stack traces.** Every error code must be registered in `src/common/error_codes.rs`.
13. **Require at least 90% line coverage and 100% coverage of all DENY paths in every subsystem.** PRs below this threshold must not merge.
14. **Never bypass VTZ zone checks in test code.** Use the `ForgeTestHarness` to construct valid CTX-IDs for testing — mocking out zone enforcement is banned.
15. **Pin every dependency to an exact version in the lockfile.** Floating ranges and `latest` tags are forbidden in all build manifests.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Gateway    │────▶│  CTX-ID Svc  │────▶│   TrustFlow    │
│   Service    │     │              │     │   Engine       │
└──────┬──────┘     └──────────────┘     └───────┬────────┘
       │                                         │
       │            ┌──────────────┐             │
       │            │   Policy     │◀────────────┘
       │            │   Authority  │
       │            └──────────────┘
       │                                  ┌──────────────┐
       └──────────────────────────────────▶│     VTZ      │
                                          │  (Trust Zone) │
                                          └──────┬───────┘
                                                 │
                    ┌──────────────┐     ┌───────┴───────┐
                    │  Credential  │◀───▶│     DTL       │
                    │  Vault       │     │  (Ledger)     │
                    └──────────────┘     └───────────────┘
```

### Gateway Service
- **Enforces:** Edge authentication, CTX-ID extraction/injection, rate limiting, request routing.
- **Called by:** External clients, load balancers.
- **Calls:** CTX-ID Service (issuance/validation), VTZ (zone routing), TrustFlow (pre-route policy check).
- **NEVER:** Terminate a request without extracting or generating a CTX-ID. Never cache policy decisions.

### CTX-ID Service
- **Enforces:** Identity issuance, cryptographic signing, TTL enforcement, revocation checks.
- **Called by:** Gateway Service, VTZ (re-validation), TrustFlow (identity claims extraction).
- **Calls:** Credential Vault (signing keys), DTL (issuance audit).
- **NEVER:** Issue a CTX-ID without recording it in the DTL. Never issue with TTL > 3600s.

### TrustFlow Engine
- **Enforces:** Policy evaluation pipeline — input claims, rule matching, PERMIT/DENY decision.
- **Called by:** Gateway Service, VTZ (inter-zone transit decisions).
- **Calls:** Policy Authority (rule fetch), CTX-ID Service (claims extraction).
- **NEVER:** Produce side effects during evaluation. Never return an ambiguous result — output is PERMIT or DENY only.

### Policy Authority
- **Enforces:** Policy CRUD, version sequencing, distribution to TrustFlow instances, conflict detection.
- **Called by:** TrustFlow Engine (rule fetch), Admin API (policy management).
- **Calls:** DTL (policy change audit), Credential Vault (policy signing).
- **NEVER:** Allow two policies with the same ID and version number. Never serve an unsigned policy.

### VTZ (Verification Trust Zone)
- **Enforces:** Trust boundary isolation, zone-scoped access control, inter-zone transit policy, CTX-ID re-verification at zone ingress.
- **Called by:** Gateway Service (zone routing), other VTZ instances (cross-zone transit).
- **Calls:** CTX-ID Service (re-verification), TrustFlow (zone-transit policy), DTL (zone crossing audit).
- **NEVER:** Allow cross-zone traffic without a fresh TrustFlow evaluation. Never trust a CTX-ID validated by another zone.

### DTL (Distributed Trust Ledger)
- **Enforces:** Append-only audit storage, tamper detection via hash chaining, replication consistency, read queries for audit.
- **Called by:** All subsystems (audit writes), Admin API (audit reads/queries).
- **Calls:** Credential Vault (ledger signing keys).
- **NEVER:** Mutate or delete an existing record. Never accept a write without verifying the caller's CTX-ID.

### Credential Vault
- **Enforces:** Secret storage, envelope encryption, key rotation, HSM delegation, opaque reference issuance.
- **Called by:** CTX-ID Service (signing keys), Policy Authority (policy signing), DTL (ledger signing), Gateway (TLS certificates).
- **Calls:** HSM backend (key operations).
- **NEVER:** Return raw key material to any caller. Never store a key outside the HSM-backed envelope.

## Interface Contracts — All Subsystems

### Gateway → CTX-ID Service
- **Protocol:** gRPC over mTLS
- **Method:** `IssueCtxId(IssueRequest) → IssueResponse`
- **Method:** `ValidateCtxId(ValidateRequest) → ValidateResponse`
- `IssueRequest`: `{ principal_id: string, scope: string[], ttl_seconds: u32, metadata: map<string, string> }`
- `IssueResponse`: `{ ctx_id: string, expires_at: i64, signature: bytes }`
- `ValidateRequest`: `{ ctx_id: string, signature: bytes }`
- `ValidateResponse`: `{ valid: bool, principal_id: string, scope: string[], expires_at: i64, error_code: optional<string> }`
- **Invariant:** `ttl_seconds` must be ≤ 3600. Responses must include `error_code` on any non-valid result.

### Gateway → TrustFlow Engine
- **Protocol:** gRPC over mTLS
- **Method:** `Evaluate(EvalRequest) → EvalResponse`
- `EvalRequest`: `{ ctx_id: string, resource: string, action: string, environment: map<string, string> }`
- `EvalResponse`: `{ decision: enum(PERMIT, DENY), reasons: string[], policy_version: u64, evaluation_id: string }`
- **Invariant:** `decision` must be exactly PERMIT or DENY — no third state.

### TrustFlow → Policy Authority
- **Protocol:** gRPC over mTLS
- **Method:** `FetchPolicies(FetchRequest) → PolicySet`
- `FetchRequest`: `{ scope: string[], min_version: u64 }`
- `PolicySet`: `{ policies: Policy[], version: u64, signature: bytes }`
- `Policy`: `{ id: string, version: u64, rules: Rule[], priority: u32 }`
- **Invariant:** TrustFlow must verify `PolicySet.signature` before using any rule.

### All Subsystems → DTL
- **Protocol:** gRPC over mTLS
- **Method:** `Append(AuditEntry) → AppendAck`
- `AuditEntry`: `{ ctx_id: string, subsystem: string, event_type: string, payload: bytes, timestamp: i64 }`
- `AppendAck`: `{ entry_id: string, sequence: u64, hash: bytes }`
- **Invariant:** Caller must block on `AppendAck` before proceeding with the action being audited.

### All Subsystems → Credential Vault
- **Protocol:** gRPC over mTLS
- **Method:** `GetKeyReference(KeyRequest) → KeyReference`
- **Method:** `Sign(SignRequest) → SignResponse`
- **Method:** `Encrypt(EncryptRequest) → EncryptResponse`
- `KeyReference`: `{ ref_id: string, algorithm: string, created_at: i64, rotates_at: i64 }`
- **Invariant:** No response ever contains raw key bytes. `ref_id` is opaque and non-derivable.

See `forge-standards/INTERFACES.md` for the full contract specifications, field constraints, and backwards-compatibility rules.

## Wire Formats and Schemas

### CTX-ID Token Structure
```
{
  "ctx_id":        string,   // UUIDv7, globally unique
  "principal_id":  string,   // Issuing principal identifier
  "scope":         string[], // Permission scopes bound to this context
  "issued_at":     i64,      // Unix epoch seconds
  "expires_at":    i64,      // Unix epoch seconds, max issued_at + 3600
  "zone_id":       string,   // VTZ zone in which this CTX-ID was issued
  "signature":     bytes     // Ed25519 signature over all preceding fields
}
```

### DTL Audit Entry (On-Wire)
```
{
  "entry_id":      string,   // UUIDv7
  "sequence":      u64,      // Monotonically increasing per partition
  "ctx_id":        string,   // CTX-ID of the actor
  "subsystem":     string,   // Originating subsystem name
  "event_type":    string,   // Registered event type from event_types.rs
  "payload":       bytes,    // Subsystem-specific serialized payload
  "timestamp":     i64,      // Unix epoch microseconds
  "prev_hash":     bytes,    // SHA-256 hash of prior entry (chain integrity)
  "entry_hash":    bytes     // SHA-256 hash of this entry including prev_hash
}
```

### TrustFlow Evaluation Result (Internal)
```
{
  "evaluation_id": string,   // UUIDv7
  "decision":      enum,     // PERMIT | DENY — no other values
  "reasons":       string[], // Human-readable policy match explanations
  "matched_rules": string[], // Policy rule IDs that contributed to decision
  "policy_version": u64,     // Version of the PolicySet used
  "evaluated_at":  i64,      // Unix epoch microseconds
  "duration_us":   u64       // Evaluation duration in microseconds
}
```

### Trust Score Record
```
{
  "principal_id":  string,
  "score":         f64,      // Range [0.0, 1.0]
  "factors":       map<string, f64>,  // Contributing factor scores
  "decay_rate":    f64,      // Per-hour decay coefficient
  "computed_at":   i64,      // Unix epoch seconds
  "ttl_seconds":   u32       // Score validity window
}
```

Reference `forge-standards/INTERFACES.md` for the complete list of schemas, enum registries, and field validation constraints.

## Error Handling Rules

### Fail-Closed Mandate
Every subsystem must deny the in-flight operation when any of the following occur:
- CTX-ID validation fails or times out.
- TrustFlow evaluation returns an error or is unreachable.
- DTL append does not return an `AppendAck` within the configured timeout.
- Policy Authority returns an unsigned or version-regressed PolicySet.
- Any deserialization or schema validation failure on an inbound message.

### Structured Error Response Format
```
{
  "error_code":    string,   // Registered in src/common/error_codes.rs
  "message":       string,   // Safe for external display — no internals
  "subsystem":     string,   // Originating subsystem
  "ctx_id":        string,   // The CTX-ID of the failed request (if available)
  "timestamp":     i64       // Unix epoch microseconds
}
```

### Banned Patterns
- **No `unwrap()` or `expect()` on fallible operations in production code.** Use `?` propagation with typed errors.
- **No `panic!()` as flow control.** Panics are reserved for unrecoverable invariant violations only.
- **No swallowed errors.** Every `Err` branch must log at `error` level and propagate or convert to a Forge error code.
- **No string-typed errors across subsystem boundaries.** Use the `ForgeError` enum from `src/common/errors.rs`.
- **No retry loops without exponential backoff and a maximum attempt count.** Default: 3 attempts, base delay 100ms, max delay 5s.
- **No catch-all error handlers that return HTTP 200 / gRPC OK.** A failed operation must surface as a failure code.

### Timeout Defaults
| Call Path | Timeout | On Timeout |
|---|---|---|
| Gateway → CTX-ID Service | 500ms | DENY request, return `ERR_CTXID_TIMEOUT` |
| Gateway → TrustFlow | 1000ms | DENY request, return `ERR_TRUSTFLOW_TIMEOUT` |
| TrustFlow → Policy Authority | 500ms | Use cached PolicySet if ≤ 60s old; else DENY |
| Any → DTL Append | 2000ms | DENY the action being audited, return `ERR_DTL_TIMEOUT` |
| Any → Credential Vault | 1000ms | DENY the operation, return `ERR_VAULT_TIMEOUT` |

## Testing Requirements

### Coverage Rules
- **Minimum 90% line coverage** on every subsystem crate. CI blocks merge below this threshold.
- **100% branch coverage on all DENY paths.** Every rule that can produce a DENY must have a test that triggers it.
- **100% coverage of all error codes.** Every variant in `ForgeError` and every code in `error_codes.rs` must be exercised by at least one test.

### Mandatory Test Categories
1. **Unit tests** — every public function, every error branch, every boundary condition.
2. **Integration tests** — every inter-subsystem call path using `ForgeTestHarness` with real CTX-IDs and mTLS.
3. **Negative tests** — expired CTX-IDs, malformed payloads, unsigned policies, revoked credentials, zone boundary violations.
4. **Fuzz targets** — required for: CTX-ID parsing, DTL entry deserialization, TrustFlow rule evaluation input, Policy Authority policy parsing. Use `cargo fuzz`. Minimum 10 million iterations per target in CI nightly.
5. **Property-based tests** — TrustFlow evaluation must be deterministic: same inputs → same decision. Write `proptest` generators for `EvalRequest`.
6. **Chaos tests** — simulate DTL unavailability, Credential Vault latency spikes, Policy Authority version regression. Verify fail-closed behavior.

### Test Prohibitions
- **Never mock VTZ zone enforcement.** Use `ForgeTestHarness::create_test_zone()` to construct real zones.
- **Never hardcode CTX-IDs in test fixtures.** Generate them via `ForgeTestHarness::issue_test_ctx_id()`.
- **Never use `#[ignore]` without a linked tracking issue.** Ignored tests must have a comment with the issue URL.
- **Never assert only on the happy path.** Every test file must contain at least one test that asserts a DENY or error.

## File Naming and Directory Layout

```
forge/
├── CLAUDE.md                          # This file — master LLM context
├── Cargo.toml                         # Workspace root