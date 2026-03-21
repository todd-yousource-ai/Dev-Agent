# DECISIONS.md

## ConsensusDevAgent documentation and source-of-truth boundaries
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with strict separation between requirements/specification artifacts and implementation. The TRDs and PRDs are the authoritative inputs for planning, generation, review, and gating. Without a clear boundary, implementation logic could drift from approved documents or mutate requirement sources.  
**Decision:** Treat `forge-docs/` as the exclusive source of truth for TRDs and PRDs, and keep ConsensusDevAgent implementation outside that directory. Read from `forge-docs/` before planning or execution; do not store implementation code, transient runtime state, or generated source files there. Place subsystem code under repository implementation roots such as `src/`, and store architectural constraints in `forge-standards/`.  
**Consequences:** ConsensusDevAgent must resolve requirements from documents in `forge-docs/` before acting. The subsystem may emit references, logs, and audit records that point to those documents, but it must not treat ad hoc prompts, comments, or generated code as higher authority than approved docs. Any feature that depends on requirement interpretation must be traceable back to repository documents.  
**Rejected alternatives:**  
- Allowing requirements to be inferred primarily from chat/session state was rejected because it weakens traceability and reproducibility.  
- Storing generated implementation artifacts alongside TRDs/PRDs in `forge-docs/` was rejected because it mixes source-of-truth documents with outputs.  
- Using a separate hidden internal spec store as the effective authority was rejected because it would diverge from the repository-visible process.

## ConsensusDevAgent must participate in the fixed build pipeline stages
**Status:** Accepted  
**Context:** The repository defines a canonical build pipeline with named stages from scope confirmation through merge. ConsensusDevAgent is one subsystem within that larger orchestration and must behave consistently with the documented contracts. A bespoke flow would break auditability and inter-agent coordination.  
**Decision:** Implement ConsensusDevAgent behavior as stage-constrained work within the repository’s fixed pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and Merge. Do not skip, reorder, or silently combine stages when making gate-affecting decisions.  
**Consequences:** ConsensusDevAgent must expose outputs and handoffs that align to pipeline stages. Any consensus result used for approval, escalation, or stopping work must be attributable to a specific stage. The subsystem cannot introduce an alternate “fast path” that bypasses documented reviews or merge controls.  
**Rejected alternatives:**  
- Letting the subsystem dynamically choose its own stage order was rejected because it undermines the documented contracts and audit trail.  
- Collapsing review into generation for efficiency was rejected because the repository requires distinct review passes.  
- Allowing merge after partial stage completion was rejected because it violates the pipeline’s gating model.

## Gate decisions are immutable and have no undo path
**Status:** Accepted  
**Context:** Multiple repository documents explicitly require that gate decisions are final and not reversible. This is especially important for safety, auditability, and operator trust. If a gate could be undone programmatically, downstream actions might occur without a clear and durable record of why a stop condition was raised.  
**Decision:** Treat every gate decision produced or consumed by ConsensusDevAgent as immutable. Do not implement undo, auto-reversal, silent reopening, or state rewrites that negate a prior gate. Any subsequent progress must occur through a new explicit decision event, preserving the original gate record.  
**Consequences:** The subsystem must model gate events append-only. UI, CLI, and API surfaces must not present “undo gate” behavior. Recovery flows must create new records such as operator overrides or new evaluations rather than mutating prior decisions. Audit logs must preserve the original gate, reason, timestamp, and triggering evidence.  
**Rejected alternatives:**  
- Supporting an operator “undo last gate” action was rejected because it conflicts with the documented requirement of no undo on gate decisions.  
- Allowing automatic ungating after timeout or re-run was rejected because it would erase the significance of the original stop event.  
- Rewriting gate state in place to reflect the latest outcome was rejected because it destroys audit history.

## SECURITY_REFUSAL is a mandatory hard-stop signal
**Status:** Accepted  
**Context:** Security controls require explicit handling of `SECURITY_REFUSAL` in LLM output. This signal indicates a condition serious enough to stop the PR flow, gate the work, and log the event. ConsensusDevAgent must not interpret it as advisory text or attempt to continue with degraded behavior.  
**Decision:** When `SECURITY_REFUSAL` appears in model output or an equivalent mandatory refusal condition is detected, stop the active PR flow immediately, create a gate event, and log the incident. Never auto-bypass, suppress, or reinterpret the refusal as non-blocking.  
**Consequences:** ConsensusDevAgent must inspect model outputs for this condition before accepting them into downstream stages. The subsystem must surface the refusal to operators and prevent automatic continuation. Consensus/arbitration logic must not “vote away” a refusal because one model’s refusal is sufficient to stop progression for the affected work item.  
**Rejected alternatives:**  
- Treating `SECURITY_REFUSAL` as a warning and continuing with other model outputs was rejected because the security controls require a stop.  
- Auto-retrying until a model no longer refuses was rejected because it amounts to bypassing the control.  
- Allowing consensus arbitration to override a refusal was rejected because security hard stops are not subject to majority vote.

