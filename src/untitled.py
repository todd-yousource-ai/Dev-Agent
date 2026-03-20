Title: <concise decision title>

ADR-Number: ADR-XXX
Date: YYYY-MM-DD
Status: Proposed
TRD-References:
- TRD-<n>
Reviewers:
- <name or role>
Approval-Gate: <e.g., design review, architecture board, TRD owner sign-off>
Supersedes:
- None
Superseded-by:
- None

# Status

Proposed

# Context

Describe the architectural problem, constraints, and relevant forces.
Include why the decision is needed now and what alternatives were considered.

# Decision

State the decision in concrete, testable terms.
Use normative language where appropriate:
- MUST
- MUST NOT
- SHOULD
- MAY

# Consequences

Document expected benefits, trade-offs, operational impacts, and follow-up work.
Include any migration or enforcement requirements.

# Compliance

Describe how compliance with this decision will be verified.
Include review gates, automated checks, test requirements, and audit expectations.

# Revision History

Date | Author | Change Summary
--- | --- | ---
YYYY-MM-DD | <author> | Initial draft
Number | Title | Status | Date | TRD References
--- | --- | --- | --- | ---
ADR-001 | Cross-TRD Precedence Hierarchy | Accepted | 2026-03-20 | TRD-7, TRD-11, PRD-001
ADR-002 | Two-Process Isolation Boundary | Accepted | 2026-03-20 | TRD-1, TRD-4, TRD-9, TRD-11
Title: Cross-TRD Precedence Hierarchy

ADR-Number: ADR-001
Date: 2026-03-20
Status: Accepted
TRD-References:
- TRD-7
- TRD-11
- PRD-001
Reviewers:
- Platform Architecture Lead
- Security Lead
Approval-Gate: Architecture board review
Supersedes:
- None
Superseded-by:
- None

# Status

Accepted

# Context

Consensus Dev Agent spans multiple TRDs with intentionally separated ownership boundaries. TRD-7 defines that boundaries may be split or merged over time, and PRD-001 establishes canonical contracts across subsystem seams. As boundaries evolve, requirements can conflict across documents, especially when one TRD describes local behavior and another describes shared interaction rules.

Without an explicit precedence hierarchy, implementers may resolve conflicts ad hoc, creating inconsistent behavior, security regressions, or contract drift. This is especially risky when local implementation choices appear to conflict with security controls or with shared contracts consumed by adjacent TRDs.

A stable, cross-TRD conflict resolution rule is required so that:
- security constraints are never weakened by lower-level documents or implementation convenience,
- ownership remains clear for subsystem-local behavior,
- shared contracts remain authoritative for interfaces crossing TRD boundaries, and
- implementation details do not override documented requirements.

Alternatives considered:
- Equal weight across all TRDs with case-by-case arbitration. Rejected because it is ambiguous and slows execution.
- Most recently edited document wins. Rejected because recency is not authority and can silently weaken security.
- Owning TRD always wins. Rejected because it could override platform-wide security requirements and shared contracts.

# Decision

When two or more requirements conflict across TRDs, the following four-tier precedence order MUST be applied, highest to lowest:

1. Tier 1 — Security requirements (TRD-11): Platform-wide security invariants.
2. Tier 2 — Owning TRD: The TRD designated as the owner of the subsystem or behavior in question.
3. Tier 3 — Shared contracts: Cross-boundary agreements established by PRD-001 or equivalent approved contract documents.
4. Tier 4 — Local implementation: Code comments, incidental behavior, and implementation decisions not ratified in a governing document.

Interpretation rules:

- Tier 1 overrides all lower tiers without exception unless superseded by a later accepted ADR or an explicit revision to TRD-11.
- Tier 2 governs subsystem-internal behavior when it does not violate Tier 1 and does not contradict an approved shared contract applicable to a cross-boundary interaction.
- Tier 3 governs interface shape, message semantics, lifecycle obligations, and compatibility rules at subsystem boundaries when not in conflict with Tier 1.
- Tier 4 MUST NOT be used to justify behavior that contradicts any higher tier.

