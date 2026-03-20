# DECISIONS.md

## [ConsensusDevAgent repository boundaries and source-of-truth]
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with explicit documentation, standards, backend, app shell, and test boundaries. TRDs and PRDs are authoritative inputs and must be consulted before implementation. Without a hard repository contract, the agent could read from or write to the wrong locations, drift from approved specifications, or couple itself to non-source-of-truth documents.  
**Decision:** Treat `forge-docs/` as the sole source of truth for TRDs and PRDs, and constrain implementation to the repository layout defined in the project documentation. Read design inputs from `forge-docs/`, place subsystem implementation in `src/`, place Python tests in `tests/`, and treat `forge-standards/DECISIONS.md` as a binding implementation constraint. Do not infer requirements from ad hoc files when a TRD or PRD exists.  
**Consequences:** Implementation must resolve requirements from `forge-docs/` before coding. The subsystem may not invent alternate document locations, parallel standards folders, or hidden metadata stores for requirements. Tests, code, and automation must preserve the documented repository layout. This reduces ambiguity and supports auditable development.  
**Rejected alternatives:**  
- Allowing requirements to be sourced from README files first: rejected because README content is summary-level and not the authoritative specification when TRDs/PRDs exist.  
- Storing subsystem-specific design decisions next to code in `src/`: rejected because standards must remain centralized and discoverable in `forge-standards/`.  
- Permitting flexible file placement by convention instead of explicit paths: rejected because it weakens enforcement and auditability.

## [No undo on gate decisions]
**Status:** Accepted  
**Context:** The build pipeline and security controls define gate behavior as irreversible once a gating condition is reached. This is explicitly called out in the requirements and must be documented as a subsystem constraint. Without this rule, an implementation could silently resume, auto-clear, or retroactively bypass a gate, undermining operator control and audit integrity.  
**Decision:** Implement gate decisions as irreversible within the ConsensusDevAgent subsystem. Once a stage, review pass, or security condition results in a gate, do not auto-undo, auto-resume, or auto-bypass that gate in code. Require explicit external operator action through the documented workflow to proceed, and record the gate in the audit trail.  
**Consequences:** The subsystem must model gates as terminal blocking states until operator intervention occurs through the approved process. Retry logic, recovery logic, and orchestration code must not clear a gate by themselves. UI, logs, and audit records must reflect that gate decisions are final for the active execution path.  
**Rejected alternatives:**  
- Automatic gate clearing after a successful retry: rejected because it violates the explicit “No undo on gate decisions” requirement.  
- Time-based expiration of gates: rejected because silent reopening would weaken safety and operator awareness.  
- Allowing downstream stages to continue with warnings after a gate: rejected because a gate is a hard stop, not advisory metadata.

## [Pipeline adherence for ConsensusDevAgent execution]
**Status:** Accepted  
**Context:** The subsystem participates in a defined multi-stage build pipeline beginning with `/prd start <intent>` and proceeding through scope confirmation, planning, generation, review, and merge. The pipeline order and stage semantics are part of the contract. Deviating from stage order would make outputs unauditable and break assumptions in downstream review and merge logic.  
**Decision:** Execute work only through the documented build pipeline stages and preserve stage ordering: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and merge-related follow-through as defined by the project pipeline contracts. Do not skip required stages, collapse distinct stages into one opaque operation, or reorder stages.  
**Consequences:** ConsensusDevAgent orchestration must expose stage transitions explicitly and maintain records for each stage outcome. The subsystem cannot directly jump from user intent to code generation without planning artifacts and review passes. Operational metrics and logs should align to stage boundaries.  
**Rejected alternatives:**  
- A simplified “plan-and-code” two-step pipeline: rejected because it omits required PRD and PR planning structure and weakens auditability.  
- Dynamic stage reordering based on heuristic confidence: rejected because stage contracts are fixed and must remain predictable.  
- Skipping review stages for low-risk changes: rejected because the pipeline defines mandatory review behavior, including security review.

## [Security refusal is a hard-stop output condition]
**Status:** Accepted  
**Context:** The security controls require `SECURITY_REFUSAL` rules in generation prompts and define `SECURITY_REFUSAL` in output as a stop condition that gates the PR, logs the event, and must never be auto-bypassed. This behavior must be enforced uniformly by the subsystem handling model outputs.  
**Decision:** Treat any LLM output containing or signaling `SECURITY_REFUSAL` as an immediate hard stop. Stop the current PR flow, create a gate, log the event in the audit trail, and do not auto-bypass or transform the refusal into a warning.  
**Consequences:** Output parsers, arbitration logic, and workflow engines must inspect generation results for `SECURITY_REFUSAL` before any downstream processing. The subsystem must not continue to code application, review, commit preparation, or merge preparation after such an output. This increases safety but may require operator intervention more frequently.  
**Rejected alternatives:**  
- Converting `SECURITY_REFUSAL` into a soft warning for later review: rejected because the requirements define it as a stop condition.  
- Retrying automatically with a different model until no refusal appears: rejected because that would function as an auto-bypass.  
- Stripping refusal markers and continuing with partial output: rejected because it hides a security event and breaks auditability.

