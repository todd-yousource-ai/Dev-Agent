# DECISIONS.md

## [Keep all TRDs and PRDs in `forge-docs/` as the sole planning source]
**Status:** Accepted  
**Context:** The repository structure defines `forge-docs/` as the location where all TRDs and PRDs live, and those documents must be read before building. The ConsensusDevAgent depends on stable, discoverable planning inputs to execute gated generation and review workflows consistently.  
**Decision:** Treat `forge-docs/` as the sole source of truth for TRD and PRD planning artifacts. Require the ConsensusDevAgent to read from `forge-docs/` before planning, generation, or review actions that depend on requirements. Do not source planning documents from ad hoc locations.  
**Consequences:** Implementation must hard-code or centrally configure `forge-docs/` as the canonical document root for requirement inputs. Planning logic, document discovery, and validation must fail closed when required artifacts are missing or misplaced. Repository traversal for requirements must not infer alternate document stores.  
**Rejected alternatives:**  
- Storing TRDs/PRDs alongside code in subsystem folders: rejected because it fragments the planning source of truth and increases drift.  
- Allowing arbitrary document paths supplied at runtime: rejected because it weakens determinism and auditability.  
- Duplicating planning docs into agent-specific directories: rejected because duplication creates version skew and review ambiguity.

## [Record gate decisions as irreversible]
**Status:** Accepted  
**Context:** The build pipeline explicitly states there is no undo on gate decisions. ConsensusDevAgent participates in gated workflow execution and must preserve operator trust, auditability, and stage integrity.  
**Decision:** Implement all gate decisions as irreversible. Once a gate is recorded as pass, fail, stop, or operator-held, do not provide an undo, revert, or silent overwrite mechanism. Require any subsequent change in direction to be represented as a new decision or new pipeline progression event, not mutation of prior gate history.  
**Consequences:** Data models must treat gate outcomes as append-only records. UI and API surfaces must not expose “undo gate” behavior. Recovery flows must create new audit entries rather than editing or deleting prior decisions. Operators must be able to see the full sequence of gate outcomes.  
**Rejected alternatives:**  
- Allowing operators to undo accidental gate actions: rejected because it breaks audit integrity and conflicts with explicit TRD guidance.  
- Permitting administrative mutation of gate history: rejected because privileged edits would undermine trust in the pipeline trail.  
- Soft-delete semantics for gate records: rejected because hidden reversals are still reversals and create ambiguity.

## [Enforce stage progression according to the defined build pipeline]
**Status:** Accepted  
**Context:** The build pipeline is the core loop triggered by `/prd start <intent>` and is organized into ordered stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent completion flow. ConsensusDevAgent must coordinate within this structure rather than inventing custom execution order.  
**Decision:** Implement ConsensusDevAgent workflow orchestration to follow the declared stage order and stage boundaries from the build pipeline. Do not skip, reorder, or merge stages unless a governing TRD explicitly permits it. Escalate errors and hold progression at the current stage when contracts are not satisfied.  
**Consequences:** Orchestration code must model explicit stage state and transition guards. Inputs and outputs for each stage must be validated before advancing. Agent coordination must align to stage contracts rather than freeform task execution. Audit records must identify stage transitions unambiguously.  
**Rejected alternatives:**  
- Allowing opportunistic stage skipping when confidence is high: rejected because it weakens process guarantees and review coverage.  
- Running stages in a dynamically inferred order: rejected because it reduces predictability and complicates audit analysis.  
- Collapsing planning and generation into a single agent step: rejected because it obscures responsibility boundaries and violates the documented pipeline.

## [Treat SECURITY_REFUSAL as a hard stop]
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL rules in every generation system prompt. If SECURITY_REFUSAL appears in output, the PR must stop, gate, and log; it must never be auto-bypassed. ConsensusDevAgent must preserve this behavior across its generation and arbitration flows.  
**Decision:** Detect SECURITY_REFUSAL as a terminal security event for the current generation or review action. Immediately stop the PR flow, raise a gate for operator handling, and write an audit log entry. Never auto-bypass, auto-retry past, suppress, or reinterpret SECURITY_REFUSAL as a warning.  
**Consequences:** Prompting, parsing, and orchestration layers must explicitly inspect model outputs for SECURITY_REFUSAL. Pipeline control flow must route directly into stop-and-gate behavior. Retry logic must not continue the same action without explicit operator intervention and a new tracked attempt.  
**Rejected alternatives:**  
- Treating SECURITY_REFUSAL as advisory and continuing with warnings: rejected because the mandatory security control defines it as a stop condition.  
- Automatically switching to another model on SECURITY_REFUSAL: rejected because that would constitute an implicit bypass.  
- Stripping SECURITY_REFUSAL tokens before downstream processing: rejected because it hides a critical security signal.