For cross-boundary work:
- Engineers MUST identify the owning TRD for each changed behavior.
- Engineers MUST identify any shared contract affected by the change.
- If a conflict is detected, resolution MUST cite the highest applicable tier.
- If conflict remains ambiguous within the same tier, the change MUST stop and require a new ADR or TRD revision before implementation proceeds.

For document evolution:
- Boundary splits or merges defined by TRD-7 MUST NOT change the precedence hierarchy.
- When ownership moves because a boundary is split or merged, Tier 2 authority moves with the newly designated owning TRD, but Tier 1 and Tier 3 remain unchanged.
- Shared contracts MUST be updated explicitly; ownership transfer alone does not implicitly modify cross-boundary obligations.

# Consequences

Benefits:
- Provides a deterministic rule for resolving cross-TRD conflicts.
- Protects security requirements from accidental override.
- Preserves clear subsystem ownership while honoring shared contracts.
- Reduces review churn by giving implementers and reviewers a common decision rubric.

Trade-offs:
- Some changes will be blocked pending ADR or TRD updates instead of proceeding with local interpretation.
- Authors must spend extra effort identifying ownership and contract scope for boundary changes.

Operational impacts:
- Review templates and design discussions should reference the precedence hierarchy.
- Cross-TRD changes may require explicit citations to TRD-11, the owning TRD, and any shared contract.
- Ambiguous same-tier conflicts require governance action rather than implementation-level compromise.

Follow-up work:
- Add review checklist items that require precedence analysis for boundary-affecting changes.
- Maintain ADR references when future governance decisions refine ownership or contract authority.

# Compliance

- Design reviews MUST include an explicit precedence check for any cross-TRD change.
- PR descriptions MUST cite the controlling TRD or ADR when implementing behavior at a boundary.
- In case of unresolved ambiguity, the system MUST fail closed procedurally by blocking the change until governance is clarified.
- Periodic audits SHOULD verify that merged changes affecting multiple TRDs include a precedence citation.

# Revision History

Date | Author | Change Summary
--- | --- | ---
2026-03-20 | Architecture Board | Initial accepted version
Title: Two-Process Isolation Boundary

ADR-Number: ADR-002
Date: 2026-03-20
Status: Accepted
TRD-References:
- TRD-1
- TRD-4
- TRD-9
- TRD-11
Reviewers:
- Platform Architecture Lead
- Security Lead
Approval-Gate: Architecture board review
Supersedes:
- None
Superseded-by:
- None

# Status

Accepted

# Context

Consensus Dev Agent coordinates planning, code generation, review, CI, and operator gating across multiple internal subsystems and external integrations. The platform handles sensitive context, developer identity, repository credentials, and potentially untrusted model output. TRD-4 describes multi-agent coordination, and TRD-9 emphasizes runner security and isolation. Platform security invariants defined in TRD-11 require that generated code is never executed by the agent and that untrusted external input is validated before processing.

A single-process design would increase blast radius by combining privileged capabilities, untrusted content handling, orchestration state, and external tool interaction into one address space. This raises the risk that parser bugs, prompt injection, malformed documents, or message-handling flaws could affect credentials, durable state, or privileged operations.

Three alternatives were evaluated before selecting a two-process boundary:
- Single-process architecture with logical module separation. Rejected because module boundaries do not provide sufficient isolation against memory corruption, parser failure, or confused-deputy behavior.
- Per-task many-process architecture. Rejected for now because it adds complexity and coordination overhead beyond the current minimum secure baseline.
- In-process sandboxing only. Rejected because it is weaker than an OS-enforced process boundary and does not satisfy TRD-11 isolation requirements.

A hard process boundary is required to reduce privilege, constrain failure domains, and make trust boundaries explicit.

# Decision

Consensus Dev Agent MUST maintain a two-process isolation model as the minimum architecture baseline.

The two processes are:

1. Control Process
2. Worker Process

