# DECISIONS.md

## ConsensusDevAgent repository placement and boundaries
**Status:** Accepted  
**Context:** The repository structure defines where implementation, standards, and source documents live. The ConsensusDevAgent subsystem must fit the existing layout and preserve clear separation between executable code, standards, and source requirements.  
**Decision:** Implement ConsensusDevAgent in `src/` as Python backend code. Treat `forge-docs/` as read-first source-of-truth requirements input, and treat `forge-standards/` as the location for governing architecture and implementation constraints. Do not place subsystem logic in `forge-docs/`, `forge-standards/`, or the macOS shell directories.  
**Consequences:** The subsystem must be implemented as backend runtime code and must consume documents from `forge-docs/` rather than co-locating with them. Standards updates belong in `forge-standards/`, not inside subsystem source trees. Tests for the subsystem belong in `tests/`.  
**Rejected alternatives:**  
- Implementing ConsensusDevAgent inside `ForgeAgent/` was rejected because the app shell is not the backend runtime boundary.  
- Placing executable orchestration code under `forge-docs/` was rejected because those documents are requirements artifacts, not runtime code.  
- Creating an isolated top-level subsystem directory outside `src/` was rejected because it would violate the declared repository layout.

## Forge documents are mandatory inputs before implementation
**Status:** Accepted  
**Context:** Repository guidance explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. ConsensusDevAgent is responsible for behavior that is tightly constrained by these documents.  
**Decision:** Require ConsensusDevAgent workflows and implementations to treat relevant TRDs and PRDs in `forge-docs/` as mandatory inputs before planning, generation, arbitration, or gate decisions.  
**Consequences:** The subsystem cannot operate as a free-form code generator detached from repository documents. Implementations must preserve document-driven behavior and should fail closed when required source documents are unavailable, incomplete, or unread.  
**Rejected alternatives:**  
- Allowing implementation from prompts alone was rejected because it would bypass the declared source-of-truth process.  
- Treating TRDs as advisory rather than mandatory was rejected because it would weaken consistency and auditability.  
- Copying document content into subsystem-local ad hoc configuration as the primary source was rejected because it would create drift from `forge-docs/`.

## ConsensusDevAgent participates in the staged build pipeline
**Status:** Accepted  
**Context:** The build pipeline is the core loop and is organized into explicit stages from scoping through merge. ConsensusDevAgent behavior must align with stage boundaries and contracts.  
**Decision:** Design ConsensusDevAgent as a stage-aware subsystem that operates only within the declared pipeline stages and honors stage contracts from scope through review and merge preparation. Do not collapse, skip, or reorder stages locally within the subsystem.  
**Consequences:** The subsystem must expose behavior compatible with Stage 1 through Stage 6 and any later pipeline gates defined by the platform. Internal orchestration must preserve stage identity for logging, audit, and operator visibility.  
**Rejected alternatives:**  
- A monolithic single-pass agent flow was rejected because it removes stage-level auditability and control.  
- Allowing the subsystem to dynamically reorder stages was rejected because it would break documented pipeline semantics.  
- Embedding review logic directly into generation without stage separation was rejected because it weakens gate clarity.

## Gate decisions are final and have no undo path
**Status:** Accepted  
**Context:** Requirements explicitly state: no undo on gate decisions. This applies to build pipeline gating and must be documented without ambiguity.  
**Decision:** Implement all ConsensusDevAgent gate decisions as append-only, final outcomes with no undo, rollback, or automatic reconsideration path inside the subsystem. Any subsequent progress must occur through a new explicit operator-driven action or a new pipeline run, not by reversing the original gate result.  
**Consequences:** The subsystem must not expose “undo gate,” “reopen gate,” or silent retry mechanisms that negate prior decisions. Audit records must preserve the original gate event permanently. UX and APIs must frame reversals as new decisions, not mutation of history.  
**Rejected alternatives:**  
- Allowing operators to undo a gate in place was rejected because it conflicts directly with stated requirements.  
- Auto-retrying failed gates until success was rejected because it would obscure decision history and weaken controls.  
- Mutating existing gate records to reflect a new status was rejected because gate history must remain append-only.

