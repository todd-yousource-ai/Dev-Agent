# DECISIONS.md

## [ConsensusDevAgent repository placement and document authority]
**Status:** Accepted  
**Context:** The subsystem must fit the repository contract used by all agentic workflows. The TRDs and README define a fixed layout where implementation lives under `src/`, standards live under `forge-standards/`, and all TRDs/PRDs live under `forge-docs/`. ConsensusDevAgent must not create competing sources of truth for design inputs.  
**Decision:** Implement ConsensusDevAgent backend code under `src/` and treat `forge-docs/` as the authoritative source for TRDs and PRDs. Store subsystem design constraints in `forge-standards/DECISIONS.md` and do not duplicate normative requirements in ad hoc locations.  
**Consequences:** ConsensusDevAgent implementations must read from repository-standard document locations and must not rely on hidden prompts, scattered specs, or generated local copies as authority. Any tooling, loaders, or planners in the subsystem must assume `forge-docs/` is canonical for product and technical requirements.  
**Rejected alternatives:**  
- Placing ConsensusDevAgent in a dedicated top-level folder outside `src/`: rejected because it breaks the declared repository layout and increases integration friction.  
- Treating generated summaries or cached parses as authoritative instead of source docs: rejected because it risks divergence from the approved TRDs/PRDs.  
- Keeping subsystem decisions only in code comments or README sections: rejected because ADR-style decisions must live in standards documentation.

## [Gate decisions are immutable and have no undo path]
**Status:** Accepted  
**Context:** The build pipeline and security controls explicitly require that gate outcomes are final. The TRD excerpts state "No undo on gate decisions" and require explicit documentation of this behavior. This is especially critical when security refusal or review gating occurs.  
**Decision:** Treat every gate decision emitted by ConsensusDevAgent or consumed from the pipeline as immutable. Do not implement undo, rollback, silent re-open, or automatic bypass semantics for gate outcomes. Any further progress must occur through a new explicit operator action or a new pipeline run, not by reversing the prior gate record.  
**Consequences:** The subsystem must model gates as append-only audit events rather than mutable state transitions that can be reversed in place. UI, APIs, and internal orchestration must avoid "undo gate" affordances. Recovery flows must create new decisions, retries, or superseding runs while preserving the original gate outcome in the audit trail.  
**Rejected alternatives:**  
- Allowing operators to undo a gate for convenience: rejected because it violates explicit TRD security and auditability requirements.  
- Auto-clearing gates after retries succeed: rejected because it destroys the integrity of the historical decision trail.  
- Mutating the original gate record from blocked to approved: rejected because it makes post hoc review and forensic analysis unreliable.

## [ConsensusDevAgent participates in the staged build pipeline, not a custom flow]
**Status:** Accepted  
**Context:** The README defines a seven-stage pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and Merge. ConsensusDevAgent must operate within this contract rather than inventing a subsystem-specific lifecycle.  
**Decision:** Integrate ConsensusDevAgent behavior into the repository’s defined pipeline stages and honor stage boundaries, contracts, and escalation points from TRD-3. Do not introduce a parallel lifecycle that bypasses or collapses required stages.  
**Consequences:** ConsensusDevAgent orchestration, state tracking, and outputs must be stage-aware. Inputs and outputs must align with the upstream and downstream contracts of the standard pipeline. Security, review, and merge behavior must occur at their designated stages rather than being embedded informally in generation logic alone.  
**Rejected alternatives:**  
- Building a standalone consensus loop that directly generates and merges code: rejected because it bypasses required planning and review stages.  
- Combining PR planning, code generation, and review into one subsystem operation: rejected because it weakens traceability and stage-specific controls.  
- Allowing subsystem-specific shortcuts for “small changes”: rejected because the pipeline contract applies uniformly unless changed by a higher-level standard.

## [Security refusal is a hard stop]
**Status:** Accepted  
**Context:** Mandatory security controls require `SECURITY_REFUSAL` rules in generation prompts and specify that if `SECURITY_REFUSAL` appears in LLM output, the system must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent is directly exposed to model outputs and therefore must enforce this invariant.  
**Decision:** Detect `SECURITY_REFUSAL` in any model output handled by ConsensusDevAgent and treat it as an immediate hard-stop condition: stop the current PR flow, create a gate, log the event, and prohibit automatic continuation or bypass.  
**Consequences:** ConsensusDevAgent must include explicit parsing and enforcement paths for security refusal signals. Arbitration, retries, or fallback models must not silently continue past a refusal in the same PR flow. Operators may inspect and initiate a new action, but the refused flow remains stopped and auditable.  
**Rejected alternatives:**  
- Ignoring refusal text if the rest of the output looks usable: rejected because it violates mandatory security controls.  
- Automatically retrying with another model and proceeding if that model does not refuse: rejected because the refusal itself is a gate-triggering event.  
- Downgrading refusal to a warning: rejected because the TRD language requires stop, gate, and log behavior.

