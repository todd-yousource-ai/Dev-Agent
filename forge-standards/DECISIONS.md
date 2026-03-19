# DECISIONS.md

## Repository structure is fixed and docs-first
**Status:** Accepted

**Context:** The subsystem is implemented within a repository whose structure is already defined by TRDs and the repository layout. The documentation set in `forge-docs/` is the source of truth and must be read before implementation. The subsystem must fit into the established backend, standards, tests, and workflow locations so that build, review, and audit stages operate consistently.

**Decision:** Implement ConsensusDevAgent within the fixed repository structure. Treat `forge-docs/` as authoritative input, place implementation under `src/`, place tests under `tests/`, and record architecture constraints in `forge-standards/`. Do not introduce alternate top-level locations for production code, standards, or source-of-truth documents.

**Consequences:** Implementation must resolve all behavior from TRDs/PRDs stored in `forge-docs/`. Code organization for this subsystem must align with existing backend conventions and CI expectations. Any new subsystem documentation must complement, not replace, the standards documents in `forge-standards/`. Build and review tooling can assume stable paths.

**Rejected alternatives:**  
- Storing subsystem-specific design docs outside `forge-docs/`: rejected because TRDs/PRDs are explicitly the source of truth.  
- Creating a separate top-level package for ConsensusDevAgent: rejected because it would diverge from the mandated `src/` backend layout.  
- Treating implementation code as the primary specification: rejected because the workflow is docs-first and requires reading TRDs before building.

## Gate decisions are irreversible
**Status:** Accepted

**Context:** The build pipeline explicitly states there is no undo on gate decisions. This is a critical control for auditability, operator trust, and security escalation. ConsensusDevAgent participates in pipeline stages that can stop, gate, or escalate work, so reversibility would undermine the control model.

**Decision:** Treat every gate decision produced or enforced by ConsensusDevAgent as final and append-only. Do not implement undo, rollback, silent reopening, or automatic bypass of a gate once issued. Require forward-only resolution through explicit subsequent operator-driven actions defined by the pipeline, not reversal of the prior gate record.

**Consequences:** The subsystem must use immutable audit semantics for gate outcomes. UI and APIs must not expose "undo gate" behavior. Recovery flows must create new audit events rather than altering prior gate decisions. Operators and downstream automation can rely on gate history being stable and non-rewriteable.

**Rejected alternatives:**  
- Allowing operator undo of a gate decision: rejected because TRD guidance explicitly forbids undo on gate decisions.  
- Allowing automatic gate reopening after retries succeed: rejected because that would function as an implicit undo and weaken auditability.  
- Physically deleting or mutating gate records: rejected because audit trail integrity requires append-only history.

## ConsensusDevAgent must operate within the staged build pipeline
**Status:** Accepted

**Context:** The repository defines a fixed build pipeline triggered by `/prd start <intent>` with ordered stages from scope through merge. ConsensusDevAgent exists inside this pipeline and must not create competing execution order or skip required stage boundaries.

**Decision:** Integrate ConsensusDevAgent behavior strictly within the defined pipeline stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, CI, and Merge. Do not collapse, reorder, or bypass stages. Any consensus or arbitration logic must execute as part of the appropriate stage contract rather than inventing a separate lifecycle.

**Consequences:** Consensus outputs must be stage-scoped and auditable. The subsystem must hand off artifacts in forms expected by later stages. Error handling and escalations must respect stage boundaries. Implementation must be compatible with TRD-3 contracts and existing pipeline orchestration.

**Rejected alternatives:**  
- Running a free-form agent loop outside the pipeline: rejected because the core loop is stage-driven and auditable.  
- Merging review and generation into one adaptive phase: rejected because the pipeline requires explicit ordered stages with separate responsibilities.  
- Letting consensus logic skip directly to merge on confidence: rejected because CI and review stages are mandatory.

## Security refusal is a hard stop
**Status:** Accepted

**Context:** Mandatory security controls require `SECURITY_REFUSAL` behavior in generation prompts and outputs. When this condition occurs, the process must stop the PR, gate, and log the event. ConsensusDevAgent may aggregate or arbitrate model outputs, so it must not dilute or override this signal.

**Decision:** On any `SECURITY_REFUSAL` emitted, detected, or inferred in ConsensusDevAgent-controlled generation or review flows, immediately stop the affected PR flow, create a gate, and log the event. Never auto-bypass, suppress, reinterpret, or outvote a `SECURITY_REFUSAL` through consensus.

