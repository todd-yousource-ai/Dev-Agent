# DECISIONS.md

## ConsensusDevAgent documents live in `forge-docs` and must be treated as source of truth
**Status:** Accepted  
**Context:** The subsystem operates inside a repository where TRDs and PRDs are authoritative inputs. Repository structure explicitly places all TRDs and PRDs under `forge-docs`, and implementation is expected to read those documents before building. The ConsensusDevAgent depends on these documents to determine workflow behavior, stage contracts, security constraints, and coordination rules.  
**Decision:** Treat `forge-docs/` as the authoritative document store for all TRDs and PRDs, and require the ConsensusDevAgent to read and align to those documents before planning, generation, review, or merge decisions.  
**Consequences:** Implementation must not hardcode product behavior that conflicts with TRDs/PRDs. Any orchestration logic, prompts, stage behavior, or review criteria must be traceable to documents in `forge-docs`. The subsystem must not use ad hoc external files or undocumented conventions as competing sources of truth.  
**Rejected alternatives:**  
- Using code comments or inline prompt text as the primary source of truth — rejected because repository design explicitly defines `forge-docs` as authoritative.  
- Allowing agent-local configuration to override TRD/PRD intent — rejected because it would create divergence from documented requirements.  
- Storing active planning documents outside `forge-docs` — rejected because it fragments auditability and breaks the documented repository contract.

## ConsensusDevAgent must conform to the repository layout contract
**Status:** Accepted  
**Context:** The repository layout is predefined across docs, standards, source code, app shell, tests, and workflows. The subsystem must integrate into this layout predictably so that generated artifacts, reviews, and automation remain discoverable and auditable.  
**Decision:** Implement the ConsensusDevAgent to operate within the documented repository layout: `forge-docs/` for specifications, `forge-standards/` for standards documents, `src/` for Python backend implementation, `tests/` for pytest coverage, and existing CI workflow locations under `.github/workflows/`.  
**Consequences:** The subsystem must write code and tests only into approved locations and must not introduce parallel directory structures for equivalent concerns. Documentation generated or updated by the subsystem must be placed in the prescribed repository areas. Tooling and prompts must assume this layout when resolving paths.  
**Rejected alternatives:**  
- Creating a dedicated top-level `agents/` or `consensus/` tree for all subsystem outputs — rejected because it conflicts with the documented repository layout.  
- Splitting implementation across undocumented folders — rejected because it reduces discoverability and complicates CI and review.  
- Treating repository layout as advisory rather than mandatory — rejected because downstream tooling depends on stable paths.

## ConsensusDevAgent must honor the staged build pipeline as the execution model
**Status:** Accepted  
**Context:** The build pipeline is the core loop and is triggered from `/prd start <intent>`. The documented stages define the order from scoping through PRD planning, PR generation, code generation, review, and merge. Consensus behavior must fit into this stage model rather than inventing a separate lifecycle.  
**Decision:** Implement the ConsensusDevAgent as a participant in the documented build pipeline stages and require all planning, generation, review, and merge actions to occur within the stage order defined by the build pipeline.  
**Consequences:** The subsystem cannot skip required stages, reorder them arbitrarily, or merge outputs that have not passed through the documented lifecycle. Consensus/arbitration logic must be stage-aware and must emit outputs that support the next stage contract.  
**Rejected alternatives:**  
- Running an independent consensus loop outside the build pipeline — rejected because it would bypass required controls and reduce auditability.  
- Collapsing multiple stages into a single generation step — rejected because the documented process separates planning, implementation, and review for quality and security reasons.  
- Allowing direct code generation from intent without PRD/PR planning — rejected because it violates the pipeline definition.

## Gate decisions are final and must never support undo
**Status:** Accepted  
**Context:** Documentation explicitly states “No undo on gate decisions” and repeats this in build pipeline material. Gate outcomes are part of the audit and escalation model, especially for security-sensitive situations. Reversible gate semantics would undermine operator trust and audit integrity.  
**Decision:** Treat every gate decision produced or consumed by the ConsensusDevAgent as irreversible. Do not implement undo, rollback, silent reopening, or automatic reconsideration of a completed gate decision.  
**Consequences:** Once a gate is issued, the subsystem must require a new forward action rather than undoing the prior one. User interfaces, APIs, prompts, and state machines must not expose undo semantics for gate results. Recovery must occur through a new explicit operator decision or subsequent workflow step, not by reversing history.  
**Rejected alternatives:**  
- Supporting “undo last gate” for operator convenience — rejected because requirements explicitly forbid undo.  
- Allowing automatic reopening after new model evidence arrives — rejected because it mutates final decisions and weakens the audit trail.  
- Soft-deleting gate events while keeping internal reversibility — rejected because it still violates the finality requirement.

## SECURITY_REFUSAL is a hard stop that must gate and log, never auto-bypass
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in every generation system prompt. If SECURITY_REFUSAL appears in LLM output, the PR must stop, a gate must be raised, and the event must be logged. Documentation explicitly forbids auto-bypass.  
**Decision:** Detect SECURITY_REFUSAL as a mandatory terminal security event for the current generation/review action: stop progression, create a gate for operator handling, log the event in the audit trail, and never auto-bypass or silently continue.  
**Consequences:** The subsystem must inspect model outputs for SECURITY_REFUSAL, propagate the event into workflow state, and prevent downstream stages from continuing automatically. Consensus logic cannot outvote or suppress a SECURITY_REFUSAL emitted by any required security-enforced generation path.  
**Rejected alternatives:**  
- Retrying automatically until a non-refusal output appears — rejected because it effectively bypasses the security stop.  
- Letting another model override a refusal through arbitration — rejected because security refusal is not a normal disagreement signal.  
- Downgrading SECURITY_REFUSAL to a warning — rejected because the requirements define a stop, gate, and log action.

