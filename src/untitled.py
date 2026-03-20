# ADR_TEMPLATE.md

```markdown
# ADR-{NUMBER}: {TITLE}

<!-- FORGE:ANCHOR adr_template_v1 -->
<!-- 
  Forge ADR Template -- Canonical format for all Architectural Decision Records.
  
  Security assumptions:
  - This template is treated as untrusted input when parsed programmatically.
  - All field values MUST be validated against allowed enumerations before indexing.
  - ADR files are append-only in main; amendments require a new ADR superseding the original.
  
  Failure behavior:
  - Any ADR missing required metadata fields MUST be rejected by CI lint.
  - Status values outside the enumeration MUST fail closed (reject, do not default).
  
  OI-13 allocation: This file is a static template; zero runtime memory allocation.
-->

## Metadata

| Field              | Value                                                                        |
|--------------------|------------------------------------------------------------------------------|
| **ADR ID**         | ADR-{NUMBER}                                                                 |
| **Title**          | {TITLE}                                                                      |
| **Status**         | {Draft \| Proposed \| Accepted \| Deprecated \| Superseded}                  |
| **Date**           | YYYY-MM-DD                                                                   |
| **Author**         | {author}                                                                     |
| **Deciders**       | {list of approvers}                                                          |
| **Depends On**     | {ADR-xxx, TRD-xx, or "None"}                                                |
| **Supersedes**     | {ADR-xxx or "None"}                                                          |
| **Superseded By**  | {ADR-xxx or "None"}                                                          |

### Status Values (Enumeration -- CI-enforced)

- **Draft** -- Under authorship, not yet reviewed.
- **Proposed** -- Submitted for review; operator gate required before acceptance.
- **Accepted** -- Approved and binding. All implementations MUST conform.
- **Deprecated** -- No longer recommended; existing uses grandfathered with timeline.
- **Superseded** -- Replaced by a newer ADR (link in `Superseded By`).

## Context

<!--
  Describe the forces at play: technical constraints, security requirements,
  cross-TRD conflicts, operational needs, or platform invariants from Forge
  Engineering Standards.
  
  All referenced external documents (TRDs, PRDs, vendor docs) MUST be cited
  by identifier. External content is untrusted input -- quote, do not inline.
-->

{Describe the problem, forces, and constraints that motivate this decision.}

## Decision

<!--
  State the decision as an imperative: "We will ...", "The system MUST ...".
  Use RFC 2119 keywords (MUST, SHOULD, MAY) for enforceability.
  
  Security decisions MUST reference the specific Forge invariant they enforce.
-->

{State the architectural decision clearly and unambiguously.}

## Consequences

### Positive

- {Benefit 1}
- {Benefit 2}

### Negative

- {Cost or trade-off 1}
- {Mitigation, if any}

### Neutral

- {Observation that is neither clearly positive nor negative}

## Compliance

<!--
  How is this ADR enforced? Every accepted ADR MUST have at least one
  automated enforcement mechanism (CI lint rule, static analysis gate,
  or runtime assertion). Human-only review is insufficient for Accepted ADRs.
  
  Each row MUST specify:
  - Mechanism type: one of {CI lint, Static analysis, Runtime assertion, Code review}
  - Automation: whether the mechanism is automated (REQUIRED for at least one row)
  - Gate behavior: what happens on violation (MUST fail closed)
-->

| Mechanism          | Automation | Gate Behavior          | Description                    |
|--------------------|------------|------------------------|--------------------------------|
| {CI lint / Static analysis / Runtime assertion / Code review} | {Automated \| Manual} | {Fail closed: reject PR / block deploy / halt process} | {How compliance is verified} |

## References

- {Link or identifier to related TRDs, ADRs, RFCs, or external standards}

## Changelog

| Date       | Author   | Change           |
|------------|----------|------------------|
| YYYY-MM-DD | {author} | Initial draft    |
```

# ADR_INDEX.md

