# DECISIONS.md

## [ConsensusDevAgent documentation source of truth]
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with a strict separation between specification artifacts and implementation. The TRDs and PRDs define expected behavior and must be consulted before building or modifying subsystem behavior. A consistent source of truth is required so the agent does not infer process or contract details from implementation alone.  
**Decision:** Treat `forge-docs/` as the authoritative source for all TRDs and PRDs, and require ConsensusDevAgent design and implementation decisions to align with those documents before code changes are made.  
**Consequences:** Implementation must read from and remain traceable to documents in `forge-docs/`. The subsystem must not treat code, comments, prompts, or generated artifacts as overriding documented requirements. Any ambiguity must be resolved against TRDs/PRDs rather than local convenience.  
**Rejected alternatives:**  
- Using implementation in `src/` as the operational source of truth — rejected because it allows drift from approved requirements.  
- Splitting authority between docs and prompts — rejected because it creates conflicting interpretations and weakens auditability.  
- Allowing generated plans to redefine requirements — rejected because planning outputs are derivative, not normative.

## [ConsensusDevAgent implementation location]
**Status:** Accepted  
**Context:** Repository structure is explicitly defined. To preserve discoverability and build consistency, each subsystem must live in the prescribed top-level areas. ConsensusDevAgent is part of the Python backend runtime rather than the macOS shell.  
**Decision:** Implement ConsensusDevAgent in the Python backend under `src/`, with tests under `tests/`, and place any governing architecture documentation in `forge-standards/`.  
**Consequences:** The subsystem must not be implemented primarily inside `ForgeAgent/` or in ad hoc directories. Python packaging, imports, CI execution, and test discovery must assume `src/` and `tests/` conventions. Documentation updates that constrain behavior belong in `forge-standards/` or `forge-docs/` as appropriate.  
**Rejected alternatives:**  
- Implementing ConsensusDevAgent inside `ForgeAgent/` — rejected because the macOS shell is not the backend execution environment.  
- Creating a separate top-level service directory — rejected because it violates the declared repository layout.  
- Storing decision records beside source files — rejected because governance documents have a dedicated standards location.

## [ConsensusDevAgent must participate in the staged build pipeline]
**Status:** Accepted  
**Context:** The system build loop is organized into named stages from scope through review. ConsensusDevAgent exists within this controlled workflow and cannot operate as an unconstrained autonomous coding agent. Pipeline participation is necessary for auditability, stage contracts, and operator control.  
**Decision:** Constrain ConsensusDevAgent to operate only within the defined build pipeline stages and honor stage boundaries, inputs, outputs, and escalation expectations from the documented pipeline.  
**Consequences:** The subsystem may not skip directly from intent to code generation without prior planning stages, and may not bypass the 3-pass review stage. State, logs, and decisions must remain attributable to a pipeline stage. Integration points must reflect stage sequencing rather than free-form orchestration.  
**Rejected alternatives:**  
- Letting the agent dynamically choose its own workflow — rejected because it undermines repeatability and audit trails.  
- Collapsing planning and implementation into a single generation step — rejected because the repository explicitly requires staged decomposition.  
- Treating review as optional for low-risk changes — rejected because the documented pipeline defines review as part of the core loop.

## [No undo on gate decisions]
**Status:** Accepted  
**Context:** The requirements explicitly state that there is no undo on gate decisions. This is a safety and governance constraint that must be documented because gating events affect security, trust, and operator oversight. Reversibility would weaken audit integrity and permit silent bypass after a stop condition.  
**Decision:** Treat every gate decision made by ConsensusDevAgent or upstream review/security mechanisms as final and non-reversible within automated execution; never implement automatic undo, rollback of gate state, or auto-bypass after a gate is issued.  
**Consequences:** Once gated, the subsystem must stop or hold at the gate and require explicit external/operator intervention through whatever approved process exists outside automated execution. State models must represent gate decisions as terminal for the current run path. UX, logs, and APIs must not expose an "undo gate" control. Recovery must occur by a new explicit run, not by reopening the gated path in place.  
**Rejected alternatives:**  
- Allowing the agent to self-clear transient gates — rejected because the requirement explicitly forbids undo.  
- Supporting operator-triggered in-place ungate inside the same automated run — rejected because it weakens finality and complicates audit trails.  
- Automatically downgrading some gates to warnings — rejected because gate semantics must remain strict and predictable.

## [SECURITY_REFUSAL is a hard stop]
**Status:** Accepted  
**Context:** Security controls mandate that `SECURITY_REFUSAL` appearing in LLM output is not advisory. It must stop the PR, create a gate, and be logged. ConsensusDevAgent must enforce this consistently because it coordinates generation and review outputs that may contain refusal signals.  
**Decision:** Implement `SECURITY_REFUSAL` handling as an unconditional hard-stop condition: stop the affected PR flow immediately, create a gate, log the event, and never auto-bypass or continue generation within that execution path.  
**Consequences:** Parsers, orchestrators, and stage runners must inspect model outputs for `SECURITY_REFUSAL`. Any detection must terminate downstream work for the affected item and produce an auditable record. The subsystem cannot reinterpret, suppress, or sanitize away the refusal to keep processing.  
**Rejected alternatives:**  
- Treating `SECURITY_REFUSAL` as model commentary — rejected because security controls require a stop.  
- Retrying automatically with a softer prompt — rejected because it functions as an auto-bypass.  
- Continuing non-security stages while recording a warning — rejected because the requirement mandates a gate and stop.

