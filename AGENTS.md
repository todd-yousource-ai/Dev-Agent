

# AGENTS.md — Forge Platform

Forge is a trust-enforcement runtime platform that validates every context identity (CTX-ID), virtualisation zone (VTZ), and data-transit layer (DTL) operation against cryptographically signed policy before any action executes, failing closed on every violation.

## How to Use This File

This file is the mandatory baseline context for every coding session — read it fully before writing or modifying any Forge code. For subsystem-specific implementation detail, see `forge-docs/` for the canonical TRDs/PRDs and `forge-standards/` for synthesised architecture, interface contracts, and decision records; the key reference files are listed in the Document Index below.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| TrustFlow TRD | TRD | `forge-docs/trd-trustflow.md` | TrustFlow engine: policy evaluation pipeline, trust scoring, chain-of-custody validation |
| CTX-ID TRD | TRD | `forge-docs/trd-ctx-id.md` | Context Identity subsystem: identity minting, rotation, revocation, binding to VTZ |
| VTZ TRD | TRD | `forge-docs/trd-vtz.md` | Virtualisation Zones: zone lifecycle, isolation boundaries, resource caps, teardown |
| DTL TRD | TRD | `forge-docs/trd-dtl.md` | Data Transit Layer: encrypted channel setup, schema validation, transit policy enforcement |
| Forge Platform PRD | PRD | `forge-docs/prd-forge-platform.md` | Product requirements, user stories, acceptance criteria for the full platform |
| Architecture Reference | Standard | `forge-standards/ARCHITECTURE.md` | Subsystem map, dependency graph, deployment topology, runtime invariants |
| Interface Contracts | Standard | `forge-standards/INTERFACES.md` | Every inter-subsystem API: method signatures, wire formats, error codes, versioning |
| Decision Log | Standard | `forge-standards/DECISIONS.md` | ADRs for all architectural choices: cryptographic primitives, storage engines, protocol versions |
| Security Model | Standard | `forge-standards/SECURITY.md` | Threat model, trust boundaries, key management lifecycle, audit-log requirements |
| Testing Strategy | Standard | `forge-standards/TESTING.md` | Coverage targets, fuzz targets, negative-test mandates, CI gate criteria |
| Engineering Standards | Standard | `forge-standards/ENGINEERING.md` | Coding style, error handling patterns, logging conventions, banned patterns |
| Runbook | Ops | `docs/RUNBOOK.md` | Operational playbooks for incident response, key rotation, zone recovery |
| Branch Context | Context | `docs/CONTEXT.md` | Branch-specific goals, in-progress work, known tech debt |

## Critical Rules — Non-Negotiable

1. **Fail closed on every trust evaluation.** If TrustFlow cannot reach a definitive ALLOW verdict, the request MUST be denied; never default to permissive.
2. **Validate CTX-ID before any subsystem call.** Every public API entry point MUST authenticate and authorise the CTX-ID in the request header before executing business logic.
3. **Never transmit plaintext across a DTL channel.** All DTL payloads MUST be encrypted with the session key negotiated during channel setup; reject any unencrypted frame at the receiver.
4. **VTZ isolation is a hard boundary.** Code in one VTZ MUST NOT read, write, or signal memory, files, or network sockets belonging to another VTZ; enforce at the syscall layer.
5. **Never log secrets, keys, or raw CTX-ID tokens.** Log only the CTX-ID fingerprint (first 8 hex chars) and never the bearer token, session key, or private key material.
6. **Every DTL schema change requires a version bump.** Wire format changes MUST increment the DTL schema version; receivers MUST reject unknown versions.
7. **TrustFlow policy documents are immutable once signed.** Never mutate a signed policy in place; publish a new version and rotate the reference.
8. **All crypto operations use Forge-approved primitives only.** Use Ed25519 for signatures, X25519 for key agreement, AES-256-GCM for symmetric encryption, BLAKE3 for hashing. No exceptions.
9. **CTX-ID rotation MUST complete atomically.** If rotation fails mid-flight, roll back to the previous CTX-ID and emit a `CTX_ROTATION_FAILED` alert; never leave a zone with an unbound identity.
10. **VTZ teardown MUST zeroize all memory before releasing resources.** Use explicit `memzero` on all key material and sensitive buffers; do not rely on garbage collection or OS page recycling.
11. **Every inter-subsystem call MUST include a trace ID propagated from the originating CTX-ID request.** Do not generate new root traces mid-pipeline.
12. **No panics in production code paths.** Return typed errors through the Result chain. Panics are permitted only in test harnesses and must be annotated `// PANIC: test-only`.
13. **All public functions MUST have unit tests covering the success path and at least two distinct failure paths.** PRs missing this coverage MUST NOT merge.
14. **Never bypass TrustFlow with feature flags, environment variables, or build tags.** Trust evaluation is always on; there is no "dev mode" that skips policy checks.
15. **Audit log writes are synchronous and MUST succeed before the triggering operation returns.** If the audit log is unavailable, the operation fails; never fire-and-forget an audit event.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    API Gateway                       │
│  Authenticates CTX-ID → routes to subsystem          │
└──────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌──▼───┐ ┌───▼─────┐
  │ CTX-ID │ │TrustFlow│ │ VTZ  │ │  DTL    │
  │ Service│ │ Engine  │ │ Mgr  │ │ Service │
  └───┬────┘ └───┬────┘ └──┬───┘ └───┬─────┘
      │          │         │         │
      └──────────┴────┬────┴─────────┘
                      │
              ┌───────▼────────┐
              │  Audit Log /   │
              │  Policy Store  │
              └────────────────┘