## Security refusal is a hard stop
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in generation prompts and explicitly state that SECURITY_REFUSAL in output must stop the PR, gate, log, and never auto-bypass.  
**Decision:** Treat any SECURITY_REFUSAL produced or detected by ConsensusDevAgent or participating model outputs as a mandatory hard-stop event: stop the current PR flow, raise a gate, log the event, and prohibit automatic bypass or silent continuation.  
**Consequences:** The subsystem must implement explicit handling for SECURITY_REFUSAL across generation and review outputs. Pipelines must transition to a blocked state and require operator handling outside the blocked attempt. No downstream stage may proceed automatically after such an event.  
**Rejected alternatives:**  
- Ignoring SECURITY_REFUSAL if other checks pass was rejected because it violates mandatory security controls.  
- Auto-bypassing with a lower-confidence model or prompt retry was rejected because requirements explicitly forbid auto-bypass.  
- Converting SECURITY_REFUSAL into a warning was rejected because the required behavior is a stop-and-gate action.

## Untrusted review content must remain labeled and non-authoritative
**Status:** Accepted  
**Context:** Security guidance requires PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged external content must be handled as untrusted input.  
**Decision:** Treat reviewer comments, flagged chunks, and similar external advisory text as untrusted data. Preserve required trust labeling in prompts and processing, and do not allow such content to become authoritative instructions for ConsensusDevAgent behavior without explicit trusted mediation.  
**Consequences:** Prompt construction, review ingestion, and arbitration logic must maintain trust boundaries. The subsystem must prevent prompt injection via reviewer content and must ensure operator visibility when flagged content is used in generation.  
**Rejected alternatives:**  
- Treating reviewer comments as trusted system instructions was rejected because it violates the defined trust model.  
- Stripping labels for cleaner prompts was rejected because the labels are required security controls.  
- Merging untrusted comments directly into implementation plans without mediation was rejected due to injection and provenance risks.

## Generated code writes must be path-validated
**Status:** Accepted  
**Context:** Security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent generates and applies code changes, so write-path enforcement is mandatory.  
**Decision:** Validate every filesystem write path initiated by ConsensusDevAgent with `path_security.validate_write_path()` before creating, modifying, or replacing files. Deny writes that do not pass validation.  
**Consequences:** File application components cannot write directly to disk without passing through path validation. The subsystem must centralize or wrap write operations so this control is not bypassed by convenience utilities or parallel workers.  
**Rejected alternatives:**  
- Validating only user-supplied paths was rejected because generated paths are also security-relevant.  
- Relying on repository-relative normalization alone was rejected because the mandated control is explicit path validation.  
- Performing validation only at batch boundaries was rejected because every write path must be checked.

## Security review is mandatory before code advances
**Status:** Accepted  
**Context:** The build pipeline includes a 3-pass review with correctness, performance, and security. Security controls further require generated code to pass Pass 3 security review, including bandit.  
**Decision:** Require ConsensusDevAgent-produced code to complete the full 3-pass review sequence and to pass the security pass, including bandit, before it can advance beyond review gates.  
**Consequences:** The subsystem cannot mark code generation complete based on synthesis alone. Review orchestration must preserve ordered pass execution and enforce failure handling on security findings.  
**Rejected alternatives:**  
- Running only correctness review was rejected because the pipeline mandates all three passes.  
- Making security review optional for low-risk changes was rejected because the requirement is mandatory for generated code.  
- Allowing merge on unresolved security pass failures was rejected because it violates gate semantics.

## Audit trail must preserve stage and gate events
**Status:** Accepted  
**Context:** The build pipeline references stage contracts, error escalation, and an audit trail schema. ConsensusDevAgent decisions, especially gates and security stops, must be traceable.  
**Decision:** Record ConsensusDevAgent stage transitions, gate outcomes, hard-stop security events, and escalation points in an append-only audit trail compatible with the pipeline audit schema.  
**Consequences:** Subsystem implementation must emit structured events rather than relying on ad hoc logs alone. Historical records must support reconstruction of how a PR or task moved through planning, generation, review, and gating.  
**Rejected alternatives:**  
- Using plain text logs as the only record was rejected because they do not provide reliable structured auditability.  
- Recording only failures was rejected because stage progression and decisions must also be reconstructable.  
- Allowing audit records to be edited in place was rejected because gate and stage history must remain append-only.