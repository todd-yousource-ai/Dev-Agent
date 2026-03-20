# DECISIONS.md

## ConsensusDevAgent repository placement and ownership
**Status:** Accepted

**Context:** The repository structure defines `forge-docs/` as the source of truth for TRDs and PRDs, `forge-standards/` for cross-cutting standards, and `src/` for Python backend implementation. The ConsensusDevAgent is a backend subsystem participating in the build pipeline and must align with the documented repository layout.

**Decision:** Implement the ConsensusDevAgent subsystem under `src/` as Python backend code. Treat `forge-docs/` as read-first source material and `forge-standards/` as the location for architectural constraints, interfaces, decisions, and conventions. Do not place ConsensusDevAgent implementation logic in the macOS shell or documentation directories.

**Consequences:** ConsensusDevAgent code must be structured as backend runtime code and tested through the Python test suite in `tests/`. UI concerns remain outside the subsystem. Documentation-driven behavior must be traceable back to TRDs/PRDs rather than embedded as ad hoc implementation policy.

**Rejected alternatives:**  
- Implementing ConsensusDevAgent inside `ForgeAgent/`: rejected because the subsystem is part of backend runtime behavior, not the macOS application shell.  
- Storing executable logic alongside documents in `forge-docs/`: rejected because `forge-docs/` is the source of truth for requirements, not a runtime code location.  
- Treating `forge-standards/` as an implementation directory: rejected because it is reserved for normative standards documents, not executable subsystem code.

## Documentation-first implementation
**Status:** Accepted

**Context:** The repository explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. ConsensusDevAgent participates in a document-driven pipeline, so implementation must reflect those artifacts rather than invent behavior during coding.

**Decision:** Require ConsensusDevAgent implementation work to begin from the relevant TRDs and PRDs in `forge-docs/`. Encode subsystem behavior as an execution of documented contracts, not as independent product interpretation.

**Consequences:** Engineering work on ConsensusDevAgent must maintain traceability to the governing documents. Changes in subsystem behavior require corresponding document updates when they alter documented contracts. Implementation may not silently diverge from TRD-defined pipeline behavior.

**Rejected alternatives:**  
- Allowing code-first implementation with later documentation sync: rejected because it would break the repository’s declared source-of-truth model.  
- Using README snippets as sole authority: rejected because README content is summary-level and the TRDs/PRDs are the governing design artifacts.  
- Letting model output define behavior dynamically at runtime: rejected because subsystem behavior must be constrained by documented contracts.

## ConsensusDevAgent is a build-pipeline subsystem
**Status:** Accepted

**Context:** The build pipeline is the core loop triggered by `/prd start <intent>`, with ordered stages from scope through merge. ConsensusDevAgent must fit into this staged architecture rather than operate as a free-form coding agent.

**Decision:** Implement ConsensusDevAgent as a stage-governed subsystem that participates in the defined build pipeline lifecycle. Preserve stage boundaries and consume or emit artifacts consistent with stage contracts rather than bypassing the sequence.

**Consequences:** ConsensusDevAgent must respect upstream and downstream dependencies in the pipeline. It cannot collapse scope, planning, generation, review, and merge concerns into one opaque operation. Observability and auditability must align with stage-based execution.

**Rejected alternatives:**  
- Implementing ConsensusDevAgent as a monolithic “one-shot” code generator: rejected because the system is explicitly stage-based.  
- Allowing the subsystem to skip directly from intent to code generation: rejected because PRD and PR planning are mandatory intermediates.  
- Treating review as advisory-only outside the pipeline: rejected because review is a required stage with gating behavior.

## Gate decisions are final and non-reversible
**Status:** Accepted

**Context:** The technical requirements explicitly state “No undo on gate decisions” and “No undo on gate decisions — document this explicitly.” The build pipeline also requires auditability and error escalation.

**Decision:** Treat every gate decision made by ConsensusDevAgent as final for that pipeline execution. Do not implement undo, rollback-of-decision, silent reopening, or automatic bypass of a recorded gate outcome.

**Consequences:** Once the subsystem records a gate result, subsequent processing must honor that result and require a new explicit execution path rather than mutating history. Audit records remain append-only in effect. Operator workflows must resolve blocked states through new actions, not reversal of prior gate decisions.

**Rejected alternatives:**  
- Adding an operator “undo last gate” control: rejected because requirements explicitly forbid undo on gate decisions.  
- Auto-reopening a failed gate after later signals improve: rejected because it mutates the meaning of an already recorded decision.  
- Softening gates into editable statuses: rejected because it undermines audit integrity and escalation semantics.

## SECURITY_REFUSAL is a hard stop
**Status:** Accepted

**Context:** Mandatory security controls require SECURITY_REFUSAL rules in every generation system prompt, and specify that SECURITY_REFUSAL in output must stop the PR, gate, log, and never auto-bypass. ConsensusDevAgent arbitrates and coordinates generation outcomes, so it must enforce this behavior centrally.

**Decision:** Detect any SECURITY_REFUSAL produced during generation or review and immediately stop the affected PR flow, create a gate, and log the event. Never auto-bypass, suppress, reinterpret, or continue past a SECURITY_REFUSAL.

**Consequences:** ConsensusDevAgent must treat SECURITY_REFUSAL as terminal for the active unit of work unless a new explicit operator-driven path is started outside the original gate decision. The subsystem must preserve the refusal signal in audit records and ensure downstream stages do not execute on refused output.

