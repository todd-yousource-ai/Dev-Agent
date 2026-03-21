# DECISIONS.md

## Repository structure for ConsensusDevAgent artifacts
**Status:** Accepted

**Context:** The subsystem must fit into the repository structure defined for the wider system so that documents remain the source of truth, implementation is discoverable, and build/review automation can locate inputs and outputs consistently.

**Decision:** Place ConsensusDevAgent implementation in `src/` and its tests in `tests/`. Store all governing TRDs and PRDs in `forge-docs/`. Store cross-cutting architectural constraints, interfaces, and this file in `forge-standards/`. Do not create an alternate docs tree, parallel standards directory, or subsystem-specific source root outside the prescribed layout.

**Consequences:** Implementation must assume `forge-docs/` is the authoritative input location for TRDs/PRDs. Tooling, prompts, and pipeline code must resolve documentation from that location. Any subsystem-specific documentation that is normative must live under the approved documentation hierarchy rather than ad hoc folders. Code search, CI, and review logic may rely on these fixed paths.

**Rejected alternatives:** Creating a dedicated `ConsensusDevAgent/` backend folder was rejected because it fragments the Python backend and diverges from the repository contract. Storing subsystem design docs beside code was rejected because `forge-docs/` is the declared source of truth. Keeping decision records only in README files was rejected because standards belong in `forge-standards/` and must be separable from onboarding content.

## Forge documents are the source of truth
**Status:** Accepted

**Context:** The pipeline depends on stable, auditable governing documents. The repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and should be read before building.

**Decision:** Treat documents in `forge-docs/` as the sole normative source for subsystem requirements and sequencing. Require ConsensusDevAgent to read and use relevant TRDs/PRDs before planning, generation, or gate evaluation. Do not treat code comments, chat state, or README summaries as substitutes for missing or conflicting document requirements.

**Consequences:** Planning and execution logic must resolve requirements from `forge-docs/` first. If implementation intent conflicts with governing documents, the subsystem must defer to the documents and surface the conflict rather than improvising. Cached interpretations must be considered derived data and invalidated when source documents change.

**Rejected alternatives:** Using prompts or agent memory as the primary requirement source was rejected because it is not auditable or stable. Allowing README excerpts to override TRDs was rejected because README material is descriptive, not governing. Inferring requirements directly from existing code when docs are absent or ambiguous was rejected because it would entrench drift rather than preserve the documented architecture.

## Build pipeline stages are fixed and sequential
**Status:** Accepted

**Context:** The system defines a seven-stage build pipeline triggered by `/prd start <intent>`, with explicit stage purposes spanning scoping, planning, generation, review, and merge. ConsensusDevAgent must conform to these stage contracts.

**Decision:** Implement ConsensusDevAgent to operate within the fixed sequential pipeline: Stage 1 Scope, Stage 2 PRD Plan, Stage 3 PRD Gen, Stage 4 PR Plan, Stage 5 Code Gen, Stage 6 3-Pass Review, Stage 7 Merge. Do not skip, reorder, or collapse stages in normal execution. Enforce stage boundaries and required outputs before advancing.

**Consequences:** Internal state machines, audit logging, and operator UX must map to these seven stages. Inputs and outputs for a later stage must be unavailable until earlier stages complete successfully or gate. Review cannot be fused into generation, and merge cannot proceed before 3-pass review completion. Recovery logic must resume at the current stage rather than inventing alternate flows.

**Rejected alternatives:** A simplified single-pass pipeline was rejected because it removes documented controls and auditability. Allowing dynamic stage reordering was rejected because it breaks stage contracts and makes review semantics ambiguous. Combining PRD/PR planning into one stage was rejected because the system explicitly separates requirement decomposition from implementation decomposition.

## Gate decisions are irreversible
**Status:** Accepted

**Context:** The requirements explicitly state “No undo on gate decisions” and repeat that gate outcomes must not be reversed automatically. This is especially important for safety, review, and audit integrity.

**Decision:** Treat every gate decision made by ConsensusDevAgent as terminal for that execution path. Do not provide an undo, auto-bypass, silent retry past the gate, or retroactive state mutation that converts a gated result into success. Require a new explicit operator-initiated run or follow-on action to proceed after a gate.

**Consequences:** State storage and APIs must represent gates as immutable terminal records. UX must not expose “undo gate” or equivalent semantics. Retry logic must start a new attempt with a new audit trail entry rather than mutating the old decision. Any downstream automation must stop when a gate is recorded.

**Rejected alternatives:** Supporting operator undo of a gate was rejected because the requirements explicitly forbid undo and because it compromises audit integrity. Automatically reopening a gated stage after minor edits was rejected because it effectively bypasses the terminal nature of the decision. Soft gates that allow execution to continue with warnings were rejected where a gate is defined, because the contract requires stopping.

## SECURITY_REFUSAL output is a hard stop
**Status:** Accepted

