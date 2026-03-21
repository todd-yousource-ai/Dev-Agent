# DECISIONS.md

## ConsensusDevAgent documentation lives under forge standards and must be derived from TRDs
**Status:** Accepted  
**Context:** The repository structure establishes `forge-docs/` as the source of truth for TRDs and PRDs, and `forge-standards/` as the location for durable implementation constraints such as architecture and decisions. ConsensusDevAgent must be implemented against documented contracts rather than ad hoc behavior.  
**Decision:** Maintain ConsensusDevAgent design decisions in `forge-standards/DECISIONS.md`, and derive those decisions from the TRDs and repository-level standards in `forge-docs/`. Treat TRDs and PRDs in `forge-docs/` as authoritative inputs before implementing or changing the subsystem.  
**Consequences:** ConsensusDevAgent implementation cannot introduce behavior that contradicts the TRDs without updating the source documents first. Developers must read relevant TRDs before modifying orchestration, gating, review, or output behavior. Decision records belong in standards, not mixed into source code or ad hoc notes.  
**Rejected alternatives:** Storing subsystem decisions inside `src/` was rejected because it hides governing constraints from the standards layer. Treating implementation as the source of truth was rejected because the repository explicitly designates `forge-docs/` as authoritative.

## ConsensusDevAgent must operate as a build-pipeline stage executor, not an open-ended agent
**Status:** Accepted  
**Context:** The README defines a fixed build pipeline triggered by `/prd start <intent>` with ordered stages from scope through merge. ConsensusDevAgent exists within that controlled flow and must not bypass stage contracts.  
**Decision:** Implement ConsensusDevAgent as a stage-bound subsystem that participates in the documented pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and downstream gate-controlled progression. Require stage completion criteria before advancing.  
**Consequences:** The subsystem must expose behavior aligned to stage inputs, outputs, and auditability rather than free-form autonomous task execution. It cannot skip review, jump directly to code generation, or merge outside the pipeline. Integration points must preserve stage ordering and handoff semantics.  
**Rejected alternatives:** A general autonomous coding agent was rejected because it would weaken auditability and gate enforcement. A loosely ordered workflow was rejected because TRD-3 and the README define explicit stage progression.

## Gate decisions are immutable and must never support undo
**Status:** Accepted  
**Context:** Multiple source excerpts explicitly state “No undo on gate decisions.” This is a hard control relevant to all gating behavior in ConsensusDevAgent, especially security and review escalation.  
**Decision:** Treat all gate decisions issued by ConsensusDevAgent or consumed by it as immutable. Do not implement undo, rollback, reversal, or silent reopening of a closed gate decision. Any subsequent action must create a new decision event rather than mutate the prior one.  
**Consequences:** Data models, APIs, UI affordances, and operator workflows must not include “undo gate,” “reopen prior gate,” or equivalent semantics. Audit trails must be append-only for gate outcomes. Recovery from an incorrect gate requires a new explicit operator action recorded as a separate event.  
**Rejected alternatives:** Allowing operator undo was rejected because the requirements explicitly forbid it. Soft-delete or mutable gate states were rejected because they undermine auditability and chain-of-custody for decisions.

## SECURITY_REFUSAL is a hard stop that blocks progress and cannot be auto-bypassed
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in generation prompts and specify that SECURITY_REFUSAL in output must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent must respect this as a first-class control path.  
**Decision:** When any model output or generation result contains a SECURITY_REFUSAL condition, immediately stop the affected PR flow, emit a gate event, log the refusal in the audit trail, and require explicit operator handling through the documented gate process. Never auto-retry around the refusal in a way that bypasses the stop condition.  
**Consequences:** ConsensusDevAgent must inspect generation outputs for SECURITY_REFUSAL outcomes and propagate them into gating. Automatic continuation, silent fallback, or hidden suppression of refusal content is prohibited. Telemetry and audit records must preserve the refusal event.  
**Rejected alternatives:** Automatically switching to another model after refusal was rejected because it would be an auto-bypass. Ignoring refusal markers and continuing the pipeline was rejected as a direct violation of mandatory security controls.

## ConsensusDevAgent must preserve security labeling and untrusted-input boundaries
**Status:** Accepted  
**Context:** Security controls require flagged chunks to gate before use in generation and require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. The subsystem coordinates model inputs and therefore must preserve trust boundaries.  
**Decision:** Propagate trust labels on all external or reviewer-supplied inputs through ConsensusDevAgent. Mark untrusted PR review content exactly as required in prompts, and if flagged content is selected for generation context, raise a gate card to the operator before proceeding.  
**Consequences:** Prompt construction, context assembly, and review ingestion must carry metadata about trust level. ConsensusDevAgent cannot flatten trusted and untrusted inputs into an unlabeled prompt. Use of flagged content becomes operator-visible and gate-controlled.  
**Rejected alternatives:** Treating all prompt inputs as equally trusted was rejected because it weakens prompt-injection defenses. Deferring trust labeling to downstream components was rejected because the subsystem itself assembles and routes generation context.