**Rejected alternatives:**  
- Retrying automatically with a modified prompt after SECURITY_REFUSAL: rejected because requirements say to stop, gate, and never auto-bypass.  
- Downgrading SECURITY_REFUSAL to a warning: rejected because the control is mandatory and blocking.  
- Filtering refusal text and continuing generation: rejected because it would conceal a security control event and violate auditability.

## Untrusted external review content must remain labeled and gated
**Status:** Accepted

**Context:** Security controls require flagged chunks used in generation to produce a gate card before proceeding, and PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent integrates review and generation inputs, making provenance handling a core concern.

**Decision:** Preserve provenance of untrusted reviewer content and inject explicit untrusted labels wherever such content is passed into model prompts or decision logic. When flagged content is used in generation, create a gate before proceeding.

**Consequences:** ConsensusDevAgent must track source trust level for review-derived inputs and prevent them from blending indistinguishably with trusted instructions. Prompt construction, audit logs, and operator gating must reflect the presence of untrusted material.

**Rejected alternatives:**  
- Normalizing reviewer comments into plain prompt context without labels: rejected because it erases trust boundaries required by security controls.  
- Allowing flagged chunks into generation without a gate card: rejected because gating is mandatory when flagged content is used.  
- Discarding all reviewer input categorically: rejected because review inputs are useful, but must be handled under explicit trust controls.

## Security review is mandatory before completion
**Status:** Accepted

**Context:** The pipeline includes a 3-pass review stage: correctness, performance, then security. Mandatory security controls state that all generated code must pass Pass 3 security review including bandit. ConsensusDevAgent must not treat security review as optional or deferred.

**Decision:** Require generated code handled by ConsensusDevAgent to complete the three-pass review sequence, with Pass 3 security review mandatory and inclusive of bandit checks, before work can advance toward merge.

**Consequences:** ConsensusDevAgent must preserve review ordering and cannot mark implementation complete before security review succeeds. Failures in Pass 3 must block progression. Any optimization for throughput must still retain the mandatory security pass.

**Rejected alternatives:**  
- Running only correctness review for small changes: rejected because all generated code must pass the full security review.  
- Swapping review order to run security first: rejected because the documented build pipeline defines the ordered 3-pass sequence.  
- Making bandit advisory-only: rejected because TRD security controls require inclusion in Pass 3.

## File writes must be path-validated
**Status:** Accepted

**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may materialize generated artifacts, patches, or code changes and therefore must enforce safe write targets.

**Decision:** Validate every file path with `path_security.validate_write_path()` before any write performed by ConsensusDevAgent or its invoked code paths. Do not permit any write path to bypass this validation.

**Consequences:** All write operations in the subsystem must flow through a common validated path. Direct filesystem writes, temporary convenience paths, and tool-specific shortcuts are constrained by the same security control. Implementation must be designed so validation is hard to omit.

**Rejected alternatives:**  
- Validating only paths originating from model output: rejected because the requirement applies to every file path before write.  
- Relying on repository-relative path checks without the mandated validator: rejected because the control explicitly names the required validation mechanism.  
- Allowing trusted internal callers to bypass validation: rejected because bypasses create inconsistent enforcement and violate the mandatory rule.

## Consensus arbitration must remain auditable
**Status:** Accepted

**Context:** The build pipeline references parallel generation and arbitration during code generation, with full stage contracts, error escalation, and audit trail schema defined in TRD-3. ConsensusDevAgent must therefore produce decisions that can be reconstructed and reviewed.

**Decision:** Record arbitration inputs, outcomes, and gate-relevant reasoning in the audit trail defined by pipeline contracts. Make consensus outcomes traceable to stage artifacts and model outputs rather than ephemeral in-memory decisions.

**Consequences:** ConsensusDevAgent implementation must expose stable artifacts for arbitration and escalation. Operational debugging, compliance review, and failure handling depend on durable decision records. The subsystem cannot rely on hidden heuristics that leave no audit trace.

**Rejected alternatives:**  
- Using best-effort logging without structured audit records: rejected because the pipeline requires an audit trail schema.  
- Keeping arbitration rationale only in transient memory: rejected because decisions must survive for escalation and review.  
- Returning only the winning output without provenance: rejected because consensus outcomes must be explainable and auditable.

## Operator gating takes precedence over autonomous continuation
**Status:** Accepted

**Context:** Multiple controls require explicit gates: SECURITY_REFUSAL events, flagged chunk usage, and stage-governed progression. The build pipeline is not designed for unrestricted autonomous continuation when risk conditions are encountered.

**Decision:** Pause ConsensusDevAgent and require operator-visible gating whenever a documented gate condition occurs. Do not continue autonomously through a condition that the pipeline or security controls classify as gate-worthy.

**Consequences:** Throughput optimizations must yield to gating requirements. UX and API behavior for ConsensusDevAgent must expose blocked states clearly and avoid background continuation. The subsystem must separate “can proceed automatically” from “must wait for operator resolution.”

**Rejected alternatives:**  
- Allowing automatic continuation with later notification: rejected because gate conditions require intervention before proceeding.  
- Hiding gate details and surfacing only generic failures: rejected because operators need actionable gate visibility.  
- Replacing gates with internal retries for all error classes: rejected because some conditions are explicitly not retryable or bypassable.