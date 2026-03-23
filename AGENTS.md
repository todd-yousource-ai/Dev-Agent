

# AGENTS.md — Forge Platform

Forge is a trust-anchored runtime platform that enforces cryptographic identity verification, context-scoped authorization, and deterministic policy evaluation on every request path — no exceptions, no bypass, no silent fallback.

## How to Use This File

This file is the authoritative baseline for every code change in this repository; read it fully before writing any code. For subsystem-specific implementation detail, see `forge-docs/` for the full TRDs and PRDs and `forge-standards/` for synthesised architecture, interface contracts, and decision records — key reference files are listed in the Document Index below.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| Forge Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, runtime topology, deployment invariants |
| Forge Interface Contracts | Standard | `forge-standards/INTERFACES.md` | All inter-subsystem wire formats, method signatures, error codes |
| Forge Engineering Standards | Standard | `forge-standards/ENGINEERING.md` | Coding conventions, review gates, CI/CD requirements |
| Forge Decision Log | Standard | `forge-standards/DECISIONS.md` | ADRs for every non-obvious architectural choice |
| Forge Security Model | Standard | `forge-standards/SECURITY.md` | Threat model, trust boundaries, cryptographic requirements |
| TrustFlow TRD | TRD | `forge-docs/trd-trustflow.md` | TrustFlow policy engine design, DTL grammar, evaluation semantics |
| CTX-ID TRD | TRD | `forge-docs/trd-ctx-id.md` | Context Identity issuance, lifecycle, rotation, revocation |
| VTZ TRD | TRD | `forge-docs/trd-vtz.md` | Verification Trust Zone boundaries, attestation, zone transitions |
| DTL Specification TRD | TRD | `forge-docs/trd-dtl.md` | Declarative Trust Language syntax, semantics, built-in predicates |
| Runtime Gateway TRD | TRD | `forge-docs/trd-gateway.md` | Request ingress, CTX-ID extraction, TrustFlow invocation |
| Audit Subsystem TRD | TRD | `forge-docs/trd-audit.md` | Immutable audit log, event schema, retention, tamper detection |
| Key Management TRD | TRD | `forge-docs/trd-keymanagement.md` | Key hierarchy, HSM integration, rotation schedules |
| Forge Platform PRD | PRD | `forge-docs/prd-platform.md` | Product requirements, user stories, acceptance criteria |
| Forge Observability PRD | PRD | `forge-docs/prd-observability.md` | Metrics, tracing, alerting requirements |
| Forge Onboarding PRD | PRD | `forge-docs/prd-onboarding.md` | Tenant provisioning, first-run ceremony, bootstrapping |

## Critical Rules — Non-Negotiable