## [Mandatory security review in three-pass review sequence]
**Status:** Accepted  
**Context:** Generated code must pass the defined review pipeline, including a security-focused pass and bandit checks. Security review is not optional and must remain distinct even if earlier passes succeed. ConsensusDevAgent must therefore preserve and enforce this mandatory review contract.  
**Decision:** Require every generated code change to complete the full three-pass review sequence—correctness, performance, and security—with the security pass mandatory in all cases. Enforce relevant security tooling, including bandit, as part of the security pass.  
**Consequences:** The subsystem must not mark generated code as complete or merge-ready after only correctness or performance review. Review orchestration must preserve pass identity and outcomes separately. Failures in the security pass must gate progress.  
**Rejected alternatives:**  
- Running only correctness and performance reviews by default: rejected because mandatory security review is explicitly required.  
- Folding security checks into a generic final review: rejected because the requirements call for a distinct security pass with specific tooling.  
- Allowing trusted files or directories to bypass bandit: rejected because the requirement applies to all generated code.

## [Path validation on every write]
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and modifies files, so write-path enforcement is a direct implementation constraint. Without universal path validation, the subsystem could enable traversal, repository escape, or writes into protected areas.  
**Decision:** Invoke `path_security.validate_write_path()` on every file path before any write, overwrite, creation, patch application, or generated artifact emission performed by the subsystem. Do not allow a write code path that bypasses validation.  
**Consequences:** All file-writing abstractions must centralize path validation or prove equivalent enforcement for every call site. Convenience utilities, patch appliers, and bulk writers must validate each target path. This may add implementation friction but is required for repository safety.  
**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated and computed paths can also be unsafe.  
- Validating only at high-level entry points: rejected because lower-level utilities could still bypass checks.  
- Relying solely on repository-relative path normalization: rejected because normalization alone is weaker than the mandated validator.

## [Untrusted review content must remain explicitly labeled]
**Status:** Accepted  
**Context:** Security controls state that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. Review content can contain prompt injection or malicious instructions, and the subsystem must preserve provenance so models and operators can treat it appropriately.  
**Decision:** Label all incorporated PR review comments and equivalent external review text as `[UNTRUSTED REVIEWER COMMENT]` whenever included in prompts, deliberation inputs, or consensus material. Do not present reviewer text as trusted system or developer instruction.  
**Consequences:** Prompt construction and context assembly must preserve trust boundaries. Reviewer comments cannot silently influence model behavior as first-class instructions. This reduces prompt injection risk and keeps external commentary distinguishable in logs and audits.  
**Rejected alternatives:**  
- Merging reviewer comments into the main task description without labels: rejected because it erases trust boundaries.  
- Treating comments from known collaborators as trusted: rejected because the requirement is about input origin class, not user reputation.  
- Excluding all reviewer comments from prompts: rejected because comments can still be useful if clearly marked untrusted.

## [Flagged chunks require operator gate before use]
**Status:** Accepted  
**Context:** Security controls specify that when a flagged chunk is used in generation, the system must create a gate card to the operator before proceeding. ConsensusDevAgent may aggregate or reuse content during generation, so flagged-content handling must be explicit and blocking.  
**Decision:** If generation would use a flagged chunk, stop and present a gate to the operator before proceeding. Do not continue automatically, even if the rest of the input appears safe or confidence is high.  
**Consequences:** Content selection, retrieval, and prompt-building components must propagate flag metadata to the orchestration layer. The subsystem must support blocking operator review before resumed generation. This may slow throughput but preserves human control over risky inputs.  
**Rejected alternatives:**  
- Using flagged chunks automatically with warning logs only: rejected because the requirement demands gating before proceeding.  
- Silently dropping flagged chunks and continuing: rejected because it changes generation inputs without operator awareness and may invalidate task fidelity.  
- Deferring flagged-chunk review until after generation: rejected because the control must occur before use.

## [Claude-selected PRD generation outcome in dual-model stage]
**Status:** Accepted  
**Context:** The build pipeline defines PRD generation as using both models, with Claude winning for the PRD Gen stage. ConsensusDevAgent must respect that contract when producing or selecting PRD outputs, rather than arbitrating freely at this stage.  
**Decision:** In the PRD generation stage, generate using both configured models but select the Claude output as the authoritative PRD result when the documented pipeline contract applies. Do not substitute a different winner-selection policy for this stage.  
**Consequences:** PRD stage orchestration must preserve dual-model execution while hard-coding the stage-specific selection rule. Arbitration logic must be stage-aware rather than globally uniform. This constrains flexibility but aligns behavior with the documented pipeline.  
**Rejected alternatives:**  
- Generic score-based arbitration across both models for PRD generation: rejected because the stage contract explicitly states Claude wins.  
- Single-model PRD generation to save time: rejected because the pipeline requires both models.  
- Selecting the non-Claude output when it appears more complete: rejected because it violates the declared stage contract.

## [Auditability over opaque autonomous progression]
**Status:** Accepted  
**Context:** Multiple requirements reference gates, stage contracts, and audit trail behavior. ConsensusDevAgent therefore must favor explicit, inspectable transitions and logged decisions over hidden autonomous progression. This is especially important where security events, stage failures, or operator confirmations occur.  
**Decision:** Record stage transitions, gate events, security-stop events, and operator-required pauses as explicit audit events, and design the subsystem so these transitions are externally inspectable. Do not implement hidden state changes that materially alter execution without corresponding audit records.  
**Consequences:** Internal state machines must surface meaningful lifecycle events. Debugging, compliance review, and incident response become easier, but implementation must carry more structured metadata and event logging.  
**Rejected alternatives:**  
- Minimal logging with only final outcomes: rejected because it is insufficient for gate and security event traceability.  
- Best-effort debug logs without structured audit events: rejected because they are harder to validate and consume programmatically.  
- Fully autonomous state repair without operator-visible records: rejected because it conflicts with gate and security-control requirements.