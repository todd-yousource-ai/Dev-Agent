# DECISIONS.md

## [ConsensusDevAgent documentation source of truth]
**Status:** Accepted

**Context:** The subsystem is implemented inside a repository where requirements and design contracts are defined in TRDs and PRDs. The repository structure explicitly states that all TRDs and PRDs live under `forge-docs/` and must be read before building. ConsensusDevAgent must operate against the same authoritative artifacts as the rest of the system.

**Decision:** Treat `forge-docs/` as the sole source of truth for TRDs and PRDs, and require ConsensusDevAgent implementation and behavior to conform to documents stored there before any code-generation or orchestration logic is executed.

**Consequences:** ConsensusDevAgent must resolve planning, gating, and implementation behavior from repository documents rather than inferred behavior or code-local assumptions. Any implementation that bypasses `forge-docs/` as the governing input is non-compliant. Repository paths and workflows must preserve this contract.

**Rejected alternatives:**  
- Embedding requirements directly in subsystem code or prompts only — rejected because it creates drift from the documented system contracts.  
- Treating code as the source of truth for agent behavior — rejected because the repository structure explicitly defines TRDs/PRDs as authoritative.  
- Allowing multiple equal sources of truth across docs and implementation comments — rejected because ambiguity would break auditability and deterministic coordination.

## [ConsensusDevAgent must fit the repository layout contract]
**Status:** Accepted

**Context:** The repository layout defines stable locations for documentation, standards, backend code, app shell code, and tests. ConsensusDevAgent must be implemented in a way that preserves these boundaries so that planning, generation, review, and CI can operate predictably.

**Decision:** Implement ConsensusDevAgent within the established repository layout and do not introduce an alternative structure for documents, standards, source, or tests. Use `forge-docs/` for TRDs/PRDs, `forge-standards/` for cross-cutting standards, `src/` for Python backend logic, and `tests/` for Python test coverage.

**Consequences:** Subsystem code, tests, and standards references must be placed where the build pipeline and operators expect them. Tooling may rely on these paths without discovery heuristics. Documentation and implementation remain auditable and consistent with the wider system.

**Rejected alternatives:**  
- Creating a subsystem-local docs directory for ConsensusDevAgent — rejected because it fragments the required source of truth.  
- Storing standards beside implementation files — rejected because standards belong in `forge-standards/` by repository contract.  
- Introducing custom path discovery for subsystem artifacts — rejected because deterministic repository conventions are simpler and safer.

## [ConsensusDevAgent participates in the staged build pipeline]
**Status:** Accepted

**Context:** The build pipeline is the core system loop and is triggered from `/prd start <intent>`. The documented stages are Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, and 3-Pass Review. ConsensusDevAgent exists within this orchestrated flow and must not bypass stage contracts.

**Decision:** Implement ConsensusDevAgent as a participant in the documented staged pipeline, preserving stage boundaries and contracts from scope confirmation through 3-pass review.

**Consequences:** ConsensusDevAgent may not collapse stages, skip review, or perform hidden transitions that evade operator visibility and audit. Inputs and outputs must be stage-appropriate, and orchestration logic must respect documented sequencing.

**Rejected alternatives:**  
- End-to-end generation in a single step — rejected because it bypasses the documented control points and review contracts.  
- Allowing dynamic stage skipping when the model is “confident” — rejected because it weakens determinism, auditability, and safety.  
- Merging planning and implementation into one subsystem-internal action — rejected because the pipeline requires explicit decomposition and reviewable artifacts.

## [No undo on gate decisions]
**Status:** Accepted

**Context:** The requirements explicitly state “No undo on gate decisions” and require this to be documented explicitly. Security and pipeline excerpts also reinforce that gate outcomes are terminal control points and must not be auto-bypassed.

**Decision:** Treat every gate decision made by ConsensusDevAgent as irreversible within the automated system. Do not implement undo, silent rollback, auto-reopen, or automatic bypass of a gate once it has been issued.

**Consequences:** When ConsensusDevAgent gates work, downstream automation must stop or wait for explicit external/operator action according to pipeline policy. The subsystem must preserve the audit record of the gate and cannot erase or negate it through later automated reasoning. UX, APIs, and internal state machines must not expose an “undo gate” capability.

**Rejected alternatives:**  
- Supporting an automatic “undo last gate” operation — rejected because it directly contradicts the documented requirement.  
- Allowing a later model pass to clear an earlier gate automatically — rejected because gate decisions must be stable and auditable.  
- Treating some gates as soft warnings that can be silently bypassed — rejected because the requirement distinguishes gates as decisive control points, not advisory notes.

## [SECURITY_REFUSAL is terminal and must stop progression]
**Status:** Accepted

**Context:** Security controls require `SECURITY_REFUSAL` handling in generation prompts and outputs. The requirements explicitly state that when `SECURITY_REFUSAL` appears in output, the PR must stop, gate, log, and never auto-bypass.

**Decision:** Make `SECURITY_REFUSAL` a terminal control signal in ConsensusDevAgent. On detection in relevant LLM output, immediately stop the current PR or generation flow, create a gate, log the event, and prohibit automatic continuation or bypass.

**Consequences:** ConsensusDevAgent must inspect model outputs for `SECURITY_REFUSAL`, integrate with audit logging, and transition to a gated state. Retry logic, arbitration, or fallback models may not silently continue past the refusal. Any recovery must occur through explicit allowed operator or workflow action outside automatic bypass behavior.

