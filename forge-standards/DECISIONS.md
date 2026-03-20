# DECISIONS.md

## [ConsensusDevAgent documentation source of truth]
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with a mandated structure. The TRDs and generated PRDs are the authoritative inputs to planning and implementation, and the repository layout explicitly places all such documents under `forge-docs/`. The agent must be constrained to read and reason from the same canonical source as the rest of the system.  
**Decision:** Treat `forge-docs/` as the sole source of truth for TRDs and PRDs. Require the ConsensusDevAgent to read relevant documents from `forge-docs/` before planning, generating, reviewing, or gating work. Do not source requirements from ad hoc files outside this directory unless they are explicitly incorporated into the documented standards.  
**Consequences:** Implementation must resolve requirements and workflow state from documents in `forge-docs/`. Planning logic, prompts, and orchestration must assume TRDs/PRDs live there. Any feature that bypasses document lookup or treats another location as authoritative is non-compliant.  
**Rejected alternatives:**  
- Using scattered markdown files across the repository as equal sources of truth — rejected because it creates ambiguity and breaks the mandated repository contract.  
- Allowing runtime operator notes to override TRDs without documentation updates — rejected because it undermines auditability and reproducibility.  
- Mirroring TRDs into subsystem-local state as an independent authority — rejected because it risks divergence from canonical documents.

## [ConsensusDevAgent must conform to the repository layout contract]
**Status:** Accepted  
**Context:** The repository layout is explicitly defined, including locations for standards, source code, tests, app shell, and CI workflows. The subsystem must operate within this structure so generated plans, code, and review outputs land in predictable places.  
**Decision:** Implement the ConsensusDevAgent to honor the repository layout contract: `forge-docs/` for TRDs/PRDs, `forge-standards/` for standards documents, `src/` for Python backend code, `tests/` for pytest suites, `ForgeAgent/` and `ForgeAgentTests/` for Swift code, and `.github/workflows/` for CI. Do not invent alternate top-level directories for equivalent artifacts.  
**Consequences:** Path resolution, task routing, file generation, and review logic must be repository-aware. The subsystem must produce artifacts only into approved locations and must be able to reason about language/runtime boundaries based on those locations.  
**Rejected alternatives:**  
- Letting each agent choose output locations dynamically — rejected because it would fragment conventions and complicate CI and review.  
- Creating a dedicated `agents/` tree for all generated artifacts — rejected because it conflicts with the defined repository structure.  
- Co-locating standards and implementation in a single directory — rejected because it blurs authoritative documentation and executable code.

## [Build pipeline stage progression is linear and gated]
**Status:** Accepted  
**Context:** The system build loop is defined as a staged pipeline from scope confirmation through PRD generation, PR planning, code generation, review, and onward. The ConsensusDevAgent is a participant in this progression and must preserve stage contracts and gate integrity.  
**Decision:** Implement the ConsensusDevAgent as a stage-bound subsystem that advances work only according to the defined build pipeline order. Require explicit gate satisfaction before moving from one stage to the next, and do not skip, reorder, or collapse stage boundaries unless the governing TRD contract is updated.  
**Consequences:** Orchestration must encode stage identity, entry criteria, and exit criteria. Consensus outcomes must be attached to a stage context. The subsystem cannot directly jump from intent to code generation or from code generation to completion without the intermediate prescribed stages and reviews.  
**Rejected alternatives:**  
- Allowing opportunistic fast-path execution that skips planning stages for “simple” work — rejected because it weakens consistency and traceability.  
- Merging PRD planning and PR planning into a single generic planning step — rejected because the pipeline explicitly distinguishes them.  
- Treating review as advisory instead of a gate — rejected because review is part of the contractual progression.

## [No undo on gate decisions]
**Status:** Accepted  
**Context:** The requirements explicitly state “No undo on gate decisions” and call out that this must be documented explicitly. Gate decisions are therefore intended to be durable audit events rather than reversible UI state.  
**Decision:** Treat every gate decision made or consumed by the ConsensusDevAgent as immutable. Do not implement undo, rollback, silent revision, or state mutation that reverses a recorded gate outcome. Any subsequent change in direction must be represented as a new decision or a new pipeline action, not an edit to the original gate record.  
**Consequences:** Audit storage must use append-only semantics for gate outcomes. UI, APIs, and orchestration must not expose “undo gate” capabilities. Recovery flows must create superseding records rather than mutating history. Prompting and operator workflows must warn that gate actions are final once recorded.  
**Rejected alternatives:**  
- Supporting operator undo for a short grace period — rejected because it directly violates the explicit requirement.  
- Allowing administrators to rewrite gate history out-of-band — rejected because it destroys audit integrity.  
- Modeling gate decisions as editable workflow state — rejected because it conflates state management with compliance records.

## [SECURITY_REFUSAL is a hard stop]
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL rules in generation prompts and specify that if SECURITY_REFUSAL appears in output, the PR must stop, gate, and log, with no automatic bypass. The ConsensusDevAgent must therefore treat this signal as authoritative and terminal for the active flow.  
**Decision:** Detect any SECURITY_REFUSAL emitted during ConsensusDevAgent-mediated generation, arbitration, or review and immediately stop the active PR flow, create a gate card for operator handling, and write an audit log entry. Never auto-bypass, suppress, reinterpret, or continue past SECURITY_REFUSAL.  
**Consequences:** Parsers, prompt wrappers, and orchestration must explicitly scan for SECURITY_REFUSAL. The subsystem must surface the event to operators and preserve the raw evidence in logs. Consensus logic cannot outvote or override the refusal. Any automation that proceeds despite the signal is prohibited.  
**Rejected alternatives:**  
- Treating SECURITY_REFUSAL as a low-confidence warning that another model can overrule — rejected because the control is mandatory and defined as a stop condition.  
- Automatically retrying with softened prompts until the refusal disappears — rejected because it functions as an auto-bypass.  
- Continuing non-security-related stages while flagging the event asynchronously — rejected because the requirement says stop PR, gate, and log.