```markdown
# ADR Index

<!-- FORGE:ANCHOR adr_index_v1 -->
<!--
  Living index of all Architectural Decision Records for the Consensus Dev Agent project.
  
  Security assumptions:
  - This index is the authoritative registry. ADR files not listed here are non-binding.
  - CI MUST validate that every ADR file in forge-standards/adrs/ has a corresponding
    row in this index. Orphaned ADRs fail the lint gate.
  - Status values are validated against the enumeration in ADR_TEMPLATE.md.
  
  Failure behavior:
  - Mismatch between filesystem and index → CI gate fails closed.
  - Duplicate ADR IDs → CI gate fails closed.
  
  OI-13 allocation: Static markdown; zero runtime memory allocation.
-->

## Governance

All ADRs follow the canonical template: [ADR_TEMPLATE.md](./ADR_TEMPLATE.md)

Status transitions require operator gate approval. No auto-approve -- ever.

## Index

| ADR ID  | Title                                    | Status   | Date       | Link                                          |
|---------|------------------------------------------|----------|------------|-----------------------------------------------|
| ADR-001 | Cross-TRD Precedence Hierarchy           | Accepted | 2025-07-11 | [ADR-001](./ADR-001-precedence-hierarchy.md)  |
| ADR-002 | Two-Process Isolation Boundary           | Accepted | 2025-07-11 | [ADR-002](./ADR-002-two-process-isolation.md) |

## Status Legend

| Status      | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| Draft       | Under authorship, not yet reviewed                             |
| Proposed    | Submitted for review; operator gate required before acceptance |
| Accepted    | Approved and binding; all implementations MUST conform         |
| Deprecated  | No longer recommended; grandfathered with sunset timeline      |
| Superseded  | Replaced by newer ADR; see `Superseded By` field              |

## CI Enforcement

<!--
  The following CI checks MUST pass on every PR that modifies files in
  forge-standards/adrs/:
-->

| CI Gate                   | Rule                                                                                   | Failure Mode   |
|---------------------------|----------------------------------------------------------------------------------------|----------------|
| `adr-index-sync`         | Every `.md` file in `adrs/` matching `ADR-\d+` MUST have a row in this index           | Fail closed    |
| `adr-id-unique`          | No duplicate ADR IDs across index rows or filenames                                     | Fail closed    |
| `adr-status-enum`        | Status value MUST be one of: Draft, Proposed, Accepted, Deprecated, Superseded          | Fail closed    |
| `adr-metadata-complete`  | All required metadata fields from ADR_TEMPLATE.md MUST be present and non-placeholder   | Fail closed    |
| `adr-compliance-automated`| Accepted ADRs MUST have at least one compliance row with `Automation = Automated`       | Fail closed    |
```

# ADR-001-precedence-hierarchy.md

```markdown
# ADR-001: Cross-TRD Precedence Hierarchy

<!-- FORGE:ANCHOR adr_001_precedence_hierarchy -->
<!--
  Security assumptions:
  - TRD-11 (Security) constraints are inviolable. No other TRD, ADR, or
    implementation decision may weaken, override, or contradict TRD-11.
  - This ADR itself is subject to Tier 1: if a future TRD-11 revision
    conflicts with this ADR, TRD-11 prevails and this ADR MUST be superseded.
  
  Failure behavior:
  - Any cross-TRD conflict that cannot be resolved by the hierarchy below
    MUST escalate to the operator gate. The system MUST NOT auto-resolve
    ambiguous precedence -- fail closed, gate, log.
  - CI lint MUST flag PRs that reference multiple TRDs without an explicit
    precedence annotation in the PR description.
  
  OI-13 allocation: Static governance document; zero runtime memory allocation.
-->

## Metadata

| Field              | Value                                                        |
|--------------------|--------------------------------------------------------------|
| **ADR ID**         | ADR-001                                                      |
| **Title**          | Cross-TRD Precedence Hierarchy                               |
| **Status**         | Accepted                                                     |
| **Date**           | 2025-07-11                                                   |
| **Author**         | Forge ConsensusDevAgent                                      |
| **Deciders**       | Engineering Lead, Security Lead                              |
| **Depends On**     | TRD-11 (Security), TRD-7 (Development Workflow)              |
| **Supersedes**     | None                                                         |
| **Superseded By**  | None                                                         |

## Context

The Consensus Dev Agent project is decomposed across multiple Technical
Requirements Documents (TRDs), each owning a bounded subsystem. When a pull
request touches concerns spanning multiple TRDs, engineers and the agent itself
need a deterministic, unambiguous rule for which specification prevails.

Without a codified hierarchy, the following failure modes arise:

1. **Security erosion** -- A convenience requirement in one TRD silently
   contradicts a security constraint in TRD-11.
2. **Deadlock** -- Two TRDs make contradictory claims with equal authority;
   the agent cannot proceed without operator intervention.
3. **Silent degradation** -- Implementation-level choices override documented
   contracts because no precedence rule exists.

Forge Engineering Standards mandate "fail closed on auth, crypto, and identity
errors" and "no silent failure paths." A precedence hierarchy is a governance
prerequisite for those invariants.

TRD-7 (Development Workflow) Section 6 defines TRD boundary mechanics (merge,
split) but does not define cross-TRD conflict resolution. This ADR fills that
gap.

## Decision

We establish a **four-tier precedence hierarchy**. When requirements from
different sources conflict, the higher tier prevails unconditionally.

### Tier 1 -- Security (TRD-11) <!-- FORGE:ANCHOR tier_1_security -->

TRD-11 security requirements are **supreme and inviolable**.

- No other TRD, ADR, or implementation decision MAY weaken, override, relax,
  or defer a TRD-11 requirement.
- If a requirement in any other TRD contradicts TRD-11, the TRD-11 requirement
  MUST be followed and the contradiction MUST be logged as a governance defect.
- This includes Forge platform invariants (fail closed, no secrets in logs,
  no eval of generated code, SECURITY_REFUSAL never bypassed).

**Traceability tag:** `[PREC:T1:SEC]` -- Use this tag in PR descriptions and
commit messages when invoking Tier 1 precedence.

### Tier 2 -- Owning TRD <!-- FORGE:ANCHOR tier_2_owning_trd -->

For any given subsystem, the **owning TRD** is authoritative over its
bounded context.

- The owning TRD defines the subsystem's contracts, invariants, and behavior.
- Example: TRD-3 (Build Pipeline) owns pipeline stage contracts; TRD-4
  (Multi-Agent Coordination) owns ledger write semantics for coordination.
- When a PR modifies code within a single TRD's boundary, that TRD's
  requirements are binding (subject to Tier 1).

**Traceability tag:** `[PREC:T2:OWN:<TRD-ID>]` -- Use this tag when invoking
Tier 2 precedence, substituting the owning TRD identifier.

### Tier 3 -- Shared Contracts <!-- FORGE:ANCHOR tier_3_shared_contracts -->

Cross-TRD interface contracts (XPC message schemas, ledger formats,
stage input/output types) are governed by the **shared contracts layer**.

- Shared contracts are defined in documents referenced by multiple TRDs
  (e.g., XPC protocol in TRD-1, stage contracts in TRD-3).
- When two owning TRDs (Tier 2) disagree on a shared interface, the
  shared contract definition prevails.
- If no shared contract exists for the disputed interface, escalation
  to the operator gate is REQUIRED (see Escalation Procedure).

**Traceability tag:** `[PREC:T3:SHR:<contract-id>]` -- Use this tag when
invoking Tier 3 precedence, substituting the shared contract identifier.

### Tier 4 -- Implementation <!-- FORGE:ANCHOR tier_4_implementation -->

Implementation-level decisions (naming conventions, internal data structures,
local optimizations) are the **lowest precedence**.

- Implementation choices MUST NOT contradict Tiers 1-3.
- Implementation choices that are not constrained by Tiers 1-3 are at
  the engineer's discretion, subject to Forge Engineering Standards.

**Traceability tag:** `[PREC:T4:IMPL]` -- Use this tag when a PR involves
only Tier 4 decisions with no cross-TRD impact.

### Precedence Resolution Rule <!-- FORGE:ANCHOR precedence_resolution_rule -->

When evaluating a conflict:

```
if conflict_involves(TRD-11 security requirement):
    → Tier 1 wins. No exceptions. Log governance defect against losing side.
