# DECISIONS.md

## ConsensusDevAgent repository placement and boundaries
**Status:** Accepted  
**Context:** The repository structure is fixed across the system. Source-of-truth documents live in `forge-docs/`, implementation lives under `src/`, and shared standards live under `forge-standards/`. The ConsensusDevAgent subsystem must fit this layout and remain consistent with the documented build pipeline and multi-agent coordination model.  
**Decision:** Implement the ConsensusDevAgent subsystem under `src/` as backend runtime code, and document its contracts and constraints in `forge-standards/`. Treat `forge-docs/` as read-first, source-of-truth input only; do not embed mutable design authority for the subsystem anywhere else.  
**Consequences:** Implementation must not create a parallel docs authority outside `forge-docs/` and `forge-standards/`. Runtime code, orchestration logic, arbitration logic, and gate handling for ConsensusDevAgent belong in Python backend code under `src/`. Any design changes must be reflected through the standards/docs workflow rather than ad hoc code comments or informal files.  
**Rejected alternatives:** Storing subsystem logic in the macOS shell was rejected because ConsensusDevAgent is a backend coordination concern, not a UI-shell concern. Creating a dedicated top-level repository folder for the subsystem was rejected because it would violate the prescribed repository layout. Treating generated PRDs or inline code comments as the authoritative design source was rejected because `forge-docs/` is explicitly the source of truth.

## ConsensusDevAgent must operate as a gated stage participant in the build pipeline
**Status:** Accepted  
**Context:** The build pipeline is stage-based and is the core execution loop. ConsensusDevAgent participates in generation, arbitration, and review-adjacent decisions. Pipeline behavior must remain consistent with TRD-defined stage contracts and auditability expectations.  
**Decision:** Implement ConsensusDevAgent as a stage-aware subsystem that only acts within explicit pipeline stage contracts and emits outputs that can be gated, audited, and handed off to subsequent stages. Do not permit free-running agent behavior outside the defined pipeline.  
**Consequences:** The subsystem must expose deterministic integration points for stage execution, status reporting, and gate creation. It must be possible to attribute ConsensusDevAgent outputs to a specific pipeline stage and run context. Any internal multi-agent behavior must still resolve to stage-bounded artifacts and decisions.  
**Rejected alternatives:** Allowing ConsensusDevAgent to operate as an autonomous background agent independent of the pipeline was rejected because it breaks stage contracts and auditability. Letting the subsystem directly mutate repository state outside stage execution was rejected because it would bypass the build pipeline and review controls.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The requirements explicitly state that there is no undo on gate decisions and that this must be documented explicitly. Security refusals and gate-triggering events are terminal in the current execution path.  
**Decision:** Treat all gate decisions produced or escalated by ConsensusDevAgent as irreversible within the current run. Never implement an automatic undo, rollback-of-decision, silent retry past a gate, or auto-bypass mechanism after a gate has been issued.  
**Consequences:** Once the subsystem raises or records a gate, execution must stop or await explicit operator handling as defined by pipeline contracts. The system may start a new run or new decision path, but it must not retroactively erase or negate the original gate event. Audit logs must preserve the original gate and its cause. UX and operator tooling must not imply that a gate can be undone in-place.  
**Rejected alternatives:** Supporting “undo gate” for operator convenience was rejected because it contradicts the requirement. Automatically clearing transient gates after retries was rejected because it weakens audit integrity. Silent continuation after gate creation was rejected because it defeats the purpose of gates and breaks security expectations.

