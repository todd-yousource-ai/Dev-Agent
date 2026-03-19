

# AGENTS.md — Forge Platform

Forge is a trust-anchored runtime platform that enforces identity verification, context integrity, and policy compliance across every request through its CTX-ID, VTZ, TrustFlow, and DTL subsystems — no request executes without passing all gates.

## How to Use This File

This file is the authoritative baseline for all LLM-assisted and human development on the Forge platform; read it fully before writing any code. For subsystem-specific design rationale see `forge-docs/` (source TRDs and PRDs), and for synthesised cross-cutting standards see `forge-standards/`.

**Key reference files to load for deep work:**
- `forge-standards/ARCHITECTURE.md` — canonical subsystem map and data-flow diagrams
- `forge-standards/INTERFACES.md` — every public interface contract, wire format, and schema
- `forge-standards/DECISIONS.md` — architectural decision records with rationale
- `forge-standards/ENGINEERING_STANDARDS.md` — complete coding, testing, and security standards

---

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Technical Reference | TRD | `forge-docs/trd-ctx-id.md` | Context Identity subsystem: ID minting, lifecycle, propagation, and revocation |
| VTZ Technical Reference | TRD | `forge-docs/trd-vtz.md` | Verification Trust Zone: request validation gates, policy enforcement points |
| TrustFlow Technical Reference | TRD | `forge-docs/trd-trustflow.md` | TrustFlow engine: trust scoring, decay model, delegation chain verification |
| DTL Technical Reference | TRD | `forge-docs/trd-dtl.md` | Distributed Trust Ledger: append-only audit log, consensus, replication |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user stories, acceptance criteria for the full platform |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, data-flow diagrams, deployment topology |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All public APIs, wire formats, schemas, versioning rules |
| Decision Records | Standard | `forge-standards/DECISIONS.md` | ADRs: every architectural choice with context, decision, and consequences |
| Engineering Standards | Standard | `forge-standards/ENGINEERING_STANDARDS.md` | Coding conventions, testing requirements, CI rules, security baseline |
| Security Model | Standard | `forge-standards/SECURITY_MODEL.md` | Threat model, trust boundaries, cryptographic requirements, key management |
| Operational Runbook | Ops | `docs/runbook.md` | Incident response, rollback procedures, monitoring alert definitions |
| Local Development Guide | Guide | `docs/dev-setup.md` | Environment setup, dependency installation, local VTZ/DTL bootstrapping |

---

## Critical Rules — Non-Negotiable

1. **Never process a request that lacks a valid CTX-ID.** Every inbound call must carry a minted, unexpired, cryptographically signed CTX-ID; reject with `401 UNTRUSTED_CONTEXT` if absent or invalid.

2. **Fail closed on every gate.** If any VTZ policy check returns an error or timeout, deny the request — never fall through to an allow path.

3. **Treat TrustFlow scores as immutable within a single request lifecycle.** Once a TrustFlow score is resolved for a CTX-ID in a request, cache it for that request; never re-query mid-execution to avoid TOCTOU races.

4. **Append to the DTL before returning success to the caller.** Every state-mutating operation must have its DTL entry confirmed (fsync-equivalent durability) before the response is sent; do not fire-and-forget audit records.

5. **Never log, serialize, or expose raw cryptographic key material.** Private keys, HMAC secrets, and session tokens must never appear in logs, error messages, traces, or API responses. Use key references (Key-ID) only.

6. **Validate all inputs at the VTZ boundary, not inside business logic.** Schema validation, size limits, encoding checks, and policy assertions happen exactly once at the VTZ ingress point.

7. **Propagate CTX-ID headers on every inter-service call.** When Forge subsystem A calls subsystem B, the `X-Forge-CTX-ID` header must be forwarded verbatim; never mint a new CTX-ID for internal hops.

8. **Enforce TrustFlow delegation depth ≤ 5.** Any delegation chain exceeding five links must be rejected with `403 DELEGATION_DEPTH_EXCEEDED`; there are no configuration overrides for this limit.

9. **Use only the approved cryptographic primitives.** Ed25519 for signatures, X25519 for key agreement, AES-256-GCM for symmetric encryption, BLAKE3 for hashing. No RSA. No SHA-1. No CBC mode. See `forge-standards/SECURITY_MODEL.md`.

