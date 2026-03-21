# DECISIONS.md

## ConsensusDevAgent repository and document source of truth
**Status:** Accepted  
**Context:** The subsystem operates inside a larger repository with a prescribed structure. TRDs and PRDs are authoritative inputs and must be read before implementation. The subsystem must not invent alternate locations for design inputs or mix generated artifacts with standards and source code.  
**Decision:** Treat `forge-docs/` as the sole source of truth for TRDs and PRDs, and implement ConsensusDevAgent within the repository layout defined by the platform:
- `forge-docs/` for TRDs and PRDs
- `forge-standards/` for architecture and decision records
- `src/` for Python backend implementation
- `tests/` for Python tests

ConsensusDevAgent implementation artifacts, orchestration code, and tests must live under the prescribed backend locations and must not create a parallel documentation or standards hierarchy.  
**Consequences:** Implementation must read design intent from `forge-docs/` before planning or execution. Decision records for this subsystem belong in `forge-standards/DECISIONS.md`. Code generation and runtime behavior must assume the documented repository contract rather than discovering ad hoc paths.  
**Rejected alternatives:**  
- Storing subsystem-specific PRDs or TRDs under `src/` or a custom agent folder: rejected because it fragments the source of truth and violates repository structure.  
- Treating generated plans or intermediate outputs as authoritative design inputs: rejected because only TRDs/PRDs in `forge-docs/` are authoritative.  
- Creating a standalone ConsensusDevAgent repository layout: rejected because the subsystem is constrained to the monorepo structure.

## ConsensusDevAgent must participate in the staged build pipeline
**Status:** Accepted  
**Context:** The platform defines a fixed build pipeline triggered from intent through planning, generation, review, and merge. ConsensusDevAgent is part of this controlled flow and must not bypass stage boundaries.  
**Decision:** Implement ConsensusDevAgent as a stage-bound subsystem that participates only through the prescribed pipeline contracts:
1. Scope
2. PRD Plan
3. PRD Gen
4. PR Plan
5. Code Gen
6. 3-Pass Review

ConsensusDevAgent must consume prior-stage outputs and produce artifacts suitable for subsequent stages without collapsing, skipping, or reordering stages.  
**Consequences:** The subsystem must expose interfaces aligned to pipeline stage inputs and outputs. It cannot directly jump from user intent to code write or merge actions. Review and security controls remain mandatory downstream gates even when consensus appears strong.  
**Rejected alternatives:**  
- A single-shot “intent to code” agent: rejected because it bypasses mandated planning and review stages.  
- Allowing the subsystem to reorder stages for efficiency: rejected because stage ordering is part of the audited process contract.  
- Embedding review logic inside generation and skipping explicit review stages: rejected because the pipeline requires separate review passes.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The build pipeline explicitly forbids undo on gate decisions. This must be documented for subsystems that may otherwise attempt automated retries, reversals, or silent bypasses after a blocking result.  
**Decision:** Treat every gate decision produced during ConsensusDevAgent execution as immutable. Do not implement automatic undo, rollback of gate state, silent reopening of a closed gate, or automated bypass after a gate has been decided. Any subsequent progress must occur through explicit new operator-approved flow rather than reversal of the prior decision.  
**Consequences:** State models must represent gate outcomes as append-only decisions. Audit logs must preserve the original gate result permanently. Retry behavior, if any, must create a new decision event rather than mutate or erase the original one.  
**Rejected alternatives:**  
- Allowing operator or system “undo” of failed or stopped gates: rejected because the documented pipeline forbids undo on gate decisions.  
- Replacing a prior gate outcome in place after regeneration: rejected because it destroys auditability.  
- Auto-bypassing a blocked gate when later model output appears safe: rejected because bypass is explicitly disallowed.

