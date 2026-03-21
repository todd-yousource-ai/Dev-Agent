# DECISIONS.md

## ConsensusDevAgent repository placement and document source of truth
**Status:** Accepted  
**Context:** The subsystem must fit the mandated repository layout and operate against the same planning and standards artifacts as the rest of the system. The TRDs and README define a strict split between implementation, standards, and source documents.  
**Decision:** Implement ConsensusDevAgent under `src/` as Python backend code, and treat `forge-docs/` as the authoritative source of all TRDs and PRDs it consumes. Store subsystem-wide architectural constraints in `forge-standards/DECISIONS.md` and related standards documents, not inside ad hoc code-local docs.  
**Consequences:** The subsystem may not create a parallel docs tree, alternate TRD cache as source of truth, or place core backend logic in the macOS shell. Planning, decomposition, and execution logic must read from repository documents in `forge-docs/` before acting.  
**Rejected alternatives:**  
- Placing ConsensusDevAgent in `ForgeAgent/`: rejected because the subsystem is backend logic, while `ForgeAgent/` is reserved for the Swift/SwiftUI application shell.  
- Treating generated summaries or embedded prompts as the source of truth: rejected because TRDs/PRDs in `forge-docs/` are explicitly authoritative.  
- Keeping decision records inside subsystem-specific README files only: rejected because repository standards require centralized architectural constraints.

## Pipeline participation is mandatory and stage-ordered
**Status:** Accepted  
**Context:** ConsensusDevAgent operates inside the build pipeline described in TRD-3 and the README. The pipeline is the core control loop and defines ordered stages with auditability and escalation semantics.  
**Decision:** Execute ConsensusDevAgent behavior only within the defined stage sequence: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent gated progression as defined by the pipeline contract. Preserve stage order and honor stage contracts rather than skipping ahead based on model confidence.  
**Consequences:** The subsystem cannot collapse planning and implementation into one step, cannot bypass review, and cannot treat earlier-stage outputs as optional. Internal optimizations are allowed only if they do not alter externally visible stage boundaries, artifacts, or gate behavior.  
**Rejected alternatives:**  
- Allowing direct intent-to-code generation for simple tasks: rejected because it breaks required planning, audit, and review stages.  
- Making stage order configurable per run: rejected because consistency and auditability depend on a fixed contract.  
- Letting model arbitration replace formal review stages: rejected because review is an independent pipeline control, not a byproduct of generation.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The TRDs explicitly require that gate decisions have no undo. This is a control-plane safety property for operator trust, audit integrity, and escalation correctness.  
**Decision:** Treat every gate decision as irreversible within the active pipeline run. Once ConsensusDevAgent records a gate outcome, it must not auto-reopen, auto-clear, auto-bypass, or silently revise that decision. Any continued work must occur through an explicit new operator action or new pipeline run, with a fresh audit trail entry.  
**Consequences:** The subsystem must model gates as append-only decisions. Retry logic cannot overwrite prior gate outcomes. Recovery flows must create new decision records rather than mutating or deleting old ones. UI and API behavior must not imply an “undo” capability for gate outcomes.  
**Rejected alternatives:**  
- Allowing automatic gate clearing after successful retry: rejected because it erodes audit integrity and contradicts the explicit no-undo rule.  
- Permitting operator-side in-place reversal of a prior gate: rejected because decisions must remain historically fixed; follow-up action must be recorded separately.  
- Soft gates that can be ignored by downstream stages: rejected because gate outcomes are intended to stop or constrain progression.

## SECURITY_REFUSAL is a hard stop, never auto-bypassed
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL handling in generation prompts and outputs. The documented behavior is explicit: stop PR, gate, log, and never auto-bypass.  
**Decision:** On any SECURITY_REFUSAL emitted by a model during ConsensusDevAgent generation or review flows, immediately stop the affected PR flow, create a gate for operator attention, and log the event in the audit trail. Never automatically reinterpret, suppress, bypass, or continue past a SECURITY_REFUSAL.  
**Consequences:** The subsystem must have first-class detection and handling for SECURITY_REFUSAL tokens or structured equivalents. Automation throughput is subordinate to this stop condition. Downstream stages must not proceed on the affected work item until a new explicit operator-directed path is taken.  
**Rejected alternatives:**  
- Retrying with a weaker prompt automatically: rejected because it constitutes an auto-bypass of a security control.  
- Downgrading SECURITY_REFUSAL to a warning if another model succeeds: rejected because the control is absolute, not consensus-based.  
- Continuing non-security-related subtasks within the same PR silently: rejected because the documented response is to stop the PR and gate.

