#!/usr/bin/env python3
"""
forge_standards_adrs_generator.py

Generates the foundational ADR framework files for Consensus Dev Agent.

Security assumptions:
- All file writes MUST be path-validated via path_security.validate_write_path()
  before execution.
- No external input is trusted; these are static governance documents.
- No secrets, credentials, or runtime config are embedded.
- No caches or buffers allocated -- OI-13 compliant, zero dynamic allocation.

Failure behavior:
- Fails closed if path validation rejects any target path.
- All errors surface with full context (path, reason).
- No silent fallback -- if a write fails, the process halts with error.
"""

import os
import sys
from pathlib import Path

# --- Memory allocation note (OI-13): ---
# Only string constants below. No caches, no buffers, no dynamic collections.
# Total static string allocation: ~18KB across 3 document constants.

# ---------------------------------------------------------------------------
# FILE 1: forge-standards/adrs/ADR_TEMPLATE.md
# ---------------------------------------------------------------------------

ADR_TEMPLATE_CONTENT = r"""<!-- forge-standards/adrs/ADR_TEMPLATE.md -->
<!-- GOVERNANCE: This template is authoritative per ADR-0o01 Tier 3 (Shared Contracts). -->
<!-- SECURITY: Any ADR touching auth/crypto/identity MUST flag Security-Critical: Yes -->
<!-- and MUST reference TRD-11 controls in its Context section. -->

# ADR-{ID}: {Title}

| Field               | Value                                                |
|---------------------|------------------------------------------------------|
| **ID**              | ADR-{ID}                                             |
| **Title**           | {Title}                                              |
| **Status**          | {Proposed \| Accepted \| Deprecated \| Superseded by ADR-XXX} |
| **Date**            | YYYY-MM-DD                                           |
| **Authors**         | {author names or handles}                            |
| **Security-Critical** | {Yes \| No}                                       |
| **TRDs Referenced** | {e.g., TRD-11, TRD-3, TRD-4}                        |
| **Supersedes**      | {ADR-XXX or None}                                    |
| **Gated**           | {Yes -- requires operator approval \| No}             |

---

## Status

<!-- One of: Proposed, Accepted, Deprecated, Superseded by ADR-XXX.        -->
<!-- Security-Critical ADRs in Proposed status MUST NOT be acted upon       -->
<!-- until Accepted. Fail closed: do not implement ambiguous decisions.     -->

**{Status}**

---

## Context

<!-- Describe the forces at play. Include:                                   -->
<!--   1. What problem or conflict triggered this decision?                  -->
<!--   2. Which TRDs are involved and what are their boundary claims?        -->
<!--   3. Are there security implications? If yes, reference TRD-11 controls -->
<!--      explicitly and explain how fail-closed behavior is maintained.     -->
<!--   4. What external constraints (platform, regulatory, OI-13 memory     -->
<!--      budget) apply?                                                     -->
<!-- All referenced TRD sections must use format: TRD-{N} §{Section}        -->

{Context}

---

## Decision

<!-- State the decision precisely and unambiguously.                         -->
<!-- Use imperative voice: "We will...", "The system SHALL..."               -->
<!-- If this decision involves precedence, reference ADR-0o01 tier explicitly.-->
<!-- Security decisions MUST include the failure mode:                        -->
<!--   "On failure, the system SHALL {fail closed / reject / halt}."         -->

{Decision}

---

## Consequences

<!-- List consequences in three categories:                                  -->

### Positive

<!-- Benefits, risk reductions, clarity improvements.                        -->

- {consequence}

### Negative

<!-- Costs, complexity increases, constraints imposed.                       -->

- {consequence}

### Neutral / Trade-offs

<!-- Things that change but are neither clearly positive nor negative.        -->

- {consequence}

---

## Compliance Checklist

<!-- All ADRs MUST complete this checklist before moving to Accepted status. -->
<!-- A checklist with any unchecked security-relevant item blocks Accepted.  -->

| # | Requirement                                                              | Done |
|---|--------------------------------------------------------------------------|------|
| 1 | No hardcoded secrets or credentials in this ADR or referenced artifacts  | [ ]  |
| 2 | Security-Critical flag is correctly set                                  | [ ]  |
| 3 | All referenced TRDs are listed in the metadata table                     | [ ]  |
| 4 | Failure behavior is explicitly stated (fail closed where applicable)     | [ ]  |
| 5 | If Security-Critical: Yes, TRD-11 controls are referenced in Context     | [ ]  |
| 6 | ADR_INDEX.md has been updated with this ADR entry                        | [ ]  |
| 7 | Operator gate requirement is correctly flagged                           | [ ]  |
| 8 | No OI-13 budget violations introduced by this decision                   | [ ]  |
| 9 | Consequences section covers Positive, Negative, and Neutral categories   | [ ]  |

---

## References

<!-- Link to TRDs, prior ADRs, external standards, or Forge Engineering Standards. -->

- {reference}
"""

# ---------------------------------------------------------------------------
# FILE 2: forge-standards/adrs/ADR_INDEX.md
# ---------------------------------------------------------------------------