1. **Attach a CTX-ID to every request.** No request may proceed past the Runtime Gateway without a valid, non-expired CTX-ID bound to it. Reject with `FORGE-4010` if absent.
2. **Evaluate TrustFlow policy on every authorization decision.** Never hard-code allow/deny logic; always invoke the TrustFlow engine with the applicable DTL policy set.
3. **Fail closed on every error path.** If any subsystem returns an error, times out, or returns an unparseable response, deny the request. Never default to allow.
4. **Never log, serialize, or transmit raw cryptographic key material.** Key material stays inside the Key Management subsystem and HSM boundary. Wrap or reference by key ID only.
5. **Validate VTZ zone membership before cross-zone calls.** Every inter-zone call must present a valid zone attestation token; the receiving VTZ must verify it before processing.
6. **Write to the Audit subsystem before returning success to the caller.** Audit writes are synchronous and mandatory. If the audit write fails, the operation fails.
7. **Use DTL for all policy definitions.** Do not express authorization logic in application code, config files, or environment variables. DTL is the single source of truth.
8. **Rotate CTX-IDs before expiry, never after.** The CTX-ID subsystem must initiate rotation at 80% of TTL. Expired CTX-IDs are irrevocably invalid.
9. **Enforce schema validation at every subsystem boundary.** All inbound payloads must be validated against the canonical schemas in `forge-standards/INTERFACES.md` before processing.
10. **Never mutate TrustFlow policy state during evaluation.** Policy evaluation is pure and deterministic — identical inputs must produce identical outputs across all replicas.
11. **Tag every outbound response with the originating CTX-ID and a trace correlation ID.** Omission is a blocker-level bug.
12. **Restrict all cryptographic operations to approved primitives.** Ed25519 for signatures, X25519 for key agreement, AES-256-GCM for symmetric encryption, SHA-512 for hashing. No exceptions without an ADR in `forge-standards/DECISIONS.md`.
13. **Run the full negative-test suite before merging any PR.** PRs that reduce negative-test coverage below 90% are automatically rejected by CI.
14. **Never bypass VTZ boundaries in test environments.** Test and staging must enforce identical zone isolation to production. Mock the internals, not the boundaries.
15. **Treat every DTL policy change as a code change.** DTL files go through the same PR review, CI validation, and audit trail as application source code.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Runtime Gateway                             │
│  Enforces: CTX-ID extraction, TLS termination, rate limiting     │
│  Calls: CTX-ID subsystem, TrustFlow engine                      │
│  Called by: External clients, internal service mesh               │
│  NEVER: Makes authorization decisions itself                     │
├─────────────────────────────────────────────────────────────────┤
│                       CTX-ID Subsystem                           │
│  Enforces: Identity issuance, validation, rotation, revocation   │
│  Calls: Key Management (for signing), Audit (for lifecycle logs) │
│  Called by: Runtime Gateway, TrustFlow, any subsystem needing ID │
│  NEVER: Caches revoked identities as valid                       │
├─────────────────────────────────────────────────────────────────┤
│                     TrustFlow Engine                             │
│  Enforces: DTL policy evaluation, authorization verdicts          │
│  Calls: CTX-ID (for identity attributes), VTZ (for zone context) │
│  Called by: Runtime Gateway, any subsystem requiring authz        │
│  NEVER: Mutates state, performs I/O during evaluation             │
├─────────────────────────────────────────────────────────────────┤
│                   DTL (Declarative Trust Language)                │
│  Enforces: Policy grammar, predicate evaluation, type safety     │
│  Calls: Nothing — DTL is data consumed by TrustFlow              │
│  Called by: TrustFlow engine (parsed and evaluated)               │
│  NEVER: Contains imperative logic or side effects                 │
├─────────────────────────────────────────────────────────────────┤
│                 VTZ (Verification Trust Zone)                    │
│  Enforces: Zone isolation, attestation, cross-zone auth          │
│  Calls: CTX-ID (for zone-scoped identity), Key Management        │
│  Called by: Any subsystem making cross-zone requests              │
│  NEVER: Allows unauthenticated zone transitions                  │
├─────────────────────────────────────────────────────────────────┤
│                     Key Management                               │
│  Enforces: Key hierarchy, HSM-backed ops, rotation schedules     │
│  Calls: HSM interface (hardware boundary)                        │
│  Called by: CTX-ID, VTZ, Audit (for signing)                     │
│  NEVER: Exposes raw key material outside its process boundary    │
├─────────────────────────────────────────────────────────────────┤
│                     Audit Subsystem                              │
│  Enforces: Immutable append-only log, tamper detection, retention│
│  Calls: Key Management (for log signing)                         │
│  Called by: Every subsystem (synchronously on state changes)      │
│  NEVER: Deletes, modifies, or overwrites existing log entries    │
├─────────────────────────────────────────────────────────────────┤
│                   Observability Layer                            │
│  Enforces: Metrics emission, distributed tracing, alert routing  │
│  Calls: External metrics/tracing backends                        │
│  Called by: All subsystems (via instrumentation middleware)       │
│  NEVER: Blocks the request path — async emission only            │
└─────────────────────────────────────────────────────────────────┘
```

## Interface Contracts — All Subsystems

### Runtime Gateway → CTX-ID Subsystem

```
ValidateCTXID(ctx_id: string, request_fingerprint: bytes) → CTXIDValidationResult
  CTXIDValidationResult {
    valid: bool
    identity_attributes: Map<string, string>
    zone_id: string
    expires_at: uint64  // Unix epoch seconds
    error_code: string | null  // FORGE-4010, FORGE-4011, FORGE-4012
  }
```

### Runtime Gateway → TrustFlow Engine

```
Evaluate(ctx_id_result: CTXIDValidationResult, resource: ResourceDescriptor, action: string) → TrustFlowVerdict
  TrustFlowVerdict {
    decision: ALLOW | DENY  // No other values permitted
    policy_id: string
    dtl_version: string
    evaluation_trace: EvalTrace[]  // For audit, never for branching
    error_code: string | null  // FORGE-5010, FORGE-5011
  }
