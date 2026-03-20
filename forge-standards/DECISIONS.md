# DECISIONS.md

## [Repository structure is fixed and document-first]
**Status:** Accepted  
**Context:** The ConsensusDevAgent subsystem operates within a repository whose layout is already defined by the TRDs and README. The system must treat design documents as the source of truth and implement within the prescribed code and standards locations. Unstructured placement would break discoverability, reviewability, and pipeline automation.  
**Decision:** Place all implementation for ConsensusDevAgent within the established repository structure and treat `forge-docs/` as authoritative input before building. Do not invent alternate top-level locations for specifications, standards, source, tests, or CI assets. Use:
- `forge-docs/` for all TRDs and PRDs
- `forge-standards/` for `ARCHITECTURE.md`, `INTERFACES.md`, `DECISIONS.md`, and `CONVENTIONS.md`
- `src/` for Python backend implementation
- `tests/` for Python tests
- existing app, test, and workflow directories as defined by repository layout

**Consequences:** Implementation must read and align with TRDs before code generation or modification. ConsensusDevAgent code, tests, interfaces, and design decisions must be stored only in their designated locations. Tooling and automation may assume this layout and need not support arbitrary alternatives.  
**Rejected alternatives:**  
- **Feature-specific top-level directories:** Rejected because they fragment standards and break the documented repository contract.  
- **Storing implementation-specific design docs alongside code:** Rejected because `forge-standards/` is the designated durable location for architectural constraints.  
- **Treating code as primary and docs as advisory:** Rejected because the repository is explicitly document-first, with TRDs/PRDs as source of truth.

## [ConsensusDevAgent must honor the staged build pipeline]
**Status:** Accepted  
**Context:** The subsystem participates in a larger build pipeline with named stages and explicit contracts. The pipeline is the governing execution model for converting operator intent into scoped plans, PRDs, PRs, code generation, and review. Ad hoc execution would undermine auditability and gate semantics.  
**Decision:** Implement ConsensusDevAgent behavior to conform to the defined build pipeline stages and their boundaries. Do not skip, merge, or silently reorder stages defined by the platform. Respect stage contracts from scope confirmation through review and escalation.  
**Consequences:** ConsensusDevAgent must expose behavior that is stage-aware, auditable, and compatible with orchestration across scope, planning, generation, and review. Internal logic may optimize within a stage but must not bypass required gates or fabricate stage completion.  
**Rejected alternatives:**  
- **Single-pass implementation from intent directly to code:** Rejected because it bypasses required planning, review, and audit steps.  
- **Dynamic stage ordering based on local heuristics:** Rejected because it conflicts with the prescribed pipeline contract.  
- **Collapsing review into generation:** Rejected because review is a separate governed stage with distinct checks and escalation rules.

## [Gate decisions are immutable and have no undo]
**Status:** Accepted  
**Context:** The TRDs and build pipeline explicitly state that there is no undo on gate decisions. Security and operational safety depend on irreversible gate outcomes once recorded, preventing silent reversal or automated bypass after refusal, escalation, or operator gating.  
**Decision:** Treat all gate decisions in ConsensusDevAgent as immutable. Do not implement undo, rollback, auto-reopen, or silent reversal for any gate outcome once committed. Any subsequent progress must occur through a new forward action or a new explicit decision event, never by erasing the prior gate decision.  
**Consequences:** State models, audit logs, APIs, and UI interactions must represent gate outcomes as append-only facts. Recovery flows must create new events rather than modify prior decisions. Operators and downstream systems must not expect reversal semantics.  
**Rejected alternatives:**  
- **Allowing operator undo of a gate decision:** Rejected because the requirements explicitly forbid undo and because reversibility weakens audit integrity.  
- **Soft-delete or hidden reversal of gate state:** Rejected because it creates ambiguity and undermines forensic traceability.  
- **Automatic retry that clears a prior gate:** Rejected because retries must be new attempts with preserved historical outcomes, not mutation of existing decisions.

## [SECURITY_REFUSAL is a hard stop, not a warning]
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in generation prompts and mandate that SECURITY_REFUSAL in output stops the PR, gates progress, and is never auto-bypassed. ConsensusDevAgent must therefore treat such output as a first-class terminal condition for the current flow.  
**Decision:** When ConsensusDevAgent detects `SECURITY_REFUSAL` in LLM output or security-review output, immediately stop the active PR/code-generation flow, create a gate for operator handling, and log the event in the audit trail. Never auto-bypass, downgrade, or continue past a SECURITY_REFUSAL.  
**Consequences:** The subsystem must include explicit detection, propagation, and logging for SECURITY_REFUSAL outcomes. Downstream stages must not receive outputs from a refused generation as if they were valid artifacts. Operators may inspect and initiate a new action, but the refused action remains blocked.  
**Rejected alternatives:**  
- **Treating SECURITY_REFUSAL as advisory text:** Rejected because requirements define it as a stop condition.  
- **Automatically retrying with a weaker prompt or bypass flag:** Rejected because auto-bypass is explicitly forbidden.  
- **Continuing to review or merge partial output after refusal:** Rejected because the refusal invalidates the generation flow and requires a gate.

