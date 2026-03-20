---
id: ADR-000
title: ADR Template
status: Template
date: YYYY-MM-DD
authors:
  - name
trd_refs:
  - TRD-XX
supersedes: []
---

# Status

Proposed | Accepted | Deprecated | Superseded

# Context

Describe the problem, constraints, security assumptions, and any cross-TRD tensions this ADR resolves.

# Decision

State the decision in precise, testable terms.

# Consequences

Describe expected benefits, trade-offs, operational impacts, and follow-up work.

# References

- Related TRDs
- Related ADRs
- Supporting design notes

# Security Assumptions

Document trust boundaries, operator-gated behaviors, validation requirements, and fail-closed expectations.

# Failure Behavior

Document how ambiguous input, conflicting authority, missing dependencies, or invalid state must fail closed with surfaced context.

---
# ADR Index

This index is the authoritative registry of Architectural Decision Records for this repository.

Security assumptions:
- This file is repository-local governance metadata and must be updated atomically with any new ADR.
- ADR identifiers are unique and immutable once published.
- Status changes must preserve auditability; supersession is preferred over mutation of historical intent.

Failure behavior:
- If an ADR is proposed without an index entry, review must fail closed.
- If duplicate IDs or ambiguous supersession chains are detected, governance review must fail closed until corrected.

| ID | Title | Status | Date | Supersedes |
| --- | ----- | ------ | ---- | ---------- |
| ADR-001 | Cross-TRD Precedence Hierarchy | Accepted | 2026-03-20 | None |
| ADR-002 | Two-Process Isolation Boundary | Accepted | 2026-03-20 | None |

---
id: ADR-001
title: Cross-TRD Precedence Hierarchy
status: Accepted
date: 2026-03-20
authors:
  - Forge Engineering
trd_refs:
  - TRD-11
  - TRD-7
  - TRD-3
  - TRD-4
  - TRD-9
supersedes: []
---

# Status

Accepted

# Context

The Consensus Dev Agent is governed by multiple TRDs that define behavior across security, workflow, pipeline, coordination, and runtime isolation. Cross-TRD conflicts are expected at subsystem boundaries, especially where one TRD defines general behavior and another defines domain-specific constraints.

The repository requires a deterministic, auditable conflict-resolution rule that:
- preserves security invariants under all ambiguity,
- supports boundary ownership defined during TRD workflow,
- prevents silent precedence inversions,
- provides an escalation path when two authorities cannot be reconciled.

The repository also operates under Forge platform invariants:
- security and identity controls fail closed,
- operator approval is mandatory at gates,
- external input is untrusted,
- unknown protocol messages are discarded and logged,
- generated code is never executed by the agent.

# Decision

Cross-TRD conflicts MUST be resolved using the following four-tier precedence hierarchy, applied in order from highest to lowest authority:

1. Tier 1 — TRD-11 security controls
   - Any requirement derived from TRD-11 security controls always prevails over any conflicting requirement in any other TRD or ADR.
   - If a proposed interpretation would weaken, bypass, or ambiguously reinterpret TRD-11 controls, the interpretation is invalid.

2. Tier 2 — Owning TRD domain authority
   - For a given subsystem or boundary, the TRD that explicitly owns that domain is authoritative for domain-specific behavior.
   - Domain ownership is determined by explicit scope statements, dependency declarations, or boundary decisions established through the TRD workflow.
   - Examples:
     - TRD-3 owns pipeline logic and stage contracts.
     - TRD-4 owns multi-agent coordination protocol behavior.
     - TRD-9 owns runner security and isolation specifics for CI runner concerns.

3. Tier 3 — Shared platform conventions and approved ADRs
   - Repository-wide conventions and accepted ADRs govern cross-cutting behavior when they do not conflict with Tier 1 or Tier 2 authority.
   - ADRs may clarify interpretation, codify patterns, or define repository-wide mechanisms, but may not override TRD-11 or an owning TRD within its declared domain.

4. Tier 4 — Local implementation detail
   - File-local or module-local implementation choices may decide unspecified details only when consistent with all higher tiers.
   - Local convenience, performance, or stylistic preference never overrides higher-tier requirements.

Additional mandatory rules:

- Narrow interpretation rule:
  When two readings are possible, the reading that preserves stricter security and smaller authority scope MUST be chosen.

- No implied override rule:
  A lower-tier document does not override a higher-tier document by omission, implication, convenience, or recency alone.

- Explicit escalation rule:
  If two documents appear to claim the same domain authority or a conflict cannot be resolved deterministically, implementation MUST stop and require a new ADR or TRD amendment. Ambiguity is not resolved ad hoc in code or review comments.

- Auditability rule:
  Any non-obvious precedence decision in implementation, review, or planning MUST cite the controlling TRD or ADR explicitly.

# Consequences

Benefits:
- Cross-TRD conflicts become deterministic and reviewable.
- Security requirements retain absolute priority.
- Domain-specific ownership is preserved without allowing local drift.
- Architectural decisions become traceable through a documented hierarchy.

Trade-offs:
- Some changes will require explicit ADRs rather than quick implementation decisions.
- Boundary disputes may slow implementation until ownership is clarified.
- Review discipline must be maintained to ensure citations and escalation are applied consistently.

Operational impacts:
- Reviewers must verify claimed authority for any cross-boundary change.
- Planning artifacts should cite the controlling tier when a design spans multiple TRDs.
- Unresolved overlap between TRDs should be treated as governance debt and not patched informally.

