# DECISIONS.md

## [ConsensusDevAgent repository boundaries and source-of-truth]
**Status:** Accepted  
**Context:** The subsystem must operate within a fixed repository structure so that documents, implementation, standards, tests, and CI assets are discoverable by both agents and operators. The TRDs and README define explicit locations for source documents and code.  
**Decision:** Treat `forge-docs/` as the source of truth for all TRDs and PRDs, `forge-standards/` as the source of truth for implementation constraints, `src/` as the Python backend location, `ForgeAgent/` as the macOS app shell location, `ForgeAgentTests/` as XCTest location, `tests/` as pytest location, and `.github/workflows/` as CI workflow location. Do not introduce alternative canonical locations for these artifact classes.  
**Consequences:** ConsensusDevAgent must read requirements from `forge-docs/` before planning or implementation, must write design constraints into `forge-standards/`, and must place code and tests only in their designated directories. Tooling, prompts, and path validation must assume this layout.  
**Rejected alternatives:**  
- Allowing TRDs/PRDs to be duplicated under feature directories was rejected because it creates ambiguity about the source of truth.  
- Allowing subsystem-specific standards files outside `forge-standards/` was rejected because it fragments implementation constraints.  
- Co-locating backend code with document artifacts was rejected because it weakens auditability and repository discipline.

## [Gate decisions are irreversible]
**Status:** Accepted  
**Context:** The build pipeline specification explicitly states there is no undo on gate decisions. Security and auditability depend on preventing silent reversal of stopped or escalated states.  
**Decision:** Treat all gate decisions in ConsensusDevAgent as append-only and irreversible. Once a gate is entered, failed, escalated, or stopped, the subsystem must not auto-clear, auto-retry past, or mutate history to represent the gate as undone. Any continuation must occur through a new explicit operator-mediated decision path, preserving the prior gate outcome in the audit trail.  
**Consequences:** State machines, persistence models, and operator UX must model gate outcomes as immutable historical facts. Retry logic must create new attempts rather than overwriting prior outcomes. The audit log must preserve the full chronology of gate events.  
**Rejected alternatives:**  
- Supporting “undo gate” operations was rejected because it conflicts with the stated pipeline rule and weakens audit integrity.  
- Allowing agents to automatically reopen failed gates after code changes was rejected because it would bypass operator control and blur decision provenance.  
- Deleting failed gate records on success was rejected because it destroys audit history.

## [Pipeline execution must align to staged contracts]
**Status:** Accepted  
**Context:** The subsystem participates in a larger build pipeline with named stages and stage-specific responsibilities. Correct coordination requires a shared understanding of progression and handoff boundaries.  
**Decision:** Implement ConsensusDevAgent behavior as stage-aware processing aligned to the defined pipeline: Scope, PRD Plan, PRD Generation, PR Plan, Code Generation, 3-Pass Review, and subsequent gated progression. Do not collapse, reorder, or skip stage contracts in subsystem orchestration without an explicit standards update.  
**Consequences:** Consensus decisions, arbitration, and outputs must be attributable to a pipeline stage. Inputs and outputs should be validated against stage expectations, and failures must escalate according to stage contract rather than ad hoc behavior.  
**Rejected alternatives:**  
- Using a free-form agent loop without stage identity was rejected because it undermines traceability and coordinated escalation.  
- Merging planning and generation stages into a single implementation step was rejected because it breaks the documented decomposition model.  
- Allowing security review to occur opportunistically outside the defined review stage was rejected because it weakens consistency and auditability.

## [Security refusal is a hard stop]
**Status:** Accepted  
**Context:** Mandatory security controls require `SECURITY_REFUSAL` behavior in generation prompts and outputs. The documented rule is explicit: when `SECURITY_REFUSAL` appears in output, the PR must stop, gate, and log, with no automatic bypass.  
**Decision:** Treat any `SECURITY_REFUSAL` emitted by a model, reviewer, or enforcement layer as a terminal hard-stop event for the active PR flow. Immediately stop progression, create a gate card for operator review where applicable, and log the event in the audit trail. Never auto-bypass, suppress, reinterpret, or continue past a `SECURITY_REFUSAL`.  
**Consequences:** ConsensusDevAgent must inspect outputs for `SECURITY_REFUSAL`, surface the event prominently, and prevent downstream actions such as file writes, PR advancement, or merge preparation. Security handling must take precedence over throughput.  
**Rejected alternatives:**  
- Treating `SECURITY_REFUSAL` as a warning was rejected because mandatory controls require a stop.  
- Allowing a second model to override a refusal automatically was rejected because it creates an unauthorized bypass path.  
- Continuing with non-sensitive portions of a PR after refusal was rejected because the control requires stopping the PR flow.

