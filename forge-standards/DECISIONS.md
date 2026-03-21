# DECISIONS.md

## ConsensusDevAgent repository boundaries and source-of-truth
**Status:** Accepted  
**Context:** The subsystem operates inside a repository with strict separation between specifications, standards, application code, and tests. The TRDs explicitly define repository layout and require implementers to read forge-docs before building. Without a hard boundary, the agent could place planning artifacts in code directories, treat generated files as authoritative, or bypass the specification set.  
**Decision:** Treat `forge-docs/` as the authoritative source for TRDs and PRDs, `forge-standards/` as the authoritative source for implementation constraints, `src/` as the Python backend implementation root for ConsensusDevAgent, and `tests/` as the Python verification root. Require the subsystem to read relevant TRDs and standards before implementation work begins, and do not persist design-authority documents outside those designated directories.  
**Consequences:** Implementation must resolve behavior from documents in `forge-docs/` and `forge-standards/` first. ConsensusDevAgent code belongs under `src/`, with tests under `tests/`. The subsystem may generate artifacts, but it must not create competing sources of truth for requirements or architecture in arbitrary locations.  
**Rejected alternatives:**  
- Keeping decision and planning artifacts colocated with code in `src/`: rejected because it blurs normative specifications with implementation.  
- Treating generated outputs or runtime state as authoritative over TRDs/PRDs: rejected because the repository structure defines documents as the source of truth.  
- Allowing subsystem-specific folder conventions independent of the repository layout: rejected because it would undermine shared tooling and review expectations.

## ConsensusDevAgent must integrate with the staged build pipeline
**Status:** Accepted  
**Context:** The repository defines a fixed build pipeline from scope confirmation through PR merge, with stage contracts and audit expectations. ConsensusDevAgent participates in this flow and cannot invent an alternate lifecycle without breaking orchestration and observability.  
**Decision:** Implement ConsensusDevAgent as a stage-compliant subsystem that fits into the defined pipeline: Scope, PRD Plan, PRD Gen, PR Plan, Code Gen, 3-Pass Review, and merge-related controls. Do not bypass, collapse, or reorder mandatory stages when acting on `/prd start <intent>` or downstream work items.  
**Consequences:** The subsystem must expose outputs that are consumable by downstream stages and must honor upstream decisions. Internal optimizations are allowed only if they preserve stage boundaries, artifacts, and auditability. Any implementation must assume that reviews, escalation, and merge gating occur within this standard pipeline.  
**Rejected alternatives:**  
- A single-pass “generate everything” workflow: rejected because it removes decomposition, review isolation, and stage-specific controls.  
- Reordering review before code generation planning: rejected because the pipeline explicitly sequences planning before implementation and review after generation.  
- Allowing each model or agent to choose its own lifecycle: rejected because cross-agent coordination depends on shared stage contracts.

## Gate decisions are immutable and have no undo path
**Status:** Accepted  
**Context:** The TRDs and supporting materials explicitly state “No undo on gate decisions.” This is a safety and audit requirement, especially for security stops, stage failures, and operator-gated events. Ambiguity here would allow unsafe retries that appear to erase prior decisions.  
**Decision:** Treat all gate decisions as append-only and irreversible. Do not implement undo, rollback-of-record, silent clearing, or automatic bypass for any gate outcome once recorded. If work resumes, it must do so through a new explicit operator action or a new decision record, not by undoing the previous gate.  
**Consequences:** State management must preserve gate history permanently in the audit trail. UX, APIs, and internal orchestration must not expose “undo gate,” “clear stop,” or equivalent semantics. Recovery flows must create new events referencing prior gated outcomes rather than mutating or deleting them.  
**Rejected alternatives:**  
- Allowing operators to undo a gate decision: rejected because the requirement explicitly forbids undo and would compromise audit integrity.  
- Auto-clearing transient gates after timeout or retry: rejected because it implicitly undoes the prior gate.  
- Mutating the original gate record to reflect the latest status: rejected because it destroys append-only history.

## SECURITY_REFUSAL is a hard stop that halts progress
**Status:** Accepted  
**Context:** Security controls require SECURITY_REFUSAL rules in generation prompts and define that SECURITY_REFUSAL in output must stop the PR, gate, and log, with no auto-bypass. This behavior must be enforced consistently by ConsensusDevAgent because it mediates generation and review outputs.  
**Decision:** Detect any SECURITY_REFUSAL emitted by participating models or generation steps and treat it as a mandatory hard stop: stop the active PR flow, create a gate, log the event, and require explicit operator handling. Never auto-bypass, suppress, reinterpret, or continue past SECURITY_REFUSAL.  
**Consequences:** Parsers, orchestrators, and stage controllers must inspect model outputs for SECURITY_REFUSAL and transition to a gated state immediately. Downstream stages must not proceed after detection. Audit logs must retain the original refusal signal and associated context.  
**Rejected alternatives:**  
- Retrying automatically with a softened prompt: rejected because the controls require stop, gate, and log.  
- Ignoring SECURITY_REFUSAL if another model produced usable output: rejected because the refusal itself is a security event.  
- Converting SECURITY_REFUSAL into a warning: rejected because the requirement defines a hard stop, not an advisory.