elif conflict is within single TRD boundary:
    → Tier 2 (owning TRD) wins.
elif conflict is at a cross-TRD interface:
    → Tier 3 (shared contract) wins.
    → If no shared contract exists: ESCALATE.
else:
    → Tier 4. Implementation yields to all above.
```

### Escalation Procedure <!-- FORGE:ANCHOR escalation_procedure -->

When the hierarchy cannot resolve a conflict deterministically:

1. The agent MUST **stop processing** the conflicting PR.
2. The agent MUST **create a gate** with full context:
   - The two (or more) conflicting requirements, cited by TRD ID and section.
   - The tier each requirement falls under.
   - Why automatic resolution failed.
3. The gate MUST **wait indefinitely** for operator input -- no auto-approve,
   no timeout, no fallback.
4. The operator's resolution MUST be recorded as a new ADR or an amendment
   to the relevant TRD(s).

## Consequences

### Positive

- **Deterministic conflict resolution** -- Engineers and the agent have an
  unambiguous rule; no ad-hoc judgment required for the common case.
- **Security primacy** -- TRD-11 can never be weakened by another TRD,
  enforcing Forge's "fail closed" and "secure by design" invariants.
- **Audit trail** -- Escalations produce ADRs, creating a permanent record
  of governance decisions.
- **Machine-parseable traceability** -- `[PREC:Tn:*]` tags enable automated
  cross-referencing and audit logging across PRs and ADRs.

### Negative

- **Rigidity** -- Legitimate cases where a security requirement should be
  relaxed (e.g., a deprecated TRD-11 clause) require a formal TRD-11
  amendment, which adds process overhead.
  - **Mitigation**: TRD-11 amendments follow TRD-7 boundary change procedures
    with mandatory security-lead sign-off.
- **Escalation latency** -- Ambiguous conflicts block the PR until an operator
  responds, which may delay development.
  - **Mitigation**: This is by design. Forge invariant: "Gates wait
    indefinitely for operator input -- no auto-approve ever."

### Neutral

- This ADR does not define _how_ TRD boundaries are drawn or merged; that
  remains in TRD-7 Section 6.

## Compliance

| Mechanism          | Automation | Gate Behavior                    | Description                                                                                                    |
|--------------------|------------|----------------------------------|----------------------------------------------------------------------------------------------------------------|
| CI lint            | Automated  | Fail closed: reject PR           | PR descriptions referencing 2+ TRDs MUST include a `Precedence:` annotation with a