**Consequences:** Consensus cannot override security refusals even if other agents disagree. The subsystem must propagate refusal states as terminal for the current flow until operator handling occurs. Audit logs must capture the source and context of the refusal. PR automation must halt deterministically.

**Rejected alternatives:**  
- Majority vote over a `SECURITY_REFUSAL`: rejected because mandatory controls require stop, gate, and log behavior.  
- Auto-retrying with prompt variations to avoid refusal: rejected because it would amount to bypassing a hard security control.  
- Downgrading refusal to a warning when confidence is high: rejected because the control is mandatory and non-optional.

## Security review remains mandatory after generation
**Status:** Accepted

**Context:** Generated code must pass the defined 3-pass review, including security review, and security tooling such as bandit is explicitly required. Consensus during code generation does not replace the review pipeline.

**Decision:** Require all code produced through ConsensusDevAgent flows to complete the full 3-pass review sequence—correctness, performance, and security—before CI and merge. Do not treat consensus agreement, arbitration outcomes, or multi-model convergence as a substitute for Pass 3 security review.

**Consequences:** The subsystem must emit artifacts suitable for downstream review and must wait for review outcomes before considering work complete. Security review findings can block progression regardless of prior consensus. Pipeline orchestration remains the source of release readiness.

**Rejected alternatives:**  
- Skipping security review when multiple agents agree on output: rejected because mandatory controls require Pass 3 security review.  
- Running only security review for high-risk changes and omitting other passes: rejected because the build pipeline defines all three passes.  
- Folding review heuristics into generation and treating that as equivalent: rejected because stage contracts require explicit review passes.

## All write paths must be validated before file output
**Status:** Accepted

**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate, select, or materialize artifacts, making file write safety a direct subsystem concern.

**Decision:** Validate every target file path with `path_security.validate_write_path()` before any write, overwrite, rename, or generated artifact materialization performed by ConsensusDevAgent. Refuse the operation and gate/log as appropriate if validation fails.

**Consequences:** File output code must centralize path validation and may not permit direct filesystem writes that bypass the control. The subsystem must assume all computed paths are untrusted until validated. Tests must cover invalid, traversal, and unexpected path cases.

**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated and derived paths can also be unsafe.  
- Validating only at the outer API layer: rejected because internal writes could bypass the control.  
- Relying on repository-relative path joins without explicit validation: rejected because mandatory controls require the explicit validator.

## Untrusted review content must remain labeled and non-authoritative
**Status:** Accepted

**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks used in generation must gate to the operator before proceeding. ConsensusDevAgent may consume review material as input for arbitration or regeneration, so provenance must be preserved.

**Decision:** Preserve untrusted provenance for reviewer-supplied content throughout ConsensusDevAgent processing. Label such content as untrusted in prompts and internal representations, and do not allow it to become authoritative instruction without required gating. If flagged chunks are used in generation, gate to the operator before proceeding.

**Consequences:** Prompt construction and artifact lineage must distinguish trusted specs from untrusted comments. Consensus scoring must not silently elevate review comments to system or source-of-truth status. Operator gating is required when flagged content influences generation. Audit records must show when untrusted content was incorporated.

**Rejected alternatives:**  
- Treating reviewer comments as equivalent to TRDs/PRDs: rejected because review comments are explicitly untrusted.  
- Stripping provenance labels before arbitration for simplicity: rejected because it weakens the security boundary.  
- Auto-incorporating flagged chunks if multiple agents agree: rejected because flagged usage requires operator gating.

## Claude-selected output wins where TRD generation specifies it
**Status:** Accepted

**Context:** The build pipeline states that PRD generation uses both models and "Claude wins." ConsensusDevAgent must not redefine this contract where the pipeline has already selected a winner.

**Decision:** In PRD generation contexts governed by the pipeline contract, implement dual-model generation but select Claude’s output as the authoritative result when finalizing the PRD artifact. Do not replace this rule with generic voting, averaging, or alternate tie-breakers.

**Consequences:** Consensus logic must be context-sensitive: it may arbitrate in some stages, but in PRD generation the final authority is predetermined. The subsystem must preserve both outputs for audit/debugging if required, while final artifact selection follows the contract. This constrains abstraction of "consensus" to avoid flattening stage-specific rules.

**Rejected alternatives:**  
- Majority vote between model outputs: rejected because the stage contract explicitly says Claude wins.  
- Always using a single model to reduce complexity: rejected because the pipeline requires both models for PRD generation.  
- Using another model as a tiebreaker: rejected because the contract already defines the winner without a tiebreak process.