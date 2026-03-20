# DECISIONS.md

## [ConsensusDevAgent repository placement and dependency boundaries]
**Status:** Accepted  
**Context:** The repository structure is fixed across the system. TRDs and PRDs are the source of truth in `forge-docs/`, implementation lives under `src/`, standards live under `forge-standards/`, and tests live under `tests/`. The ConsensusDevAgent subsystem must fit this structure without creating a parallel documentation or implementation layout.  
**Decision:** Implement ConsensusDevAgent backend code under `src/`. Store subsystem tests under `tests/`. Treat `forge-docs/` as read-first source material and `forge-standards/DECISIONS.md` as the binding implementation decision record. Do not store TRDs, PRDs, or generated planning artifacts inside subsystem code directories.  
**Consequences:** Documentation and implementation remain separable. The subsystem must read from canonical docs rather than embedding divergent local copies. Any ConsensusDevAgent code must be organized to respect repository-wide boundaries and must not introduce ad hoc top-level directories for prompts, plans, or decision records.  
**Rejected alternatives:**  
- Placing subsystem docs beside implementation in `src/`: rejected because `forge-docs/` is the mandated source of truth.  
- Creating a subsystem-local decisions file: rejected because standards and decisions are centralized under `forge-standards/`.  
- Storing generated PRD or planning artifacts in the subsystem tree: rejected because it blurs source-of-truth boundaries and increases drift risk.

## [Gate decisions are final and non-reversible]
**Status:** Accepted  
**Context:** The build pipeline explicitly states that gate decisions have no undo. Security refusal behavior also requires stopping, gating, and logging rather than silently recovering or auto-bypassing. ConsensusDevAgent participates in stage transitions and must enforce the same invariant.  
**Decision:** Treat every gate decision made by ConsensusDevAgent as final. Do not implement undo, rollback, silent reopening, automatic reconsideration, or operator-hidden reversal of a closed gate outcome. Require a new explicit forward action or new run context rather than mutating historical gate state.  
**Consequences:** Auditability is preserved because the recorded gate history is immutable in meaning. Operators cannot “undo” a failed, blocked, or refused gate from the subsystem state machine. Any retry must create a new evaluation or subsequent decision record, not alter the prior one. API and persistence design must model append-only gate events rather than mutable gate status history.  
**Rejected alternatives:**  
- Allowing operator undo of gate outcomes: rejected because it violates the explicit no-undo pipeline rule.  
- Allowing automatic retry to overwrite previous gate state: rejected because it destroys audit clarity.  
- Soft-deleting gate decisions and recomputing current state: rejected because it obscures historical accountability.