## Security review is mandatory and includes Pass 3 security checks
**Status:** Accepted  
**Context:** The build pipeline defines a 3-pass review sequence, and mandatory controls require all generated code to pass security review, including bandit. ConsensusDevAgent must not treat security as optional or deferred.  
**Decision:** Require every code artifact produced through ConsensusDevAgent to pass the full 3-pass review pipeline, with Pass 3 dedicated to security validation, including configured static security checks such as bandit where applicable.  
**Consequences:** Code generation is not complete at synthesis time; completion requires review passage. The subsystem must preserve review artifacts and outcomes as part of execution state. Security findings block progression according to pipeline gate rules.  
**Rejected alternatives:**  
- Running only correctness review for low-risk changes: rejected because the control applies to all generated code.  
- Performing security review asynchronously after merge: rejected because the pipeline requires review before progression.  
- Folding security checks into generic linting only: rejected because Pass 3 is an explicit, distinct security review stage.

## Untrusted review content must remain labeled and non-authoritative
**Status:** Accepted  
**Context:** Mandatory security controls specify that PR review comments are labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. The subsystem must guard against prompt injection and authority confusion from external review text.  
**Decision:** Preserve explicit untrusted labeling on reviewer-supplied or externally sourced review content whenever it is included in prompts, summaries, or model context. Do not treat such content as authoritative instructions, policy, or executable requirements without separate validation.  
**Consequences:** ConsensusDevAgent must maintain provenance metadata for review inputs and ensure prompt construction preserves the trust boundary. Reviewer comments may inform analysis but cannot override TRDs, standards, operator instructions, or security rules.  
**Rejected alternatives:**  
- Normalizing reviewer comments into plain prompt context: rejected because it obscures trust boundaries and increases prompt injection risk.  
- Letting reviewer comments directly mutate implementation plans: rejected because external comments are advisory until validated.  
- Excluding all reviewer comments from model context: rejected because useful feedback should still be consumable when clearly labeled as untrusted.

## Flagged chunks require operator gating before use in generation
**Status:** Accepted  
**Context:** Security controls require that when a flagged chunk is used in generation, the system must gate to the operator before proceeding. This protects against unsafe or tainted context entering model synthesis.  
**Decision:** Before ConsensusDevAgent uses any flagged chunk in a generation step, create an operator gate and block further generation until the gate is explicitly resolved through the approved control flow.  
**Consequences:** Retrieval and prompt assembly must track chunk risk status. The subsystem cannot silently include flagged material in model context. Generation latency may increase, but trust and auditability take precedence.  
**Rejected alternatives:**  
- Including flagged chunks with a warning banner only: rejected because the requirement is to gate before proceeding.  
- Auto-sanitizing flagged chunks and continuing: rejected because sanitization does not remove the need for operator review.  
- Permanently excluding all flagged chunks: rejected because some may still be legitimately needed after gated operator approval.

## File writes must use path validation on every write
**Status:** Accepted  
**Context:** Mandatory generated-code controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and applies code changes, so filesystem safety is a mandatory invariant.  
**Decision:** Validate every target file path with `path_security.validate_write_path()` immediately before any write, overwrite, move, or patch application performed by ConsensusDevAgent. Treat validation failure as a hard error subject to pipeline stop/gate behavior as defined by security policy.  
**Consequences:** The subsystem cannot directly write arbitrary paths, even if earlier planning deemed them valid. Validation must occur at the point of effect, not only during planning. Utility wrappers for file output are required so write-path validation is not bypassed by convenience code.  
**Rejected alternatives:**  
- Validating only once at PR planning time: rejected because path safety must be enforced at the moment of write.  
- Restricting writes by convention without explicit validation calls: rejected because convention is weaker than the mandated control.  
- Validating only newly created files, not edits: rejected because every write path is in scope.

## Claude wins where the pipeline specifies model arbitration for PRD generation
**Status:** Accepted  
**Context:** The documented pipeline states that PRD generation uses both models and that Claude wins. ConsensusDevAgent must implement the specified arbitration policy rather than inventing a dynamic winner-selection scheme for that stage.  
**Decision:** For the PRD generation stage, run the required multi-model generation flow and select Claude’s result as the authoritative output whenever the stage contract specifies “Claude wins.”  
**Consequences:** The subsystem may still capture comparative outputs for audit or analysis, but the final PRD artifact for that stage must follow the prescribed winner. This constrains arbitration logic and prevents stage-specific policy drift.  
**Rejected alternatives:**  
- Selecting whichever model scores higher on internal heuristics: rejected because the stage contract already defines the winner.  
- Merging both PRD outputs automatically: rejected because it creates an unsanctioned artifact and weakens accountability.  
- Using a single model to reduce cost: rejected because the pipeline explicitly requires both models for that stage.