# DECISIONS.md

## [ConsensusDevAgent repository boundaries and document source of truth]
**Status:** Accepted  
**Context:** The subsystem must operate within a repository layout that separates specifications, standards, implementation, app shell, and tests. The TRDs explicitly define where source documents live and the README defines the canonical top-level layout. ConsensusDevAgent depends on these boundaries to locate inputs, produce outputs, and avoid writing artifacts into the wrong areas.  
**Decision:** Treat `forge-docs/` as the exclusive source of truth for TRDs and PRDs, and constrain ConsensusDevAgent implementation to the established repository layout:
- `forge-docs/` for TRDs and PRDs only
- `forge-standards/` for architecture and policy documents, including this file
- `src/` for Python backend implementation
- `ForgeAgent/` for the Swift/SwiftUI macOS shell
- `ForgeAgentTests/` for XCTest suites
- `tests/` for Python tests
- `.github/workflows/` for CI workflows

ConsensusDevAgent must read planning and specification inputs from `forge-docs/` before acting, and must not redefine, mirror, or relocate the canonical document store inside subsystem-specific directories.  
**Consequences:** Implementation must use repository-aware path handling and assume specs are externalized from runtime code. The subsystem cannot invent alternate storage locations for PRDs/TRDs, cannot treat generated summaries as source of truth, and must preserve compatibility with other subsystems that rely on the same layout. Path writes must target only approved locations and remain compatible with centralized path validation controls.  
**Rejected alternatives:**  
- Storing subsystem-local copies of TRDs/PRDs under `src/` or a hidden state directory: rejected because it creates divergence from the canonical document store.  
- Embedding TRD content directly into code or prompts as the primary source: rejected because it prevents document-driven updates and breaks repository governance.  
- Allowing flexible per-agent repository layouts: rejected because cross-agent coordination requires deterministic paths.

## [ConsensusDevAgent participates in the fixed build pipeline stages]
**Status:** Accepted  
**Context:** The build pipeline is defined as a staged workflow from scope confirmation through PR merge. ConsensusDevAgent must fit into this sequence rather than introducing an alternate lifecycle. The subsystem’s consensus and implementation behavior is constrained by upstream planning stages and downstream review and merge gates.  
**Decision:** Implement ConsensusDevAgent as a participant in the fixed pipeline stages:
1. Scope
2. PRD Plan
3. PRD Gen
4. PR Plan
5. Code Gen
6. 3-Pass Review
7. Tests
8. Human Gate
9. Merge

ConsensusDevAgent must consume artifacts produced by earlier stages, produce artifacts expected by later stages, and must not skip, reorder, collapse, or auto-complete mandatory gates.  
**Consequences:** The subsystem cannot be designed as a standalone coding loop. Consensus resolution must align with stage contracts, especially around Code Gen, Review, Tests, and Human Gate. Any state model, logging, or orchestration must map cleanly onto this pipeline so auditability and operator visibility are preserved.  
**Rejected alternatives:**  
- A simplified subsystem-specific pipeline that combines generation, review, and test execution: rejected because it would violate the documented core loop and weaken auditability.  
- Allowing the subsystem to decide dynamically which stages are necessary: rejected because mandatory controls must remain uniform across work items.  
- Making consensus generation an out-of-band side process with no stage identity: rejected because downstream gating depends on traceable stage outputs.

## [No undo on gate decisions]
**Status:** Accepted  
**Context:** The TRDs explicitly require that gate decisions are irreversible. This rule is security- and governance-relevant because gate outcomes must remain part of the audit trail and must not be silently reversed by automation after a stop condition or refusal has been reached.  
**Decision:** Enforce gate finality. Once ConsensusDevAgent records a gate decision, including stop, refusal, escalation, or operator gate requirement, it must not automatically undo, clear, downgrade, or bypass that decision. Any subsequent progress must occur through a new explicit operator-driven action or a new pipeline run, not by mutating the prior gate outcome.  
**Consequences:** State transitions must be append-only for gate outcomes. Recovery flows must create new events or new runs rather than editing prior decisions. The subsystem must be designed so retries, resumptions, and re-plans do not invalidate historical gate records. UI and logs must reflect that a gate decision remains part of permanent history.  
**Rejected alternatives:**  
- Allowing automatic reopening after transient failures or model retries: rejected because it would create ambiguous audit history and undermine gate integrity.  
- Permitting a later model consensus result to overwrite an earlier stop decision: rejected because safety and operator control take precedence over convenience.  
- Supporting an “undo” command for operators that mutates history: rejected because the requirement is explicit that there is no undo on gate decisions.

