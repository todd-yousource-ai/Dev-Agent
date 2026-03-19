# DECISIONS.md

## Repository structure places ConsensusDevAgent inside the monorepo source tree
**Status:** Accepted  
**Context:** The TRDs and repository layout define a single monorepo where documentation, standards, backend code, tests, and the macOS shell coexist. ConsensusDevAgent must fit this structure so that build pipeline stages, standards, and tests resolve deterministically.  
**Decision:** Implement ConsensusDevAgent under `src/` as part of the Python backend, with tests under `tests/`, and treat `forge-docs/` as the source of truth for TRDs and PRDs and `forge-standards/` as the source of implementation constraints. Do not create a separate repository, package root, or parallel document store for this subsystem.  
**Consequences:** This constrains imports, CI, and ownership boundaries to the existing monorepo layout. Documentation consumed by the subsystem must be read from `forge-docs/`. Architectural constraints must be read from `forge-standards/`. Any UI affordances for the subsystem belong in `ForgeAgent/`, not in the backend tree.  
**Rejected alternatives:** Creating ConsensusDevAgent as a standalone repository was rejected because it would break the documented monorepo contract and complicate build and review stages. Storing subsystem-specific design docs outside `forge-docs/` was rejected because TRDs/PRDs are explicitly centralized there. Implementing core backend logic inside the macOS app shell was rejected because backend runtime code belongs in `src/`.

## ConsensusDevAgent must honor the documented staged build pipeline
**Status:** Accepted  
**Context:** The build pipeline is the system’s core loop and is explicitly staged from scope through merge. ConsensusDevAgent participates in generation and review, so it must not invent an alternate workflow.  
**Decision:** Integrate ConsensusDevAgent behavior into the documented pipeline stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent gate/merge handling as defined by the TRDs and README. Do not skip, merge, or reorder stages locally within the subsystem.  
**Consequences:** Subsystem APIs and state transitions must map to explicit pipeline stages. Auditability and operator visibility depend on stage boundaries remaining intact. Internal optimizations are allowed only if they preserve the external stage contract and outputs.  
**Rejected alternatives:** A simplified single-pass generation flow was rejected because it violates the documented build loop. Allowing the subsystem to dynamically reorder stages was rejected because it weakens auditability and operator expectations. Combining review into code generation was rejected because the 3-pass review is a distinct required control.

## Gate decisions are final and must not support undo
**Status:** Accepted  
**Context:** The TRDs explicitly state “No undo on gate decisions” and require this to be documented explicitly. Gate outcomes are security- and audit-relevant workflow controls.  
**Decision:** Treat every gate decision in ConsensusDevAgent as immutable once recorded. Do not implement undo, rollback, silent reversal, or automatic reconsideration of a gate outcome. Any further progress after a blocking gate requires a new explicit operator action or a new pipeline run, not reversal of the original decision.  
**Consequences:** Data models must record append-only gate history. UI and API surfaces must not expose undo semantics for gate outcomes. Recovery paths must be modeled as new decisions, retries, or new runs. Audit logs must preserve the original gate event permanently.  
**Rejected alternatives:** Supporting operator undo was rejected because it contradicts the explicit requirement. Automatic reopening of failed gates after regeneration was rejected because it functionally acts as undo. Mutating prior gate records in place was rejected because it destroys audit integrity.

## SECURITY_REFUSAL output is a hard stop and may never be auto-bypassed
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in generation prompts and specify that SECURITY_REFUSAL in output must stop the PR, gate, and log, with no automatic bypass. ConsensusDevAgent must enforce this consistently.  
**Decision:** On any model output containing or signaling `SECURITY_REFUSAL`, immediately stop the active PR flow, raise a gate to the operator, and write an audit log entry. Never auto-bypass, suppress, reinterpret, or continue execution past this condition without explicit external handling outside the blocked run.  
**Consequences:** Parsers and orchestration logic must treat SECURITY_REFUSAL as a terminal control signal, not ordinary content. Downstream generation, write, review, and merge actions must be inhibited after detection. Audit artifacts must capture the event for traceability.  
**Rejected alternatives:** Treating SECURITY_REFUSAL as advisory text was rejected because the TRD defines it as a stop condition. Automatically retrying with a softened prompt was rejected because that is an implicit bypass. Allowing later stages to continue while flagging the issue was rejected because the requirement says stop PR, gate, and log.