**Context:** Mandatory security controls require SECURITY_REFUSAL rules in generation prompts, and explicitly state that SECURITY_REFUSAL in output must stop the PR, gate, and log, with no auto-bypass.

**Decision:** When ConsensusDevAgent encounters `SECURITY_REFUSAL` in model output, immediately stop the active PR flow, record a gate, and write an audit log entry. Never auto-bypass, suppress, reinterpret, or continue generation/review past this event.

**Consequences:** Model adapters, parsers, and orchestration layers must inspect outputs for SECURITY_REFUSAL before any downstream action. Partial artifacts from the same step must not be applied after a refusal is detected. Operator intervention must occur through a new explicit workflow, not through in-place continuation. Tests must cover refusal detection and hard-stop behavior.

**Rejected alternatives:** Treating SECURITY_REFUSAL as advisory text was rejected because security controls define it as a stop condition. Automatically retrying another model without gating was rejected because it would create an implicit bypass. Stripping the token from output and continuing was rejected because it destroys the security signal and audit trail.

## Security review is mandatory in the 3-pass review stage
**Status:** Accepted

**Context:** The build pipeline defines Stage 6 as a 3-pass review: correctness, performance, then security. Security controls further require generated code to pass security review including bandit.

**Decision:** Require ConsensusDevAgent to execute all three review passes in order during Stage 6, with the security pass always included and enforced before merge eligibility. Do not mark review complete if the security pass is skipped, deferred, or downgraded.

**Consequences:** Stage 6 completion criteria must include explicit success outcomes for correctness, performance, and security. Merge gating must depend on all three passes. The subsystem must integrate security tooling such as bandit as part of pass execution or pass evidence collection. Failures in any pass must block advancement.

**Rejected alternatives:** Running only correctness and performance by default was rejected because the pipeline defines a 3-pass review and security controls are mandatory. Allowing security review only on high-risk changes was rejected because generated code always requires the security pass. Parallel unordered passes were rejected because the documented stage names imply a defined review structure and ordered audit trail.

## Untrusted reviewer content must remain explicitly labeled
**Status:** Accepted

**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompt contexts. This prevents accidental elevation of untrusted text into authoritative instruction.

**Decision:** Preserve and inject external PR review comments into model prompts only with the exact untrusted labeling semantics required by the security controls. Do not normalize such comments into first-party instructions, system guidance, or unlabeled context.

**Consequences:** Prompt-construction code must track provenance for reviewer comments and apply the required label consistently. Reviewer text cannot be merged into trusted planning context without explicit operator or system mediation. Audit records should preserve that the content was untrusted. Prompt templates must reserve a distinct section for these comments.

**Rejected alternatives:** Including reviewer comments verbatim without labels was rejected because it enables prompt injection and violates the security control. Omitting reviewer comments entirely was rejected because they are useful inputs when properly scoped. Rewriting reviewer comments into summarized trusted instructions was rejected because it obscures provenance and can accidentally endorse malicious content.

## Flagged chunks used in generation require operator gating
**Status:** Accepted

**Context:** Security controls state that when a flagged chunk is used in generation, a gate card must be presented to the operator before proceeding.

**Decision:** If ConsensusDevAgent intends to use flagged content as generation input, it must stop and present an operator gate before continuing. Do not silently include flagged chunks in prompts or proceed based on inferred acceptance.

**Consequences:** Retrieval and prompt assembly must propagate flag metadata into the orchestration layer. The subsystem must be able to block generation pending operator acknowledgment or decision. Audit logs must record the flagged content event and resulting gate. Automation must not treat flagged content as ordinary context.

**Rejected alternatives:** Automatically excluding all flagged chunks was rejected because some flagged content may still be intentionally reviewed and used under operator control. Automatically including flagged chunks with a warning was rejected because the requirement calls for gating before proceeding. Clearing flags during preprocessing was rejected because it destroys the control signal needed for enforcement.

## Validate every write path before file output
**Status:** Accepted

**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent will generate or modify artifacts and therefore must enforce this universally.

**Decision:** Call `path_security.validate_write_path()` on every filesystem destination before any create, overwrite, append, rename, or move operation performed by ConsensusDevAgent. Do not rely on caller discipline or partial coverage.

**Consequences:** All file-writing code paths must funnel through a shared validated write abstraction or equivalent enforcement point. Direct writes that bypass validation are non-compliant. Refactors must preserve validation coverage for temporary files, generated code, logs, and document outputs. Tests must verify that invalid paths are rejected before writes occur.

**Rejected alternatives:** Validating only user-supplied paths was rejected because generated and derived paths can also be unsafe. Performing validation only at high-level entry points was rejected because nested helpers can introduce new write targets. Relying on OS sandboxing alone was rejected because the requirement explicitly mandates path validation and sandboxing does not replace application-layer policy.