## [SECURITY_REFUSAL is a hard stop]
**Status:** Accepted  
**Context:** Security controls require `SECURITY_REFUSAL` handling in generation prompts and outputs. If such a refusal appears in LLM output, the system must stop the PR, gate to the operator, and log the event. ConsensusDevAgent must not interpret refusal as a soft signal that can be arbitrated away by another model or retried automatically.  
**Decision:** Treat any `SECURITY_REFUSAL` emitted during ConsensusDevAgent operation as a hard-stop terminal event for the active PR flow. The subsystem must:
- stop further automated processing for that PR
- create a gate card or equivalent operator-facing escalation
- log the refusal in the audit trail
- never auto-bypass, suppress, relabel, or resolve the refusal through consensus arbitration alone

If multiple models are involved, one model’s `SECURITY_REFUSAL` is sufficient to trigger the stop.  
**Consequences:** Consensus logic is subordinate to security refusal handling. Arbitration cannot “outvote” a refusal. Retry loops must short-circuit when a refusal occurs. The subsystem must surface enough context for operator review while preserving the refusal as a first-class audit event.  
**Rejected alternatives:**  
- Requiring both models to refuse before stopping: rejected because the security rule requires refusal to be terminal, not majority-based.  
- Treating refusal as a review warning while continuing execution: rejected because the documented control says to stop the PR and gate.  
- Automatically rerouting the task to another model after refusal: rejected because that would be an implicit bypass.

## [Mandatory security controls on generated writes and review flow]
**Status:** Accepted  
**Context:** The TRDs define mandatory controls for generated code and review handling, including path validation on every write, explicit treatment of untrusted review comments, and mandatory security review participation. ConsensusDevAgent will generate or coordinate code changes and therefore must implement these controls directly rather than assuming another layer will do so.  
**Decision:** Enforce the following controls in ConsensusDevAgent:
- Validate every file write path with `path_security.validate_write_path()` before writing.
- Treat labeled PR review comments as untrusted input and preserve the `[UNTRUSTED REVIEWER COMMENT]` designation in prompts and processing.
- Ensure generated code proceeds through the full 3-pass review, including the security pass.
- Ensure security tooling requirements such as bandit remain part of the review/test path where applicable.
- If flagged content is used in generation, require operator gating before proceeding.

These controls are mandatory and may not be disabled per task, per branch, or per model.  
**Consequences:** File I/O APIs in the subsystem must be wrapped or centralized so path validation cannot be skipped. Prompt-construction logic must carry trust labels through to models. ConsensusDevAgent cannot directly merge or finalize generated changes without the mandated review path. Security-sensitive provenance must be preserved end to end.  
**Rejected alternatives:**  
- Relying on developers to manually validate paths: rejected because the control is mandatory on every write.  
- Sanitizing away untrusted-review labels before prompt submission: rejected because provenance must remain visible to the model and audit trail.  
- Making the security pass optional for low-risk PRs: rejected because the requirements state generated code must pass security review.

## [Consensus outcomes must integrate with human gate rather than replace it]
**Status:** Accepted  
**Context:** The pipeline includes an explicit Human Gate before merge. ConsensusDevAgent may perform arbitration and produce recommendations, but the documented process reserves a human-controlled decision point. This is especially important in cases involving refusals, flagged inputs, and reviewed generated changes.  
**Decision:** Design ConsensusDevAgent to produce structured recommendations, evidence, and consensus outcomes for operator review, but never to replace the Human Gate. The subsystem must surface enough rationale and artifact references for a human to approve, block, or request follow-up, and it must honor operator gating requirements triggered by security conditions.  
**Consequences:** The subsystem must expose inspectable outputs rather than opaque “approved” states. Merge readiness remains advisory until the human gate is satisfied. Automation may prepare, summarize, and validate, but it cannot independently convert consensus into final authorization.  
**Rejected alternatives:**  
- Allowing consensus success to auto-satisfy the Human Gate: rejected because the pipeline explicitly includes a separate human-controlled stage.  
- Restricting operator input to exceptional cases only: rejected because operator review is a normal required gate, not just an error handler.  
- Hiding model disagreement once a winning output is selected: rejected because human reviewers need evidence, not only the final pick.