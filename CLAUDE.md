

# CLAUDE.md — Forge Platform

Forge is a zero-trust runtime enforcement platform that validates every context transition, virtualisation boundary, and trust delegation through cryptographically attested contracts — any violation fails closed, no exceptions.

## How to Use This File

This file is the authoritative baseline for all code generation, review, and refactoring in the Forge repository; read it completely before writing any code. For subsystem-specific implementation detail, see `forge-docs/` for the full TRDs and PRDs, and `forge-standards/` for synthesised architecture documents and interface contracts.

**Key reference files to load when working on any subsystem:**

- `forge-standards/ARCHITECTURE.md` — Canonical subsystem map, dependency graph, runtime invariants
- `forge-standards/INTERFACES.md` — All inter-subsystem wire formats, RPC schemas, and contract signatures
- `forge-standards/DECISIONS.md` — Architecture Decision Records with rationale and constraints
- `forge-standards/ENGINEERING_STANDARDS.md` — Complete coding standards, patterns, and banned practices

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| CTX-ID Technical Reference | TRD | `forge-docs/trd-ctx-id.md` | Context identity issuance, lifecycle, rotation, and revocation |
| VTZ Technical Reference | TRD | `forge-docs/trd-vtz.md` | Virtualisation Trust Zones — boundary enforcement, zone transitions, attestation |
| TrustFlow Technical Reference | TRD | `forge-docs/trd-trustflow.md` | Trust delegation chains, policy evaluation, propagation rules |
| DTL Technical Reference | TRD | `forge-docs/trd-dtl.md` | Distributed Trust Ledger — append-only audit log, consensus, replication |
| Policy Engine Technical Reference | TRD | `forge-docs/trd-policy-engine.md` | Policy authoring, compilation, runtime evaluation, conflict resolution |
| Attestation Service Technical Reference | TRD | `forge-docs/trd-attestation.md` | Cryptographic attestation issuance, verification, and chain validation |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user stories, acceptance criteria, rollout plan |
| Gateway PRD | PRD | `forge-docs/prd-gateway.md` | API gateway requirements, rate limiting, ingress trust validation |
| Architecture Reference | Synthesised | `forge-standards/ARCHITECTURE.md` | Subsystem topology, dependency rules, runtime invariants |
| Interface Contracts | Synthesised | `forge-standards/INTERFACES.md` | All RPC definitions, wire formats, schema versions, backward-compat rules |
| Architecture Decisions | Synthesised | `forge-standards/DECISIONS.md` | ADRs with full context, alternatives considered, and binding constraints |
| Engineering Standards | Synthesised | `forge-standards/ENGINEERING_STANDARDS.md` | Code style, error handling, testing, performance, and security standards |
| Security Model | Synthesised | `forge-standards/SECURITY_MODEL.md` | Threat model, trust boundaries, cryptographic requirements, key management |
| Deployment Topology | Reference | `docs/DEPLOYMENT.md` | Environment-specific config, scaling rules, zone placement |
| Runbook | Reference | `docs/RUNBOOK.md` | Incident response, rollback procedures, health check endpoints |

## Critical Rules — Non-Negotiable

1. **Fail closed on every trust validation error.** If CTX-ID validation, VTZ boundary check, or TrustFlow policy evaluation returns an error or timeout, deny the request — never fall through to a default-allow path.

2. **Never cache a CTX-ID beyond its TTL.** CTX-ID tokens carry an explicit `expires_at` field; treat any cached identity as invalid the instant that timestamp passes, even if the cache eviction has not yet fired.

3. **Validate VTZ zone transitions at both the source and destination boundary.** A request leaving Zone A and entering Zone B must pass egress policy in A and ingress policy in B independently; passing one does not imply the other.

4. **Every TrustFlow delegation chain must be re-validated on use, not on issuance alone.** A delegation that was valid at creation time may have had an intermediate link revoked; verify the full chain at evaluation time.

5. **DTL writes are append-only and cryptographically chained.** Never update or delete a DTL record. Every new entry includes the SHA-256 hash of the previous entry. Any function that mutates existing DTL state is a critical security defect.

6. **All inter-subsystem calls carry a CTX-ID in the request metadata.** No subsystem accepts an unauthenticated internal call. If you add a new RPC, it must require and validate a CTX-ID before any business logic executes.

7. **Policy Engine evaluation must be deterministic and side-effect-free.** Given the same policy version and input context, the engine must return the same decision. Policy evaluation functions must never write to a database, emit events, or mutate shared state.

