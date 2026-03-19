# DECISIONS.md

## ConsensusDevAgent repository and source-of-truth boundaries
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with strict separation between specifications, standards, implementation, UI shell, tests, and CI assets. The TRDs and README establish that all TRDs and PRDs live under `forge-docs/`, standards live under `forge-standards/`, Python backend code lives under `src/`, the macOS shell lives under `ForgeAgent/`, and tests/CI assets have fixed locations. ConsensusDevAgent must not blur these boundaries because planning, generation, review, and audit depend on deterministic file placement.  
**Decision:** Treat repository layout as a hard contract. Read specifications from `forge-docs/`, place design constraints in `forge-standards/`, implement ConsensusDevAgent backend code under `src/`, place Python tests under `tests/`, and never treat generated code or transient artifacts as substitutes for source-of-truth documents.  
**Consequences:** Implementation must resolve paths relative to these fixed roots and must not invent alternate storage conventions. Document readers and planners must consume TRDs/PRDs from `forge-docs/` only. Any subsystem code that persists standards or decision records must write to `forge-standards/`. This constrains path handling, configuration defaults, test fixtures, and integration behavior.  
**Rejected alternatives:**  
- Storing subsystem-specific specs alongside implementation in `src/`: rejected because it breaks the declared repository contract and weakens documentation governance.  
- Allowing multiple document roots via ad hoc configuration: rejected because it complicates auditability and creates ambiguity over which spec version governs behavior.  
- Treating generated plans or prompts as de facto source of truth: rejected because TRDs/PRDs are explicitly the authoritative inputs.

## ConsensusDevAgent shall enforce irreversible gate decisions
**Status:** Accepted  
**Context:** The TRDs and pipeline notes explicitly require “No undo on gate decisions.” ConsensusDevAgent participates in generation, arbitration, and review where failures may trigger operator gates. If a gate could be reversed automatically or silently retried past, the audit trail and security posture would be invalidated.  
**Decision:** Implement gate decisions as irreversible events. Once ConsensusDevAgent records a gate outcome that stops, refuses, or escalates work, the subsystem shall not auto-clear, auto-bypass, or “undo” that gate. Any continuation must occur as a new explicit operator-driven action with a new audit event, not a reversal of the original decision.  
**Consequences:** State machines must model terminal or operator-blocked states explicitly. APIs and UI flows must avoid “undo gate” semantics. Retry logic must create new attempts rather than mutate prior gate history. Audit records must preserve the original gate and any subsequent operator action as separate facts.  
**Rejected alternatives:**  
- Providing an undo action for operator convenience: rejected because it violates the explicit TRD constraint.  
- Silently reopening gated work after model regeneration succeeds: rejected because it would erase the meaning of the original stop decision.  
- Mutating prior gate state from blocked to passed: rejected because it destroys audit integrity.

## ConsensusDevAgent shall operate within the staged build pipeline
**Status:** Accepted  
**Context:** The repository defines a fixed build pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent stages. ConsensusDevAgent is part of this larger orchestration and must interoperate with ordered stage contracts, escalation points, and audit schema from TRD-3.  
**Decision:** Implement ConsensusDevAgent as a stage-aware subsystem that honors the canonical pipeline order and stage boundaries. The subsystem shall not skip required earlier stages, collapse distinct stages into one opaque action, or emit outputs that pretend a later stage has completed without its contract being satisfied.  
**Consequences:** Interfaces must carry stage context. Consensus generation and arbitration outputs must be attributable to the current stage. Review and gating logic must align with stage-specific acceptance criteria. This constrains orchestration, resumability, audit metadata, and error propagation.  
**Rejected alternatives:**  
- A free-form agent loop that decides its own stage order dynamically: rejected because it conflicts with the defined pipeline and weakens operational predictability.  
- Combining planning and code generation into one generic “agent run”: rejected because it obscures review boundaries and audit semantics.  
- Allowing later stages to backfill missing earlier artifacts: rejected because it breaks traceability from intent to implementation.

## ConsensusDevAgent shall preserve explicit auditability for consensus and gating outcomes
**Status:** Accepted  
**Context:** The pipeline references audit trail schema and escalation behavior. ConsensusDevAgent makes consequential decisions: selecting outputs, escalating disagreements, and stopping on security or quality gates. These decisions must be inspectable after the fact.  
**Decision:** Record consensus inputs, arbitration outcomes, gate triggers, and operator escalations as explicit audit events rather than implicit logs or overwritten state. The subsystem shall preserve enough metadata to explain why a result was accepted, rejected, or escalated.  
**Consequences:** Data models must include decision provenance and timestamps. Logging alone is insufficient where structured audit events are required. Implementations must avoid destructive updates that lose prior reasoning context. This increases storage and schema requirements but is necessary for post hoc review and compliance.  
**Rejected alternatives:**  
- Relying only on unstructured application logs: rejected because logs are insufficiently deterministic for audit reconstruction.  
- Persisting only the final accepted artifact: rejected because it hides arbitration and gate reasoning.  
- Overwriting previous consensus state on each retry: rejected because it erases decision history.

