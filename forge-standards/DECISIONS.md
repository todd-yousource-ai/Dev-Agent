# DECISIONS.md

## ConsensusDevAgent lives in the Python backend under `src/`
**Status:** Accepted  
**Context:** Repository structure is fixed across the system. The backend implementation belongs in `src/`, while documents live in `forge-docs/`, standards live in `forge-standards/`, the macOS shell lives in `ForgeAgent/`, and tests are split between `tests/` and `ForgeAgentTests/`. The ConsensusDevAgent subsystem must fit this layout so it is discoverable, testable, and consistent with the rest of the platform.  
**Decision:** Implement the ConsensusDevAgent subsystem in the Python backend under `src/`. Place its automated tests under `tests/`. Do not place subsystem source code in `forge-docs/`, `forge-standards/`, or the macOS shell directories.  
**Consequences:** The subsystem is constrained to backend runtime conventions, Python tooling, and pytest-based test coverage. UI-facing behavior must be exposed through backend interfaces rather than implemented directly in the Swift app shell. Documentation for the subsystem must be maintained separately from implementation code.  
**Rejected alternatives:**  
- Implementing ConsensusDevAgent inside `ForgeAgent/` was rejected because the macOS shell is not the system’s backend execution environment.  
- Storing executable logic alongside TRDs in `forge-docs/` was rejected because `forge-docs/` is the source of truth for requirements, not runtime code.  
- Creating a new top-level repository area for agent code was rejected because the repository layout is already prescribed and should not fragment implementation.

## Forge documents are the source of truth before implementation
**Status:** Accepted  
**Context:** The repository explicitly states that all TRDs and PRDs live in `forge-docs/` and must be read before building. ConsensusDevAgent behavior is derived from those documents and must not drift from them.  
**Decision:** Read applicable TRDs and PRDs in `forge-docs/` before implementing or modifying ConsensusDevAgent behavior. Treat those documents as authoritative over inferred behavior, convenience shortcuts, or undocumented local conventions.  
**Consequences:** Implementation work is gated by document review. When code and documents conflict, the subsystem must align to approved documents or trigger document-driven clarification rather than silently diverging. This increases traceability and reduces undocumented behavior in the subsystem.  
**Rejected alternatives:**  
- Treating existing code as the primary source of truth was rejected because repository policy assigns that role to TRDs and PRDs.  
- Allowing implementers to infer missing behavior without checking documents was rejected because it invites drift and weakens auditability.  
- Keeping subsystem-specific requirements only in code comments was rejected because requirements belong in the controlled documentation set.

## ConsensusDevAgent must participate in the staged build pipeline
**Status:** Accepted  
**Context:** The system build loop is explicitly defined as a sequence of stages from scope through PRD planning, PR generation, code generation, 3-pass review, and subsequent gates. ConsensusDevAgent is part of this orchestration domain and must conform to stage contracts rather than inventing an ad hoc workflow.  
**Decision:** Implement ConsensusDevAgent behavior to align with the defined build pipeline stages and their contracts. Do not bypass, collapse, or reorder required stages when generating plans, code, or reviews.  
**Consequences:** The subsystem must preserve stage boundaries, stage-specific outputs, and auditability. Any functionality that creates artifacts or decisions must be attributable to a pipeline stage. This constrains orchestration logic, state transitions, and operator messaging.  
**Rejected alternatives:**  
- A single-step “generate everything” workflow was rejected because it breaks the staged contracts and reduces control.  
- Allowing ConsensusDevAgent to reorder stages opportunistically was rejected because it weakens determinism and audit trail integrity.  
- Making review optional for selected work items was rejected because the pipeline defines required review behavior.

## Gate decisions are final and must never support undo
**Status:** Accepted  
**Context:** The requirements explicitly state “No undo on gate decisions” and repeat that constraint in build pipeline material. Gate decisions are therefore irreversible control points, especially for safety and auditability. ConsensusDevAgent must encode this rule directly and visibly.  
**Decision:** Treat every gate decision made by or within ConsensusDevAgent as immutable. Do not implement undo, rollback, silent reversal, implicit reopening, or automatic bypass of a gate once recorded.  
**Consequences:** The subsystem must model gates as append-only decisions. If later action is needed, it must occur through a new explicit decision or escalation record rather than mutation of prior gate state. UI, API, and persistence layers must all enforce finality. Audit logs remain consistent because prior gate decisions cannot be rewritten.  
**Rejected alternatives:**  
- Supporting operator “undo” for convenience was rejected because the requirement explicitly forbids it.  
- Allowing privileged internal rollback of gates was rejected because it would create an undocumented bypass path.  
- Mutating prior gate records in place was rejected because it destroys auditability and historical accuracy.