**Rejected alternatives:**  
- Ignoring `SECURITY_REFUSAL` if another model produced usable output — rejected because the requirement says stop, gate, and never auto-bypass.  
- Treating `SECURITY_REFUSAL` as a warning and continuing review — rejected because it is defined as a terminal stop condition.  
- Automatically retrying until a model stops refusing — rejected because it would functionally bypass the refusal signal.

## [ConsensusDevAgent must preserve gate-card escalation for flagged untrusted content]
**Status:** Accepted

**Context:** Security controls specify that when flagged chunk content is used in generation, a gate card must be shown to the operator before proceeding. PR review comments are also labeled as untrusted in prompts. ConsensusDevAgent must preserve these trust boundaries.

**Decision:** Require ConsensusDevAgent to gate before proceeding whenever flagged untrusted content is incorporated into generation, and preserve explicit untrusted labeling in any prompt material derived from review comments or similar sources.

**Consequences:** The subsystem must track provenance of content used during generation and cannot treat all inputs as equally trusted. Operator-visible gating is mandatory before continuation in flagged cases. Prompt assembly and review handling must maintain trust annotations rather than normalizing them away.

**Rejected alternatives:**  
- Stripping provenance markers and treating all text as trusted context — rejected because it defeats the required trust model.  
- Proceeding automatically after logging flagged usage — rejected because the requirement calls for a gate card before proceeding.  
- Silently excluding all flagged content without operator involvement — rejected because the documented control is gating, not hidden suppression.

## [Three-pass review is mandatory before completion]
**Status:** Accepted

**Context:** The build pipeline defines Stage 6 as a 3-pass review: correctness, performance, and security. Security controls further require that generated code pass Pass 3 security review, including bandit.

**Decision:** Require ConsensusDevAgent outputs destined for completion or merge readiness to pass the full three-pass review sequence—correctness, then performance, then security—with no pass omitted.

**Consequences:** ConsensusDevAgent cannot declare code complete after generation alone. Review orchestration must maintain ordered review passes and include security tooling expectations such as bandit where applicable. A failure in any pass must prevent progression according to pipeline policy.

**Rejected alternatives:**  
- Running only security review for high-risk changes — rejected because the pipeline requires all three passes.  
- Reordering passes dynamically — rejected because the documented sequence is part of the stage contract.  
- Skipping performance review for small changes — rejected because no exception is provided in the stage definition.

## [Path validation is required before any file write]
**Status:** Accepted

**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent performs or coordinates generated code and file output, so write safety must be enforced uniformly.

**Decision:** Validate every target file path with `path_security.validate_write_path()` before any write, overwrite, create, or generated-file emission performed by or through ConsensusDevAgent.

**Consequences:** All write-capable code paths in the subsystem must funnel through validated path handling. Convenience writes, temporary bypasses, and direct filesystem calls without validation are prohibited. This constrains implementation structure toward centralized file-write primitives or wrappers.

**Rejected alternatives:**  
- Validating only user-provided paths — rejected because the requirement applies to every file path before write.  
- Validating only in top-level orchestration code — rejected because lower-level writes could still bypass controls.  
- Relying on repository-relative joins without explicit validation — rejected because path normalization alone is not the mandated control.

## [Security controls must be enforced in prompts and runtime behavior]
**Status:** Accepted

**Context:** The requirements specify `SECURITY_REFUSAL` rules in every generation system prompt and define mandatory runtime responses when such signals appear. ConsensusDevAgent coordinates model interactions, so both prompt-layer and runtime-layer enforcement are required.

**Decision:** Encode mandatory security rules, including `SECURITY_REFUSAL` handling expectations, in every generation system prompt used by ConsensusDevAgent and enforce matching runtime checks on produced outputs.

**Consequences:** Prompt construction is a governed interface, not an ad hoc implementation detail. The subsystem must maintain consistency between what models are instructed to do and how outputs are evaluated. Prompt templates become security-sensitive assets and must not omit required controls.

**Rejected alternatives:**  
- Enforcing security only after output generation — rejected because the requirements explicitly mandate prompt-level rules as well.  
- Relying solely on model-provider safety systems — rejected because subsystem-specific controls must be explicit and auditable.  
- Applying security prompts only to code-generation stages — rejected because the requirement states every generation system prompt.

## [Auditability takes precedence over autonomous recovery]
**Status:** Accepted

**Context:** The pipeline and security controls emphasize gating, logging, error escalation, and audit trail preservation. ConsensusDevAgent is a coordination subsystem and therefore must prioritize visible, reviewable state transitions over hidden self-healing actions that could obscure why decisions were made.

**Decision:** Prefer explicit logging, gating, and auditable state transitions over autonomous recovery behaviors whenever the two are in tension, especially for security-relevant or gate-triggering events.

**Consequences:** ConsensusDevAgent implementations must expose meaningful events for operator and pipeline audit rather than masking them through automatic retries or internal compensation. Error handling should preserve causality and decision history. This also reinforces the prohibition on undoing gate decisions.

**Rejected alternatives:**  
- Self-healing workflows that automatically clear failures and continue silently — rejected because they undermine auditability and the gate model.  
- Best-effort continuation after security-related anomalies — rejected because security controls require stop-and-gate behavior in defined cases.  
- Minimizing logs to reduce implementation complexity — rejected because the subsystem is part of an audited build and review pipeline.