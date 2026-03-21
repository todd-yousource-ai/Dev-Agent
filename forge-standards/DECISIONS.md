# DECISIONS.md

## ConsensusDevAgent documentation source of truth
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with a strict separation between implementation, standards, and requirements artifacts. The TRDs and PRDs define behavior before implementation, and the agent must not invent structure outside that contract.  
**Decision:** Treat `forge-docs/` as the authoritative source for all TRDs and PRDs, and require ConsensusDevAgent to read applicable documents there before planning, generation, review, or gate decisions.  
**Consequences:** Implementation must load and reference documents from `forge-docs/` before acting. Behavior cannot be derived primarily from code comments, ad hoc prompts, or unstored operator memory when a governing TRD/PRD exists. Documentation lookup and traceability are mandatory parts of the subsystem.  
**Rejected alternatives:**  
- Using repository code as the primary source of truth: rejected because the TRDs explicitly define the build and coordination model.  
- Allowing prompts or chat context to override `forge-docs/`: rejected because it breaks reproducibility and auditability.  
- Duplicating requirements into subsystem-local files: rejected because it creates drift from the canonical docs set.

## ConsensusDevAgent is constrained by the staged build pipeline
**Status:** Accepted  
**Context:** The repository defines a fixed build pipeline with ordered stages from scope through review. ConsensusDevAgent participates in this flow and must not collapse, skip, or reorder stages opportunistically.  
**Decision:** Implement ConsensusDevAgent as a stage-constrained subsystem that respects the repository pipeline order: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, and 3-Pass Review, with gate behavior integrated according to stage contracts.  
**Consequences:** The subsystem must expose state and outputs aligned to pipeline stages. It may not perform code generation before planning is complete, and may not treat review as optional or post hoc. Audit records must preserve stage lineage.  
**Rejected alternatives:**  
- A freeform autonomous loop that plans, writes, and merges continuously: rejected because it violates explicit stage contracts.  
- A simplified two-stage design of “generate then review”: rejected because it omits required decomposition and governance points.  
- Dynamic stage reordering based on model confidence: rejected because deterministic process is required for traceability.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The TRDs and repository guidance explicitly state that there is no undo on gate decisions. This must be documented unambiguously because it affects operator expectations, audit design, and recovery flows.  
**Decision:** Treat every gate decision made by ConsensusDevAgent as irreversible within the active workflow; do not provide an automatic or in-band “undo,” rollback, or silent reopening of a closed gate.  
**Consequences:** Once a gate is tripped or a stop condition is recorded, the subsystem must require a new explicit workflow action rather than resuming as if the gate never happened. State machines, UI affordances, logs, and APIs must not imply reversible gates. Recovery must occur through a new decision or restart path with fresh audit entries.  
**Rejected alternatives:**  
- Allowing operators to click “undo last gate”: rejected because it contradicts the explicit repository rule.  
- Automatically reopening a gate after transient errors clear: rejected because it weakens auditability and operator control.  
- Soft gates that can be bypassed implicitly by retry: rejected because they are indistinguishable from non-gates in practice.