10. **Version every wire-format message with a `forge_schema_version` field.** Every serialized message (Protobuf, JSON, or internal) must carry this field; deserializers must reject unknown versions rather than guessing.

11. **Never mutate DTL records.** The DTL is append-only. There is no update or delete API. Any code that attempts to overwrite a DTL entry is a critical defect.

12. **Require 90% line coverage and 100% coverage of error paths in every subsystem.** PRs that drop below these thresholds must not merge. Negative tests (malformed input, expired CTX-ID, revoked trust) are mandatory, not optional.

13. **Time-bound every external call with an explicit timeout.** No unbounded I/O. Default timeout is 3 seconds for inter-subsystem calls and 10 seconds for DTL consensus rounds. These values live in `src/config/timeouts.rs` — not hardcoded at call sites.

14. **Tag every log line with the CTX-ID of the active request.** Structured logs must include `ctx_id`, `subsystem`, `timestamp_utc`, and `severity`. Free-form string logs are banned.

15. **Run `forge lint`, `forge test`, and `forge security-audit` before every commit.** CI will reject any PR where these commands do not pass with zero warnings. Local pre-commit hooks enforce the same gates.

---

## Architecture Overview

### CTX-ID — Context Identity Service
- **Enforces:** Globally unique, cryptographically signed identity tokens for every request context.
- **Called by:** VTZ (at ingress to validate identity), TrustFlow (to resolve identity for scoring).
- **Calls:** Internal key store for signing operations.
- **Must NEVER:** Issue a CTX-ID without verifying the requesting principal's credentials. Must NEVER reuse a revoked or expired CTX-ID value.

### VTZ — Verification Trust Zone
- **Enforces:** Policy-based admission control at every service boundary; input validation, rate limiting, schema conformance.
- **Called by:** All external API gateways and inter-subsystem ingress points.
- **Calls:** CTX-ID (to validate context tokens), TrustFlow (to fetch trust scores for policy decisions).
- **Must NEVER:** Allow a request to bypass policy evaluation. Must NEVER return a detailed internal error to an external caller.

### TrustFlow — Trust Scoring Engine
- **Enforces:** Dynamic trust scores with time-decay, delegation chain verification, and threshold enforcement.
- **Called by:** VTZ (for admission decisions), application services (for authorization checks).
- **Calls:** DTL (to read historical trust events), CTX-ID (to resolve identity chains).
- **Must NEVER:** Assign a trust score above the delegator's own score (trust cannot escalate through delegation). Must NEVER cache scores across request boundaries in a shared mutable cache without TTL.

### DTL — Distributed Trust Ledger
- **Enforces:** Append-only, tamper-evident audit trail of all trust-relevant events; consensus-based replication across nodes.
- **Called by:** TrustFlow (to record and read trust events), VTZ (to log policy decisions), operational tooling (for audit queries).
- **Calls:** Peer DTL nodes (for consensus protocol), persistent storage layer.
- **Must NEVER:** Expose a delete or update API. Must NEVER confirm a write to the caller before achieving the configured quorum (default: majority of nodes).

### Config Service
- **Enforces:** Centralized, versioned configuration for timeouts, feature flags, and policy rules.
- **Called by:** All subsystems at startup and on config-change notification.
- **Calls:** Persistent config store.
- **Must NEVER:** Serve config without validating the requesting subsystem's CTX-ID. Must NEVER allow hot-reload of security-critical parameters (crypto primitives, delegation depth) without a signed config change record in the DTL.

---

## Interface Contracts — All Subsystems

### CTX-ID API

```
POST /ctx-id/mint
  Request:  { principal_id: string, scope: string[], ttl_seconds: u32 }
  Response: { ctx_id: string, issued_at: u64, expires_at: u64, signature: bytes }
  Errors:   400 INVALID_PRINCIPAL | 401 UNAUTHENTICATED | 500 MINT_FAILURE

POST /ctx-id/validate
  Request:  { ctx_id: string, signature: bytes }
  Response: { valid: bool, principal_id: string, scope: string[], expires_at: u64 }
  Errors:   400 MALFORMED_CTX_ID | 401 EXPIRED_CTX_ID | 401 REVOKED_CTX_ID

POST /ctx-id/revoke
  Request:  { ctx_id: string, reason: string }
  Response: { revoked: bool, dtl_entry_id: string }
  Errors:   404 CTX_ID_NOT_FOUND | 500 REVOCATION_FAILURE
```

### VTZ API