## Security controls are mandatory on all generated code write paths
**Status:** Accepted  
**Context:** The security controls require path validation on every file write, security review of all generated code, and prompt-level refusal policies. ConsensusDevAgent is responsible for turning generation into repository changes and therefore must enforce these controls uniformly.  
**Decision:** Enforce security controls on every generated-code path: require `path_security.validate_write_path()` before any write, route all generated code through the defined security review pass, and preserve SECURITY_REFUSAL handling in all generation contexts. Do not provide a fast path that skips these controls.  
**Consequences:** File-write helpers, patch application logic, and artifact persistence layers must centralize path validation. Code generation cannot write directly to disk without validated paths. Security review is mandatory even when earlier passes succeed or changes appear trivial.  
**Rejected alternatives:**  
- Validating only user-provided paths and not generated paths: rejected because the requirement applies to every file path before write.  
- Allowing test-only or docs-only writes to bypass path validation: rejected because the control is universal.  
- Skipping the security pass for low-risk changes: rejected because all generated code must pass Pass 3 security review.

## Untrusted review content must remain explicitly labeled and non-authoritative
**Status:** Accepted  
**Context:** Security controls specify that PR review comments must be labeled `[UNTRUSTED REVIEWER COMMENT]` in prompts and that flagged chunks used in generation must gate to an operator before proceeding. ConsensusDevAgent must prevent prompt injection and authority confusion from external review content.  
**Decision:** Treat external review comments and flagged content as untrusted inputs. Preserve explicit labeling of untrusted review content in prompts, and if flagged chunks are used in generation, create an operator gate before proceeding. Do not allow untrusted review text to become silent instructions or authoritative requirements.  
**Consequences:** Prompt assembly must maintain provenance labels. Review-ingestion code must track trust level and flagged status. Generation pipelines must branch to a gate when flagged chunks are incorporated, rather than continuing automatically.  
**Rejected alternatives:**  
- Merging reviewer comments directly into system or developer instructions: rejected because it erases trust boundaries.  
- Treating all PR comments as trusted because they are repository-adjacent: rejected because the controls explicitly classify them as untrusted.  
- Proceeding automatically when flagged chunks seem harmless: rejected because flagged-chunk usage requires an operator gate.

## Multi-model generation must remain stage-governed rather than model-governed
**Status:** Accepted  
**Context:** The pipeline references multiple models and arbitration behavior, including cases where one model’s output is preferred for specific stages. ConsensusDevAgent must coordinate model participation without allowing per-model autonomy to override the pipeline.  
**Decision:** Use multiple models only within the constraints of the defined stage contracts and arbitration rules. The subsystem must make stage-level decisions about which model outputs are accepted, and model preference rules must be explicit, deterministic, and auditable.  
**Consequences:** Implementation must separate raw model outputs from accepted stage artifacts. Arbitration logic must be codified rather than ad hoc. A model cannot independently advance the workflow, redefine a stage result, or bypass review because its output appears complete.  
**Rejected alternatives:**  
- Letting the “best” model decide whether a stage is complete: rejected because completion is governed by pipeline contracts, not model confidence.  
- Accepting the first successful model response without arbitration: rejected because the pipeline anticipates coordinated multi-model behavior.  
- Allowing different engineers or agents to pick different model precedence rules at runtime: rejected because it would reduce reproducibility and auditability.

## Audit trail must be append-only across stages, gates, and security events
**Status:** Accepted  
**Context:** The build pipeline references audit trail schema and error escalation, and the no-undo rule requires durable historical records. ConsensusDevAgent must preserve a complete history of decisions, stops, and resumptions.  
**Decision:** Record stage transitions, gate decisions, SECURITY_REFUSAL events, operator interventions, and resumptions in an append-only audit trail. Do not rewrite prior entries to reflect current state; instead, add new entries that reference prior events.  
**Consequences:** Data models must support immutable event records and correlation across a workflow. Operational debugging, compliance review, and incident analysis will rely on event history rather than mutable status snapshots alone. Any UI or API presenting “current status” must derive it from the event stream or a projection of it.  
**Rejected alternatives:**  
- Storing only the latest workflow status: rejected because it loses gate and escalation history.  
- Editing prior events in place to simplify storage: rejected because it conflicts with audit integrity and no-undo requirements.  
- Logging only failures and not successful stage transitions: rejected because stage progression itself is part of the required workflow record.