## SECURITY_REFUSAL is a hard stop
**Status:** Accepted  
**Context:** Security controls require explicit handling when an LLM emits `SECURITY_REFUSAL`. This condition is not advisory; it is a mandatory stop condition tied to PR gating and audit logging. ConsensusDevAgent must enforce this consistently during generation and review orchestration.  
**Decision:** On any `SECURITY_REFUSAL` in model output, immediately stop the current PR flow, create a gate requiring operator attention, and log the event in the audit trail. Never auto-bypass, suppress, reinterpret, or continue past `SECURITY_REFUSAL`.  
**Consequences:** Generation orchestration must scan outputs for `SECURITY_REFUSAL` before accepting artifacts. Downstream automation must halt on detection. Recovery requires explicit operator handling in a new flow, not automatic continuation.  
**Rejected alternatives:**  
- Treating `SECURITY_REFUSAL` as a warning while continuing generation: rejected because the security controls require stop, gate, and log.  
- Auto-reprompting indefinitely until refusal disappears: rejected because it attempts to bypass a hard security stop.  
- Filtering `SECURITY_REFUSAL` from stored output to keep pipelines green: rejected because it undermines security and audit integrity.

## Security controls are mandatory in generation and file writes
**Status:** Accepted  
**Context:** The subsystem generates code and may write files. Mandatory security controls specify prompt-level refusal behavior, required security review, and path validation before any write. ConsensusDevAgent must not weaken these controls for convenience or speed.  
**Decision:** Enforce the mandatory security controls for all ConsensusDevAgent-generated artifacts:
- Include `SECURITY_REFUSAL` rules in every generation system prompt used by the subsystem.
- Require generated code to pass the dedicated security review pass, including bandit where applicable.
- Validate every write target with `path_security.validate_write_path()` before writing.
- Treat flagged content and untrusted review comments as untrusted inputs that must be labeled and handled per security policy.

**Consequences:** Prompt builders, review orchestration, and file output layers must all include security enforcement points. File-writing code cannot directly write to paths without validation. The subsystem must preserve trust labels on external or reviewer-provided content.  
**Rejected alternatives:**  
- Applying security prompts only to code-generation stages but not planning or arbitration: rejected because refusal behavior must be enforced in every generation system prompt.  
- Running security review only on final merged output: rejected because generated code must pass the security review pass before progression.  
- Validating only relative paths or only user-provided paths: rejected because every file path before write must be validated.  
- Stripping trust labels from reviewer comments for cleaner prompts: rejected because untrusted input labeling is mandatory.

## Consensus outcomes do not override security or pipeline gates
**Status:** Accepted  
**Context:** ConsensusDevAgent may aggregate multiple model outputs or arbitrate between candidates. However, the platform’s gate and security mechanisms are authoritative. Consensus cannot be used to overrule a failed review, a security refusal, or a closed gate.  
**Decision:** Use consensus only to choose among eligible candidate outputs within a stage. Do not allow consensus scoring, arbitration, or model majority to override:
- pipeline gate outcomes,
- security review failures,
- `SECURITY_REFUSAL`,
- required operator gate cards.

**Consequences:** Arbitration logic must run inside the bounds of existing gates, not above them. A “best” candidate can still be rejected if it fails review or triggers security controls. Metrics and model agreement are advisory within stage scope only.  
**Rejected alternatives:**  
- Letting majority model agreement bypass a failed security pass: rejected because security gates are mandatory and final for that flow.  
- Allowing arbitration to reopen blocked PRs automatically: rejected because gate decisions are immutable.  
- Treating consensus confidence as sufficient for merge readiness: rejected because explicit review stages remain required.

## Audit trail must be append-only for gates, refusals, and stage outcomes
**Status:** Accepted  
**Context:** The pipeline references audit trail requirements, and immutable gate decisions require durable historical records. ConsensusDevAgent produces decisions and transitions that must remain inspectable.  
**Decision:** Record stage transitions, gate decisions, `SECURITY_REFUSAL` events, and operator-required stops in an append-only audit trail. Never mutate prior records to reflect newer outcomes; instead append new records that reference earlier events.  
**Consequences:** Persistence and event models must support immutable history. Operational tooling must display current state as a projection over recorded events rather than by rewriting history. Incident review and compliance reporting can rely on preserved original records.  
**Rejected alternatives:**  
- Updating a single status row in place for simplicity: rejected because it obscures historical gate and refusal events.  
- Deleting refusal or failed-review records after successful regeneration: rejected because it violates auditability.  
- Keeping only final pipeline state: rejected because intermediate gate decisions are part of the required process history.