## SECURITY_REFUSAL is terminal and non-bypassable
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` handling in every generation system prompt, and any `SECURITY_REFUSAL` in output must stop the PR, gate, and log the event. The rules explicitly state this must never be auto-bypassed.  
**Decision:** Detect `SECURITY_REFUSAL` as a terminal control outcome in ConsensusDevAgent. On detection, immediately stop the affected PR or work item, create the required gate, log the event in the audit trail, and prohibit automatic continuation or bypass.  
**Consequences:** ConsensusDevAgent must inspect model outputs for `SECURITY_REFUSAL`, propagate the event into gate handling, and ensure downstream stages do not proceed on the affected work item. This behavior must be enforced uniformly across generation and any arbitration path that consumes model outputs.  
**Rejected alternatives:** Treating `SECURITY_REFUSAL` as advisory text was rejected because the security controls define it as a hard stop. Allowing one model’s non-refusal output to override another model’s refusal was rejected because it would create an auto-bypass path. Deferring refusal handling until later review stages was rejected because the requirement is to stop immediately.

## Consensus decisions must remain auditable and attributable
**Status:** Accepted  
**Context:** The pipeline references audit trail requirements, error escalation, and stage contracts. ConsensusDevAgent coordinates multiple model outputs and therefore must make arbitration transparent enough for later inspection.  
**Decision:** Record all material ConsensusDevAgent decisions with run-level attribution, stage attribution, participating inputs, selected outcome, and gate/escalation state in the audit trail. Do not allow opaque consensus outcomes that cannot be reconstructed from logged artifacts.  
**Consequences:** The subsystem must emit structured metadata for arbitration and consensus events. Operators and later review stages must be able to determine what was considered, what was chosen, and whether a gate or escalation occurred. Logging must preserve security-relevant events without masking the existence of a refusal or conflict.  
**Rejected alternatives:** Logging only final outputs was rejected because it hides arbitration rationale. Storing consensus reasoning only in ephemeral memory was rejected because it defeats auditability. Allowing unstructured free-text logs only was rejected because they are insufficient for reliable stage and gate analysis.

## ConsensusDevAgent must not write files without path validation
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate or coordinate generated artifacts that result in repository writes.  
**Decision:** Validate every file write path originating from or executed by ConsensusDevAgent with `path_security.validate_write_path()` before any write operation. Never permit direct writes that bypass this validation layer.  
**Consequences:** All repository mutations initiated by the subsystem must route through a validated write abstraction. This constrains implementation choices for artifact emission, patch application, temporary file handling, and generated output materialization.  
**Rejected alternatives:** Validating only user-supplied paths was rejected because generated paths can also be unsafe. Performing path validation only at a higher orchestration layer was rejected because subsystem-local writes could bypass it. Relying on repository-relative path joins alone was rejected because that is not the mandated control.

## Untrusted review content must remain explicitly labeled in agent inputs
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent may consume reviewer feedback during arbitration or follow-up generation.  
**Decision:** Preserve explicit untrusted labeling for any reviewer-supplied content passed into ConsensusDevAgent or downstream model prompts. Never normalize, strip, or blend untrusted reviewer content into trusted instruction channels.  
**Consequences:** Prompt construction and internal message formatting must maintain trust boundaries. Consensus decisions that use review comments must treat them as data, not authority. This reduces prompt-injection risk from external review content.  
**Rejected alternatives:** Merging reviewer comments into the main instruction block was rejected because it collapses trust boundaries. Sanitizing by omission of labels was rejected because it hides provenance. Trusting reviewer comments from repository collaborators by default was rejected because the requirement defines the content class as untrusted.

## Flagged content usage requires operator gating
**Status:** Accepted  
**Context:** The security controls state that when flagged chunk content is used in generation, a gate card must be shown to the operator before proceeding. ConsensusDevAgent may aggregate or select model inputs that include flagged material.  
**Decision:** If ConsensusDevAgent uses, selects, or propagates flagged content into generation or decision-making that requires operator acknowledgment, it must raise the required operator gate before proceeding. Do not continue automatically once such usage is detected.  
**Consequences:** The subsystem must track provenance of flagged chunks through arbitration and generation paths. It must be able to surface a gate at the point flagged content becomes operative, not merely when the content first appears. This may reduce automation throughput, but it preserves the required operator control.  
**Rejected alternatives:** Gating only on initial ingestion of flagged content was rejected because usage, not mere presence, is the operative trigger. Allowing consensus to proceed silently if the flagged content was only one of several inputs was rejected because the selected outcome may still depend on it. Deferring operator notice until after code generation was rejected because the requirement says to gate before proceeding.

## ConsensusDevAgent outputs remain subject to downstream 3-pass review
**Status:** Accepted  
**Context:** The build pipeline defines a 3-pass review stage: correctness, performance, and security. Security controls also require generated code to pass Pass 3, including bandit. ConsensusDevAgent may select or arbitrate code, but selection does not replace review.  
**Decision:** Treat all ConsensusDevAgent-generated or ConsensusDevAgent-selected implementation output as provisional until it passes the defined downstream review stages. Do not let consensus selection act as a substitute for correctness, performance, or security review.  
**Consequences:** The subsystem cannot mark its own outputs as final merely because multiple agents agree. Integration contracts must hand off artifacts into the formal review pipeline. Security review remains mandatory even for unanimously selected outputs.  
**Rejected alternatives:** Allowing consensus unanimity to skip review was rejected because the pipeline requires review. Skipping security review for low-risk changes was rejected because mandatory controls require Pass 3. Treating arbitration confidence as equivalent to verification was rejected because confidence is not a security or correctness guarantee.