## [Gate when flagged chunks or untrusted review content influence generation]
**Status:** Accepted  
**Context:** Security controls require that when flagged chunk content is used in generation, a gate card must be presented to the operator before proceeding. PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts. ConsensusDevAgent handles multi-source context assembly and must distinguish trusted from untrusted inputs.  
**Decision:** Mark flagged chunks and untrusted reviewer content explicitly in prompt construction and provenance metadata. If flagged chunk content is included for generation, require an operator gate before proceeding. Preserve untrusted review comments with the required label and do not upgrade their trust level implicitly.  
**Consequences:** Context assembly must track provenance per chunk. Prompt builders must support trust labeling. The subsystem must interrupt automatic progression when flagged chunks are selected for use. Audit trails must capture which untrusted or flagged inputs were included.  
**Rejected alternatives:**  
- Treating all retrieved context as equally trusted: rejected because it violates mandatory security distinctions.  
- Silently including flagged content without operator gating: rejected because the security control requires explicit gating.  
- Dropping reviewer comments entirely: rejected because review feedback is still useful if properly labeled and handled.

## [Validate every write path before file output]
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent produces documents, patches, and code artifacts and therefore must not rely on caller discipline for filesystem safety.  
**Decision:** Invoke `path_security.validate_write_path()` on every path before any write, overwrite, move-into-place, or generated artifact materialization performed by ConsensusDevAgent. Treat validation failure as a hard error and do not attempt fallback writes to unvalidated paths.  
**Consequences:** File-writing abstractions must centralize path validation and forbid bypass. Temporary-file and atomic-write implementations must validate both temporary and final paths as applicable. Tests must verify that all write surfaces enforce this contract.  
**Rejected alternatives:**  
- Validating only user-supplied paths: rejected because generated or derived paths can also be unsafe.  
- Relying on repository-root prefix checks instead of the mandated validator: rejected because it diverges from the required control and risks incomplete coverage.  
- Allowing internal trusted components to bypass validation: rejected because mandatory controls apply universally.

## [Require security review coverage for all generated code]
**Status:** Accepted  
**Context:** Mandatory security controls state that all generated code must pass Pass 3 security review, including bandit. ConsensusDevAgent coordinates code generation and review, so it must not consider code generation complete before required security analysis succeeds or is formally gated.  
**Decision:** Require every generated code change to enter and complete Pass 3 security review, including execution of bandit where applicable, before the subsystem reports success for that PR flow. If security review fails or cannot run, stop progression and gate according to pipeline rules.  
**Consequences:** Completion criteria for generated code must include security review artifacts, not just compilation or tests. Review orchestration must preserve pass ordering and failure semantics. “Successful generation” in APIs and UI must exclude outputs lacking completed Pass 3 review.  
**Rejected alternatives:**  
- Making security review optional for low-risk changes: rejected because the control applies to all generated code.  
- Running only lightweight static checks instead of Pass 3: rejected because it reduces the mandated review scope.  
- Marking code complete before security pass and reconciling later: rejected because it creates false-positive success states.

## [Use append-only audit trails for stage, gate, and security events]
**Status:** Accepted  
**Context:** The pipeline references full stage contracts, error escalation, and an audit trail schema. Combined with the “no undo” requirement and mandatory stop-and-log security behavior, ConsensusDevAgent needs durable, immutable event recording.  
**Decision:** Implement audit logging for stage transitions, gate decisions, security-triggered stops, operator interventions, and document/code generation events as append-only records. Do not mutate or delete historical audit entries as part of normal operation.  
**Consequences:** Persistence models must support immutable event history and ordered reconstruction of execution. Operator and debugging tools must read history as a sequence of events rather than a mutable current-state blob alone. Compliance and incident analysis become possible without hidden edits.  
**Rejected alternatives:**  
- Storing only the latest mutable status per PR or stage: rejected because it loses decision history and weakens auditability.  
- Logging only failures: rejected because successful transitions are necessary to reconstruct process integrity.  
- Allowing log compaction that removes original events: rejected because it conflicts with irreversible gate history and forensic needs.

## [Constrain ConsensusDevAgent to repository-standard locations]
**Status:** Accepted  
**Context:** The repository layout defines standard top-level locations, including `forge-docs/` for planning artifacts, `forge-standards/` for standards such as `DECISIONS.md`, `src/` for Python backend code, and `tests/` for pytest suites. ConsensusDevAgent must integrate without inventing conflicting repository conventions.  
**Decision:** Implement ConsensusDevAgent artifacts within the declared repository layout. Place backend implementation under `src/`, tests under `tests/`, and standards or architecture-facing documentation updates under `forge-standards/` when applicable. Do not create alternate top-level roots for equivalent concerns without an explicit governing decision.  
**Consequences:** Code generation and file planning logic must target the standard paths. Review and validation logic can assume stable repository zones. Future contributors receive a predictable structure for locating subsystem code and policies.  
**Rejected alternatives:**  
- Creating a dedicated top-level `agents/` tree for subsystem code: rejected because it duplicates the purpose of `src/` and fragments backend implementation.  
- Placing tests adjacent to generated modules by default: rejected because the repository standard already defines `tests/` as the Python test suite location.  
- Storing standards near implementation code: rejected because `forge-standards/` exists to centralize repository-wide standards.