## Security review is mandatory and includes a dedicated security pass
**Status:** Accepted  
**Context:** The build pipeline mandates 3-pass review: correctness, performance, and security. Additional controls specify that generated code must pass the security pass including bandit. ConsensusDevAgent must preserve this review contract.  
**Decision:** Require generated code handled by ConsensusDevAgent to pass all three review passes in order, including a distinct security review pass with the mandated tooling and checks. Do not mark implementation complete or merge-ready before the security pass succeeds.  
**Consequences:** Review orchestration must model three separate pass results. Security findings must block completion until resolved or otherwise handled through documented gating. Tooling integration must include the required security checks.  
**Rejected alternatives:** A two-pass review flow was rejected because it omits a mandated control. Folding security checks into correctness review was rejected because the pipeline requires a dedicated security pass. Making security review best-effort was rejected because the TRD states generated code passes Pass 3 including bandit.

## All file writes must validate paths before write
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and modifies code and documents, so write safety must be enforced uniformly.  
**Decision:** Validate every destination path with `path_security.validate_write_path()` immediately before any file write performed by ConsensusDevAgent. Do not allow direct writes, renames, or patch applications that bypass this validation step.  
**Consequences:** File operation abstractions in the subsystem must route through a single validated write path. Convenience helpers that write files directly are prohibited unless they call the validator. Refactors must preserve validation coverage for all write-capable paths.  
**Rejected alternatives:** Validating only user-supplied paths was rejected because the requirement covers every file path before write. Performing validation only once at planning time was rejected because the operative requirement is immediately before write. Relying on repository-relative path normalization alone was rejected because the mandated control is the validator function.

## Untrusted review content must remain explicitly labeled and isolated in prompts
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks must trigger a gate card before use in generation. ConsensusDevAgent consumes review feedback and therefore must preserve trust boundaries.  
**Decision:** Label all externally sourced PR review comments injected into model prompts as `[UNTRUSTED REVIEWER COMMENT]`, and when flagged content would be used in generation, halt and present a gate card to the operator before proceeding. Do not silently blend reviewer text into trusted instructions or implementation context.  
**Consequences:** Prompt builders must maintain source attribution and trust labeling. The subsystem must distinguish trusted repository documents from untrusted reviewer input. Generation plans that depend on flagged untrusted content must pause for operator review.  
**Rejected alternatives:** Treating reviewer comments as trusted project instructions was rejected because the TRD explicitly marks them untrusted. Removing labels after preprocessing was rejected because it erodes the trust boundary inside prompts. Auto-incorporating flagged chunks was rejected because operator gating is mandatory.

## Consensus-based generation must preserve explicit arbitration outcomes
**Status:** Accepted  
**Context:** The pipeline description states that PRD generation uses both models with “Claude wins,” and code generation uses parallel generation with arbitration. ConsensusDevAgent exists to coordinate multi-model output, so arbitration rules must be explicit and durable.  
**Decision:** Represent multi-model generation as explicit candidate production followed by recorded arbitration. Preserve which model outputs were considered, what arbitration rule was applied, and which candidate won. Where the documented rule is fixed, enforce it exactly rather than allowing ad hoc tie-breaking.  
**Consequences:** The subsystem must store candidate metadata and arbitration rationale in its run records. Later review and audit can reconstruct why a particular artifact was selected. Implementation cannot silently overwrite one model’s output with another without recording the decision.  
**Rejected alternatives:** Returning only the final merged artifact without candidate provenance was rejected because it undermines auditability. Letting whichever model responds first win was rejected because it conflicts with documented arbitration. Fully manual arbitration for every step was rejected because the pipeline already defines deterministic selection in some stages.

## Subsystem decisions and standards must be documented in-repo, not embedded only in code
**Status:** Accepted  
**Context:** The repository layout reserves `forge-standards/` for architecture and standards documents, including `DECISIONS.md`. ConsensusDevAgent implementation constraints need a stable, reviewable home outside source comments.  
**Decision:** Record architectural constraints for ConsensusDevAgent in repository standards documents, especially `forge-standards/DECISIONS.md`, and treat those documents as binding implementation inputs. Do not rely on code comments, prompt text, or tribal knowledge as the sole source of design decisions.  
**Consequences:** Changes to subsystem architecture require documentation updates alongside code changes. Reviewers can verify behavior against a canonical decision log. Code and prompts must remain consistent with the recorded decisions.  
**Rejected alternatives:** Keeping design decisions only in code comments was rejected because comments are fragmented and not a governed standards surface. Storing decisions only in TRDs was rejected because subsystem-level implementation constraints need a maintained in-repo operational decision log. Using issue tracker tickets as the primary decision record was rejected because they are not part of the repository source of truth.