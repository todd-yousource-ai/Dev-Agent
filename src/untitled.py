<!--
Security assumptions:
- This repository content is documentation-only; no executable code, secrets, or external inputs are introduced.
- Files define governance and isolation boundaries that must be interpreted fail-closed by implementers.
- No large allocations are introduced; content is static markdown only.
- Failure behavior:
  - If a downstream process cannot determine applicable precedence, it must stop work and escalate.
  - If isolation guarantees cannot be met, the system must not co-locate trust domains and must gate on operator review.
-->

# Architecture Decision Record Template

Status: Approved
ADR ID: ADR-XXX
Title: <concise decision title>
Date: YYYY-MM-DD
Deciders: <names or roles>
Consulted: <names or roles>
Informed: <names or roles>
TRD References: <TRD IDs and sections>
Supersedes: <ADR IDs or "None">
Superseded By: <ADR IDs or "None">

## Status Values

Use exactly one of:
- Proposed
- Accepted
- Approved
- Superseded
- Deprecated
- Rejected

## Context

Describe the problem, forces, constraints, and relevant background.

Authoring requirements:
- Cite the controlling TRDs and exact sections when available.
- State what trust boundary, safety property, or operability concern is affected.
- Identify any ambiguity or conflict across TRDs explicitly.
- Treat all external documents and comments as untrusted until validated by the owning process.
- If security controls are implicated, state how fail-closed behavior is preserved.

## Decision

State the decision in clear normative language.

Authoring requirements:
- Use SHALL / MUST / MUST NOT for binding requirements.
- Define scope and boundary conditions.
- If this ADR establishes precedence, specify tie-break behavior.
- If this ADR introduces a process boundary, specify authority, data flow, validation points, and denial behavior.
- Do not defer critical security behavior to “implementation detail.”

## Consequences

List outcomes, tradeoffs, follow-on work, and operational implications.

Authoring requirements:
- Include positive, negative, and neutral consequences.
- Identify migration or compatibility impact.
- State what happens when required assumptions are violated.
- Note any documents, schemas, tests, or runbooks that must be updated.

## Alternatives Considered

List meaningful alternatives and why they were not chosen.

## Compliance / Verification

Describe how compliance will be verified.

Suggested checks:
- TRD traceability review
- Security review
- Test or contract validation updates
- Operator gating implications
- Rollout or migration checks

## Notes

Optional implementation notes, references, or open questions.

---
Authoring checklist:
- Metadata header completed
- Status valid
- Controlling TRDs cited
- Security and failure behavior explicit
- Consequences include operational impact
- ADR index updated

# ADR Index

Security assumptions:
- This index is the authoritative inventory of ADR identifiers and lifecycle state.
- Consumers MUST treat unknown, duplicate, or conflicting ADR IDs as an error and stop for review.
- This index does not override the content of an ADR; it is a discoverability and status aid.
- Failure behavior: if the index and an ADR disagree on status or title, the inconsistency MUST be surfaced and resolved before relying on the ADR set.

| ID | Title | Status | Date | TRD References | Superseded By |
|---|---|---|---|---|---|
| ADR-001 | Cross-TRD Precedence Hierarchy | Approved | 2026-03-20 | TRD-7 §6, Appendix B; TRD-3 §1; TRD-4; TRD-9 §13 | None |
| ADR-002 | Two-Process Isolation Boundary | Approved | 2026-03-20 | TRD-4; TRD-9 §13; TRD-3 §1; TRD-7 §6 | None |

# ADR-001: Cross-TRD Precedence Hierarchy

Status: Approved
ADR ID: ADR-001
Title: Cross-TRD Precedence Hierarchy
Date: 2026-03-20
Deciders: Consensus Dev Agent Architecture
Consulted: Security Engineering, Runtime Engineering, Workflow Engineering
Informed: All subsystem owners
TRD References: TRD-7 §6 "Phase 3: TRD Boundary Definition"; TRD-7 Appendix B; TRD-3 §1 "Purpose and Scope"; TRD-4; TRD-9 §13
Supersedes: None
Superseded By: None

## Context

Consensus Dev Agent is specified across multiple TRDs with explicit subsystem boundaries. TRD-3 states scope boundaries for the build pipeline and explicitly excludes other domains. TRD-7 defines boundary merge and split workflows, which means document ownership can evolve over time. TRD-4 and TRD-9 introduce coordination and isolation concerns that can intersect with workflow and pipeline behavior.

Without an explicit cross-TRD precedence rule, implementers can encounter ambiguous or conflicting requirements when:
- a shared protocol spans multiple domains,
- a workflow document references behavior owned by another TRD,
- a security control constrains a domain-specific implementation choice,
- a boundary merge or split changes document ownership over time.

This ADR establishes a fail-closed hierarchy so ambiguity does not degrade into ad hoc implementation decisions.

## Decision

The project SHALL apply the following precedence hierarchy, from highest to lowest authority, when requirements from multiple TRDs or derivative artifacts intersect:

1. TRD-11 security controls.
2. The owning TRD for domain-specific requirements.
3. Shared contracts.
4. Implementation decisions.

### Tier definitions