## SECURITY_REFUSAL must stop work, gate the flow, and never auto-bypass
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL rules in every generation system prompt and specify that a SECURITY_REFUSAL in output must stop the PR, create a gate, and be logged. The same controls explicitly prohibit auto-bypass. ConsensusDevAgent must enforce this uniformly.  
**Decision:** When any model output contains a SECURITY_REFUSAL condition, immediately stop the active work item, create the required gate for operator handling, and log the event. Never auto-bypass, suppress, reinterpret, or continue past a SECURITY_REFUSAL.  
**Consequences:** Model orchestration, review flow, and PR progression must all include explicit SECURITY_REFUSAL detection and hard-stop behavior. Recovery must require operator-visible gating rather than automatic retries that continue execution as if nothing happened. This constrains prompt handling, parsers, state machines, and PR lifecycle logic.  
**Rejected alternatives:**  
- Automatically retrying with a different prompt or model and continuing silently was rejected because the control says stop, gate, and log.  
- Treating SECURITY_REFUSAL as a warning instead of a hard stop was rejected because it weakens the mandatory security posture.  
- Allowing a hidden admin bypass was rejected because the requirement explicitly says never auto-bypass.

## Untrusted review content must remain labeled and operator-gated when used
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks used in generation must produce a gate card to the operator before proceeding. ConsensusDevAgent may consume external review text, so trust boundaries must be explicit.  
**Decision:** Preserve untrusted reviewer content as explicitly labeled untrusted input in all prompts and internal handling. If flagged untrusted content is used in generation, stop for an operator gate before proceeding.  
**Consequences:** Prompt assembly and review ingestion must carry trust metadata, not plain text alone. The subsystem must distinguish trusted system instructions from untrusted reviewer-supplied material and must not blend them without labels. Operator gating becomes mandatory when flagged chunks influence generation.  
**Rejected alternatives:**  
- Stripping labels from reviewer comments for cleaner prompts was rejected because it hides trust boundaries.  
- Treating all PR review comments as trusted project input was rejected because review text may contain adversarial instructions.  
- Allowing flagged content to flow into generation without an operator gate was rejected because the control explicitly requires gating.

## Every file write path must pass path security validation
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent will generate or modify artifacts, so file output is a direct security boundary.  
**Decision:** Validate every destination path with `path_security.validate_write_path()` before any file write, overwrite, rename-into-place, or generated artifact persistence performed by ConsensusDevAgent.  
**Consequences:** File operations cannot write directly to arbitrary paths. The subsystem must route all write-capable operations through a validated path layer, including temporary-file workflows that culminate in writes. This constrains low-level I/O helpers and prevents shortcut implementations.  
**Rejected alternatives:**  
- Validating only user-supplied paths was rejected because generated or derived paths can also be unsafe.  
- Validating only final writes but not intermediate write steps was rejected because intermediate files can still violate policy.  
- Relying on repository-relative path joins alone was rejected because joining paths is not equivalent to security validation.

## Generated code must pass the 3-pass review, including security tooling
**Status:** Accepted  
**Context:** The build pipeline defines a 3-pass review sequence: correctness, performance, and security. Security controls further require generated code to pass Pass 3, including bandit. ConsensusDevAgent must not treat generated code as complete before those checks succeed.  
**Decision:** Require all code produced or advanced by ConsensusDevAgent to pass the full 3-pass review sequence, with Pass 3 including the mandated security review and bandit execution, before the work can proceed as approved.  
**Consequences:** Code generation is not a terminal state; review completion is. The subsystem must orchestrate review execution, capture failures, and block advancement on unresolved findings. Approval logic must depend on review results rather than generation success alone.  
**Rejected alternatives:**  
- Skipping performance or security review for small changes was rejected because the pipeline defines all three passes.  
- Treating bandit as advisory only was rejected because security controls require passing Pass 3 including bandit.  
- Marking code complete immediately after arbitration or generation was rejected because review remains mandatory.

## Claude wins in PRD generation where the pipeline specifies it
**Status:** Accepted  
**Context:** The build pipeline states that PRD generation uses both models and that Claude wins. ConsensusDevAgent must respect that arbitration rule when participating in PRD document generation or downstream logic derived from it.  
**Decision:** In PRD generation flows governed by the pipeline, run both required models and select Claude’s result as the authoritative output when a winner must be chosen. Do not substitute a different arbitration rule in this stage.  
**Consequences:** Model orchestration for PRD generation is constrained by a fixed winner rule, improving predictability and consistency with the documented pipeline. Downstream stages must consume the selected authoritative PRD output rather than an ad hoc merge or alternate model preference.  
**Rejected alternatives:**  
- Choosing the cheapest or fastest model output was rejected because the pipeline already specifies the winner.  
- Merging both model outputs automatically was rejected because the documented stage contract says Claude wins, not “combine both.”  
- Letting operators choose a winner by default was rejected because it would replace a defined system rule with inconsistent manual arbitration.