```

### CTX-ID Service
- **Enforces:** Identity minting, validation, rotation, revocation, and binding to VTZ zones.
- **Called by:** API Gateway (on every inbound request), VTZ Manager (zone binding), DTL Service (channel auth).
- **Calls:** Policy Store (identity policy lookup), Audit Log (identity lifecycle events).
- **MUST NEVER:** Issue a CTX-ID without validating the requesting principal's credentials against the active policy. MUST NEVER cache identity decisions beyond the TTL declared in the policy.

### TrustFlow Engine
- **Enforces:** Policy evaluation, trust scoring, chain-of-custody validation, and allow/deny verdicts.
- **Called by:** API Gateway (pre-route policy check), CTX-ID Service (rotation authorisation), VTZ Manager (zone creation authorisation), DTL Service (transit policy).
- **Calls:** Policy Store (policy document retrieval), Audit Log (verdict logging).
- **MUST NEVER:** Return an ambiguous verdict. MUST NEVER cache a policy document past its `max-age` header. MUST NEVER evaluate against an unsigned or expired policy.

### VTZ Manager
- **Enforces:** Zone lifecycle (create, suspend, resume, teardown), resource caps, isolation invariants, memory zeroization on teardown.
- **Called by:** API Gateway (zone operations), CTX-ID Service (binding notifications).
- **Calls:** TrustFlow (zone creation authorisation), CTX-ID Service (identity binding verification), Audit Log (zone lifecycle events), OS/hypervisor layer (isolation enforcement).
- **MUST NEVER:** Allow cross-zone resource access. MUST NEVER skip memory zeroization. MUST NEVER create a zone without a TrustFlow ALLOW verdict.

### DTL Service
- **Enforces:** Encrypted channel establishment, schema-validated transit, payload integrity, session key rotation.
- **Called by:** API Gateway (data transit requests), any subsystem sending inter-zone data.
- **Calls:** CTX-ID Service (channel endpoint authentication), TrustFlow (transit policy evaluation), Audit Log (transit events).
- **MUST NEVER:** Transmit a payload that fails schema validation. MUST NEVER reuse a session key past its rotation interval. MUST NEVER downgrade cipher suite negotiation.

### Audit Log
- **Enforces:** Immutable, append-only event log with cryptographic chaining (BLAKE3 hash chain).
- **Called by:** Every subsystem (all security-relevant events).
- **Calls:** Persistent storage backend.
- **MUST NEVER:** Allow deletion or mutation of existing entries. MUST NEVER drop events silently. MUST NEVER accept an event without a valid CTX-ID fingerprint and trace ID.

### Policy Store
- **Enforces:** Signed policy document storage, versioning, retrieval, and expiry.
- **Called by:** TrustFlow (policy retrieval), CTX-ID Service (identity policy lookup).
- **Calls:** Persistent storage backend, Audit Log (policy mutation events).
- **MUST NEVER:** Serve an unsigned policy document. MUST NEVER serve an expired policy. MUST NEVER allow in-place mutation of a signed document.

## Interface Contracts — All Subsystems

### CTX-ID Minting
```
POST /ctx-id/mint
Request:  { principal_cred: bytes, vtz_id: string?, policy_ref: string }
Response: { ctx_id: CTX-ID, fingerprint: string, expires_at: u64, bound_vtz: string? }
Errors:   CTX_INVALID_CRED (401), CTX_POLICY_DENIED (403), CTX_STORE_UNAVAIL (503)
```

### CTX-ID Validation
```
GET /ctx-id/validate/{fingerprint}
Header:   Authorization: Bearer <ctx-id-token>
Response: { valid: bool, expires_at: u64, bound_vtz: string?, trust_score: f64 }
Errors:   CTX_NOT_FOUND (404), CTX_EXPIRED (410), CTX_REVOKED (410)
```

### TrustFlow Evaluate
```
POST /trustflow/evaluate
Request:  { ctx_id_fingerprint: string, action: string, resource: string, context: map }
Response: { verdict: "ALLOW" | "DENY", score: f64, policy_version: string, trace_id: string }
Errors:   TF_POLICY_NOT_FOUND (404), TF_POLICY_EXPIRED (410), TF_ENGINE_ERROR (500)
```

### VTZ Create
```
POST /vtz/create
Request:  { ctx_id_fingerprint: string, resource_caps: ResourceCaps, policy_ref: string }
Response: { vtz_id: string, state: "ACTIVE", created_at: u64, bound_ctx_id: string }
Errors:   VTZ_AUTH_DENIED (403), VTZ_RESOURCE_EXCEEDED (429), VTZ_CREATE_FAILED (500)
```

### VTZ Teardown
```
POST /vtz/{vtz_id}/teardown
Request:  { ctx_id_fingerprint: string, force: bool }
Response: { vtz_id: string, state: "TORN_DOWN", zeroized: bool, teardown_at: u64 }
Errors:   VTZ_NOT_FOUND (404), VTZ_TEARDOWN_FAILED (500)
```

### DTL Channel Open
```
POST /dtl/channel/open
Request:  { src_ctx_id: string, dst_ctx_id: string, schema_version: u32, policy_ref: string }
Response: { channel_id: string, session_key_id: string, schema_version: u32, expires_at: u64 }
Errors:   DTL_AUTH_DENIED (403), DTL_SCHEMA_MISMATCH (422), DTL_CHANNEL_FAILED (500)
```

### DTL Send
```
POST /dtl/channel/{channel_id}/send
Request:  { payload: encrypted_bytes, schema_version: u32, integrity_hash: string }
Response: { ack: bool, sequence: u64 }
Errors:   DTL_SCHEMA_INVALID (422), DTL_INTEGRITY_FAILED (400), DTL_CHANNEL_EXPIRED (410)
```

See `forge-standards/INTERFACES.md` for the full contract list including batch operations, health checks, and admin endpoints.

## Wire Formats and Schemas

### CTX-ID Token (JWT-like, Ed25519-signed)
```
{
  "fingerprint": string,        // BLAKE3(public_key)[0:16] hex-encoded
  "issued_at":   u64,           // Unix epoch seconds
  "expires_at":  u64,           // Unix epoch seconds
  "bound_vtz":   string | null, // VTZ ID or null if unbound
  "issuer":      string,        // CTX-ID Service instance ID
  "signature":   bytes          // Ed25519 over canonical JSON of above fields
}
```

### TrustFlow Policy Document
```
{
  "version":      string,       // Semver (e.g., "2.4.1")
  "rules":        Rule[],       // Ordered evaluation; first match wins
  "default":      "DENY",       // MUST always be DENY
  "signed_by":    string,       // Fingerprint of signing key
  "signature":    bytes,        // Ed25519 over BLAKE3(canonical JSON of version+rules+default)
  "max_age_secs": u64           // Cache TTL; policy store MUST NOT serve past this
}
```

### Rule
```
{
  "id":        string,
  "action":    string,          // Glob pattern (e.g., "vtz:create")
  "resource":  string,          // Glob pattern (e.g., "zone:prod-*")
  "conditions": Condition[],
  "verdict":   "ALLOW" | "DENY"
}
```

### DTL Frame
```
| version: u8 | schema_version: u32 | channel_id: 16 bytes | sequence: u64 |
| payload_len: u32 | encrypted_payload: [u8; payload_len] | integrity: 32 bytes (BLAKE3) |
```

### VTZ ResourceCaps
```
{
  "max_memory_bytes": u64,
  "max_cpu_millis":   u64,
  "max_fds":          u32,
  "max_net_egress":   u64,      // bytes per second; 0 = no egress
  "max_ttl_secs":     u64       // zone auto-teardown deadline
}
```

### Audit Log Entry
```
{
  "entry_id":       u64,        // Monotonic, gapless
  "timestamp":      u64,
  "ctx_id_fp":      string,     // Fingerprint only, never full token
  "trace_id":       string,
  "subsystem":      string,     // "ctx-id" | "trustflow" | "vtz" | "dtl" | "policy-store"
  "event_type":     string,
  "payload":        map,        // Subsystem-specific; MUST NOT contain secrets
  "prev_hash":      bytes,      // BLAKE3 of previous entry
  "hash":           bytes       // BLAKE3(entry_id || timestamp || ... || prev_hash)
}
```

Reference `forge-standards/INTERFACES.md` for the full schema catalogue.

## Error Handling Rules

1. **Fail closed.** Any error in TrustFlow evaluation, CTX-ID validation, or DTL integrity checking MUST result in denial of the triggering operation. Never optimistically proceed.
2. **Return typed errors.** Use the `ForgeError` enum (defined in `src/common/error.rs`). Do not use raw strings or integer codes outside of wire serialisation.
3. **Map errors at subsystem boundaries.** Internal errors MUST be mapped to the subsystem's public error type before crossing an API boundary. Never leak internal stack traces to callers.
4. **Retry only on transient errors.** Retry is permitted only for `503 / *_UNAVAIL` errors. Do not retry `4xx` errors. Retry with exponential backoff (base 100ms, max 3 attempts, jitter).
5. **Audit every denied operation.** Every DENY verdict, failed validation, and rejected frame MUST produce an audit log entry before the error response is sent.
6. **Banned patterns:**
   - `unwrap()` and `expect()` in non-test code.
   - Catch-all `_ =>` arms that silently discard error variants.
   - Empty `catch` / `except` blocks.
   - Logging an error and then returning `Ok` / success.
   - `todo!()` or `unimplemented!()` in any code path reachable from a public API.
7. **Timeouts are errors.** Every outbound call (subsystem-to-subsystem, storage, external) MUST have an explicit timeout. Timeout fires → treat as transient error → fail closed.
8. **Poison on corruption.** If an audit log hash-chain validation fails, or a policy signature is invalid, mark the affected subsystem as POISONED and refuse all requests until operator intervention. Emit `SUBSYSTEM_POISONED` alert.

## Testing Requirements

1. **90% line coverage minimum.** CI gates on 90% for every subsystem crate. No exceptions, no `#[cfg(not(tarpaulin_include))]` on business logic.
2. **Every public function has:**
   - At least one positive test (happy path).
   - At least two negative tests (distinct failure modes — e.g., expired CTX-ID, invalid signature).