ADR_INDEX_CONTENT = r"""<!-- forge-standards/adrs/ADR_INDEX.md -->
<!-- GOVERNANCE: This is the authoritative index of all Architecture Decision Records. -->
<!-- SECURITY: Security-Critical ADRs are flagged and MUST NOT be modified without -->
<!-- operator gate approval. See ADR-0o01 for precedence rules. -->
<!-- MAINTENANCE: Update this index atomically with every new/modified ADR. -->

# ADR Index -- Consensus Dev Agent

> **Invariant**: Every ADR in `forge-standards/adrs/` MUST have a corresponding
> row in this table. An ADR without an index entry is non-authoritative and
> MUST NOT be acted upon. Fail closed on ambiguity.

| ID      | Title                              | Status   | Date       | Security-Critical | Gated |
|---------|------------------------------------|----------|------------|--------------------|-------|
| ADR-0o01 | Cross-TRD Precedence Hierarchy     | Accepted | 2026-0o3-19 | Yes                | Yes   |
| ADR-0o02 | Two-Process Isolation Boundary     | Accepted | 2026-0o3-19 | Yes                | Yes   |

---

## Status Definitions

| Status                  | Meaning                                                                 |
|-------------------------|-------------------------------------------------------------------------|
| **Proposed**            | Under review. MUST NOT be implemented. No behavioral changes permitted. |
| **Accepted**            | Ratified. Binding on all subsystems. Operator-gated if flagged.         |
| **Deprecated**          | No longer recommended. Existing usage should migrate.                   |
| **Superseded by ADR-X** | Replaced. The superseding ADR is now authoritative.                    |

---

## Process

1. Copy `ADR_TEMPLATE.md` to `ADR-{NNN}-{slug}.md`.
2. Fill all metadata fields. Security-Critical flag is **mandatory**.
3. Complete the Compliance Checklist. All items must be checked for Accepted status.
4. Submit PR. Security-Critical ADRs require explicit operator approval gate.
5. On merge, update this index **in the same commit**. Atomic update is required.
6. ADRs MUST NOT be deleted -- only Deprecated or Superseded.

---

## Validation Rules

- IDs are sequential, zero-padded to 3 digits (ADR-0o01, ADR-0o02, ...).
- No two ADRs may share an ID. Duplicate IDs are a build-breaking error.
- Every Security-Critical ADR MUST reference TRD-11 in its TRDs Referenced field.
- Gated ADRs require operator sign-off before the PR can merge.
- Every ADR MUST include a completed Compliance Checklist section.
"""

# ---------------------------------------------------------------------------
# FILE 3: forge-standards/adrs/ADR-0o01-precedence-hierarchy.md
# ---------------------------------------------------------------------------