Follow-up work:
- Future ADRs that define cross-cutting behavior must list affected TRDs.
- Boundary ownership clarified in workflow outputs should be linked from relevant ADRs where appropriate.

# References

- TRD-11 security controls
- TRD-7 development workflow and boundary definition guidance
- TRD-3 pipeline scope and exclusions
- TRD-4 multi-agent coordination protocol
- TRD-9 runner security and isolation

# Security Assumptions

- TRD-11 is the immutable top-tier authority for security interpretation unless and until superseded by an equally authoritative security governance mechanism.
- Ambiguity is treated as a security risk because it can enable accidental policy bypass.
- External commentary, PR descriptions, and review discussion are not authoritative unless ratified into a TRD or accepted ADR.

# Failure Behavior

- If a conflict involves security interpretation and no clear TRD-11-compatible path exists, work must fail closed and escalate.
- If domain ownership is ambiguous, implementation and approval must stop pending explicit governance clarification.
- If an ADR conflicts with an owning TRD or TRD-11, the ADR is invalid to the extent of the conflict and must be corrected or superseded.

---
id: ADR-002
title: Two-Process Isolation Boundary
status: Accepted
date: 2026-03-20
authors:
  - Forge Engineering
trd_refs:
  - TRD-1
  - TRD-4
  - TRD-9
  - TRD-11
supersedes: []
---

# Status

Accepted

# Context

Consensus Dev Agent performs planning, code generation orchestration, review, CI interaction, and operator-gated merge flow. The platform serves sensitive enterprise environments and must minimize blast radius when handling untrusted model output, external documents, CI results, and network-facing operations.

A single-process architecture would unnecessarily co-locate high-trust capabilities with untrusted content handling. The repository therefore requires a clear architectural boundary that separates privileged authority from untrusted execution-adjacent orchestration.

This ADR establishes a minimum two-process isolation model suitable for future implementation and review.

# Decision

The system MUST maintain a two-process isolation boundary with distinct trust levels:

1. Control Process
   - High-trust process responsible for:
     - engineer identity and auth state,
     - keychain and secret access,
     - policy enforcement,
     - operator gating,
     - path validation and protected file-write authorization,
     - final decision authority for privileged actions.
   - The Control Process MUST be deny-by-default and MUST fail closed on auth, crypto, identity, and policy errors.
   - The Control Process MUST NOT execute generated code, MUST NOT trust model output as instructions, and MUST treat all inbound messages as untrusted input.

2. Worker Process
   - Lower-trust process responsible for:
     - model-provider interaction,
     - draft planning artifacts,
     - code generation outputs,
     - non-privileged transformation of repository content,
     - parsing and summarizing untrusted external inputs.
   - The Worker Process MUST have no direct access to secrets, identity material, protected credentials, or unrestricted file-write capability.
   - The Worker Process MUST not independently approve merges, policy exceptions, or privileged network actions.

Inter-process boundary requirements:

- All messages crossing the boundary MUST use explicit typed schemas.
- Unknown, malformed, oversized, or out-of-state messages MUST be discarded and logged with context; they MUST NOT be treated as recoverable commands.
- The Control Process is the sole authority for:
  - releasing secrets,
  - approving writes to protected paths,
  - approving operator-gated transitions,
  - invoking privileged actions on behalf of the user identity.

Capability constraints:

- Secrets and tokens remain resident only in the Control Process or platform-managed secure storage.
- The Worker Process receives only the minimum scoped data required for the current task.
- Generated code, model-suggested shell fragments, and external document content are data only; they are never executable authority.

Review and audit requirements:

- Any feature that crosses the process boundary MUST document:
  - initiating side,
  - message schema,
  - validation rules,
  - authorization decision point,
  - failure mode.
- Any attempt to collapse the boundary, share mutable privileged state, or permit direct secret access from the Worker Process requires a superseding ADR and explicit security review.

# Consequences

Benefits:
- Reduced blast radius for prompt injection, malformed outputs, and worker compromise.
- Clear authority separation between untrusted content handling and privileged action.
- Easier review of auth, secret, and file-write paths.
- Better alignment with deny-by-default and fail-closed platform requirements.

Trade-offs:
- Additional implementation complexity in message design and state synchronization.
- Some workflows require explicit serialization across the process boundary.
- Latency may increase for authorization-heavy operations.

Operational impacts:
- New commands and features must specify which process owns them.
- Message schema evolution must be versioned and reviewed carefully.
- Debugging requires correlation across process-local logs without exposing secrets.

Follow-up work:
- Define the concrete IPC schema and validation strategy.
- Define per-message authorization mapping.
- Define structured logging and correlation identifiers appropriate for both processes.

# References

- TRD-1 app shell, XPC, keychain, and engineer identity
- TRD-4 multi-agent coordination protocol
- TRD-9 runner security and isolation
- TRD-11 security controls
- ADR-001 cross-TRD precedence hierarchy

# Security Assumptions

- The Worker Process may handle adversarial content and is therefore not trusted with privileged authority.
- The Control Process is the enforcement boundary for identity, secrets, and policy.
- Process separation is a minimum isolation requirement, not a substitute for validation, authorization, or least privilege.

# Failure Behavior

- If message validation fails at the boundary, the receiving process must reject the message and surface contextual error information without executing requested effects.
- If authorization cannot be determined, the Control Process must deny the action.
- If process role ownership is unclear for a new capability, implementation must stop until ownership is documented and reviewed.