## [Untrusted content must remain explicitly labeled and gated]
**Status:** Accepted  
**Context:** Security controls distinguish trusted system inputs from untrusted review comments and flagged chunks. ConsensusDevAgent may consume reviewer comments or flagged content during planning, arbitration, or code review, creating prompt injection and provenance risks unless trust boundaries are preserved.  
**Decision:** Preserve explicit trust labeling for untrusted inputs, include required markers such as `[UNTRUSTED REVIEWER COMMENT]` where applicable, and gate to the operator before proceeding when flagged chunks are used in generation.  
**Consequences:** Prompt assembly, review ingestion, and generation context builders must carry provenance metadata through the pipeline. The subsystem must not silently merge untrusted review text into trusted instructions. Use of flagged chunks in generation requires an operator gate before continuing.  
**Rejected alternatives:**  
- Normalizing all inputs into a single prompt without labels — rejected because it erases trust boundaries.  
- Dropping all untrusted inputs entirely — rejected because reviewer feedback and flagged material may still be operationally necessary.  
- Allowing the model to determine whether a chunk is trusted — rejected because trust classification is a system control, not a model judgment.

## [Generated code writes must pass path security validation]
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent coordinates code generation and file materialization, so path validation must be enforced centrally and without exception to prevent traversal or out-of-scope writes.  
**Decision:** Validate every generated or modified write target with `path_security.validate_write_path()` before any filesystem write occurs, with no bypass path for “known safe” or internally generated paths.  
**Consequences:** All file-writing code paths in the subsystem must route through a validated write abstraction or equivalent enforcement point. Direct file writes are non-compliant unless they invoke the validator first. Failures must halt the write and surface a security-relevant error.  
**Rejected alternatives:**  
- Validating only model-suggested paths — rejected because internal transformations can also introduce unsafe paths.  
- Allowing bypass for repository-relative paths — rejected because relative paths can still be malicious or malformed.  
- Relying on OS-level sandboxing alone — rejected because the documented control requires explicit application-level validation.

## [Security review is mandatory for all generated code]
**Status:** Accepted  
**Context:** Mandatory controls state that all generated code must pass Pass 3 security review, including bandit. Since ConsensusDevAgent participates in code generation and arbitration, it must not consider implementation complete before the security pass succeeds.  
**Decision:** Require every generated code change produced through ConsensusDevAgent to pass the defined security review stage, including bandit and any documented Pass 3 checks, before the change can be considered accepted by the pipeline.  
**Consequences:** The subsystem must integrate with or block on Pass 3 review results. It cannot mark generation successful based only on correctness or performance. Pipelines and status models must distinguish “generated” from “accepted after security review.”  
**Rejected alternatives:**  
- Running security review only for risky files or dependencies — rejected because the control applies to all generated code.  
- Making bandit advisory — rejected because Pass 3 is mandatory.  
- Deferring security review until after merge — rejected because the pipeline requires review before acceptance.

## [Consensus outputs must remain auditable at stage and gate boundaries]
**Status:** Accepted  
**Context:** The build pipeline references audit trails, error escalation, and stage contracts. ConsensusDevAgent, by nature, synthesizes and arbitrates between model outputs; without explicit audit records, it would be impossible to reconstruct why a decision was made, especially when gating or selecting among alternatives.  
**Decision:** Record auditable artifacts for stage transitions, consensus/arbitration outcomes, security stops, and gate events in a form that preserves provenance and supports reconstruction of the decision path.  
**Consequences:** The subsystem must emit structured logs or equivalent durable records at key boundaries rather than only final outputs. Arbitration cannot be a black box; selected outputs, rejected outputs, and stop reasons must be attributable. This may increase storage and implementation complexity, but it is required for compliance and debugging.  
**Rejected alternatives:**  
- Logging only final generated files — rejected because it does not explain stage decisions or gates.  
- Keeping ephemeral in-memory traces only — rejected because audit trails must survive process termination.  
- Recording only errors and not successful consensus decisions — rejected because acceptance paths also require reconstruction.

## [Claude-wins document generation rule must not be generalized beyond its documented scope]
**Status:** Accepted  
**Context:** The pipeline specifies that in PRD generation, both models may generate and Claude wins. This is a stage-specific rule. ConsensusDevAgent may use multiple models and arbitration, but undocumented global winner rules would create hidden behavior and violate stage contracts.  
**Decision:** Apply the “both models, Claude wins” rule only to the documented PRD generation stage, and do not generalize it as a universal arbitration policy for all ConsensusDevAgent decisions unless separately documented.  
**Consequences:** Multi-model consensus logic must be configurable by stage and contract. Implementers cannot assume a single model has blanket precedence across planning, code generation, review, or gating. Stage-specific arbitration behavior must be explicit.  
**Rejected alternatives:**  
- Making Claude the global winner for every conflict — rejected because the documents only specify this for PRD generation.  
- Forcing all stages into equal-weight voting — rejected because some stages have explicit non-voting precedence rules.  
- Leaving precedence implicit per implementation — rejected because hidden arbitration rules reduce predictability and auditability.