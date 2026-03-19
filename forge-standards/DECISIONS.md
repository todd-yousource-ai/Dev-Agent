# DECISIONS.md

## Repository structure is fixed and document-first
**Status:** Accepted  
**Context:** The ConsensusDevAgent subsystem operates within a repository whose layout is explicitly defined by the TRDs and README. The system must reliably locate source-of-truth documents, standards, implementation code, tests, and CI configuration without runtime ambiguity or per-install customization.  
**Decision:** Treat the repository layout as fixed. Read all TRDs and PRDs from `forge-docs/`. Store architecture and implementation constraints in `forge-standards/`. Implement Python backend code in `src/`, Swift/macOS shell code in `ForgeAgent/`, XCTest suites in `ForgeAgentTests/`, Python tests in `tests/`, and CI workflows in `.github/workflows/`. Do not introduce alternate source-of-truth locations for requirements documents.  
**Consequences:** Path resolution, document loading, validation, and automation must assume these canonical locations. The subsystem must fail clearly when required directories or documents are missing rather than silently searching elsewhere. Any implementation that writes or reads requirements artifacts outside these locations is non-compliant.  
**Rejected alternatives:**  
- Allowing configurable document roots via environment variables or user settings: rejected because it weakens determinism and makes auditability harder.  
- Co-locating generated planning artifacts with implementation code: rejected because TRDs/PRDs are explicitly document-first and separated from source.  
- Supporting multiple repository layouts: rejected because the TRDs define a single canonical structure and the subsystem must conform to it.

## Gate decisions are irreversible
**Status:** Accepted  
**Context:** The build pipeline and security controls require clear operator-visible gates with strong audit semantics. The TRDs explicitly state “No undo on gate decisions.” This must be enforced at the subsystem level so that downstream stages cannot erase, reverse, or auto-bypass a recorded decision.  
**Decision:** Implement gate decisions as append-only and irreversible. Once a gate outcome is recorded, the subsystem must not provide undo, rollback, silent overwrite, or automatic reconsideration of that decision. Any subsequent action must be represented as a new decision record, not a mutation of the original.  
**Consequences:** State models, persistence, UI actions, and APIs must prevent deletion or reversal of prior gate outcomes. Audit trails must preserve the original gate event and any later follow-up events separately. Recovery flows must use explicit new gates rather than editing history.  
**Rejected alternatives:**  
- Allowing operator undo for mistaken gate actions: rejected because it violates the explicit TRD rule and weakens audit integrity.  
- Permitting administrators to rewrite gate history: rejected because privileged mutation still breaks append-only auditability.  
- Auto-reopening failed or blocked gates after code changes: rejected because reconsideration must be explicit and recorded as a new gate event.

## Build pipeline stage progression is controlled and contract-bound
**Status:** Accepted  
**Context:** The subsystem participates in a staged build pipeline defined in the README and TRD-3. Stage progression carries audit, safety, and quality obligations. Loose or out-of-order execution would undermine reproducibility and review guarantees.  
**Decision:** Enforce ordered progression through the defined build pipeline stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent pipeline actions as specified by stage contracts. Do not skip mandatory stages, collapse stage boundaries, or advance on partial completion where stage contracts require completion and gating.  
**Consequences:** The subsystem must model stage state explicitly and validate prerequisites before execution. Logs and audit records must identify stage entry, exit, outcomes, and escalation points. Parallelism may exist inside a stage only where stage contracts permit it; it must not bypass stage sequencing.  
**Rejected alternatives:**  
- Free-form agent execution based on heuristic readiness: rejected because it breaks stage contracts and auditability.  
- Allowing direct code generation from intent without PRD/PR planning: rejected because the pipeline is explicitly document- and plan-driven.  
- Merging all review passes into a single generic review step: rejected because correctness, performance, and security are separately required.

## Security refusal is a hard stop, not a recoverable warning
**Status:** Accepted  
**Context:** Security controls mandate `SECURITY_REFUSAL` behavior in generation prompts and outputs. The TRD excerpts explicitly require that when `SECURITY_REFUSAL` appears in output, the PR stops, a gate is raised, and the event is logged. Auto-bypass is forbidden.  
**Decision:** Treat any `SECURITY_REFUSAL` emitted by a model or generation path as a terminal stop for the active PR flow. Immediately stop further automated progression for that PR, create an operator gate, and log the event. Never auto-bypass, suppress, reinterpret, or downgrade `SECURITY_REFUSAL` to a warning.  
**Consequences:** The subsystem must detect `SECURITY_REFUSAL` reliably in model outputs and route control flow to gated handling. Retry logic, arbitration, and fallback models must not continue the same PR automatically after such an event. Audit logs must capture the refusal source, context, and halted stage.  
**Rejected alternatives:**  
- Automatically retrying with a different model after refusal: rejected because refusal is defined as a stop condition, not a model-specific transient error.  
- Converting refusal into a soft warning for operator review after generation continues: rejected because generation must stop immediately.  
- Filtering refusal tokens from output and proceeding: rejected because it would constitute an implicit bypass of a mandatory security control.