## [Security review is mandatory for all generated code]
**Status:** Accepted  
**Context:** Mandatory security controls state that all generated code must pass Pass 3 security review, including bandit. Because the ConsensusDevAgent coordinates or adjudicates generated outputs, it must enforce this as a release gate rather than a best-effort check.  
**Decision:** Require every code artifact produced under ConsensusDevAgent control to pass the security review pass before the PR can advance. Include the mandated security tooling and checks, including bandit where applicable, and fail the gate on unresolved security findings.  
**Consequences:** The subsystem must integrate with the 3-pass review structure and ensure security is not skipped when correctness or performance appear satisfactory. Generated outputs remain non-advancing until security review succeeds. Consensus scoring must not mark code complete before this pass is green.  
**Rejected alternatives:**  
- Running security review only on changed files deemed “high risk” — rejected because the requirement applies to all generated code.  
- Treating security findings as non-blocking for internal branches — rejected because the control is mandatory.  
- Folding security checks into correctness review informally — rejected because the pipeline defines a distinct security pass.

## [Untrusted reviewer comments must remain explicitly untrusted]
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. The ConsensusDevAgent may consume reviewer input during arbitration and planning, but must preserve its trust boundary.  
**Decision:** Propagate external PR review comments into ConsensusDevAgent prompts and internal reasoning only with the explicit `[UNTRUSTED REVIEWER COMMENT]` label. Do not elevate such comments to trusted instructions, requirements, or policy without separate validation against authoritative documents or operator approval.  
**Consequences:** Prompt assembly must preserve labeling. Consensus logic must distinguish authoritative requirements from untrusted commentary. The subsystem must not execute file changes, policy shifts, or workflow actions solely because a reviewer comment suggested them.  
**Rejected alternatives:**  
- Treating all repository review comments as trusted because they originate inside GitHub — rejected because review content is explicitly designated untrusted.  
- Omitting the label after sanitization — rejected because the trust boundary must remain visible to the model.  
- Blocking reviewer comments entirely from prompts — rejected because useful feedback is still allowed if clearly marked untrusted.

## [Flagged untrusted content requires operator gating before use]
**Status:** Accepted  
**Context:** Security controls specify that when flagged chunk is used in generation, a gate card must be presented to the operator before proceeding. The ConsensusDevAgent must therefore not silently incorporate flagged material into generated outcomes.  
**Decision:** When the ConsensusDevAgent determines that flagged or untrusted content would be used in generation or arbitration, pause progression and create an operator gate card before proceeding. Do not incorporate the content into output until the gate is resolved through the prescribed workflow.  
**Consequences:** Retrieval, prompt-building, and evidence-selection components must track provenance and trust flags. The subsystem must support pause-and-gate behavior mid-flow. Silent inclusion of flagged text into prompts or outputs is prohibited.  
**Rejected alternatives:**  
- Automatically stripping the most dangerous parts and proceeding without operator review — rejected because the requirement mandates a gate before use.  
- Using flagged content if multiple models agree — rejected because consensus does not remove trust risk.  
- Logging the use after generation instead of gating before generation — rejected because the control is preventative, not merely forensic.

## [All write paths must be validated before file output]
**Status:** Accepted  
**Context:** Mandatory controls state that `path_security.validate_write_path()` must run on every file path before write. Since the ConsensusDevAgent may create or modify repository artifacts, path validation is a required security boundary.  
**Decision:** Call `path_security.validate_write_path()` on every filesystem write initiated by the ConsensusDevAgent, without exception. Reject writes that fail validation and surface them as gated errors rather than attempting fallback writes to alternate paths.  
**Consequences:** File creation and patch application must route through a common validated write layer. Direct writes, temp-path shortcuts, and tool-specific bypasses are prohibited unless they invoke the same validation contract. Test coverage must verify path validation on all write-capable code paths.  
**Rejected alternatives:**  
- Validating only paths derived from model output — rejected because every write path must be checked.  
- Relying on repository root normalization instead of explicit validation — rejected because the control names a specific validation function.  
- Auto-correcting invalid paths to the nearest allowed location — rejected because it may mask abuse or operator mistakes.

## [Consensus outcomes must preserve audit trail semantics]
**Status:** Accepted  
**Context:** The build pipeline references full stage contracts, error escalation, and an audit trail schema. Because the ConsensusDevAgent produces decisions that affect stage progression and gating, its outputs must be durable, attributable, and auditable.  
**Decision:** Record ConsensusDevAgent decisions, gate interactions, refusals, escalations, and stage transitions as audit events aligned with the pipeline’s audit schema. Use append-only event recording for consequential actions, especially gates and security stops.  
**Consequences:** Implementation must include structured event emission with enough context to reconstruct why a decision was made, at which stage, and under what evidence. Silent in-memory decisions that do not produce an auditable record are insufficient for consequential workflow transitions.  
**Rejected alternatives:**  
- Keeping only final outputs and discarding intermediate decision records — rejected because it prevents forensic reconstruction.  
- Logging free-form text only — rejected because stage contracts and audit schema require structured traceability.  
- Storing mutable workflow snapshots without event history — rejected because it conflicts with immutable gate semantics and auditability.