## ConsensusDevAgent must enforce mandatory security checks on generated code paths
**Status:** Accepted  
**Context:** Mandatory controls require `path_security.validate_write_path()` on every file path before write, and generated code must pass security review including bandit. ConsensusDevAgent is responsible for coordinating code generation outputs into repository writes and review stages.  
**Decision:** Validate every proposed write path with `path_security.validate_write_path()` before any file creation or modification initiated by ConsensusDevAgent. Require generated code to pass the documented security review pass, including bandit, before the pipeline may advance.  
**Consequences:** The subsystem cannot directly write arbitrary model-proposed paths. File application logic must be mediated by path validation. Security review is a release gate, not an informational step. Failed security checks must halt advancement and generate auditable outcomes.  
**Rejected alternatives:** Validating only final merged paths was rejected because unsafe intermediate writes remain possible. Treating bandit as optional advisory output was rejected because the security controls define Pass 3 security review as mandatory.

## ConsensusDevAgent must use the documented three-pass review as a required quality gate
**Status:** Accepted  
**Context:** The pipeline defines “3-Pass Review — correctness → performance → security.” ConsensusDevAgent must coordinate outputs that are reviewable and stage-gated in this order.  
**Decision:** Require every generated PR artifact under ConsensusDevAgent control to pass the three review passes in order: correctness first, performance second, security third. Do not collapse, reorder, or omit passes for convenience.  
**Consequences:** Review orchestration APIs and state machines must model distinct pass outcomes. Performance concerns cannot override correctness failures, and security review cannot be skipped after earlier success. Audit logs must identify pass-specific results.  
**Rejected alternatives:** A single combined review pass was rejected because it loses ordered accountability and pass-specific gating. Running security first was rejected because the documented contract specifies the ordered sequence.

## ConsensusDevAgent must support parallel generation with explicit arbitration, not first-result wins
**Status:** Accepted  
**Context:** The build pipeline specifies “parallel generation, arbitration” during Code Gen, and PRD generation indicates dual-model generation where “Claude wins.” ConsensusDevAgent exists to coordinate consensus behavior, so arbitration is core to the subsystem.  
**Decision:** Run configured parallel generation workers where required by the stage contract and resolve outputs through explicit arbitration logic rather than accepting the first completed result. Where a stage contract defines a winner policy, implement that policy exactly.  
**Consequences:** The subsystem must model multiple candidate outputs, comparison, and selection rationale. It cannot optimize for latency by blindly accepting first completion. Arbitration decisions must be inspectable and auditable.  
**Rejected alternatives:** First-result-wins was rejected because it does not constitute consensus or arbitration. Manual-only selection for every generation was rejected because the pipeline explicitly anticipates automated comparative generation behavior.

## ConsensusDevAgent must produce append-only audit records for stage, review, and gate events
**Status:** Accepted  
**Context:** TRD-3 is referenced for full stage contracts, error escalation, and the audit trail schema. Combined with the no-undo gate rule, ConsensusDevAgent requires durable event recording.  
**Decision:** Record ConsensusDevAgent actions as append-only audit events for stage transitions, arbitration outcomes, review pass results, security refusals, escalations, and gate decisions. Never rewrite historical events to reflect later conclusions.  
**Consequences:** Storage and event schemas must support immutable history. Observability, debugging, and compliance analysis rely on event reconstruction rather than mutable status replacement. Derived current state may be materialized separately, but source events remain intact.  
**Rejected alternatives:** Mutable status rows without event history were rejected because they are insufficient for audit reconstruction. Deleting superseded events was rejected because it conflicts with immutable gate and escalation history.

## ConsensusDevAgent must escalate errors through gate-controlled workflows rather than silent recovery
**Status:** Accepted  
**Context:** TRD-3 references error escalation alongside stage contracts and audit trails. Security and gate rules further require explicit stops for certain failure modes.  
**Decision:** Escalate stage failures, arbitration failures, refusal events, and review-blocking issues through explicit gate-controlled error workflows. Do not silently swallow errors, downgrade blocking failures to warnings, or continue on partial state without an auditable decision.  
**Consequences:** Error handling must differentiate retryable operational failures from gate-worthy decision failures, but both must be recorded. Operator-visible escalation paths are required for blocked progress. Automatic recovery may be used only when it does not violate gate contracts or conceal failure history.  
**Rejected alternatives:** Best-effort continuation after blocking errors was rejected because it undermines pipeline guarantees. Silent retries with no audit trace were rejected because they break accountability and diagnosability.