# DECISIONS.md

## ConsensusDevAgent documents live in `forge-docs/` and must be treated as authoritative inputs
**Status:** Accepted  
**Context:** The subsystem operates inside a repository where TRDs and PRDs are the source of truth. The repository structure explicitly places all TRDs and PRDs under `forge-docs/`, and implementation is expected to be derived from those documents before code generation or review begins.  
**Decision:** Read design inputs from `forge-docs/` only, and treat the documents there as authoritative for subsystem behavior, interfaces, pipeline constraints, and review requirements. Do not invent requirements outside those documents without operator confirmation.  
**Consequences:** Implementation of ConsensusDevAgent must resolve and consume requirements from `forge-docs/` before acting. The subsystem cannot treat ad hoc prompts, code comments, or generated artifacts as a higher-priority specification than TRDs/PRDs. Any future extension must preserve `forge-docs/` as the canonical documentation location.  
**Rejected alternatives:**  
- Reading requirements primarily from source code: rejected because source code is an implementation artifact, not the authoritative product/design specification.  
- Allowing requirements to be split across arbitrary folders: rejected because it weakens traceability and makes pipeline behavior ambiguous.  
- Treating operator chat input as equal to TRDs/PRDs: rejected because the documented workflow establishes repository documents as the source of truth.

## ConsensusDevAgent must conform to the staged build pipeline
**Status:** Accepted  
**Context:** The build pipeline is the core execution model for the system, with explicit stages from scope confirmation through review and merge. ConsensusDevAgent participates in decomposition, code generation, and review-related activities and therefore must align to stage boundaries and contracts.  
**Decision:** Implement ConsensusDevAgent so that all work occurs within the defined pipeline stages: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and subsequent gated progression. Do not skip, merge, or reorder stages without an explicit documented change to the pipeline contract.  
**Consequences:** The subsystem must expose state and artifacts in a way that is stage-aware. Outputs must be attributable to a specific stage, and handoff behavior must preserve auditability. Logic that would “fast-path” generation directly to merge or bypass review is prohibited.  
**Rejected alternatives:**  
- A monolithic agent loop with no explicit stages: rejected because it reduces observability, weakens audit trails, and conflicts with the repository’s documented workflow.  
- Dynamic stage reordering based on model confidence: rejected because stage contracts are fixed and must remain predictable.  
- Combining code generation and review into one pass: rejected because the 3-pass review is a separate control, especially for security.

## Gate decisions are irreversible within a run
**Status:** Accepted  
**Context:** The repository materials explicitly state “No undo on gate decisions.” This is a control for safety, traceability, and operator trust, particularly when a stage has halted, escalated, or refused to proceed.  
**Decision:** Treat every gate decision made by ConsensusDevAgent as final for the current run. Do not automatically reopen, reverse, or silently bypass a gate once it has been triggered. Any further progress must occur through a new run or an explicit external/operator action recorded outside the original gate path.  
**Consequences:** The subsystem must persist gate outcomes durably and must not include “retry by override” behavior inside the same execution path. UX and API surfaces must communicate that a gate stop is terminal for that run. Recovery flows must create a new traceable execution rather than mutating history.  
**Rejected alternatives:**  
- Allowing the agent to self-clear gates after additional reasoning: rejected because it undermines the integrity of safety and review controls.  
- Providing an internal undo stack for failed gates: rejected because it directly conflicts with the documented requirement.  
- Automatically downgrading hard gates to warnings after timeout: rejected because it creates unsafe non-deterministic behavior.

## SECURITY_REFUSAL must hard-stop the pipeline and may never be auto-bypassed
**Status:** Accepted  
**Context:** Mandatory security controls require SECURITY_REFUSAL rules in generation prompts and define that SECURITY_REFUSAL in output must stop the PR, gate progress, and log the event. The documents also state that such outcomes must never be auto-bypassed.  
**Decision:** On any SECURITY_REFUSAL emitted or detected in ConsensusDevAgent-controlled generation or review output, immediately stop the affected PR/work item, raise a gate, and log the event in the audit trail. Never auto-bypass, suppress, or reinterpret SECURITY_REFUSAL as success, warning, or retry-safe output.  
**Consequences:** The subsystem must include explicit detection and handling for SECURITY_REFUSAL tokens or equivalent refusal signals. Downstream stages must not continue after detection. Logging and operator-visible status must clearly reflect that the halt was security-driven.  
**Rejected alternatives:**  
- Retrying generation automatically until the refusal disappears: rejected because it masks a security event and acts as an implicit bypass.  
- Treating SECURITY_REFUSAL as a soft validation warning: rejected because the requirements define it as a stop condition.  
- Continuing non-security stages while pausing only code write actions: rejected because the documented control says stop PR and gate, not partial continuation.