## Security review is mandatory for all generated code
**Status:** Accepted  
**Context:** The security controls require that all generated code pass Pass 3 security review, including bandit. This requirement applies regardless of perceived code risk, subsystem size, or earlier review success.  
**Decision:** Require every generated code change to complete the full 3-pass review sequence, with Pass 3 dedicated to security review, and include mandated security tooling such as bandit where applicable. Do not ship or merge generated code that has not passed the required security review stage.  
**Consequences:** Review orchestration must preserve a distinct security pass and record its results. Earlier correctness or performance approval cannot waive security review. Failures in Pass 3 must block progression and trigger the appropriate gate/escalation flow.  
**Rejected alternatives:**  
- Running security review only for files matching sensitive paths: rejected because the requirement applies to all generated code.  
- Treating static analysis as sufficient replacement for a dedicated security pass: rejected because Pass 3 is explicitly required as a stage, not merely a tool invocation.  
- Allowing low-risk changes to bypass bandit or equivalent checks: rejected because the control is mandatory, not risk-optional.

## Every filesystem write path must be validated before write
**Status:** Accepted  
**Context:** Security controls explicitly require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent will create and modify artifacts across docs, source, tests, and workflow files, making path traversal and out-of-scope writes a concrete risk.  
**Decision:** Validate every filesystem write target with `path_security.validate_write_path()` before any create, overwrite, append, rename-into-place, or generated artifact write operation. Treat validation as mandatory and non-bypassable for all write-capable code paths.  
**Consequences:** File-writing abstractions must centralize path validation and forbid direct raw writes that skip validation. Temporary-file and atomic-write implementations must validate both temporary and final paths as applicable. Failures must stop the write and surface a clear security error.  
**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated and internally composed paths can also be dangerous.  
- Validating only final destination paths: rejected because temporary/intermediate writes can still escape allowed boundaries.  
- Relying on repository-root prefix checks instead of the mandated validator: rejected because the TRD requires the specific validation control.

## Untrusted reviewer content must remain explicitly labeled and treated as untrusted
**Status:** Accepted  
**Context:** The security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. Reviewer-supplied text can contain prompt injection or malicious instructions and must not be conflated with trusted system or design inputs.  
**Decision:** Preserve explicit untrusted labeling for reviewer-originated content whenever it is injected into prompts or otherwise used by the subsystem. Do not merge reviewer text into trusted instruction channels or strip the untrusted marker during processing.  
**Consequences:** Prompt assembly must maintain content provenance and role separation. The subsystem must not let reviewer comments override TRDs, standards, system prompts, or gate outcomes. Any generation path using flagged or untrusted chunks must route through required gating behavior.  
**Rejected alternatives:**  
- Normalizing reviewer comments into plain context text for model simplicity: rejected because it erases trust boundaries.  
- Allowing reviewer comments to directly amend requirements documents in prompts: rejected because reviewer text is not source-of-truth.  
- Ignoring reviewer comments entirely: rejected because they are useful inputs, but only when explicitly handled as untrusted.

## Flagged content usage requires operator gating before proceeding
**Status:** Accepted  
**Context:** The security controls specify that when flagged content is used in generation, a gate card must be presented to the operator before proceeding. This ensures explicit human awareness when risky or trust-limited material influences output.  
**Decision:** If generation would consume flagged content, stop normal automated progression and require an operator gate before continuing. Record that flagged content was used, what classification triggered the gate, and the operator’s decision as a new audit event.  
**Consequences:** Content classification and prompt assembly must communicate flagged status into orchestration. Generation cannot silently proceed with flagged inputs. Because gate decisions are irreversible, the decision and its context must be durably preserved.  
**Rejected alternatives:**  
- Proceeding automatically with only a warning in logs: rejected because operator gating is explicitly required.  
- Dropping flagged content and continuing without disclosure: rejected because it changes generation context silently and defeats auditability.  
- Blocking flagged content absolutely with no operator path: rejected because the requirement is to gate before proceeding, not to universally forbid use.