ADR_001_CONTENT = r"""<!-- forge-standards/adrs/ADR-0o01-precedence-hierarchy.md -->
<!-- SECURITY: This ADR is Security-Critical. TRD-11 controls are Tier 1. -->
<!-- Any modification to this ADR requires operator gate approval. -->

# ADR-0o01: Cross-TRD Precedence Hierarchy

| Field               | Value                                                     |
|---------------------|-----------------------------------------------------------|
| **ID**              | ADR-0o01                                                   |
| **Title**           | Cross-TRD Precedence Hierarchy                            |
| **Status**          | Accepted                                                  |
| **Date**            | 2026-0o3-19                                                |
| **Authors**         | YouSource.ai Engineering                                  |
| **Security-Critical** | Yes                                                    |
| **TRDs Referenced** | TRD-1, TRD-3, TRD-4, TRD-5, TRD-7, TRD-9, TRD-11       |
| **Supersedes**      | None                                                      |
| **Gated**           | Yes -- requires operator approval                          |

---

## Status

**Accepted**

---

## Context

The Consensus Dev Agent architecture is defined across multiple Technical
Requirements Documents (TRDs), each owning a specific subsystem boundary:

- **TRD-1**: App Shell -- XPC, Keychain, engineer identity
- **TRD-3**: Build Pipeline -- stage contracts, pipeline logic
- **TRD-4**: Multi-Agent Coordination -- ledger, consensus protocol
- **TRD-5**: GitHub Operations -- API interactions, PR management
- **TRD-7**: Development Workflow -- TRD boundary definition, merge/split rules
- **TRD-9**: Mac CI Runner -- runner security and isolation
- **TRD-11**: Security Controls -- auth, crypto, identity, fail-closed policy

Conflicts arise when:

1. Two TRDs make overlapping claims about the same interface or behavior.
2. A shared contract (e.g., XPC message format) is referenced by multiple TRDs
   with subtly different expectations.
3. An implementation decision is made that has no explicit TRD coverage.
4. A security control in TRD-11 constrains behavior that another TRD's domain
   logic would otherwise permit.

Without a codified precedence hierarchy, engineers and the agent itself face
ambiguous resolution paths. Per Forge Engineering Standards, ambiguity in
security-relevant decisions MUST fail closed. This ADR eliminates that ambiguity.

### Security Context

TRD-11 defines the security invariants that protect the entire system:
- Fail closed on auth, crypto, and identity errors
- No silent failure paths
- Secrets never in logs or generated code
- All external input is untrusted
- Generated code is never executed by the agent

These invariants are **non-negotiable** and MUST override any conflicting
requirement from any other TRD. This is not a suggestion -- it is a hard
constraint derived from the threat model of an AI agent that generates and
reviews code in defense/financial sector environments.

### Process Isolation Context

TRD-9 §13 (Runner Security and Isolation) and TRD-1 (App Shell -- XPC boundary)
establish that the system operates across process boundaries. The two-process
isolation model (UI host process + agent XPC service) is a security-critical
architectural decision that intersects with TRD-3 (pipeline execution), TRD-4
(multi-agent coordination), and TRD-5 (GitHub operations). Precedence rules
must account for cross-process boundary decisions.

---

## Decision

### Four-Tier Precedence Hierarchy

We establish the following strict precedence hierarchy for resolving conflicts
between TRDs, shared contracts, and implementation decisions. **Higher tiers
override lower tiers unconditionally.** There is no exception mechanism for
Tier 1.

#### Tier 1: TRD-11 Security Controls (Absolute Precedence)

- **Scope**: All security invariants defined in TRD-11, including but not
  limited to: authentication, authorization, cryptographic operations, identity
  verification, secret handling, input validation, and fail-closed behavior.
- **Override rule**: No other TRD, ADR, shared contract, or implementation
  decision may weaken, bypass, or conditionally disable a Tier 1 control.
- **Failure mode**: On conflict detection, the system SHALL halt and surface
  the conflict to the operator gate. The conflicting lower-tier requirement
  is **blocked** until the operator explicitly resolves the conflict.
- **Modification**: Tier 1 rules may only be modified by amending TRD-11
  itself, which requires operator gate approval and security review.

#### Tier 2: Owning TRD Domain Rules

- **Scope**: Each TRD is authoritative over its defined domain boundary
  (as established in TRD-7 §6, Phase 3: TRD Boundary Definition).
- **Override rule**: Within its domain, a TRD's requirements override shared
  contracts and implementation decisions, provided they do not conflict with
  Tier 1.
- **Boundary disputes**: When two TRDs claim authority over the same behavior:
  1. Check if TRD-7 boundary definitions resolve the overlap.
  2. If unresolved, the TRD that **owns the data** (writes it, stores it,
     validates it) takes precedence over the TRD that **consumes** the data.
  3. If still unresolved, escalate to operator gate. Do NOT auto-resolve.
- **Failure mode**: On unresolvable Tier 2 conflict, the system SHALL gate
  and wait indefinitely for operator input. No auto-approve.

#### Tier 3: Shared Contracts and Interfaces

- **Scope**: Cross-TRD interfaces including XPC message schemas, pipeline
  stage contracts, ledger record formats, API response shapes, and ADR
  governance rules (including this template).
- **Override rule**: Shared contracts override implementation decisions but
  yield to Tier 1 and Tier 2.
- **Modification**: Changes to shared contracts require updating all
  consuming TRDs' compatibility notes. Breaking changes require a new ADR.
- **Failure mode**: On contract violation, the system SHALL reject the
  non-conforming message/artifact and log the violation with full context
  (source TRD, expected schema, actual payload shape -- never payload content
  that might contain secrets).

#### Tier 4: Implementation Decisions

- **Scope**: All decisions not covered by Tiers 1-3, including algorithm
  choices, internal data structures, performance optimizations, and
  module-internal APIs.
- **Override rule**: Implementation decisions yield to all higher tiers.
- **Documentation**: Implementation decisions that affect cross-module
  behavior SHOULD be recorded as ADRs for traceability.
- **Failure mode**: Implementation-level errors surface with context but
  do not trigger operator gates unless they cascade to higher-tier violations.

### Precedence Resolution Algorithm

When a conflict is detected (by engineer, agent, or CI validation):

```
1. CLASSIFY each conflicting requirement by tier (1-4).
2. IF tiers differ:
     The higher-tier requirement wins. No negotiation.
     Log: "Precedence: Tier {winner} overrides Tier {loser}: {description}"
3. IF tiers are equal AND tier is 1:
     HALT. Gate for operator. TRD-11 internal conflicts are critical.
4. IF tiers are equal AND tier is 2:
     Apply Tier 2 boundary dispute rules (data ownership, then gate).
5. IF tiers are equal AND tier is 3:
     The more recently Accepted shared contract wins.
     If same date, gate for operator.
6. IF tiers are equal AND tier is 4:
     The implementation with test coverage wins.
     If equal coverage, either is acceptable (developer discretion).
7. ALWAYS log the resolution with: tier, winning requirement, losing
   requirement, rationale, and timestamp.
```

### Application to Two-Process Isolation Boundary

The two-process isolation model is classified as follows:

- **The existence of the process boundary** (UI host vs. agent XPC service)
  is a **Tier 1** decision because it enforces privilege separation, a
  TRD-11 security control. It MUST NOT be collapsed into a single process.
- **XPC message schemas** crossing the boundary are **Tier 3
