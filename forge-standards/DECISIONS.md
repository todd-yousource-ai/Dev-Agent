# DECISIONS.md

## ConsensusDevAgent repository placement and document authority
**Status:** Accepted  
**Context:** The subsystem must fit the repository contract used across the product and must not create ambiguity about where implementation lives versus where governing design artifacts live. The TRDs and README define a fixed repository layout and identify the documentation source of truth.  
**Decision:** Place ConsensusDevAgent implementation under `src/` and treat `forge-docs/` as the source of truth for TRDs and PRDs. Place cross-cutting architectural constraints for the subsystem in `forge-standards/`, including this file. Do not store governing TRDs, PRDs, or substitute design specs inside subsystem code directories.  
**Consequences:** Implementation must read from and conform to documents in `forge-docs/`. Any subsystem-specific architecture notes that constrain implementation belong in standards documents, not ad hoc README files in code folders. Build and review flows must assume documentation authority is external to the subsystem source tree.  
**Rejected alternatives:**  
- Storing ConsensusDevAgent design documents beside code in `src/consensus_dev_agent/`: rejected because it conflicts with the repository-wide rule that TRDs and PRDs live in `forge-docs/`.  
- Treating inline code comments or module docs as the design source of truth: rejected because it weakens traceability to approved TRDs and PRDs.  
- Creating a separate docs root for the subsystem: rejected because it fragments the documentation model and breaks the documented repository structure.

## ConsensusDevAgent must participate in the staged build pipeline
**Status:** Accepted  
**Context:** The system build flow is defined as a fixed staged pipeline, from scope through review. ConsensusDevAgent is part of the agentic development workflow and therefore must integrate with, not bypass, that pipeline.  
**Decision:** Implement ConsensusDevAgent as a subsystem that operates only within the defined pipeline stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, and 3-Pass Review. Do not add an alternate execution path that skips stage contracts or collapses stage boundaries.  
**Consequences:** Interfaces and state handling must preserve stage identity and handoff semantics. Consensus logic must be callable from the relevant stages without undermining auditability. Any optimization must retain explicit stage boundaries and outputs.  
**Rejected alternatives:**  
- A single monolithic “generate everything” workflow: rejected because it bypasses documented stage contracts and weakens control points.  
- Allowing arbitrary stage skipping when the model appears confident: rejected because it creates unauditable behavior and inconsistent outcomes.  
- Embedding review logic directly into generation with no separate review stage: rejected because it conflicts with the required 3-pass review model.

## No undo on gate decisions
**Status:** Accepted  
**Context:** Multiple source documents explicitly state that there is no undo on gate decisions. This must be reflected as an implementation constraint, especially for a subsystem coordinating consensus and progression through pipeline stages.  
**Decision:** Treat every gate decision as final and append-only. Once ConsensusDevAgent records a gate outcome, it must not provide any undo, rollback, silent overwrite, or automatic bypass mechanism for that decision. Any subsequent progress must occur through a new forward-moving decision or operator-mediated continuation defined by the pipeline, not mutation of prior gate history.  
**Consequences:** Data models must be append-only for gate outcomes. APIs must not expose “undo gate,” “reopen by overwrite,” or equivalent mutating operations. UI and operator tooling must present gate results as immutable historical facts. Recovery flows must create new records rather than rewriting old ones.  
**Rejected alternatives:**  
- Supporting operator undo for convenience: rejected because it directly violates the explicit no-undo requirement.  
- Allowing automatic rollback of a gate on later consensus change: rejected because it destroys audit integrity and creates ambiguous state transitions.  
- Soft-deleting prior gate decisions and showing only the latest state: rejected because it conceals history and undermines traceability.