## Untrusted review content must remain explicitly labeled and cannot silently influence generation
**Status:** Accepted  
**Context:** Security controls require PR review comments to be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts, and flagged content used in generation must trigger a gate card to the operator before proceeding. ConsensusDevAgent consumes review artifacts and may feed them into subsequent model calls, making provenance labeling essential.  
**Decision:** Preserve untrusted review content with explicit provenance labels whenever it is included in prompts, summaries, or agent context. If flagged or untrusted chunks are to be used in generation, require an operator-visible gate before proceeding. Do not normalize, merge, or paraphrase such content in a way that removes its untrusted status.  
**Consequences:** Prompt construction and context assembly must be provenance-aware. The subsystem must track trusted versus untrusted inputs and ensure labels survive transformations. Operator intervention becomes mandatory before untrusted flagged content affects generation.  
**Rejected alternatives:**  
- Stripping labels after sanitization: rejected because sanitization does not change provenance, and loss of labeling weakens downstream safeguards.  
- Fully excluding all review comments from prompts: rejected because review feedback is useful and expected, but must be handled safely.  
- Trusting comments from repository collaborators by default: rejected because the requirement is to label reviewer comments as untrusted in prompts.

## All file writes performed by ConsensusDevAgent must pass path validation
**Status:** Accepted  
**Context:** Security controls state that `path_security.validate_write_path()` must be used on every file path before write. ConsensusDevAgent produces documents, code patches, and review artifacts that may touch multiple repository locations.  
**Decision:** Validate every output path with `path_security.validate_write_path()` before any create, overwrite, append, rename, or patch-write operation performed by ConsensusDevAgent. Abort the write and gate the operation on validation failure.  
**Consequences:** All write-capable code paths must centralize through a validated file I/O layer. Direct filesystem writes, ad hoc path joins, or model-suggested paths cannot be executed without validation. The subsystem must be designed so path validation is not optional.  
**Rejected alternatives:**  
- Validating only final absolute paths in some write flows: rejected because every write operation must be protected consistently.  
- Relying on repository root checks without the mandated validator: rejected because it does not satisfy the stated control.  
- Allowing prompt-generated paths to bypass validation when they target known directories: rejected because trusted destination classes do not eliminate traversal and path confusion risks.

## Security review is mandatory and cannot be collapsed into general correctness review
**Status:** Accepted  
**Context:** The build pipeline defines a 3-pass review: correctness, performance, and security. Mandatory controls also require all generated code to pass security review including bandit. ConsensusDevAgent is responsible for generating and/or coordinating outputs that enter this review flow.  
**Decision:** Require a distinct security review pass for all generated code and prohibit treating correctness or performance review as a substitute. Include required security tooling and checks, including bandit where applicable, before code may progress.  
**Consequences:** Review orchestration in ConsensusDevAgent must model security as a first-class pass with separate outcomes, logs, and failure handling. A PR cannot be marked review-complete unless the security pass has executed and passed.  
**Rejected alternatives:**  
- A single holistic review prompt covering all concerns: rejected because it weakens the explicit control boundary of the mandated 3-pass process.  
- Running security review only on files heuristically classified as risky: rejected because the requirement applies to all generated code.  
- Making tooling optional when model review appears sufficient: rejected because the documents explicitly require security review including bandit.

## Claude-prevails arbitration is required where the pipeline specifies dual-model generation
**Status:** Accepted  
**Context:** The documented PRD generation flow states “both models, Claude wins.” ConsensusDevAgent is a consensus-oriented subsystem, but where the pipeline defines a winner, arbitration behavior must be deterministic rather than negotiated indefinitely.  
**Decision:** In stages where dual-model generation is required and the repository workflow specifies winner selection, implement deterministic arbitration with Claude as the prevailing output. Use other model output as comparative input, critique, or fallback evidence, but not as the final selected artifact when Claude output is available and valid.  
**Consequences:** ConsensusDevAgent must not attempt open-ended consensus loops in place of the documented winner-take arbitration rule. Data models should preserve both candidate outputs and the selection rationale, but final artifact promotion must follow the prescribed winner.  
**Rejected alternatives:**  
- Requiring unanimous agreement between models before progress: rejected because it can stall the pipeline and conflicts with the explicit winner rule.  
- Random or score-based final selection across models: rejected because the workflow already defines the tiebreak/selection policy.  
- Always merging both outputs into a synthesized result: rejected because it obscures provenance and departs from deterministic stage behavior.