```

### Any Subsystem → VTZ

```
RequestZoneTransition(source_zone: string, target_zone: string, attestation_token: bytes) → ZoneTransitionResult
  ZoneTransitionResult {
    granted: bool
    session_token: bytes  // Scoped to this transition, single-use
    ttl_seconds: uint32
    error_code: string | null  // FORGE-6010, FORGE-6011
  }
```

### Any Subsystem → Audit

```
WriteAuditEntry(entry: AuditEntry) → AuditWriteResult
  AuditEntry {
    timestamp: uint64
    ctx_id: string
    subsystem: string
    action: string
    resource: string
    verdict: string
    trace_id: string
    payload_hash: bytes  // SHA-512 of the relevant request payload
  }
  AuditWriteResult {
    persisted: bool
    sequence_number: uint64
    error_code: string | null  // FORGE-7010, FORGE-7011
  }
```

### Any Subsystem → Key Management

```
Sign(key_id: string, data: bytes) → SignatureResult
Verify(key_id: string, data: bytes, signature: bytes) → VerificationResult
RotateKey(key_id: string) → RotationResult
  // Raw key material is NEVER returned. Only key_id references.
```

Full schemas, including nested types and all error code enumerations, are defined in `forge-standards/INTERFACES.md`.

## Wire Formats and Schemas

### CTX-ID Token Format (JWT-like, Ed25519-signed)

```json
{
  "header": {
    "alg": "EdDSA",
    "kid": "<key_id from Key Management>",
    "typ": "CTX"
  },
  "payload": {
    "sub": "<entity identifier>",
    "zone": "<VTZ zone identifier>",
    "iat": 1700000000,
    "exp": 1700003600,
    "attrs": {
      "<attribute_key>": "<attribute_value>"
    },
    "nonce": "<16-byte hex>"
  },
  "signature": "<Ed25519 signature, base64url>"
}
```

### DTL Policy Document Structure

```
policy <policy_id> version <semver> {
  target resource <resource_pattern> action <action_pattern>;
  
  rule <rule_name> {
    when <predicate_expression>;
    then ALLOW | DENY;
  }
  
  default DENY;  // MANDATORY — every policy must end with default DENY
}
```

### Audit Log Entry (on-disk / on-wire)

```json
{
  "seq": 1042,
  "ts": 1700000000000,
  "ctx_id": "<CTX-ID token hash>",
  "subsystem": "trustflow",
  "action": "evaluate",
  "resource": "/api/v1/accounts/123",
  "verdict": "DENY",
  "trace_id": "abc123def456",
  "payload_hash": "<SHA-512 hex>",
  "prev_hash": "<SHA-512 of previous entry>",
  "sig": "<Ed25519 signature of this entry, base64url>"
}
```

Reference `forge-standards/INTERFACES.md` for the complete field-level specification of all wire formats, including optional fields, extension points, and version negotiation.

## Error Handling Rules

### Error Code Taxonomy

| Range | Subsystem | Meaning |
|---|---|---|
| `FORGE-40xx` | CTX-ID | Identity validation failures |
| `FORGE-50xx` | TrustFlow | Policy evaluation failures |
| `FORGE-60xx` | VTZ | Zone transition failures |
| `FORGE-70xx` | Audit | Audit persistence failures |
| `FORGE-80xx` | Key Management | Cryptographic operation failures |
| `FORGE-90xx` | Runtime Gateway | Ingress/routing failures |

### Mandatory Error Handling Behaviors

1. **On CTX-ID validation failure (`FORGE-40xx`):** Reject the request immediately. Do not forward to TrustFlow. Return HTTP 401 with the error code. Write audit entry.
2. **On TrustFlow evaluation failure (`FORGE-50xx`):** Treat as DENY. Never interpret an evaluation error as ALLOW. Return HTTP 403. Write audit entry.
3. **On VTZ transition failure (`FORGE-60xx`):** Abort the cross-zone call. Do not retry automatically — the caller must re-attest. Write audit entry.
4. **On Audit write failure (`FORGE-70xx`):** Fail the entire originating operation. The request that triggered the audit entry must not succeed. Emit a critical alert via Observability.
5. **On Key Management failure (`FORGE-80xx`):** Fail closed. If signing or verification fails, the dependent operation (CTX-ID issuance, audit signing, zone attestation) fails. No fallback to unsigned operations.
6. **On timeout to any subsystem:** Treat as failure. Apply the same fail-closed rule as an explicit error. Default timeout is 500ms for intra-zone calls, 2000ms for cross-zone calls.

### Banned Patterns

- **`catch (...) { return OK; }`** — Swallowing errors to return success is a terminable offense against the codebase. Never.
- **Retry loops on authorization failures** — Authorization denials are deterministic given the same inputs. Retrying wastes resources and masks bugs.
- **Logging errors without propagating them** — Log AND propagate. An error that is logged but not returned to the caller is a silent failure.
- **String-matching on error messages** — Always match on structured error codes (`FORGE-XXXX`). Error messages are for humans, not branching logic.

## Testing Requirements

### Coverage Rules

- **Line coverage minimum: 90%** across all subsystems. CI blocks merge below this threshold.
- **Branch coverage minimum: 85%**. Every conditional in TrustFlow evaluation and CTX-ID validation must have both branches exercised.
- **DTL policy tests: 100% of rules must have at least one positive and one negative test case.** A DTL policy without a test that triggers its `default DENY` is incomplete.

### Mandatory Negative Tests

Every subsystem must include explicit tests for:
- Expired CTX-IDs presented to the Gateway.
- Revoked CTX-IDs presented to the Gateway.
- Malformed DTL policy documents submitted to TrustFlow.
- Cross-zone calls with expired or forged attestation tokens.
- Audit subsystem unavailability during a write attempt (must verify the originating operation fails).
- Key rotation mid-flight (verify in-flight operations complete with the old key or fail cleanly — never with a mismatched key).

### Fuzz Targets

Maintain active fuzz targets for:
- `src/dtl/parser/` — DTL grammar parsing. Fuzz with arbitrary byte sequences.
- `src/ctx-id/validator/` — CTX-ID token parsing and signature verification.
- `src/gateway/request_parser/` — HTTP request parsing and CTX-ID extraction.
- `src/vtz/attestation/` — Attestation token parsing and verification.

Run fuzz targets in CI nightly with a minimum corpus of 10,000 inputs per target.

### Integration Test Requirements

- Every interface contract in this document must have a corresponding integration test that exercises the happy path and at least two error paths.
- Integration tests must run against real subsystem instances (not mocks) in CI. Mock only external dependencies (HSM, external metrics backends).

## File Naming and Directory Layout

```
forge/
├── CLAUDE.md                          # THIS FILE — read first, always
├── forge-docs/                        # Source TRDs, PRDs — authoritative design docs
│   ├── trd-trustflow.md
│   ├── trd-ctx-id.md
│   ├── trd-vtz.md
│   ├── trd-dtl.md
│   ├── trd-gateway.md
│   ├── trd-audit.md
│   ├── trd-keymanagement.md
│   ├── prd-platform.md
│   ├── prd-observability.md
│   └── prd-onboarding.md
├── forge-standards/                   # Synthesised standards — derived from TRDs
│   ├── ARCHITECTURE.md
│   ├── INTERFACES.md
│   ├── ENGINEERING.md
│   ├── DECISIONS.md
│   └── SECURITY.md
├── docs/                              # Branch-specific and operational docs
├── src/
│   ├── gateway/                       # Runtime Gateway subsystem
│   │   ├── ingress/                   # TLS termination, rate limiting
│   │   ├── request_parser/            # CTX-ID extraction, schema validation
│   │   └── router/                    # Request routing to downstream subsystems
│   ├── ctx-id/                        # CTX-ID subsystem
│   │   ├── issuer/                    # CTX-ID creation and signing
│   │   ├── validator/                 # CTX-ID verification and attribute extraction
│   │   ├── rotator/                   # Proactive rotation at 80% TTL
│   │   └── revocation/               # Revocation list management
│   ├── trustflow/                     # TrustFlow policy engine
│   │   ├── engine/                    # Core evaluation loop
│   │   ├── loader/                    # DTL policy loading and versioning
│   │   └── cache/                     # Compiled policy cache (read-only at eval time)
│   ├── dtl/                           # Declarative Trust Language
│   │   ├── parser/                    # Grammar parsing, AST construction
│   │   ├── compiler/                  # AST to evaluable form
│   │   ├── predicates/                #