## [Security review remains mandatory even after consensus]
**Status:** Accepted  
**Context:** Consensus among generation agents does not replace the required review pipeline. Mandatory controls require all generated code to pass Pass 3 security review, including bandit, and the build pipeline specifies a 3-pass review sequence: correctness, performance, security.  
**Decision:** Do not treat model consensus as approval to skip review. Require every ConsensusDevAgent-generated code artifact to pass the full 3-pass review pipeline, with security review mandatory before merge.  
**Consequences:** Consensus output is only a candidate implementation, not a merge-ready artifact. The subsystem must produce outputs consumable by review stages and must not mark changes as approved solely because multiple agents agreed. Performance and correctness checks remain required, and security review is non-optional.  
**Rejected alternatives:**  
- Using consensus as a substitute for review: rejected because agreement between models is not a security or correctness guarantee.  
- Running only security review on consensual outputs: rejected because the standard pipeline requires correctness and performance passes too.  
- Skipping bandit when human reviewers are present: rejected because the TRD makes automated security review part of the mandatory control set.

## [Untrusted external text must remain labeled and non-authoritative]
**Status:** Accepted  
**Context:** The security controls distinguish trusted instructions from untrusted inputs such as PR review comments and flagged chunks. PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]`, and flagged content requires gating before use in generation. ConsensusDevAgent aggregates and arbitrates textual inputs, making trust handling a core design concern.  
**Decision:** Preserve trust boundaries inside ConsensusDevAgent. Label untrusted reviewer or external text as untrusted in prompts and internal representations, and do not elevate such content to authoritative instructions without the required gate or operator approval.  
**Consequences:** Prompt assembly, arbitration context, and explanation outputs must carry trust metadata. The subsystem must not let untrusted comments override repository standards, TRDs, PRDs, or system-level instructions. When flagged content is used in generation, the required gate to the operator must occur before proceeding.  
**Rejected alternatives:**  
- Treating all textual inputs as equivalent once normalized: rejected because it enables prompt injection and instruction confusion.  
- Stripping untrusted labels before model invocation for cleaner prompts: rejected because the labels are a required security control.  
- Allowing reviewer comments to directly modify execution behavior: rejected because reviewer text is explicitly non-authoritative unless elevated through the proper process.

## [File writes must be path-validated before persistence]
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate, update, or materialize code and documentation artifacts, so write-path enforcement must be systemic.  
**Decision:** Validate every filesystem write path produced or used by ConsensusDevAgent with `path_security.validate_write_path()` before any write occurs. Do not implement alternate write paths that bypass this validation.  
**Consequences:** All file emission, patch application, artifact staging, and temporary output flows in the subsystem must route through path validation. This constrains utility design, requiring centralized write helpers or equivalent enforcement points. It also limits the subsystem’s ability to write outside approved repository locations.  
**Rejected alternatives:**  
- Validating only final destination paths and not temporary files: rejected because temporary-file bypasses can still become write vulnerabilities.  
- Relying on caller-side validation: rejected because the subsystem itself must enforce mandatory controls.  
- Using allowlists without calling the shared validation function: rejected because the TRD names the required enforcement mechanism explicitly.

## [Consensus results must be auditable as append-only pipeline artifacts]
**Status:** Accepted  
**Context:** The pipeline references full stage contracts, error escalation, and an audit trail schema. Because ConsensusDevAgent synthesizes multiple model outputs into a single result, its decisions must be reconstructable for review, escalation, and forensic analysis. This is especially important given immutable gate decisions.  
**Decision:** Record ConsensusDevAgent outputs, arbitration outcomes, refusals, and gate-triggering events as append-only audit artifacts aligned to the pipeline’s audit trail model. Do not overwrite prior deliberation records in place.  
**Consequences:** The subsystem must retain enough metadata to explain which candidates were considered, what outcome was selected, and why a gate or stop occurred. Storage and APIs must support historical inspection. Any correction or retry must be captured as a new record linked to prior records rather than mutation of history.  
**Rejected alternatives:**  
- Storing only the final chosen output: rejected because it is insufficient for audit and escalation.  
- Rewriting the audit record to reflect the latest state only: rejected because it conflicts with append-only gate and review history.  
- Keeping detailed deliberation only in transient logs: rejected because operational logs alone are not a durable audit artifact.

## [Claude-defined winner logic from TRD stages must not be generalized into unrestricted model preference]
**Status:** Accepted  
**Context:** The repository pipeline includes a stage-specific rule in PRD generation where "both models, Claude wins." That rule exists in a particular stage contract and should not be expanded into a blanket subsystem rule without explicit authorization. ConsensusDevAgent must respect stage-specific policy instead of embedding hidden universal model preferences.  
**Decision:** Apply model precedence only where an explicit stage contract defines it. Do not encode a global "one model always wins" rule inside ConsensusDevAgent outside the stages that require it.  
**Consequences:** ConsensusDevAgent must support stage-sensitive arbitration policy. In stages without an explicit winner rule, the subsystem must use the defined consensus/arbitration mechanism rather than hard-coded vendor preference. This preserves flexibility and alignment with TRD contracts.  
**Rejected alternatives:**  
- Making Claude the universal winner for all consensus decisions: rejected because the source requirement is stage-specific, not system-wide.  
- Making one model the default winner unless overridden: rejected because it hides policy in implementation and weakens contract clarity.  
- Ignoring explicit stage-specific winner rules to keep arbitration uniform: rejected because the pipeline contract is authoritative where it specifies precedence.