8. **Attestation signatures use Ed25519 with the Forge-specific domain separation tag `forge-attest-v1`.** Do not use ECDSA, RSA, or any other signature scheme for attestation. Do not omit the domain separation tag.

9. **Schema changes to wire formats require a version bump in the `schema_version` field and a backward-compatible migration.** Never add a required field to an existing schema version. Add it as optional in the current version or introduce a new version.

10. **Never log CTX-ID tokens, private keys, delegation secrets, or raw attestation blobs at any log level.** Structured logging must redact these fields. Use the `redact()` wrapper from `forge-lib/logging` for any value that could contain credentials.

11. **All subsystem boundaries are defined in `forge-standards/INTERFACES.md`.** If you need a new cross-subsystem call, add it to INTERFACES.md first, get it reviewed, then implement. Do not create ad-hoc internal APIs.

12. **VTZ enforcement runs in-kernel or at the hypervisor layer — never in userspace alone.** The VTZ boundary check is a security boundary; a userspace-only implementation is bypassable and constitutes a critical defect.

13. **TrustFlow maximum delegation depth is 5.** Any chain longer than 5 hops must be rejected at evaluation time. This limit is enforced in `src/trustflow/evaluator.rs` and must not be overridden by configuration.

14. **Test coverage for any subsystem must be ≥ 90% line coverage, with mandatory negative tests for every error branch.** PRs that drop coverage below 90% must not be merged.

15. **Every cryptographic operation must use the Forge-approved primitives in `forge-lib/crypto`.** Do not import external crypto crates or stdlib crypto directly. The approved library handles constant-time comparison, key zeroing, and side-channel mitigations.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        API Gateway                           │
│  Enforces: ingress rate limits, initial CTX-ID presence      │
│  Calls: CTX-ID Service, Policy Engine                        │
│  Called by: external clients                                  │
│  NEVER: terminates TLS and re-issues without re-attestation  │
├──────────────────────────────────────────────────────────────┤
│                       CTX-ID Service                         │
│  Enforces: identity issuance, validation, rotation, revoke   │
│  Calls: Attestation Service, DTL                             │
│  Called by: all subsystems (every request path)               │
│  NEVER: issues a CTX-ID without a verified attestation       │
├──────────────────────────────────────────────────────────────┤
│                     VTZ Boundary Enforcer                    │
│  Enforces: zone ingress/egress, isolation, transition audit  │
│  Calls: Policy Engine, DTL, CTX-ID Service                   │
│  Called by: hypervisor hooks, kernel modules                  │
│  NEVER: allows a zone transition without dual-boundary check │
├──────────────────────────────────────────────────────────────┤
│                     TrustFlow Evaluator                      │
│  Enforces: delegation chain validity, depth limits, revoke   │
│  Calls: CTX-ID Service, Policy Engine, DTL                   │
│  Called by: any service performing delegated actions          │
│  NEVER: caches a delegation decision beyond the request scope│
├──────────────────────────────────────────────────────────────┤
│                       Policy Engine                          │
│  Enforces: deterministic policy evaluation, conflict resolve │
│  Calls: (pure computation — no outbound calls at eval time)  │
│  Called by: VTZ, TrustFlow, Gateway, CTX-ID Service          │
│  NEVER: performs I/O or mutates state during evaluation       │
├──────────────────────────────────────────────────────────────┤
│                    Attestation Service                       │
│  Enforces: Ed25519 attestation issuance and verification     │
│  Calls: DTL (to log attestation events)                      │
│  Called by: CTX-ID Service, VTZ Boundary Enforcer            │
│  NEVER: issues attestation without hardware-rooted evidence  │
├──────────────────────────────────────────────────────────────┤
│              DTL (Distributed Trust Ledger)                  │
│  Enforces: append-only, hash-chained, replicated audit log   │
│  Calls: peer DTL nodes (consensus protocol)                  │
│  Called by: all subsystems (for audit writes and reads)       │
│  NEVER: exposes a delete or update API, even internally      │
└──────────────────────────────────────────────────────────────┘
```

**Dependency rule:** Subsystems may only call downward or lateral in the diagram. The Policy Engine has zero runtime dependencies. DTL has no upstream dependencies except peer nodes. Circular calls are forbidden.

## Interface Contracts — All Subsystems

### CTX-ID Service

```
rpc IssueCtxId(IssueRequest) -> CtxIdToken
  requires: valid AttestationProof in metadata
  returns:  CtxIdToken { id: uuid, subject: string, expires_at: timestamp, attestation_ref: hash }
  errors:   ATTESTATION_INVALID, SUBJECT_BANNED, RATE_LIMITED