## Security review is mandatory and includes a dedicated security pass
**Status:** Accepted  
**Context:** The pipeline defines a 3-pass review sequence: correctness, performance, and security. Security controls further require all generated code to pass Pass 3 security review, including bandit. Consensus-driven generation does not reduce this obligation.  
**Decision:** Require every code artifact produced under ConsensusDevAgent orchestration to complete the full 3-pass review pipeline, with Pass 3 security review mandatory and including the prescribed automated checks such as bandit.  
**Consequences:** No consensus-selected implementation may be merged or treated as complete until it passes all required review passes. The subsystem must preserve review ordering and cannot replace the security pass with heuristic model agreement.  
**Rejected alternatives:**  
- Using consensus agreement as a substitute for security review — rejected because review stages are mandatory and distinct.  
- Making security review conditional on changed file types or model confidence — rejected because generated code universally requires Pass 3.  
- Running only automated scanners without the documented security pass semantics — rejected because the pipeline defines a dedicated security review stage.

## Untrusted review content must remain explicitly labeled and never be treated as trusted instructions
**Status:** Accepted  
**Context:** Security controls state that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. This is intended to prevent prompt injection and privilege escalation via review content. ConsensusDevAgent will consume review feedback during arbitration and revision, making trust boundaries critical.  
**Decision:** Preserve explicit untrusted labeling for reviewer-supplied content in all prompts and internal representations, and never treat such content as trusted system or developer instructions.  
**Consequences:** Prompt construction, review ingestion, and revision logic must maintain trust separation. Consensus logic must evaluate reviewer comments as data to consider, not authority to obey. Any workflow using external review text must keep provenance and labels intact.  
**Rejected alternatives:**  
- Normalizing all comments into plain instruction text for simpler prompting — rejected because it erases trust boundaries.  
- Treating maintainer or PR comment text as trusted by default — rejected because the requirement explicitly labels review comments as untrusted in prompt context.  
- Allowing model arbitration to strip labels for readability — rejected because that weakens the control.

## Flagged chunk usage in generation requires operator gating before proceeding
**Status:** Accepted  
**Context:** Security controls specify that when a flagged chunk is used in generation, a gate card must be presented to the operator before proceeding. The ConsensusDevAgent may aggregate context from multiple sources, so use of flagged material must trigger explicit human oversight.  
**Decision:** Detect use of flagged chunks during generation or revision and require operator gating before any further progression of the affected workflow.  
**Consequences:** The subsystem must track source chunks and their trust/flag status through prompt assembly and generation. Work cannot continue automatically once flagged content is used. Audit records must show that the gate occurred before progression resumed.  
**Rejected alternatives:**  
- Allowing flagged chunks if multiple models agree on the result — rejected because consensus does not replace mandatory operator gating.  
- Logging flagged usage without blocking — rejected because the requirement explicitly requires a gate before proceeding.  
- Filtering the flag after sanitization without operator involvement — rejected because the control requires human gate handling, not silent remediation.

## Every file write performed by ConsensusDevAgent must validate the target path
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. The subsystem generates and edits repository artifacts, making path traversal and unauthorized writes a concrete risk.  
**Decision:** Invoke `path_security.validate_write_path()` for every file write, overwrite, create, rename, or patch operation performed by the ConsensusDevAgent before touching the filesystem.  
**Consequences:** All write-capable code paths must route through a validated write abstraction or enforce equivalent mandatory precondition checks. The subsystem must fail closed on validation failure and must not provide raw write bypasses for convenience or performance.  
**Rejected alternatives:**  
- Validating only user-provided paths — rejected because generated and derived paths can also be unsafe.  
- Validating only top-level operations and trusting downstream helpers — rejected because it leaves gaps in nested write flows.  
- Relying on repository root checks alone — rejected because the required control is the specific path validation mechanism.

## Consensus outcomes must remain subordinate to operator gates and documented stage controls
**Status:** Accepted  
**Context:** The subsystem’s role is to help decide among planning, generation, and review outputs, but the repository’s process already defines operator confirmations, gates, and stage contracts. Consensus cannot become an authority that bypasses human or pipeline controls.  
**Decision:** Use consensus only to inform or select candidate outputs within a stage; do not allow consensus outcomes to bypass operator gates, override mandatory stops, or skip documented stage controls.  
**Consequences:** Arbitration logic must integrate with the workflow state machine rather than replacing it. A consensus result may recommend an action, but progression still requires satisfaction of all stage and gate requirements.  
**Rejected alternatives:**  
- Making consensus the final authority for merge readiness — rejected because review passes and operator controls remain mandatory.  
- Auto-advancing stages when model agreement exceeds a threshold — rejected because stage transitions are governed by the pipeline, not confidence scores.  
- Letting consensus overrule security or gate events — rejected because mandatory controls take precedence.