## ConsensusDevAgent shall stop and gate on SECURITY_REFUSAL outputs
**Status:** Accepted  
**Context:** Security controls are mandatory. The TRD excerpts explicitly require SECURITY_REFUSAL rules in generation prompts and specify that when SECURITY_REFUSAL appears in output, the system must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent, which aggregates and arbitrates model outputs, is a critical enforcement point.  
**Decision:** Detect SECURITY_REFUSAL as a first-class terminal security signal. When any relevant model output for ConsensusDevAgent work contains SECURITY_REFUSAL, the subsystem shall stop the affected work item, create a gate for operator review, log the event, and prohibit automatic continuation or bypass.  
**Consequences:** Parsers and arbitration logic must inspect outputs for refusal markers before treating them as valid candidates. Consensus must not “vote away” a security refusal. Recovery paths must require explicit operator action in a new decision record. This constrains prompt handling, result validation, and workflow control.  
**Rejected alternatives:**  
- Ignoring SECURITY_REFUSAL if another model produced usable output: rejected because the requirement is to stop and gate, not average across outputs.  
- Automatically retrying with a softened prompt: rejected because mandatory controls forbid auto-bypass.  
- Treating SECURITY_REFUSAL as an ordinary generation failure: rejected because it is a security event, not just a quality issue.

## ConsensusDevAgent shall not auto-bypass mandatory security review controls
**Status:** Accepted  
**Context:** Security controls require generated code to pass the security review pass, use path validation on every write, and escalate flagged content to an operator gate. ConsensusDevAgent may be involved in choosing between generated candidates or coordinating progression to later stages; therefore it must not normalize or weaken mandatory controls.  
**Decision:** Enforce security controls as non-optional prerequisites. ConsensusDevAgent shall not mark work complete, accepted, or ready for merge when required security checks, path validation requirements, or operator gates remain unresolved.  
**Consequences:** The subsystem must consume security-review status as a blocking dependency. Arbitration logic cannot prefer “faster” outputs that skipped mandatory security constraints. File-writing integrations must assume path validation is required on every write path.  
**Rejected alternatives:**  
- Allowing security review to run asynchronously after acceptance: rejected because mandatory review is part of the gate to proceed.  
- Trusting model self-attestation that security requirements were followed: rejected because controls require actual enforcement, not claims.  
- Letting operator convenience settings suppress mandatory gates by default: rejected because the controls are specified as mandatory.

## ConsensusDevAgent shall treat untrusted review content as untrusted input
**Status:** Accepted  
**Context:** The security controls specify that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent may consume review comments during arbitration or refinement. Without explicit treatment as untrusted input, review text could influence generation in unsafe or non-transparent ways.  
**Decision:** Mark and propagate external review comments and similar non-authoritative text as untrusted input in all ConsensusDevAgent prompt construction and decision flows. The subsystem shall not merge such content into trusted instructions or specifications.  
**Consequences:** Prompt builders and data models must preserve trust boundaries. Consensus logic must distinguish between authoritative specs and reviewer suggestions. This constrains how context windows are assembled and how agent instructions are serialized.  
**Rejected alternatives:**  
- Flattening all context into a single prompt without trust labels: rejected because it obscures provenance and increases prompt-injection risk.  
- Treating reviewer comments as equivalent to TRD/PRD requirements: rejected because only source-of-truth documents are authoritative.  
- Dropping reviewer comments entirely: rejected because comments can be useful, but only when clearly marked untrusted.

## ConsensusDevAgent shall require validated file paths for any write operation it initiates
**Status:** Accepted  
**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may write plans, generated artifacts, decision records, or intermediate outputs. Because the subsystem can influence filesystem writes, it must comply universally rather than opportunistically.  
**Decision:** Validate every filesystem write path through the required path-security mechanism before any write, rename, move, or overwrite initiated by ConsensusDevAgent. No internal trust shortcut, repository-relative assumption, or caller attestation may replace this check.  
**Consequences:** File IO abstractions must route through a validated write API. Tests must verify failed validation blocks writes. Temporary-file and atomic-write implementations must validate both temporary and final destinations as applicable.  
**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated/internal paths can also be unsafe.  
- Validating only final output paths, not temp paths: rejected because temp paths are also writes.  
- Assuming repository-root normalization is sufficient: rejected because the mandated control is explicit path validation, not convention-based safety.

## ConsensusDevAgent shall honor document-first development workflow
**Status:** Accepted  
**Context:** The repository and pipeline establish a document-driven process: intent becomes PRDs, PRDs become PR plans, then implementation follows. ConsensusDevAgent must fit this workflow rather than shortcutting from vague intent directly to code or decisions detached from documents.  
**Decision:** Require upstream document artifacts appropriate to the current stage before producing downstream implementation decisions. ConsensusDevAgent shall use TRDs/PRDs as governing inputs and shall not treat ad hoc prompts alone as sufficient authority for implementation-changing actions.  
**Consequences:** The subsystem must validate document availability and stage prerequisites. It must reject or gate requests that attempt to bypass missing PRD/plan artifacts. This constrains operator UX, API contracts, and resumability semantics.  
**Rejected alternatives:**  
- Direct code generation from an initial intent: rejected because it bypasses the specified PRD-driven process.  
- Allowing undocumented implementation changes if consensus between models is high: rejected because consensus does not replace design authority.  
- Inferring missing specs from repository context: rejected because it introduces ambiguity and weakens traceability.