## [SECURITY_REFUSAL is a hard stop signal]
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` rules in generation prompts and mandate that `SECURITY_REFUSAL` in output stops the PR, gates the workflow, and logs the event. ConsensusDevAgent must participate in consensus and arbitration without weakening this control.  
**Decision:** Interpret any `SECURITY_REFUSAL` emitted by a contributing model, review pass, or consensus input as a hard stop. Immediately stop progression of the affected work item, open a gate to the operator, and log the event. Never auto-bypass, auto-sanitize away, suppress, or downgrade a `SECURITY_REFUSAL`.  
**Consequences:** Consensus cannot outvote a security refusal. A majority of non-refusing agents must not override a single valid `SECURITY_REFUSAL` signal. The subsystem must propagate refusal semantics across generation, review, and arbitration paths. Logging and gate creation become mandatory side effects of detection.  
**Rejected alternatives:**  
- Majority-vote override of a refusal: rejected because security refusal is mandatory and not subject to consensus dilution.  
- Automatic prompt repair and resume without operator gate: rejected because the required behavior is stop, gate, and log.  
- Treating refusal as a low-priority warning: rejected because the control requires PR stoppage.

## [Consensus outputs must preserve untrusted input labeling]
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks must trigger an operator gate before use in generation. ConsensusDevAgent aggregates multi-source input and therefore must preserve trust boundaries during synthesis.  
**Decision:** Preserve explicit trust labels on all untrusted or externally sourced inputs throughout consensus assembly, prompting, and decision rendering. Do not merge untrusted reviewer content into trusted instruction channels. When a flagged chunk would be used for generation or consensus justification, gate to the operator before proceeding.  
**Consequences:** Prompt construction, intermediate data models, and consensus summaries must carry provenance and trust metadata. The subsystem must distinguish trusted policy, trusted repository context, and untrusted reviewer/user content. Consensus explanations may quote untrusted content only with explicit labeling.  
**Rejected alternatives:**  
- Flattening all inputs into one prompt context without trust labels: rejected because it enables prompt injection and violates mandatory controls.  
- Sanitizing labels away in final consensus summaries: rejected because downstream consumers would lose provenance.  
- Allowing flagged chunks in generation after best-effort filtering without gating: rejected because operator gating is required.

## [ConsensusDevAgent must align to the staged build pipeline]
**Status:** Accepted  
**Context:** The repository defines a staged build pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent execution flow. ConsensusDevAgent is a subsystem within this larger pipeline and must not invent an incompatible lifecycle.  
**Decision:** Design ConsensusDevAgent as a stage-aware subsystem that consumes and emits explicit stage-compatible outcomes. It must respect stage boundaries, surface gate decisions at the appropriate stage, and avoid skipping, collapsing, or reordering mandated pipeline stages on its own authority.  
**Consequences:** Interfaces must include stage context. Consensus results must be usable by upstream and downstream pipeline components without translation ambiguity. The subsystem cannot directly advance work from planning to merge readiness without required review stages.  
**Rejected alternatives:**  
- A standalone consensus loop independent of the pipeline: rejected because it would conflict with stage contracts and audit expectations.  
- Allowing the subsystem to skip stages when confidence is high: rejected because required stages are contractual.  
- Combining multiple pipeline stages into one consensus action: rejected because it weakens traceability and gate semantics.

## [Security review constraints apply to generated and modified code paths]
**Status:** Accepted  
**Context:** Mandatory security controls state that all generated code must pass Pass 3 security review including bandit, and every file write path must be validated with `path_security.validate_write_path()`. ConsensusDevAgent may coordinate code generation or write artifacts and therefore must enforce these constraints.  
**Decision:** Require ConsensusDevAgent to route any generated or modified code through the security review path and to validate every file path before write using the mandated path validation mechanism. Do not allow consensus-selected outputs to bypass Pass 3 or path validation because they were “approved by consensus.”  
**Consequences:** Consensus is advisory for selection, not an exemption from security controls. Any subsystem component that persists files must depend on the shared path validation utility. Workflow integration must ensure that selected outputs still undergo mandatory security scanning and review gates.  
**Rejected alternatives:**  
- Skipping security review for consensus-approved code: rejected because mandatory controls apply to all generated code.  
- Validating only final merged file paths but not temporary writes: rejected because every write path must be validated.  
- Treating non-code artifacts as exempt without explicit classification: rejected because write safety must be enforced consistently unless a narrower rule is formally established.

## [Decision records must be append-only and audit-oriented]
**Status:** Accepted  
**Context:** The pipeline and gate model emphasize audit trail integrity, especially around errors, refusals, and gate actions. Since gate decisions cannot be undone, ConsensusDevAgent must maintain records that support reconstruction of what happened and why.  
**Decision:** Record consensus inputs, outcomes, gate events, and refusal-related actions in an append-only manner sufficient for audit and later inspection. Do not mutate prior decision records to reflect newer conclusions; instead append superseding records with explicit linkage.  
**Consequences:** Persistence schemas and APIs must support immutable event capture and supersession references. Debugging and compliance review can reconstruct the exact sequence of decisions. Consumers must compute “latest effective state” from appended records rather than relying on destructive updates to history.  
**Rejected alternatives:**  
- Updating a single mutable “current decision” row: rejected because it loses historical reasoning and conflicts with no-undo semantics.  
- Storing only final consensus outcomes: rejected because refusals, gates, and intermediate escalation decisions are audit-relevant.  
- Deleting erroneous records: rejected because corrections must be represented as subsequent records, not erasure.