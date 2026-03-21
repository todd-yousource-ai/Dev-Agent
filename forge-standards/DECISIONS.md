# DECISIONS.md

## ConsensusDevAgent repository placement and source-of-truth boundaries
**Status:** Accepted  
**Context:** The subsystem must fit the repository structure defined across the TRDs and README. The system distinguishes documents that define intent and standards from implementation code, and this boundary is necessary for traceability, review, and auditability.  
**Decision:** Place all ConsensusDevAgent implementation in the existing repository layout only. Treat `forge-docs/` as the source of truth for TRDs and PRDs, `forge-standards/` as the source of truth for architecture and implementation constraints, and `src/` as the Python backend implementation location for ConsensusDevAgent code. Do not place executable subsystem logic inside `forge-docs/` or `forge-standards/`.  
**Consequences:** Implementation must read from document sources but not redefine them in code-owned locations. Design artifacts, planning artifacts, and generated documents remain separated from runtime code. Any ConsensusDevAgent module structure must preserve traceability back to TRDs/PRDs without moving those documents.  
**Rejected alternatives:**  
- Embedding TRD or PRD copies inside `src/`: rejected because it creates drift and duplicates the source of truth.  
- Storing subsystem-specific standards beside implementation code: rejected because standards belong in `forge-standards/` and must constrain all subsystems consistently.  
- Creating a new top-level repository area for ConsensusDevAgent: rejected because it violates the prescribed repository layout.

## ConsensusDevAgent must operate as a backend subsystem in Python
**Status:** Accepted  
**Context:** The repository layout explicitly places backend implementation in `src/` and the macOS shell in `ForgeAgent/`. ConsensusDevAgent belongs to the backend execution path, not the Swift UI shell.  
**Decision:** Implement ConsensusDevAgent as a Python backend subsystem under `src/`. Expose integration points suitable for orchestration by the broader build pipeline and agent coordination stack, while keeping macOS UI concerns out of subsystem core logic.  
**Consequences:** Core consensus logic, arbitration, gating, audit handling, and pipeline interactions must be written in Python. UI-specific state, view models, and presentation decisions cannot be embedded into ConsensusDevAgent core modules. Tests for subsystem behavior belong primarily in `tests/` using pytest.  
**Rejected alternatives:**  
- Implementing ConsensusDevAgent in Swift inside `ForgeAgent/`: rejected because ConsensusDevAgent is part of backend runtime behavior, not app-shell UI behavior.  
- Splitting core logic across Python and Swift: rejected because it increases coupling, complicates testing, and weakens backend determinism.  
- Treating the subsystem as a documentation-only process: rejected because the build pipeline requires executable orchestration and enforcement.

## ConsensusDevAgent is constrained by the staged build pipeline
**Status:** Accepted  
**Context:** The README defines a fixed build pipeline from scope through merge, and the TRDs require explicit stage contracts, escalation, and auditability. ConsensusDevAgent must participate without redefining stage order or semantics.  
**Decision:** Implement ConsensusDevAgent to operate within the existing pipeline stages and their contracts. Do not collapse, reorder, or bypass stages. Where the subsystem contributes consensus, arbitration, review, or gating behavior, it must do so as part of the defined stage flow.  
**Consequences:** The subsystem cannot introduce ad hoc execution paths that skip planning, review, or gates. Internal APIs should reflect stage boundaries so that actions are attributable to a pipeline stage. Audit records must preserve stage context.  
**Rejected alternatives:**  
- Allowing direct code generation from intent without PRD/PR planning stages: rejected because it breaks the required staged workflow.  
- Merging review stages into code generation for speed: rejected because the 3-pass review is explicitly required and separately auditable.  
- Letting agents dynamically reorder stages based on confidence: rejected because deterministic stage contracts are mandatory.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The TRD content explicitly states “No undo on gate decisions” and requires this to be documented. Gate outcomes exist to preserve audit integrity and prevent silent rollback of safety-critical decisions.  
**Decision:** Treat every gate decision made by ConsensusDevAgent as append-only and irreversible. Do not provide an undo, rollback, silent override, or automatic bypass for a recorded gate outcome. Any further progress requires a new forward action, new operator intervention, or a new pipeline attempt with separately recorded state.  
**Consequences:** Data models, APIs, and UI affordances must not include “undo gate” behavior. If a gate blocks progression, the subsystem must record the block and require explicit subsequent handling rather than mutating history. Audit trails must preserve all gate outcomes as historical facts.  
**Rejected alternatives:**  
- Supporting operator undo of prior gate decisions: rejected because it violates the explicit TRD requirement and weakens auditability.  
- Auto-clearing gates after retries: rejected because it effectively acts as an undo and hides prior decisions.  
- Mutating prior gate records in place: rejected because gate history must remain append-only.

## SECURITY_REFUSAL is a hard stop, never auto-bypassed
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL handling in generation prompts and outputs. The requirements explicitly state that SECURITY_REFUSAL in output must stop the PR, trigger a gate, and be logged, with no automatic bypass.  
**Decision:** Implement SECURITY_REFUSAL as a terminal gating event for the active PR flow. When detected in model output or applicable generation paths, ConsensusDevAgent must stop progression, create or surface a gate to the operator, and write an audit log entry. Never auto-bypass, suppress, or reinterpret SECURITY_REFUSAL as a recoverable warning.  
**Consequences:** ConsensusDevAgent must include explicit detection, logging, and gate creation logic for SECURITY_REFUSAL. Downstream stages must not proceed after such an event until a new valid forward path is initiated under recorded controls. Prompting, arbitration, and output parsing must preserve the visibility of refusals.  
**Rejected alternatives:**  
- Retrying automatically until a non-refusal output is produced: rejected because it bypasses a mandatory security stop.  
- Treating SECURITY_REFUSAL as a low-severity review issue: rejected because requirements define it as a PR-stopping event.  
- Stripping refusal tokens from output and continuing: rejected because it destroys security signaling and audit integrity.