#### 1. TRD-11 security controls

Security controls defined by TRD-11 SHALL take precedence over all other requirements when there is any conflict, ambiguity, or implementation tradeoff affecting confidentiality, integrity, authentication, authorization, isolation, validation, auditability, or fail-closed behavior.

No lower-tier document MAY weaken, bypass, or silently narrow a TRD-11 control.

#### 2. Owning TRD for domain-specific requirements

For behavior clearly within a subsystem boundary, the owning TRD SHALL be the authoritative source for requirements inside that domain.

Examples:
- Pipeline stage logic and stage contracts are owned by TRD-3.
- Multi-agent coordination protocol behavior is owned by TRD-4.
- Runner isolation behavior is owned by TRD-9 where runner security and isolation are concerned.

If TRD boundaries are merged or split under the TRD-7 workflow, the resulting ownership decision SHALL update which TRD is authoritative for future domain-specific interpretation.

#### 3. Shared contracts

Shared contracts include cross-boundary protocol and schema artifacts such as:
- XPC protocol definitions,
- API schemas,
- ledger or message contracts,
- other explicit interface agreements consumed by multiple subsystems.

Shared contracts SHALL govern interoperability semantics between domains. They MUST NOT override TRD-11 security controls or the owning TRD’s domain-specific requirements. If a shared contract conflicts with an owning TRD, the contract MUST be updated or versioned; implementers MUST NOT locally reinterpret the conflict.

#### 4. Implementation decisions

Implementation decisions include source-level choices, module boundaries, local algorithms, internal naming, and other engineering details not elevated into a TRD or shared contract.

Implementation decisions SHALL conform to all higher tiers and MUST NOT be used to resolve conflicts by convenience.

### Conflict resolution procedure

When a requirement appears to conflict across sources, the following procedure SHALL be used:

1. Determine whether TRD-11 security controls apply.
2. Determine the current owning TRD for the domain in question.
3. Determine whether a shared contract governs the cross-boundary interaction.
4. Only then select implementation details consistent with the above.

If ownership, scope, or applicability cannot be determined with high confidence, the process MUST fail closed:
- stop the affected work,
- surface the ambiguity with source citations,
- request architecture or operator review,
- do not proceed on assumption.

### Tie-break and ambiguity rules

- If two documents appear to claim the same domain, the current boundary decision recorded under the TRD development workflow SHALL control until superseded.
- If a shared contract is more restrictive than an owning TRD and does not weaken security, the stricter interpretation MAY be followed temporarily, but the inconsistency MUST be recorded for correction.
- If any lower-tier artifact appears to permit behavior prohibited by a higher-tier artifact, the prohibition controls.
- Silence in a higher-tier artifact does not grant permission to violate an explicit lower-tier contract; the lower-tier rule applies only if it does not conflict with higher tiers.

## Consequences

### Positive

- Reduces ambiguity during implementation and review.
- Provides a deterministic, fail-closed method for resolving cross-document conflicts.
- Preserves security controls as the non-negotiable top tier.
- Clarifies how ownership changes created by boundary merge/split activity affect authority.

### Negative

- Some issues will stop work and require explicit escalation instead of local interpretation.
- Shared contracts may need versioning or coordinated updates more frequently.
- Additional documentation maintenance is required when boundaries change.

### Neutral

- This ADR does not redefine subsystem boundaries; it defines how to interpret them.
- This ADR does not replace detailed TRD content or interface specifications.

### Required follow-on work

- Update future ADRs to cite controlling TRDs explicitly.
- Ensure boundary changes in the TRD workflow update ownership references.
- Add review checks that detect unresolved cross-TRD ambiguity before implementation proceeds.

### Failure behavior

If precedence cannot be established, the system MUST stop and escalate rather than continue with inferred behavior.

## Alternatives Considered

### Last-modified document wins

Rejected because document edit order is not a trustworthy indicator of architectural authority.

### Most-specific text wins without ownership analysis

Rejected because apparent specificity can still violate security controls or documented subsystem ownership.

### Shared contracts always override TRDs

Rejected because interfaces cannot safely supersede security controls or owning-domain requirements.

## Compliance / Verification

Compliance SHALL be verified by:
- ADR review for explicit TRD citations,
- architecture review of cross-boundary changes,
- security review when TRD-11 applicability is implicated,
- workflow checks ensuring unresolved ownership conflicts block implementation,
- index maintenance ensuring supersession status remains consistent.

# ADR-002: Two-Process Isolation Boundary

Status: Approved
ADR ID: ADR-002
Title: Two-Process Isolation Boundary
Date: 2026-03-20
Deciders: Consensus Dev Agent Architecture
Consulted: Security Engineering, Runtime Engineering, CI/Runner Engineering
Informed: All subsystem owners
TRD References: TRD-4 "Multi-Agent Coordination Protocol"; TRD-9 §13 "Runner Security and Isolation"; TRD-3 §1 "Purpose and Scope"; TRD-7 §6 "Phase 3: TRD Boundary Definition"
Supersedes: None
Superseded By: None

## Context