Control Process responsibilities:
- MUST own operator interaction, approval gates, and final decision authority.
- MUST own privileged capabilities, including credential access, identity-bearing operations, and durable policy enforcement.
- MUST validate all inbound and outbound messages crossing the process boundary.
- MUST discard and log unknown message types rather than raising them as fatal protocol exceptions.
- MUST fail closed on authentication, authorization, identity, and cryptographic validation errors.
- MUST NOT execute generated code or delegate execution of generated code through the Worker Process.

Worker Process responsibilities:
- MUST handle untrusted content processing, model-provider interaction, document transformation, and other lower-privilege computation delegated by the Control Process.
- MUST operate with the minimum privileges required for assigned work.
- MUST treat all external documents, PR comments, CI output, and model output as untrusted input.
- MUST return structured results and explicit error states to the Control Process.
- MUST NOT access secrets, long-lived credentials, or operator approval mechanisms directly unless explicitly granted by a future accepted ADR.

Boundary rules:
- Communication between the two processes MUST use an explicit versioned message contract.
- Each message MUST declare type, correlation identifier, and payload schema version.
- Unknown, malformed, or schema-invalid messages MUST be rejected by the receiver; for the Control Process this rejection MUST discard and log, and for the Worker Process it MUST return a structured error or drop the message according to protocol definition.
- The boundary MUST be deny-by-default: capabilities are unavailable unless explicitly exposed through the message contract.
- Shared mutable state across the boundary MUST be minimized; authoritative state transitions MUST occur in the Control Process.
- Security-sensitive decisions, including approvals, identity use, policy exceptions, and merge authorization, MUST remain in the Control Process.
- The Worker Process MAY be restarted independently after fault, but restart MUST NOT imply approval, state advancement, or implicit retry of privileged actions.

Execution rules:
- Generated code, generated shell commands, and generated scripts MUST NOT be executed by either process unless a future governing document explicitly authorizes a narrowly scoped mechanism with compensating controls.
- CI execution, when permitted by platform design, MUST occur only through controlled, separately governed mechanisms and MUST NOT collapse the Control/Worker boundary.

Failure behavior:
- If boundary integrity cannot be established, the system MUST stop and surface a contextual error.
- If message validation fails for a security-relevant field, the receiver MUST fail closed for that operation.
- If process role ownership is ambiguous for a capability, that capability MUST remain in the Control Process until a later accepted ADR delegates it explicitly.

Feature classification:
- New features MUST declare whether they run in the Control Process or Worker Process.
- Features that require secrets, approvals, identity, or policy decisions MUST default to the Control Process.
- Features that process untrusted content SHOULD default to the Worker Process unless doing so conflicts with Tier 1 security requirements (ADR-001) or accepted boundary contracts.

# Consequences

Benefits:
- Reduces blast radius of untrusted input handling.
- Creates a clear home for privileged capabilities and policy enforcement.
- Makes message validation and protocol governance explicit.
- Establishes a minimum secure baseline that future ADRs can refine without collapsing isolation.

Trade-offs:
- Requires explicit message contracts and additional coordination overhead.
- Some features will need boundary design work before implementation.
- Debugging can be more complex than in a single-process design.

Operational impacts:
- Teams must classify new capabilities by process role during design.
- Protocol changes require versioning and compatibility review.
- Logging and telemetry must preserve enough context to diagnose boundary failures without leaking secrets.

Follow-up work:
- Define the initial message contract and schema validation rules.
- Enumerate Control Process capabilities and Worker Process allowed operations.
- Add tests that verify unknown message discard behavior, fail-closed validation, and no-approval-on-restart semantics.

# Compliance

- Design reviews MUST verify that new features declare their process assignment (Control or Worker).
- Integration tests MUST validate that unknown messages are discarded by the Control Process and that schema-invalid messages produce structured errors from the Worker Process.
- Security reviews MUST confirm that secrets, credentials, and approval gates are not accessible from the Worker Process.
- Restart tests MUST verify that Worker Process restart does not advance state, grant approval, or retry privileged actions.
- Audits SHOULD verify that no execution of generated code occurs in either process without an explicit governing ADR.

# Revision History

Date | Author | Change Summary
--- | --- | ---
2026-03-20 | Architecture Board | Initial accepted version