## Security review is mandatory for all generated code
**Status:** Accepted  
**Context:** The security controls require all generated code to pass Pass 3 security review, including bandit, before progression. ConsensusDevAgent participates in generation and therefore must enforce the security pass rather than treating it as optional.  
**Decision:** Require every code artifact produced through ConsensusDevAgent flows to complete the defined 3-pass review pipeline, with Pass 3 security review mandatory and blocking. Include required automated security checks such as bandit where applicable, and do not mark generation complete before security review passes.  
**Consequences:** Subsystem orchestration must preserve review dependencies and cannot fast-path generated code to merge-ready state. Review status must be represented explicitly in state and audit records. Any consensus about correctness or performance is insufficient without security clearance.  
**Rejected alternatives:**  
- Skipping Pass 3 for low-risk changes: rejected because the requirement applies to all generated code.  
- Running security review asynchronously after merge preparation: rejected because security review is a blocking pass, not a post hoc check.  
- Substituting model self-assessment for actual security pass execution: rejected because the controls require real review enforcement.

## File writes must use validated paths only
**Status:** Accepted  
**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and updates files and therefore is part of the enforcement boundary.  
**Decision:** Validate every target path with `path_security.validate_write_path()` before any file write initiated by ConsensusDevAgent. Treat failed validation as a blocking error and do not attempt fallback writes to unvalidated paths.  
**Consequences:** All write-capable code paths must centralize through a validated file-writing abstraction or equivalent enforced call pattern. Direct filesystem writes without prior validation are prohibited. Error handling must preserve the failed validation outcome in logs or audit records as appropriate.  
**Rejected alternatives:**  
- Validating only user-provided paths: rejected because generated and internally constructed paths can also be unsafe.  
- Validating only top-level directories once per run: rejected because every concrete write target must be checked.  
- Allowing emergency bypass flags for trusted internal writes: rejected because mandatory path validation must be universal.

## Untrusted review content must remain explicitly labeled
**Status:** Accepted  
**Context:** Security controls specify that PR review comments are labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent must preserve trust boundaries when incorporating reviewer input into consensus or generation.  
**Decision:** Preserve explicit untrusted labeling for reviewer-supplied content in all prompt construction, arbitration context, and downstream processing. Do not normalize, relabel, or silently merge untrusted review text into trusted instruction channels.  
**Consequences:** Prompt assembly and context formatting must maintain source provenance. Consensus logic must distinguish trusted system/process instructions from untrusted reviewer commentary. This reduces prompt-injection risk from review content and constrains how comments can influence generation.  
**Rejected alternatives:**  
- Treating all review comments as trusted because they come from the repository workflow: rejected because the controls explicitly mark them as untrusted.  
- Stripping the untrusted label after ingestion: rejected because it erodes the trust boundary at the point of use.  
- Blocking all reviewer comments from prompts entirely: rejected because reviewer input is useful, but must be handled with explicit trust labeling.

## Flagged chunks used in generation must trigger an operator gate
**Status:** Accepted  
**Context:** Security controls require that when a flagged chunk is used in generation, a gate card must be presented to the operator before proceeding. ConsensusDevAgent is responsible for coordinating generation and therefore must enforce this pause.  
**Decision:** When generation would use content identified as a flagged chunk, stop automatic progression and raise an operator gate before proceeding. Record the event and require explicit operator-visible handling rather than silently continuing.  
**Consequences:** Retrieval, prompt-construction, and generation orchestration must propagate flagged-content metadata into gating logic. The subsystem cannot treat flagged content as ordinary context. Audit records must show that flagged content influenced a gated decision point.  
**Rejected alternatives:**  
- Allowing flagged chunks when model confidence is high: rejected because operator gating is mandatory.  
- Silently removing flagged chunks and continuing: rejected because it hides a material decision and may alter intent without visibility.  
- Logging flagged chunk usage without gating: rejected because the requirement explicitly demands a gate card before proceeding.

## Consensus decisions must be auditable and append-only
**Status:** Accepted  
**Context:** The build pipeline and gate constraints require an audit trail schema, explicit escalation, and immutable decision history. ConsensusDevAgent produces arbitration and gate outcomes that must withstand later review.  
**Decision:** Record consensus outcomes, gates, escalations, and stage-affecting decisions as append-only audit events. Do not overwrite prior decision records in place. Any revised outcome must be captured as a new event linked to prior context.  
**Consequences:** Persistence design must favor event history over mutable latest-state-only storage. APIs should expose both current state and historical lineage. This directly supports the no-undo rule and ensures forensic traceability of multi-agent behavior.  
**Rejected alternatives:**  
- Storing only current status fields with no event history: rejected because it cannot support audit or no-undo semantics.  
- Rewriting prior records to reflect final outcomes: rejected because it destroys traceability.  
- Keeping audit data only in ephemeral logs: rejected because durable, queryable decision history is required.