## SECURITY_REFUSAL is a hard stop
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` handling in every generation prompt and mandate that if it appears in output, the PR must stop, gate, and log, with no automatic bypass. ConsensusDevAgent must enforce this consistently when arbitrating or aggregating model outputs.  
**Decision:** Detect `SECURITY_REFUSAL` as a terminal security signal. When any participating model or consensus path emits `SECURITY_REFUSAL`, immediately stop the affected PR or generation flow, create a gate for operator review, and log the event. Never auto-bypass, suppress, reinterpret, or outvote a `SECURITY_REFUSAL` through consensus.  
**Consequences:** Consensus logic cannot treat refusal as just another vote. Arbitration must short-circuit on security refusal before normal winner selection. Audit logs must capture the signal and resulting gate. Downstream code generation and merge actions must be blocked until operator handling occurs through the approved process.  
**Rejected alternatives:**  
- Majority vote over a refusal if other models succeed: rejected because security refusal is a hard stop, not a weighted opinion.  
- Automatically retrying until a non-refusal answer is obtained: rejected because it would function as an implicit bypass.  
- Hiding refusal text from operators and continuing with partial output: rejected because it violates the required stop, gate, and log behavior.

## Security review remains mandatory after consensus
**Status:** Accepted  
**Context:** The documented pipeline requires 3-pass review, including a dedicated security pass, and generated code must pass security controls including Bandit and path validation requirements. ConsensusDevAgent may help select or synthesize outputs, but it cannot replace mandatory security review.  
**Decision:** Require all code output selected, merged, or synthesized by ConsensusDevAgent to proceed through the full 3-pass review pipeline, with security review preserved as an explicit pass. Do not treat model agreement or consensus confidence as a substitute for Pass 3 security review.  
**Consequences:** ConsensusDevAgent must emit artifacts suitable for downstream review rather than final deployment by default. Integration points must preserve handoff to security review tools and checks. Any “accepted by consensus” status must still be non-terminal until required review passes complete.  
**Rejected alternatives:**  
- Skipping security review for unanimous model outputs: rejected because consensus does not satisfy the mandatory security pass requirement.  
- Combining correctness, performance, and security into one blended pass: rejected because it removes the required distinct review stages.  
- Using consensus confidence to downgrade security findings: rejected because security controls are mandatory and not advisory.

## Consensus decisions must be auditable
**Status:** Accepted  
**Context:** The pipeline and gate model rely on audit trails. Because ConsensusDevAgent influences PR generation and gating, its decisions must be reconstructable for review, escalation, and compliance with stage contracts.  
**Decision:** Record every material consensus decision with append-only audit data sufficient to reconstruct inputs, participating outputs, selected outcome, gate interactions, and final disposition. Do not allow silent arbitration or ephemeral-only decision making for actions that affect PR progression.  
**Consequences:** Storage and event schemas must include decision provenance. Operational tooling must be able to display why a result was selected or blocked. Error escalation and operator review can rely on durable records rather than transient runtime memory.  
**Rejected alternatives:**  
- Logging only the final chosen result: rejected because it is insufficient for reconstruction and review.  
- Keeping consensus traces only in memory for performance: rejected because it breaks auditability.  
- Sampling or probabilistically omitting low-risk decisions from logs: rejected because gate and stage progression require consistent traceability.

## Claude-wins rule applies where the pipeline specifies it
**Status:** Accepted  
**Context:** The documented pipeline explicitly states that PRD generation uses both models and that Claude wins. ConsensusDevAgent must not redefine that contract in the stages where it is already prescribed.  
**Decision:** Honor stage-specific winner rules from the pipeline. In PRD generation, when both models participate, implement the prescribed outcome that Claude wins. ConsensusDevAgent may coordinate collection, comparison, and recording, but must not override this rule with an alternate arbitration policy.  
**Consequences:** Consensus behavior is not globally uniform; it must be stage-aware. The subsystem must support deterministic winner policies when mandated by the pipeline. Any generalized consensus engine must allow fixed per-stage resolution rules.  
**Rejected alternatives:**  
- Applying one universal voting algorithm to every stage: rejected because it conflicts with explicit stage-specific contracts.  
- Letting ConsensusDevAgent choose a winner dynamically in PRD generation: rejected because the pipeline already defines the winner.  
- Averaging or merging both PRD outputs by default: rejected because it would replace a defined contract with an implicit synthesis rule.

## Untrusted review content must remain labeled and non-authoritative
**Status:** Accepted  
**Context:** Security controls require PR review comments from untrusted sources to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent may consume reviewer input during review or arbitration and must preserve trust boundaries.  
**Decision:** Preserve explicit trust labeling for untrusted reviewer content in all ConsensusDevAgent inputs and internal prompt construction. Do not elevate untrusted review comments to authoritative instructions, and do not strip the required label before passing the content to model participants.  
**Consequences:** Prompt builders, review aggregators, and consensus summaries must maintain provenance and trust metadata. The subsystem must distinguish between operator directives, trusted system instructions, and untrusted reviewer suggestions. Consensus outputs must not treat untrusted comments as controlling policy.  
**Rejected alternatives:**  
- Normalizing all comments into unlabeled plain text for simplicity: rejected because it removes required trust signaling.  
- Treating reviewer comments as equal to system instructions once ingested: rejected because it violates security boundaries.  
- Excluding all reviewer comments from consensus inputs: rejected because useful review context is needed, but it must be handled as untrusted.

## File writes produced through consensus must enforce path validation
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may select or synthesize file operations and therefore must not bypass write-path validation.  
**Decision:** Require path validation on every filesystem write initiated from ConsensusDevAgent outputs, including generated files, modified files, patches materialized to disk, and audit artifacts where applicable. Do not permit direct writes from model-selected paths without validation.  
**Consequences:** File operation interfaces for the subsystem must centralize validated writes. Model output cannot be executed as raw path instructions. Security review can assume path validation is invariant across consensus-mediated generation.  
**Rejected alternatives:**  
- Validating only newly created files but not modifications: rejected because the requirement applies to every file path before write.  
- Trusting repository-relative paths emitted by models: rejected because model output is not trusted input.  
- Performing validation only in a later pipeline pass: rejected because invalid writes must be blocked before they occur.