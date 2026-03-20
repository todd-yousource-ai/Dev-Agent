# DECISIONS.md

## ConsensusDevAgent repository placement and boundaries
**Status:** Accepted  
**Context:** The repository structure is fixed across the system, and the ConsensusDevAgent subsystem must fit within the documented source-of-truth layout. TRDs and PRDs live in `forge-docs/`, standards live in `forge-standards/`, Python backend code lives in `src/`, and tests live in `tests/`. This subsystem participates in the build pipeline and multi-agent coordination, so its implementation location and document dependencies must be explicit.  
**Decision:** Implement ConsensusDevAgent backend code under `src/` and its tests under `tests/`. Treat `forge-docs/` as read-first source material and `forge-standards/DECISIONS.md` as binding implementation guidance. Do not place subsystem logic inside document directories, the macOS shell, or workflow definitions except for thin integration points.  
**Consequences:** The subsystem must be implemented as Python backend code, with document consumption separated from runtime logic. Design and API contracts must be documented in standards/docs rather than embedded ad hoc in code layout. Integration with the Swift app shell or CI must occur through defined interfaces, not by relocating subsystem code.  
**Rejected alternatives:**  
- Placing ConsensusDevAgent inside `forge-docs/` because those directories are documentation sources, not runtime implementation locations.  
- Implementing the subsystem in `ForgeAgent/` because the macOS app shell is not the backend runtime for agent orchestration.  
- Splitting core logic across workflow files because CI configuration is not an application architecture boundary.

## ConsensusDevAgent must operate as a gated build-pipeline participant
**Status:** Accepted  
**Context:** The documented build pipeline is the core execution loop, progressing from scope through PRD generation, PR planning, code generation, 3-pass review, and onward. The subsystem must behave consistently with stage contracts and auditability requirements.  
**Decision:** Integrate ConsensusDevAgent as a stage-aware participant in the build pipeline. Require it to honor stage boundaries, consume prior-stage artifacts, and emit outputs suitable for subsequent stages and audit trails. Do not allow the subsystem to bypass, reorder, or collapse documented pipeline stages.  
**Consequences:** Consensus behavior must be deterministic enough to fit within stage contracts. Inputs and outputs must be structured for handoff across pipeline stages. Failures must escalate through pipeline mechanisms rather than via silent local retries that obscure stage outcomes.  
**Rejected alternatives:**  
- Letting the subsystem run as an independent loop outside the pipeline because that would break traceability and stage governance.  
- Allowing dynamic stage skipping for speed because it undermines the documented process and review guarantees.  
- Merging consensus and review into one opaque step because the pipeline requires explicit stage separation.

## No undo on gate decisions
**Status:** Accepted  
**Context:** The requirements explicitly state: no undo on gate decisions. Security and pipeline excerpts reinforce that gate outcomes are terminal and must be documented explicitly.  
**Decision:** Treat every gate decision made or triggered by ConsensusDevAgent as immutable. Do not implement undo, rollback, silent reversal, or automatic bypass of a recorded gate outcome. Require any further progress to occur through a new explicit operator-mediated decision path, with the original gate preserved in the audit trail.  
**Consequences:** The subsystem must model gate decisions as append-only records. UX, APIs, and internal state transitions must prevent mutation of prior gate outcomes. Recovery flows must create new events rather than editing history.  
**Rejected alternatives:**  
- Supporting an "undo gate" action for operator convenience because it violates explicit requirements.  
- Allowing automatic retry to clear a prior gate because that effectively bypasses immutability.  
- Rewriting prior gate state in place because it destroys auditability.

## SECURITY_REFUSAL is terminal and must stop progression
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in every generation system prompt, and if SECURITY_REFUSAL appears in output the PR must stop, gate, and log, with no auto-bypass. ConsensusDevAgent coordinates model outputs and therefore must enforce this contract.  
**Decision:** Detect SECURITY_REFUSAL in any model output handled by ConsensusDevAgent and immediately stop progression for the affected unit of work. Raise a gate to the operator, record the event in logs/audit artifacts, and prohibit automatic bypass or silent continuation.  
**Consequences:** Consensus arbitration cannot treat SECURITY_REFUSAL as one vote among many. Any downstream generation, merge, or review action for the affected work item must halt until an explicit subsequent operator-mediated path is taken. Logging and observability must preserve the refusal event verbatim enough for audit and diagnosis.  
**Rejected alternatives:**  
- Ignoring SECURITY_REFUSAL if another model produced usable output because security refusals are terminal, not advisory.  
- Auto-falling back to another model because the requirements forbid auto-bypass.  
- Converting SECURITY_REFUSAL into a warning because that weakens a mandatory control into an optional signal.