## SECURITY_REFUSAL is a hard stop
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` handling in LLM output. The documented behavior is explicit: stop PR, gate, log, and never auto-bypass. ConsensusDevAgent must enforce this consistently across generation and review.  
**Decision:** On any `SECURITY_REFUSAL` emitted by a participating model or detected in generation output, immediately stop the current PR flow, create a gate, write an audit log entry, and prohibit automatic bypass or continuation.  
**Consequences:** The subsystem must scan relevant model outputs for `SECURITY_REFUSAL`, propagate the event into workflow state, and prevent downstream stages from continuing. Manual intervention may inspect the event, but the subsystem itself must not suppress, reinterpret, or downgrade it.  
**Rejected alternatives:**  
- Treating `SECURITY_REFUSAL` as a warning while continuing with fallback models: rejected because the controls specify stop-and-gate behavior.  
- Auto-retrying with prompt modifications until refusal disappears: rejected because it effectively bypasses the security stop.  
- Logging only without gating: rejected because it fails the mandatory control.

## Operator gate card is required when flagged chunks are used
**Status:** Accepted  
**Context:** Security controls require operator visibility whenever flagged content is used in generation. This is a human-governance checkpoint, not a best-effort notification.  
**Decision:** Present a gate card to the operator before proceeding whenever generation uses a flagged chunk, and block continuation until the gate is resolved through the defined workflow.  
**Consequences:** ConsensusDevAgent must track provenance of generation inputs, detect flagged chunk usage, and surface a formal gate artifact rather than a transient log line. The gate must occur before downstream progression.  
**Rejected alternatives:**  
- Showing a passive warning banner while continuing automatically: rejected because the requirement is to gate before proceeding.  
- Logging flagged chunk usage for later review only: rejected because it removes the required operator checkpoint.  
- Blocking all flagged chunks outright with no operator gate: rejected because the documented control is conditional gating, not unconditional prohibition.

## Untrusted PR review comments must remain explicitly labeled
**Status:** Accepted  
**Context:** Security controls state that PR review comments from untrusted reviewers must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. Prompt hygiene is a core defense against prompt injection and instruction laundering.  
**Decision:** Preserve and inject the exact label `[UNTRUSTED REVIEWER COMMENT]` for untrusted PR review comments in all ConsensusDevAgent prompt construction paths that include such content.  
**Consequences:** Prompt builders must carry trust metadata for review comments and must not strip, paraphrase, or normalize away the required label. Downstream model orchestration must distinguish trusted system instructions from untrusted review text.  
**Rejected alternatives:**  
- Merging all review comments into a single unlabeled prompt section: rejected because it obscures trust boundaries.  
- Using a different warning label format: rejected because the requirement specifies the exact marker.  
- Excluding untrusted comments entirely: rejected because the system still needs to consider them, but safely.

## Security review is mandatory in the 3-pass review stage
**Status:** Accepted  
**Context:** Generated code must pass three review passes: correctness, performance, and security. Security review is not optional and explicitly includes `bandit`. ConsensusDevAgent must treat this as a release gate, not advice.  
**Decision:** Require all generated code handled by ConsensusDevAgent to pass the full 3-pass review sequence, with security review including `bandit`, before the PR can advance or complete.  
**Consequences:** Review orchestration must execute all three passes in order or under a documented equivalent contract that preserves all three outcomes. A PR may not be considered complete after correctness-only or performance-only validation. Tooling integration for `bandit` is mandatory where Python code is affected.  
**Rejected alternatives:**  
- Skipping security review for low-risk or documentation-heavy changes: rejected because the control applies to all generated code.  
- Combining all three passes into one undifferentiated review result: rejected because pass-specific accountability is required.  
- Running `bandit` only on demand: rejected because it is explicitly part of mandatory security review.

## Path validation is mandatory before every write
**Status:** Accepted  
**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate or modify files, so write safety must be enforced centrally and uniformly.  
**Decision:** Validate every file path with `path_security.validate_write_path()` immediately before any filesystem write initiated by ConsensusDevAgent, without exception.  
**Consequences:** All write APIs, file generation routines, patch application paths, and temporary-output promotion paths must route through a validated write boundary. Direct writes, convenience shortcuts, and “trusted internal path” bypasses are disallowed.  
**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated and computed paths can also be unsafe.  
- Validating once at session start: rejected because path safety must be checked per write operation.  
- Relying on repository-relative normalization alone: rejected because the mandated control is an explicit validation call.

## Consensus decisions must produce durable audit trail entries
**Status:** Accepted  
**Context:** The pipeline and security controls both emphasize auditability, including gate events and stage outcomes. ConsensusDevAgent makes arbitration and progression decisions that must be reconstructible after the fact.  
**Decision:** Emit durable audit trail records for stage transitions, arbitration outcomes, gate events, security refusals, and operator-required checkpoints produced by ConsensusDevAgent.  
**Consequences:** The subsystem must not rely solely on ephemeral console output or in-memory state for decision history. Audit records must be sufficient to explain why progress occurred, why it stopped, and which inputs or model outcomes contributed.  
**Rejected alternatives:**  
- Logging only errors: rejected because normal decision progression also needs traceability.  
- Storing audit data only in volatile process memory: rejected because it is not durable or reviewable.  
- Recording only final outcomes: rejected because intermediate gates and consensus rationale matter.

## ConsensusDevAgent must not auto-bypass mandatory controls
**Status:** Accepted  
**Context:** Multiple repository rules prohibit implicit bypass, especially for gate decisions and security refusal handling. A consensus subsystem is especially prone to “fallback” behavior unless constrained explicitly.  
**Decision:** Do not implement automatic bypass, silent downgrade, or fallback continuation for mandatory controls, including gates, `SECURITY_REFUSAL`, flagged-chunk gate cards, required labeling of untrusted comments, required review passes, and write-path validation.  
**Consequences:** Recovery paths must be explicit, auditable, and operator-mediated where required. Reliability features such as retry, alternate model selection, or degraded mode must stop short of violating mandatory controls.  
**Rejected alternatives:**  
- Auto-fallback to another model after a control-triggered stop: rejected because it can become an implicit bypass.  
- Hidden “best effort” mode for noninteractive runs: rejected because mandatory controls apply regardless of execution context.  
- Config flags to disable controls in development: rejected because they create implementation paths that contradict accepted decisions.