Consensus Dev Agent coordinates untrusted external inputs, model outputs, workflow state, and build/CI execution across multiple subsystems. TRD-4 governs multi-agent coordination. TRD-9 requires runner security and isolation. The platform context requires that generated code is never executed by the agent, that unknown XPC messages are discarded and logged, and that operator gates are never auto-approved.

These constraints imply a hard trust separation between:
- a control-plane process that handles orchestration, policy, identity-aware decisions, and operator gating, and
- a worker process that handles lower-trust document parsing, protocol mediation, and bounded transformation of untrusted content.

A single-process model would increase blast radius by co-locating trust-sensitive orchestration with untrusted content handling.

## Decision

The system SHALL implement a two-process isolation boundary with explicit authority separation.

### Process roles

#### 1. Control process

The control process SHALL be the higher-trust authority responsible for:
- workflow orchestration,
- policy enforcement,
- identity and authorization decisions,
- operator gating,
- final acceptance or rejection of state transitions,
- write authorization decisions,
- validation of requests that would mutate protected state.

The control process MUST fail closed on auth, crypto, identity, policy, and protocol state errors.

#### 2. Worker process

The worker process SHALL be the lower-trust execution domain responsible for:
- receiving and handling untrusted external content,
- preparing bounded, validated inputs for the control process,
- performing non-authoritative transformations,
- mediating shared contracts and schemas,
- discarding and logging unknown XPC message types rather than raising them as fatal exceptions.

The worker process MUST NOT be able to:
- self-approve gates,
- mutate protected state without control-process authorization,
- redefine policy,
- bypass validation,
- execute generated code,
- expand its authority based on model output or external document content.

### Boundary requirements

1. All cross-process communication SHALL occur through explicit versioned message contracts.
2. Every inbound message SHALL be validated for type, shape, required fields, and size bounds before use.
3. Unknown or unsupported message types received by the worker SHALL be discarded and logged.
4. Unknown or unsupported message types received by the control process SHALL be rejected as non-authoritative input and surfaced with context.
5. The control process SHALL treat all worker-originated data as untrusted until validated.
6. The worker process SHALL not receive secrets unless strictly required for a defined contract; if not required, access MUST be denied by default.
7. File writes initiated by either process SHALL occur only after path validation by the platform’s path security controls.
8. If the isolation boundary cannot be enforced, the affected operation MUST stop and require operator review.

### Data flow and authority

The permitted authority model is:
- Worker proposes.
- Control validates.
- Control decides.
- Worker applies only the actions explicitly authorized through validated contracts.

The worker MAY assemble candidate artifacts, parse repository state, or normalize document inputs, but the control process SHALL remain the sole authority for:
- merging workflow outcomes,
- recording authoritative decisions,
- approving state transitions,
- accepting or rejecting PR progression,
- granting write intent to protected locations.

### Isolation assumptions

The isolation boundary assumes:
- separate process identities,
- deny-by-default message handling,
- no ambient trust transfer from worker to control,
- no implicit elevation based on prior successful messages,
- minimal necessary data sharing.

If these assumptions are not satisfied in a deployment environment, the deployment SHALL be considered non-compliant.

### Failure behavior

The system MUST fail closed at the boundary:
- invalid messages are rejected,
- ambiguous authority is rejected,
- missing validation is rejected,
- unavailable control-process confirmation blocks the state transition,
- inability to maintain separation blocks execution.

No component MAY silently downgrade to single-process behavior for convenience or availability.

## Consequences

### Positive

- Reduces blast radius of untrusted input handling.
- Preserves a clear trust boundary for policy and approval decisions.
- Aligns orchestration authority with explicit validation points.
- Makes boundary-focused review and testing practical.

### Negative

- Introduces IPC and contract maintenance overhead.
- Requires careful versioning and compatibility handling.
- Some operations will incur extra latency due to validation and authorization hops.

### Neutral

- This ADR does not mandate a specific IPC transport.
- This ADR does not assign implementation language or framework choices.
- This ADR complements, but does not replace, runner isolation controls in TRD-9.

### Required follow-on work

- Define versioned message schemas for cross-process operations.
- Add conformance tests for invalid, oversized, and unknown messages.
- Document which state transitions require explicit control-process authorization.
- Review secret distribution to ensure the worker receives no unnecessary credentials.

### Failure behavior

If the platform cannot prove that control and worker responsibilities remain separated for a given operation, that operation MUST not proceed.

## Alternatives Considered

### Single-process architecture with in-process modules

Rejected because module boundaries are insufficient for the required trust isolation and increase the impact of parser, protocol, or validation failures.

### Multi-process architecture with shared mutable authority

Rejected because shared authority weakens accountability and makes fail-closed enforcement unreliable.

### Worker-authoritative execution with control-process auditing

Rejected because post hoc auditing does not satisfy deny-by-default or operator-gated approval requirements.

## Compliance / Verification

Compliance SHALL be verified by:
- architecture review of the authority split,
- contract tests for all cross-process message types,
- negative tests for unknown, malformed, and oversized messages,
- security review of secret and identity handling,
- operational checks that no gate can be auto-approved,
- verification that generated code is never executed by the agent,
- deployment review confirming the boundary is enforced rather than simulated.
