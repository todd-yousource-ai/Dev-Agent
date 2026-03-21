# DECISIONS.md

## Repository structure and source-of-truth boundaries
**Status:** Accepted

**Context:** The ConsensusDevAgent subsystem operates within a repository that separates requirements, standards, implementation, and platform-specific code. The TRDs define that all TRDs and PRDs live under `forge-docs/`, while the repository layout also reserves `forge-standards/` for governing engineering documents and `src/` for Python backend implementation. Clear boundaries are required so ConsensusDevAgent can locate authoritative inputs and write outputs without ambiguity.

**Decision:** Treat `forge-docs/` as the exclusive source of truth for TRDs and PRDs, `forge-standards/` as the exclusive location for engineering governance documents including `DECISIONS.md`, and `src/` as the implementation root for the ConsensusDevAgent backend. Do not store implementation code in `forge-docs/`, and do not store product requirements or technical requirements outside `forge-docs/`.

**Consequences:** ConsensusDevAgent must read requirements from `forge-docs/` before planning or implementation. Any code generation, review, orchestration, or persistence for this subsystem must target `src/` unless explicitly part of another reserved top-level area. Tooling, prompts, and path validation must enforce these write boundaries. Documentation discovery logic can be deterministic because document classes are directory-scoped.

**Rejected alternatives:**  
- Co-locating PRDs/TRDs with implementation code in `src/`: rejected because it weakens source-of-truth separation and increases risk of generated code mutating requirements artifacts.  
- Storing decisions inside subsystem-local folders: rejected because governance documents are repository-wide standards and must remain centrally discoverable under `forge-standards/`.  
- Allowing flexible document placement anywhere in the repository: rejected because it makes planning, audit, and path-security enforcement unreliable.

## Gate decisions are final and must never be auto-undone
**Status:** Accepted

**Context:** The build pipeline explicitly states there is no undo on gate decisions. Security controls also require stopping and gating on certain outputs such as `SECURITY_REFUSAL`. Because ConsensusDevAgent participates in generation, arbitration, and review, it must implement this rule consistently and audibly.

**Decision:** Treat every gate decision as terminal for the current execution path. Never auto-bypass, auto-reopen, auto-clear, or silently reverse a gate once issued. Require an explicit new operator action or new pipeline execution to proceed after a gate.

**Consequences:** ConsensusDevAgent must model gate state as immutable within a run. Retry logic may not invalidate a prior gate. UI, logs, and audit records must present gated outcomes as final for that run. Any workflow branch encountering `SECURITY_REFUSAL` or other terminal gate conditions must stop PR progression immediately.

**Rejected alternatives:**  
- Allowing automated retries to clear failed gates: rejected because it violates the documented “no undo” rule and weakens auditability.  
- Permitting lower-severity components to override higher-severity gates: rejected because it creates inconsistent enforcement and unsafe escalation semantics.  
- Treating gates as warnings unless confirmed by an operator: rejected because the TRDs require gating behavior, not advisory-only behavior.

## ConsensusDevAgent must align to the staged build pipeline
**Status:** Accepted

**Context:** The repository build pipeline is the core loop, with explicit stages from Scope through Merge. ConsensusDevAgent exists within a larger multi-stage system and must not invent a competing workflow. Its responsibilities must fit the documented sequence, especially around code generation and review.

**Decision:** Implement ConsensusDevAgent as a subsystem that operates only within the established pipeline stage contracts, with primary participation in PR planning, code generation, arbitration support, and review-related stages. Do not introduce ad hoc stages, reorder canonical stages, or permit subsystem-local shortcuts that skip required pipeline stages.

**Consequences:** Inputs and outputs for ConsensusDevAgent must be stage-aware and compatible with upstream and downstream orchestration. The subsystem must expect gating and audit obligations from the pipeline. Any internal optimizations must preserve externally visible stage order and semantics.

**Rejected alternatives:**  
- Designing ConsensusDevAgent as a standalone end-to-end workflow engine: rejected because the repository already defines the canonical build pipeline.  
- Allowing direct jump from planning to merge for “simple” changes: rejected because it bypasses required review and gate semantics.  
- Embedding subsystem-specific hidden stages in the public pipeline: rejected because it obscures auditability and breaks contract clarity.

## Claude-prevails generation arbitration for PRD generation is not generalized to code generation
**Status:** Accepted

**Context:** The documented pipeline specifies “both models, Claude wins” for PRD generation, while code generation is described as parallel generation with arbitration. ConsensusDevAgent must not collapse these distinct contracts into a single winner-selection rule.

**Decision:** Preserve stage-specific arbitration rules. Use the documented “Claude wins” rule only where explicitly defined for PRD generation, and implement code-generation arbitration as a separate mechanism appropriate to the Code Gen stage rather than inheriting the PRD-generation precedence rule.