## Security hard stops take precedence over consensus outcomes
**Status:** Accepted  
**Context:** ConsensusDevAgent exists to compare, arbitrate, or reconcile outputs across agents/models. However, repository security controls define conditions that must halt progress regardless of model agreement or disagreement. This establishes a precedence rule between consensus and security.  
**Decision:** Apply security and gate controls before accepting any consensus result as actionable. If any participating output triggers a mandatory security stop, the subsystem must gate the work even if other outputs would otherwise win arbitration or achieve consensus.  
**Consequences:** Consensus scoring, ranking, or tie-breaking must occur only on admissible outputs. The subsystem must keep security validation separate from preference selection. “Best available” output selection is prohibited when the available set contains a hard-stop security condition for the active task.  
**Rejected alternatives:**  
- Selecting the highest-quality non-refusing output while ignoring the refusing one was rejected because hard-stop conditions override comparative quality.  
- Averaging or weighting refusal against other signals was rejected because security controls are categorical, not probabilistic.  
- Deferring security evaluation until after consensus was rejected because unsafe outputs could influence downstream decisions.

## Untrusted review content must remain explicitly labeled and non-authoritative
**Status:** Accepted  
**Context:** Repository security guidance states that PR review comments are untrusted and must be labeled in prompts. ConsensusDevAgent will likely ingest reviewer comments, generated review text, and external critique during review and arbitration. Without explicit treatment, prompt injection or authority confusion could occur.  
**Decision:** Preserve untrusted provenance on reviewer-supplied or externally sourced review text, including explicit labeling such as `[UNTRUSTED REVIEWER COMMENT]`, and never treat such content as authoritative instructions. Use it only as evidence to evaluate, not as a command to execute.  
**Consequences:** ConsensusDevAgent must carry provenance metadata through collection, prompting, and audit logs. Review comments may influence investigation or re-evaluation, but they cannot directly alter stage flow, security posture, or file operations. Prompt construction must distinguish trusted system/process instructions from untrusted content.  
**Rejected alternatives:**  
- Merging reviewer comments into trusted prompts without labels was rejected because it increases injection risk.  
- Ignoring reviewer comments entirely was rejected because they are useful evidence during review.  
- Treating highly rated or internal reviewer comments as implicitly trusted was rejected because trust must derive from channel and policy, not sentiment or reputation alone.

## All file writes initiated by ConsensusDevAgent must pass path validation
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate, patch, or emit artifacts across repository directories; uncontrolled writes could escape repository boundaries or alter protected areas.  
**Decision:** Validate every target path with `path_security.validate_write_path()` before any write, overwrite, patch application, rename, or generated artifact emission performed by ConsensusDevAgent. Abort the operation and gate/escalate when validation fails for a required action.  
**Consequences:** The subsystem must centralize file-writing behind a validated path layer. Direct filesystem writes are prohibited outside that layer. Features that stage diffs, temporary files, or generated outputs must still validate final and intermediate write targets where applicable.  
**Rejected alternatives:**  
- Validating only user-supplied paths was rejected because model-generated paths are also untrusted.  
- Validating only final writes but not temp or patch paths was rejected because intermediate writes can also be exploited.  
- Relying on repository-relative normalization alone was rejected because explicit policy validation is mandated.

## ConsensusDevAgent outputs are subject to the mandatory 3-pass review gate
**Status:** Accepted  
**Context:** The repository build pipeline requires three review passes: correctness, performance, and security. ConsensusDevAgent may produce or choose code and plans, but its outputs are not exempt from the same review contract. Security guidance also explicitly requires generated code to pass security review including bandit.  
**Decision:** Require all code or code-affecting outputs selected, synthesized, or emitted by ConsensusDevAgent to pass the full 3-pass review sequence before merge progression, with security review treated as mandatory and inclusive of required automated checks such as bandit where applicable.  
**Consequences:** Consensus selection is not equivalent to approval. The subsystem must hand off selected outputs into review and must not mark work merge-ready based solely on agreement between agents/models. Failures in any review pass must block progression according to pipeline rules.  
**Rejected alternatives:**  
- Treating agreement between two models as a substitute for review was rejected because the pipeline requires explicit review passes.  
- Running only security review on generated code was rejected because correctness and performance are also required stages.  
- Allowing selective review skipping for small changes was rejected because no such exception is defined in the provided requirements.