## [Untrusted review content must remain explicitly labeled]
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged content used in generation must be surfaced to the operator before proceeding. This prevents prompt injection and provenance confusion.  
**Decision:** Preserve explicit trust labeling for all untrusted reviewer-sourced content in ConsensusDevAgent prompts, context assembly, and audit records. When flagged chunks are incorporated into generation context, create an operator gate before proceeding. Do not normalize, silently merge, or relabel untrusted review text as trusted instruction.  
**Consequences:** Prompt builders, review ingestion, and consensus logic must track provenance metadata per content chunk. Operator-facing interfaces must expose when untrusted input affected generation.  
**Rejected alternatives:**  
- Stripping labels after ingestion was rejected because it obscures provenance.  
- Treating GitHub review comments as trusted by default was rejected because the security controls explicitly classify them as untrusted.  
- Allowing flagged untrusted chunks into generation without operator gating was rejected because it violates mandatory controls.

## [All file writes must pass path security validation]
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may produce or arbitrate code and document changes across multiple repository areas, making path enforcement essential.  
**Decision:** Require path validation on every write, overwrite, move, or generated artifact emission initiated by ConsensusDevAgent. No file system mutation may occur until the target path has been approved by `path_security.validate_write_path()` or an equivalent centrally approved wrapper that preserves the same guarantee.  
**Consequences:** All writer utilities and code generation sinks must route through validated path helpers. Direct writes, ad hoc path concatenation, and bypass channels are prohibited. Security review can assume path validation is universal rather than best-effort.  
**Rejected alternatives:**  
- Validating only generated code writes and not document writes was rejected because the control applies to every file path before write.  
- Performing validation only at a higher orchestration layer was rejected because lower-level writers could still bypass it.  
- Relying on repository-relative path checks alone was rejected because the mandated control is explicit and stronger.

## [Security review is mandatory for generated code]
**Status:** Accepted  
**Context:** The security controls require that all generated code pass Pass 3 security review, including bandit. ConsensusDevAgent must not treat consensus or model agreement as a substitute for security validation.  
**Decision:** Require every generated-code change set produced or selected by ConsensusDevAgent to pass the defined security review stage, including bandit and any other Pass 3 checks, before the PR can advance. Consensus outcome does not waive or reduce required security review depth.  
**Consequences:** Code generation and arbitration outputs must be reviewable artifacts suitable for Pass 3. The subsystem must preserve enough metadata to connect generated changes to security findings and gate decisions.  
**Rejected alternatives:**  
- Skipping Pass 3 for trivial changes was rejected because the control applies to all generated code.  
- Allowing unanimous multi-model agreement to substitute for security review was rejected because consensus is not a security control.  
- Deferring security review until after merge was rejected because the pipeline requires review before advancement.

## [Consensus outputs must be auditable and stage-linked]
**Status:** Accepted  
**Context:** The pipeline references audit trail requirements, and irreversible gate behavior requires durable history. ConsensusDevAgent introduces arbitration and coordination decisions that must be explainable after the fact.  
**Decision:** Record consensus inputs, model provenance, arbitration outcomes, gate triggers, and stage association in an append-only audit trail sufficient to reconstruct why a decision was made and why progression did or did not occur. Do not emit opaque final decisions without preserving the decision basis.  
**Consequences:** The subsystem must persist metadata beyond final artifacts, including stage identity, refusal events, and operator gates. Observability and storage design must support forensic reconstruction.  
**Rejected alternatives:**  
- Keeping only the final selected output was rejected because it prevents reconstruction of arbitration rationale.  
- Storing audit data only in transient logs was rejected because gate history must persist.  
- Capturing only success-path events was rejected because failures and stops are central to auditability.

## [Operator mediation is required at defined trust and security boundaries]
**Status:** Accepted  
**Context:** The pipeline includes explicit operator confirmation at scope selection, and security controls require operator gating when flagged chunks are used in generation. ConsensusDevAgent therefore cannot be fully autonomous across trust boundaries.  
**Decision:** Require explicit operator mediation whenever the subsystem crosses a documented trust or security boundary, including scope confirmation and use of flagged untrusted content in generation. Do not replace these checkpoints with automatic consensus or heuristic confidence thresholds.  
**Consequences:** UX and orchestration must support pause-and-resume behavior with clear gate cards and context for operator decisions. Throughput is subordinate to controlled advancement at these boundaries.  
**Rejected alternatives:**  
- Fully autonomous continuation through all stages was rejected because documented gates require operator involvement.  
- Using model confidence as a substitute for operator approval was rejected because confidence does not satisfy the control requirement.  
- Sampling operator approval asynchronously after continuation was rejected because gating must occur before proceeding.