**Consequences:** ConsensusDevAgent must encode stage-aware arbitration policies. It cannot assume that a model-precedence rule used for documents applies to implementation artifacts. Audit logs must record which arbitration policy was applied and why.

**Rejected alternatives:**  
- Applying “Claude wins” uniformly across all stages: rejected because the pipeline explicitly distinguishes PRD generation from code generation arbitration.  
- Eliminating arbitration and selecting the first successful output: rejected because it reduces quality controls and contradicts the parallel generation/arbitration design.  
- Using a dynamic undocumented precedence rule per run: rejected because it harms reproducibility and auditability.

## Three-pass review is mandatory after code generation
**Status:** Accepted

**Context:** The build pipeline requires a 3-pass review sequence: correctness, then performance, then security. Security controls further require that generated code pass security review including bandit. ConsensusDevAgent must honor this ordered review contract.

**Decision:** Require all ConsensusDevAgent-generated code to pass the full three-pass review sequence in order: correctness first, performance second, security third. Do not merge, advance, or treat code as complete if any pass is skipped, reordered, or failed.

**Consequences:** The subsystem must produce artifacts suitable for sequential review and must preserve state between passes. Failures in any pass must block advancement. Security review is mandatory even if earlier passes are clean. Integration with review tooling must support pass-specific evidence and outcomes.

**Rejected alternatives:**  
- Running review passes in parallel: rejected because the documented contract specifies an ordered sequence.  
- Performing only correctness and security review: rejected because performance review is an explicit required pass.  
- Allowing security review only for “sensitive” changes: rejected because generated code must always pass Pass 3.

## SECURITY_REFUSAL is a hard-stop signal
**Status:** Accepted

**Context:** Mandatory security controls specify that `SECURITY_REFUSAL` in LLM output must stop the PR, gate, and log, and must never be auto-bypassed. Because ConsensusDevAgent directly consumes and produces model outputs, this rule must be implemented as a first-class invariant.

**Decision:** Treat any occurrence of `SECURITY_REFUSAL` in relevant model output as an immediate hard-stop event. Stop further PR progression, create a gate, and write an audit log entry. Never suppress, reinterpret, trim, or automatically recover from this signal.

**Consequences:** Output parsers, orchestrators, and reviewers in ConsensusDevAgent must scan for `SECURITY_REFUSAL` before proceeding. Partial outputs accompanying the signal must not be treated as usable implementation results. Operators must be informed through the gate path rather than silent failure handling.

**Rejected alternatives:**  
- Ignoring `SECURITY_REFUSAL` when surrounding content appears valid: rejected because the security rule is explicit and mandatory.  
- Retrying the same prompt automatically after `SECURITY_REFUSAL`: rejected because it constitutes an auto-bypass of a gate condition.  
- Downgrading the event to a warning in non-production branches: rejected because the control is not branch-conditional.

## All file writes must be path-validated before execution
**Status:** Accepted

**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent performs code generation and may create or modify files; therefore path validation must be universal and non-optional.

**Decision:** Validate every destination path with `path_security.validate_write_path()` immediately before any filesystem write initiated by ConsensusDevAgent. Do not rely solely on earlier planning-time validation or caller assertions.

**Consequences:** File-writing code paths must centralize through a validated write abstraction. Even internally computed or previously approved paths require revalidation at write time. This constrains performance optimizations that would otherwise batch or defer validation without per-write checks.

**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated and transformed paths can also become unsafe.  
- Validating once at the start of a run: rejected because paths may change across stages or be influenced by intermediate outputs.  
- Relying on repository-relative path joins without explicit validation: rejected because normalization alone does not enforce policy.

## Untrusted review content must remain explicitly labeled in prompts and flows
**Status:** Accepted

**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks used in generation must gate to the operator before proceeding. ConsensusDevAgent consumes review feedback and may feed it back into generation or analysis, creating prompt-injection risk.

**Decision:** Preserve explicit untrusted-data labeling for all reviewer-supplied or externally sourced review content passed into ConsensusDevAgent prompts or decision flows. When flagged chunks are used in generation, gate to the operator before continuing.

**Consequences:** Prompt assembly and review-ingestion layers must track provenance and attach mandatory labels. ConsensusDevAgent cannot flatten trusted and untrusted inputs into a single undifferentiated context block. Some automation paths will intentionally stop for operator review when flagged content is involved.

**Rejected alternatives:**  
- Sanitizing review comments and then treating them as trusted: rejected because provenance remains external and risk persists.  
- Omitting labels for internal repository reviewers: rejected because trust is based on source class, not convenience.  
- Automatically excluding all untrusted comments from generation: rejected because useful review signal would be lost and the TRD instead requires explicit labeling and gating when flagged content is used.