rpc ValidateCtxId(CtxIdToken) -> ValidationResult
  requires: token not expired, signature valid, not revoked in DTL
  returns:  ValidationResult { valid: bool, subject: string, remaining_ttl: duration }
  errors:   TOKEN_EXPIRED, TOKEN_REVOKED, SIGNATURE_INVALID

rpc RevokeCtxId(RevokeRequest) -> RevokeAck
  requires: caller must hold the issuing CTX-ID or an admin delegation
  effects:  writes revocation record to DTL (irreversible)
  errors:   NOT_AUTHORIZED, ALREADY_REVOKED
```

### VTZ Boundary Enforcer

```
rpc CheckTransition(TransitionRequest) -> TransitionDecision
  requires: source_zone, dest_zone, ctx_id, payload_hash
  returns:  TransitionDecision { allowed: bool, audit_ref: dtl_hash }
  errors:   ZONE_UNKNOWN, CTX_ID_INVALID, POLICY_DENIED
  invariant: both egress(source) and ingress(dest) policies evaluated

rpc RegisterZone(ZoneSpec) -> ZoneAck
  requires: admin CTX-ID with zone-admin delegation
  returns:  ZoneAck { zone_id: string, effective_at: timestamp }
  errors:   DUPLICATE_ZONE, INVALID_SPEC
```

### TrustFlow Evaluator

```
rpc EvaluateDelegation(DelegationChain) -> DelegationDecision
  requires: chain of DelegationLink[], terminal_action
  returns:  DelegationDecision { permitted: bool, effective_permissions: []string, chain_depth: u8 }
  errors:   CHAIN_TOO_DEEP, LINK_REVOKED, LINK_EXPIRED, INVALID_SIGNATURE
  invariant: max chain_depth = 5; every link re-verified against DTL

rpc IssueDelegation(DelegationRequest) -> DelegationLink
  requires: issuer CTX-ID, delegate CTX-ID, permission set, expiry
  effects:  records delegation in DTL
  errors:   INSUFFICIENT_PERMISSIONS, DELEGATE_BANNED
```

### Policy Engine

```
fn evaluate(policy: CompiledPolicy, context: EvalContext) -> PolicyDecision
  pure function — no RPC, no I/O, no side effects
  returns:  PolicyDecision { effect: ALLOW | DENY, matched_rules: []RuleId, trace: EvalTrace }
  invariant: deterministic — same inputs always produce same output

rpc CompilePolicy(PolicySource) -> CompiledPolicy
  requires: valid policy DSL source, schema version
  returns:  CompiledPolicy { bytecode: bytes, version: u64, hash: sha256 }
  errors:   SYNTAX_ERROR, CONFLICT_DETECTED, UNSUPPORTED_VERSION
```

### Attestation Service

```
rpc Attest(AttestRequest) -> AttestationProof
  requires: hardware evidence (TPM quote, SEV report, or TDX quote)
  returns:  AttestationProof { signature: ed25519_sig, evidence_hash: sha256, domain_tag: "forge-attest-v1" }
  errors:   EVIDENCE_INVALID, HARDWARE_UNSUPPORTED, NONCE_REUSED

rpc VerifyAttestation(AttestationProof) -> VerifyResult
  requires: proof with valid domain_tag
  returns:  VerifyResult { valid: bool, signer_id: string, evidence_freshness: duration }
  errors:   SIGNATURE_INVALID, DOMAIN_TAG_MISMATCH, PROOF_EXPIRED
```

### DTL (Distributed Trust Ledger)

```
rpc Append(DTLEntry) -> AppendAck
  requires: entry { payload: bytes, prev_hash: sha256, timestamp: timestamp, author_ctx_id: CtxIdToken }
  returns:  AppendAck { entry_hash: sha256, sequence: u64 }
  errors:   PREV_HASH_MISMATCH, AUTHOR_INVALID, DUPLICATE_ENTRY
  invariant: no Update or Delete RPC exists or may be added

rpc Query(DTLQuery) -> DTLEntryStream
  requires: filter by author, time range, entry type
  returns:  ordered stream of DTLEntry
  errors:   QUERY_TOO_BROAD, CTX_ID_INVALID