```
POST /vtz/evaluate
  Request:  { ctx_id: string, resource: string, action: string, payload_hash: bytes }
  Response: { decision: ALLOW | DENY, policy_id: string, trust_score: f64 }
  Errors:   401 UNTRUSTED_CONTEXT | 403 POLICY_DENIED | 429 RATE_LIMITED | 500 EVALUATION_FAILURE

GET /vtz/policies/{policy_id}
  Response: { policy_id: string, rules: Rule[], version: u32, active: bool }
  Errors:   404 POLICY_NOT_FOUND
```

### TrustFlow API

```
GET /trustflow/score/{ctx_id}
  Response: { ctx_id: string, score: f64, delegation_depth: u8, computed_at: u64 }
  Errors:   404 CTX_ID_NOT_FOUND | 403 DELEGATION_DEPTH_EXCEEDED

POST /trustflow/delegate
  Request:  { delegator_ctx_id: string, delegatee_ctx_id: string, scope: string[], max_depth: u8 }
  Response: { delegation_id: string, effective_score: f64, dtl_entry_id: string }
  Errors:   400 INVALID_DELEGATION | 403 SCORE_ESCALATION_DENIED | 403 DELEGATION_DEPTH_EXCEEDED
```

### DTL API

```
POST /dtl/append
  Request:  { event_type: string, ctx_id: string, payload: bytes, subsystem: string }
  Response: { entry_id: string, sequence: u64, quorum_ack: bool, timestamp: u64 }
  Errors:   400 INVALID_EVENT | 500 QUORUM_FAILURE | 503 CONSENSUS_TIMEOUT

GET /dtl/query
  Request:  { ctx_id?: string, event_type?: string, after_sequence?: u64, limit: u32 }
  Response: { entries: DtlEntry[], has_more: bool }
  Errors:   400 INVALID_QUERY | 500 READ_FAILURE
```

**Full contract specifications including field-level validation rules, header requirements, and pagination behavior are in `forge-standards/INTERFACES.md`.**

---

## Wire Formats and Schemas

### CTX-ID Token (binary layout)

```
Field               Type        Bytes   Notes
─────────────────────────────────────────────────
version             u8          1       Must be 0x01
principal_id        [u8; 32]    32      BLAKE3 hash of principal identity
scope_bitfield      u64         8       Bit flags per scope definition
issued_at           u64         8       Unix epoch seconds UTC
expires_at          u64         8       Unix epoch seconds UTC
nonce               [u8; 16]    16      Cryptographic random
signature           [u8; 64]    64      Ed25519 over all preceding fields
─────────────────────────────────────────────────
Total                           137
```

### DTL Entry (Protobuf)

```protobuf
message DtlEntry {
  uint32 forge_schema_version = 1;  // Must be present. Currently 1.
  string entry_id = 2;              // UUIDv7
  uint64 sequence = 3;              // Monotonic per DTL partition
  string event_type = 4;            // Enum: MINT | REVOKE | DELEGATE | POLICY_DECISION | SCORE_UPDATE
  string ctx_id = 5;
  bytes  payload = 6;               // Subsystem-specific, max 64 KiB
  string subsystem = 7;             // Enum: CTX_ID | VTZ | TRUSTFLOW | DTL
  uint64 timestamp_utc = 8;         // Unix epoch milliseconds
  bytes  entry_signature = 9;       // Ed25519 over fields 1–8
}
```

### TrustFlow Score Record (JSON — internal cache)

```json
{
  "forge_schema_version": 1,
  "ctx_id": "string",
  "score": "f64 [0.0, 1.0]",
  "delegation_chain": ["ctx_id_0", "ctx_id_1"],
  "delegation_depth": "u8 [0, 5]",
  "decay_factor": "f64 (0.0, 1.0]",
  "computed_at_utc_ms": "u64",
  "ttl_ms": "u64"
}
```

**See `forge-standards/INTERFACES.md` for all schema definitions, field constraints, and evolution rules.**

---

## Error Handling Rules

### Mandatory Patterns

1. **Fail closed.** Any error in VTZ evaluation, CTX-ID validation, or TrustFlow scoring results in request denial. Never default to allow.

2. **Return structured errors.** Every error response must use the standard envelope:
   ```json
   {
     "error_code": "UNTRUSTED_CONTEXT",
     "subsystem": "VTZ",
     "ctx_id": "...",
     "message": "Human-readable, no internal details",
     "timestamp_utc": 1700000000000
   }
   ```

