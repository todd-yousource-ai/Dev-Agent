# DECISIONS.md

## ConsensusDevAgent repository placement and boundaries
**Status:** Accepted

**Context:** The repository structure is explicitly defined across the provided TRD and README excerpts. `forge-docs/` is the source of truth for TRDs and PRDs, `forge-standards/` contains architectural constraints, and implementation belongs under `src/`. The ConsensusDevAgent subsystem must fit this structure without introducing ambiguity about where decision records, source code, and generated planning artifacts live.

**Decision:** Place ConsensusDevAgent implementation under `src/` and treat `forge-docs/` as read-first source material and `forge-standards/DECISIONS.md` as the binding design-constraint record. Do not store executable subsystem logic, generated runtime state, or implementation source in `forge-docs/`.

**Consequences:** The subsystem must read requirements from documents in `forge-docs/`, but its code, tests, and runtime behavior are implemented outside that directory. Architectural and behavioral constraints for the subsystem must be captured in this file rather than embedded only in prompts, code comments, or ad hoc documentation. This prevents drift between documentation and implementation layout.

**Rejected alternatives:** Storing subsystem code alongside TRDs in `forge-docs/` was rejected because that directory is reserved for requirements artifacts, not implementation. Keeping decisions only in source comments or prompt templates was rejected because decisions must be centrally visible and auditable. Creating a subsystem-specific parallel standards location was rejected because the repository layout already defines `forge-standards/` as the standards home.

## Document-first execution for ConsensusDevAgent
**Status:** Accepted

**Context:** The repository guidance states that all TRDs and PRDs live in `forge-docs/` and must be read before building. The build pipeline is initiated from intent and proceeds through planning and generation stages rooted in those artifacts. ConsensusDevAgent therefore must not operate from implicit assumptions or code-only configuration when requirements documents exist.

**Decision:** Require ConsensusDevAgent to read and ground its planning and implementation decisions in the relevant TRDs and PRDs from `forge-docs/` before performing generation, arbitration, or gate-affecting actions.

**Consequences:** The subsystem must include a document-ingestion step before downstream actions. Implementations that skip document grounding, rely solely on operator shorthand, or proceed from stale cached assumptions are non-compliant. The subsystem must be designed to fail closed when required source documents are unavailable or unread.

**Rejected alternatives:** Allowing generation from only operator intent was rejected because it bypasses the documented source of truth. Treating repository code as the primary source of requirements was rejected because the TRDs/PRDs explicitly hold that role. Making document reads optional for speed was rejected because it weakens traceability and correctness.

## ConsensusDevAgent participates in the staged build pipeline only
**Status:** Accepted

**Context:** The build pipeline is explicitly defined as a sequence of stages from scope through review and merge. The excerpts also reference stage contracts, escalation, and audit trail requirements in TRD-3. ConsensusDevAgent must integrate into this staged model rather than inventing an alternate execution loop.

**Decision:** Implement ConsensusDevAgent as a stage-bound subsystem that operates only within the defined build pipeline contracts and honors stage entry, exit, and gating semantics from the pipeline.

**Consequences:** The subsystem cannot skip stages, merge stage responsibilities without authorization, or perform out-of-band progression after a failed gate. Its APIs and internal state transitions must align to pipeline stages such as planning, code generation, and review. Auditability must be preserved at stage boundaries.

**Rejected alternatives:** A free-form agent loop was rejected because it conflicts with the documented pipeline. Allowing the subsystem to self-select stages dynamically without stage contracts was rejected because it reduces predictability and auditability. Combining planning, generation, and approval into one opaque step was rejected because the TRDs define separate stages with distinct controls.

## No undo on gate decisions
**Status:** Accepted

**Context:** The provided material explicitly states, multiple times, that there is no undo on gate decisions. Security refusal output must stop the PR, gate, and log, and the build pipeline text repeats that there is no undo on gate decisions. This must be documented as a hard constraint, not left implicit.

**Decision:** Treat every gate decision made by ConsensusDevAgent as immutable. Do not implement undo, silent reversal, automatic reopening, or post hoc bypass of any gate decision once recorded.

**Consequences:** The subsystem must model gate outcomes as append-only decisions in the audit trail. Recovery from an incorrect gate must occur through explicit new forward actions or operator-driven escalation paths defined by the pipeline, not by mutating historical gate state. UX, APIs, and storage schemas must not expose an “undo gate” capability.

**Rejected alternatives:** Allowing operators to undo failed gates was rejected because the TRD text explicitly forbids undo. Providing automatic gate reset after retries was rejected because it mutates the meaning of recorded decisions. Soft-delete or hidden reversal of gate entries was rejected because it undermines audit integrity.

## SECURITY_REFUSAL is terminal for the active PR flow
**Status:** Accepted

**Context:** The mandatory security controls specify that SECURITY_REFUSAL rules must be present in generation prompts and that SECURITY_REFUSAL in output must stop the PR, gate, and log, with no auto-bypass. ConsensusDevAgent is part of the generation and arbitration path and therefore must enforce this uniformly.

**Decision:** When ConsensusDevAgent observes SECURITY_REFUSAL in model output or a security-control path that requires refusal, it must immediately stop the active PR flow, create or update the gate state, and emit an audit log entry. Never auto-bypass, auto-retry past the refusal, or silently continue.