```

**Full contract specifications with all field types, enum values, and version negotiation rules are in `forge-standards/INTERFACES.md`.**

## Wire Formats and Schemas

### CtxIdToken

```
{
  "schema_version": 1,
  "id": "uuid-v4",
  "subject": "string (max 256 chars, UTF-8, no control chars)",
  "issued_at": "RFC 3339 timestamp",
  "expires_at": "RFC 3339 timestamp",
  "attestation_ref": "hex-encoded SHA-256",
  "signature": "base64url-encoded Ed25519 signature",
  "issuer_key_id": "hex-encoded 32-byte key identifier"
}
```

### DelegationLink

```
{
  "schema_version": 1,
  "delegation_id": "uuid-v4",
  "issuer_ctx_id": "uuid-v4 (references CtxIdToken.id)",
  "delegate_ctx_id": "uuid-v4 (references CtxIdToken.id)",
  "permissions": ["string array, each max 128 chars"],
  "issued_at": "RFC 3339 timestamp",
  "expires_at": "RFC 3339 timestamp",
  "depth": "u8 (0-indexed, max value 4 for 5-hop limit)",
  "parent_delegation_id": "uuid-v4 | null (null for root delegations)",
  "signature": "base64url-encoded Ed25519 signature"
}
```

### DTLEntry

```
{
  "schema_version": 1,
  "entry_hash": "hex-encoded SHA-256",
  "prev_hash": "hex-encoded SHA-256",
  "sequence": "u64",
  "timestamp": "RFC 3339 timestamp",
  "author_ctx_id": "uuid-v4",
  "entry_type": "enum: CTX_ISSUED | CTX_REVOKED | DELEGATION_ISSUED | DELEGATION_REVOKED | ZONE_TRANSITION | ATTESTATION | POLICY_COMPILED",
  "payload": "base64url-encoded bytes (type-specific, max 64 KiB)",
  "signature": "base64url-encoded Ed25519 signature"
}
```

### PolicyDecision

```
{
  "effect": "enum: ALLOW | DENY",
  "matched_rules": ["RuleId strings"],
  "trace": {
    "evaluated_rules": "u32",
    "eval_duration_us": "u64",
    "policy_version": "u64",
    "policy_hash": "hex-encoded SHA-256"
  }
}
```

**Complete schema catalog with all enums, nested types, and migration rules is in `forge-standards/INTERFACES.md`.**

## Error Handling Rules

### Fail-Closed Mandate

Every subsystem must fail closed. If a dependency is unreachable, if a timeout fires, if a response is malformed, or if an unexpected error variant is encountered — **deny the request**. There is no "best-effort allow" mode in Forge.

### Error Classification and Required Behavior

| Error Class | Examples | Required Action |
|---|---|---|
| **Authentication failure** | TOKEN_EXPIRED, SIGNATURE_INVALID, CTX_ID_INVALID | Deny immediately. Do not retry. Log (redacted) at WARN. |
| **Authorization failure** | POLICY_DENIED, NOT_AUTHORIZED, CHAIN_TOO_DEEP | Deny immediately. Do not retry. Log at WARN with decision trace. |
| **Transient infrastructure** | Timeout, connection reset, DTL peer unavailable | Deny the current request. Retry is the caller's responsibility (with backoff). Log at ERROR. |
| **Data integrity** | PREV_HASH_MISMATCH, DUPLICATE_ENTRY, DOMAIN_TAG_MISMATCH | Deny. Trigger an integrity alert. Log at CRITICAL. Do not retry — manual investigation required. |
| **Internal/unexpected** | Panic, OOM, unknown enum variant | Deny. Crash the request handler (not the process). Log full context at CRITICAL with stack trace. |

### Banned Error Handling Patterns

- **Never use `unwrap()` or `expect()` in production paths.** Use explicit error propagation with typed errors.
- **Never swallow errors with `_ = potentially_failing_call()`.** Every error must be logged and propagated.
- **Never return a generic 500 with no structured error body.** Use the Forge error envelope: `{ "error_code": string, "message": string, "trace_id": string }`.
- **Never retry authentication or authorization failures.** These are deterministic; retrying is a waste and a potential amplification vector.
- **Never catch a panic and continue processing the same request.** Panics indicate invariant violations; the request is tainted.

### Error Propagation Convention

All Rust subsystems use `forge_lib::ForgeError` as the error type. All Go subsystems use `forgeerr.ForgeError`. Both implement:

```
ForgeError {
    code: ErrorCode,        // enum from forge-standards/INTERFACES.md
    message: String,        // human-readable, never contains secrets
    source: Option<Box>,    // wrapped cause
    trace_id: String,       // propagated from request CTX-ID
}
```

## Testing Requirements