3. **Mandatory negative tests for every security boundary:**
   - Cross-VTZ access attempts MUST be tested and MUST fail.
   - Unsigned/expired/revoked CTX-ID MUST be rejected.
   - Tampered DTL frames MUST be rejected.
   - Expired policies MUST not evaluate to ALLOW.
4. **Fuzz targets:** Maintain fuzz harnesses in `src/{subsystem}/fuzz/` for:
   - DTL frame parsing (`dtl_frame_fuzz`).
   - TrustFlow policy parsing (`policy_parse_fuzz`).
   - CTX-ID token deserialisation (`ctx_id_token_fuzz`).
   - Run fuzz targets for a minimum of 10 million iterations in weekly CI.
5. **Integration tests** in `tests/integration/` MUST spin up all four subsystems and validate end-to-end flows: mint CTX-ID → create VTZ → open DTL channel → send data → teardown VTZ.
6. **Property-based tests** for all crypto operations: verify that sign→verify round-trips, encrypt→decrypt round-trips, and that any single-bit flip in ciphertext causes integrity rejection.
7. **Audit log chain tests:** Every test that writes audit events MUST validate the hash chain is intact at test teardown.
8. **No mocking of TrustFlow in integration tests.** Use real policy documents signed with test keys. Test keys live in `tests/fixtures/keys/` and MUST NOT appear in production config.

## File Naming and Directory Layout

```
src/
├── common/                     # Shared types, error enum, crypto primitives
│   ├── error.rs                # ForgeError enum — all subsystem error types
│   ├── crypto.rs               # Ed25519, X25519, AES-256-GCM, BLAKE3 wrappers
│   ├── types.rs                # CTX-ID,