## [Untrusted external content must remain explicitly labeled]
**Status:** Accepted  
**Context:** Security controls specify that PR review comments from untrusted sources must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks used in generation require gating before proceeding. ConsensusDevAgent must preserve trust boundaries when incorporating external text into model context.  
**Decision:** Treat review comments, flagged chunks, and other untrusted external content as tainted input. Preserve required labeling in prompts, never normalize away trust markers, and require operator gating before generation proceeds when flagged chunks are used.  
**Consequences:** Prompt assembly, context formatting, and review ingestion logic must carry trust metadata end-to-end. ConsensusDevAgent cannot silently blend trusted and untrusted content into a single undifferentiated prompt context. Audit trails must reflect when tainted content influenced generation.  
**Rejected alternatives:**  
- **Inlining review comments without trust labels:** Rejected because it hides provenance from the model and violates mandatory controls.  
- **Auto-approving flagged chunks for use in generation:** Rejected because operator gating is required.  
- **Discarding trust metadata after ingestion:** Rejected because downstream generation and auditability depend on provenance.

## [All generated file writes must pass path validation]
**Status:** Accepted  
**Context:** Security controls mandate `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and modifies repository files and therefore must enforce path validation uniformly to prevent path traversal, out-of-scope writes, and repository corruption.  
**Decision:** Validate every destination path with `path_security.validate_write_path()` before any create, overwrite, append, rename, or patch application performed by ConsensusDevAgent. Refuse the operation and gate/log on validation failure.  
**Consequences:** File I/O abstractions for the subsystem must centralize write-path validation and make bypass impossible in normal operation. Tests must cover invalid path attempts and ensure failures are enforced before any filesystem mutation occurs.  
**Rejected alternatives:**  
- **Validating only user-supplied paths:** Rejected because generated or transformed paths are equally risky.  
- **Best-effort logging without blocking writes:** Rejected because the control is mandatory and preventive, not observational.  
- **Per-call optional validation:** Rejected because optional enforcement leads to inconsistent security coverage.

## [Security review is mandatory for generated code]
**Status:** Accepted  
**Context:** Mandatory controls require all generated code to pass Pass 3 security review, including bandit. ConsensusDevAgent must not consider code generation complete merely because code compiles or passes functional checks.  
**Decision:** Require every generated code artifact from ConsensusDevAgent to pass the defined security review stage before it can advance. Do not mark implementation complete, ready, or mergeable prior to successful security review, including required automated checks such as bandit where applicable.  
**Consequences:** The subsystem must integrate with the 3-pass review model and represent security review as a blocking prerequisite, not an optional enhancement. Failure in security review must halt progression and trigger the appropriate gate/escalation path.  
**Rejected alternatives:**  
- **Running only correctness and performance review for trusted changes:** Rejected because all generated code must undergo security review.  
- **Deferring security review until after merge:** Rejected because the requirement is pre-advancement, not post hoc.  
- **Treating static analysis as sufficient replacement for Pass 3:** Rejected because the decision requires the full security review stage, with bandit included rather than substituted.

## [Audit trail must record gate and security events as append-only facts]
**Status:** Accepted  
**Context:** The build pipeline references audit trail schema and escalation behavior, and the no-undo rule requires durable historical recording. ConsensusDevAgent decisions around gating, refusals, and review outcomes must therefore be traceable and non-destructive.  
**Decision:** Record gate decisions, SECURITY_REFUSAL events, escalation events, and stage transitions as append-only audit entries. Never overwrite prior audit facts to reflect a later state change.  
**Consequences:** Data models and persistence must support chronological event history instead of mutable status-only storage. Reporting may derive current status from events, but the underlying record must preserve prior decisions intact. This also constrains repair and retry flows to add events rather than rewrite history.  
**Rejected alternatives:**  
- **Mutable current-state-only records:** Rejected because they lose evidence of prior gate and refusal decisions.  
- **Rewriting audit entries during retries:** Rejected because it violates append-only traceability and conflicts with no-undo semantics.  
- **Logging only failures, not successful transitions:** Rejected because a complete stage and gate history is required for reliable auditing.