3. **Log the full error internally, return a sanitized error externally.** Internal logs include stack context and CTX-ID. External responses include only the error code and a safe message.

4. **Retry only on explicitly retryable errors.** `503 CONSENSUS_TIMEOUT` from DTL is retryable (with exponential backoff, max 3 attempts). All 4xx errors are terminal — do not retry.

5. **Propagate cancellation.** When a request's CTX-ID is revoked mid-flight, all downstream calls for that CTX-ID must be cancelled within 500ms.

### Banned Patterns

- **`unwrap()` / `expect()` in production paths.** Use explicit error handling with `Result<T, ForgeError>`. `unwrap()` is permitted only in tests and explicitly marked `#[cfg(test)]` code.
- **Catch-all exception handlers that swallow errors.** Every error must be logged and mapped to a specific `ForgeError` variant.
- **Returning `200 OK` with an error payload.** HTTP status codes must accurately reflect the outcome.
- **Panic-based control flow.** Panics in production code are treated as P0 bugs.
- **String-typed error codes.** Use the `ForgeErrorCode` enum defined in `src/common/errors.rs`.

---

## Testing Requirements

### Coverage Thresholds

| Metric | Minimum | Enforcement |
|---|---|---|
| Line coverage (per subsystem) | 90% | CI gate — PR blocked if below |
| Branch coverage (per subsystem) | 85% | CI gate — PR blocked if below |
| Error path coverage | 100% | Manual review + CI lint rule |
| Integration test coverage (cross-subsystem) | 80% | CI gate on `main` branch |

### Mandatory Test Categories

1. **Unit tests:** Every public function. Every `ForgeError` variant must have a test that triggers it.
2. **Negative tests (required for every endpoint):**
   - Malformed CTX-ID (truncated, wrong version, corrupted signature)
   - Expired CTX-ID
   - Revoked CTX-ID
   - TrustFlow score below threshold
   - Delegation depth exceeded
   - DTL quorum failure (simulated)
   - Oversized payloads (above 64 KiB DTL limit)
   - Missing `forge_schema_version` field
3. **Fuzz targets:** Required for all deserialization code — CTX-ID token parsing, DTL entry deserialization, VTZ policy rule parsing. Fuzz targets live in `src/{subsystem}/fuzz/`.
4. **Integration tests:** Cross-subsystem flows (mint → evaluate → delegate → audit) in `tests/integration/`.
5. **Performance tests:** Latency benchmarks for CTX-ID minting (<5ms p99), VTZ evaluation (<10ms p99), DTL append (<50ms p99). Benchmarks in `benches/`.

### Test Commands

```bash
forge test                    # Run all unit + integration tests
forge test --subsystem vtz    # Run tests for a single subsystem
forge fuzz --target ctx-id    # Run fuzz targets for CTX-ID parsing
forge bench                   # Run performance benchmarks
forge coverage                # Generate coverage report, fail if below thresholds
```

---

## File Naming and Directory Layout

```
forge/
├── CLAUDE.md                          # THIS FILE — read first
├── Cargo.toml                         # Workspace root
├── forge-docs/                        # Source design documents
│   ├── trd-ctx-id.md
│   ├── trd-vtz.md
│   ├── trd-trustflow.md
│   ├── trd-dtl.md
│   └── prd-forge-platform.md
├── forge-standards/                   # Synthesised engineering standards
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   ├── DECISIONS.md
│   ├── ENGINEERING_STANDARDS.md
│   └── SECURITY_MODEL.md
├── docs/                              # Operational and development guides
│   ├── runbook.md
│   └── dev-setup.md
├── src/
│   ├── common/                        # Shared types, errors, config, crypto
│   │   ├── errors.rs                  # ForgeError enum, ForgeErrorCode enum
│   │   ├── config.rs                  # Config loading, validation
│   │   ├── crypto.rs                  # Ed25519, X25519, AES-256-GCM, BLAKE3 wrappers
│   │   ├── types.rs                   # CtxId, DtlEntryId, TrustScore, shared newtypes
│   │   └── logging.rs                 # Structured logging with mandatory ctx_id field
│   ├── ctx_id/                        # CTX-ID subsystem
│   │   ├── mod.rs
│   │   ├── mint.rs                    # Token minting logic
│   │   ├── validate.rs