**Consequences:** Generation and arbitration logic must be able to short-circuit all downstream actions on refusal. The subsystem must preserve the refusal artifact for audit and operator review. Any retry or continuation must begin as a new explicit action consistent with gate rules, not as hidden continuation of the refused flow.

**Rejected alternatives:** Automatically falling back to another model after a refusal was rejected because the controls require stop, gate, and log. Suppressing refusal text and continuing was rejected because it violates mandatory security behavior. Treating refusal as a warning instead of a terminal event was rejected because it weakens the gate model.

## Human gate card required when flagged content is used
**Status:** Accepted

**Context:** The mandatory security controls specify that when flagged chunk content is used in generation, a gate card must be presented to the operator before proceeding. ConsensusDevAgent may consume or arbitrate generated content and therefore must carry this obligation through its flow.

**Decision:** Require ConsensusDevAgent to halt progression and surface a gate card to the operator before proceeding whenever flagged content is incorporated into generation or downstream decision-making.

**Consequences:** The subsystem must track provenance of input chunks and know when flagged content influences output. It must support a pre-progression hold state pending operator visibility. Silent use of flagged material is prohibited even if the resulting output appears valid.

**Rejected alternatives:** Logging flagged-content usage without operator gating was rejected because the controls require a gate card before proceeding. Allowing the model to self-certify flagged usage as safe was rejected because operator visibility is mandatory. Deferring disclosure until after code generation was rejected because the control is explicitly pre-proceeding.

## Untrusted PR review comments must remain explicitly labeled
**Status:** Accepted

**Context:** The security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent will consume review feedback during review, arbitration, or iteration, and must preserve this trust boundary.

**Decision:** Preserve and propagate the explicit `[UNTRUSTED REVIEWER COMMENT]` label on PR review comment content whenever ConsensusDevAgent includes such content in prompts, summaries, or decision inputs.

**Consequences:** The subsystem must not normalize away, strip, or paraphrase away the untrusted marker when passing reviewer content into model contexts. Prompt construction and summarization routines must maintain trust annotations. Downstream logic must assume reviewer comments are untrusted unless separately verified.

**Rejected alternatives:** Treating all review comments as trusted repository context was rejected because the controls explicitly classify them as untrusted in prompts. Replacing the label with internal metadata only was rejected because the requirement is prompt-visible labeling. Omitting review comments entirely was rejected because review feedback is still operationally useful when properly labeled.

## Security review is mandatory before completion
**Status:** Accepted

**Context:** The build pipeline defines a 3-pass review sequence: correctness, performance, and security. The security controls additionally state that all generated code passes Pass 3 security review including bandit. ConsensusDevAgent must not consider implementation complete before this pass succeeds.

**Decision:** Require ConsensusDevAgent to route all generated code through the full 3-pass review pipeline and specifically through Pass 3 security review, including bandit, before considering a PR eligible for completion or merge progression.

**Consequences:** The subsystem cannot mark code generation success as final delivery. Any workflow state claiming completion must depend on successful security review. Tooling integration for bandit and other Pass 3 checks is mandatory where the subsystem manages generated code outcomes.

**Rejected alternatives:** Ending the subsystem’s responsibility at code generation was rejected because the pipeline defines review as part of the core loop. Making security review optional for low-risk changes was rejected because the controls say all generated code must pass Pass 3. Running only correctness review was rejected because it omits required passes.

## File writes must be path-validated
**Status:** Accepted

**Context:** The security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may materialize generated code, plans, or intermediate artifacts and therefore must enforce this on all writes it initiates.

**Decision:** Validate every filesystem write path with `path_security.validate_write_path()` before ConsensusDevAgent creates, modifies, or overwrites any file.

**Consequences:** All write operations in the subsystem must be centralized or wrapped so validation cannot be bypassed accidentally. Raw file writes without validation are non-compliant. This constrains implementation toward explicit path-handling abstractions and away from ad hoc direct writes.

**Rejected alternatives:** Validating only user-supplied paths was rejected because the control applies to every file path before write. Relying on repository-relative path joins without validation was rejected because path traversal and mis-targeted writes remain possible. Post-write auditing was rejected because prevention is required, not merely detection.

## Audit trail over mutable history
**Status:** Accepted

**Context:** The stage contracts reference error escalation and an audit trail schema, and gate decisions are explicitly non-undoable. ConsensusDevAgent must therefore preserve an append-only history of actions and outcomes sufficient to explain how consensus, gating, and progression occurred.

**Decision:** Record ConsensusDevAgent stage actions, gate outcomes, security refusals, and escalations as append-only audit events rather than mutable status replacements.

**Consequences:** Data models must support historical event retention and reconstruction of the execution path. Current status may be derivable for convenience, but it must not replace the underlying event history. This aligns with immutable gate decisions and supports forensic review.

**Rejected alternatives:** Maintaining only latest-state records was rejected because it cannot faithfully represent non-undoable gate history. Allowing in-place mutation of prior decision records was rejected because it weakens traceability. Relying solely on external logs was rejected because subsystem-level audit semantics must be part of the design.