## Consensus decisions must preserve audit trail compatibility
**Status:** Accepted  
**Context:** The build pipeline documentation references full stage contracts, error escalation, and an audit trail schema. ConsensusDevAgent makes arbitration and gating decisions that materially affect outputs and therefore must be auditable.  
**Decision:** Emit structured, append-only records for ConsensusDevAgent inputs, arbitration outcomes, gate triggers, and escalations in a form compatible with the system audit trail. Record enough metadata to reconstruct which artifacts, stages, and model outputs contributed to each decision.  
**Consequences:** Internal decision logic must expose traceable reasoning artifacts at the system level, even if model internals are abstracted. Data models and APIs must support event recording as a first-class concern. Debugging and compliance workflows can rely on subsystem records without scraping transient logs.  
**Rejected alternatives:**  
- Logging only final outputs because that is insufficient to reconstruct arbitration and gate decisions.  
- Keeping audit details solely in memory because they would be lost across process boundaries and failures.  
- Writing free-form logs only because they are harder to validate against audit contracts.

## Security controls apply to all file writes initiated by the subsystem
**Status:** Accepted  
**Context:** Mandatory security controls require `path_security.validate_write_path()` on every file path before write. ConsensusDevAgent may generate, select, or materialize artifacts and therefore participates in write paths.  
**Decision:** Validate every filesystem write path used by ConsensusDevAgent with `path_security.validate_write_path()` before writing. Apply this rule uniformly to generated artifacts, temporary outputs promoted to durable storage, logs, and any synthesized review assets.  
**Consequences:** File output helpers for the subsystem must centralize path validation and forbid direct unmanaged writes. Tests must cover rejection of invalid or unsafe paths. Performance optimizations cannot skip validation.  
**Rejected alternatives:**  
- Validating only user-supplied paths because generated/internal paths can also be unsafe.  
- Validating only final destination writes because temporary and intermediate writes still create risk.  
- Trusting repository-relative paths without validation because relative paths can still be abused.

## Untrusted review content must remain explicitly labeled in prompts and processing
**Status:** Accepted  
**Context:** Security controls state that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged chunks used in generation must gate to the operator before proceeding. ConsensusDevAgent aggregates and arbitrates across multiple inputs, including review-derived content.  
**Decision:** Preserve explicit untrusted labeling for any reviewer-originated or otherwise untrusted content that ConsensusDevAgent forwards into prompts, arbitration inputs, or generation context. If flagged chunks are included in generation, require an operator gate before proceeding.  
**Consequences:** Input normalization must track trust level metadata, not just text content. Prompt construction cannot flatten trusted and untrusted inputs into indistinguishable context. Consensus scoring and synthesis must account for provenance.  
**Rejected alternatives:**  
- Stripping trust labels for cleaner prompts because it removes a mandatory safeguard.  
- Treating all repository-adjacent text as trusted because review comments are explicitly untrusted.  
- Allowing flagged content into generation without a gate because that violates the control requirement.

## ConsensusDevAgent must not auto-bypass security or review failures
**Status:** Accepted  
**Context:** The documented 3-pass review includes a security pass, and mandatory controls prohibit auto-bypass of SECURITY_REFUSAL. The subsystem may arbitrate generation results, but it cannot weaken review gates.  
**Decision:** Prohibit ConsensusDevAgent from auto-approving, auto-merging, or auto-advancing work that has failed or been halted by correctness, performance, or security review controls. Require failures to flow through documented gate and escalation paths.  
**Consequences:** Consensus logic must respect review outcomes as hard constraints, not optimization opportunities. Any "best available output" mode must exclude blocked artifacts. Operator visibility into failure reasons is mandatory before any further action.  
**Rejected alternatives:**  
- Letting consensus override a failing review if confidence is high because review gates are authoritative.  
- Auto-selecting the least-bad candidate after security failure because that still bypasses mandatory controls.  
- Collapsing review failures into ranking penalties because that turns hard stops into soft preferences.