# CLAUDE.md
Crafted Dev Agent is a native macOS AI coding agent that turns technical specifications and operator intent into staged GitHub pull requests through a two-process architecture with a Swift shell and Python backend.

## How to Use This File
Use this file as the baseline operating contract before modifying any code in this repository. Read the subsystem-specific TRDs in `crafted-docs/` for authoritative requirements and use `crafted-standards/` for synthesized architecture, interfaces, and decision references.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `crafted-docs/AGENTS.md` | Repository identity, implementation workflow, TRD-first development expectations, and agent operating instructions. |
| CLAUDE | MD | `crafted-docs/CLAUDE.md` | Prior repository-level build guidance, architecture summary, and TRD authority mapping. |
| GitHub-Integration-Lessons-Learned | DOCX / MD | `crafted-docs/GitHub-Integration-Lessons-Learned.md` | Production lessons from GitHub API integration, including draft PR lifecycle behavior and automation edge cases. |
| GitHub-Integration-Lessons-Learned | DOCX | `crafted-docs/GitHub-Integration-Lessons-Learned.docx` | Source document for GitHub API integration lessons and operational constraints. |
| README | MD | `crafted-docs/README.md` | Product overview, operator workflow, repository purpose, and TRD index entry point. |
| TRD-1-macOS-Application-Shell-Crafted | MD | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift macOS application shell responsibilities, UI process behavior, auth handling, Keychain usage, and shell/backend boundary. |
| TRD-1-macOS-Application-Shell-Crafted | DOCX | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.docx` | Source document for the macOS application shell specification. |
| TRD-10-Document-Store-Crafted | MD | `crafted-docs/TRD-10-Document-Store-Crafted.md` | Document store ingestion, chunking, embedding, retrieval, and external document handling requirements. |
| TRD-10-Document-Store-Crafted | DOCX | `crafted-docs/TRD-10-Document-Store-Crafted.docx` | Source document for the document store specification. |
| TRD-11-Security-Threat-Model-Crafted | MD | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security threat model, trust boundaries, credential handling, generated code restrictions, and fail-closed controls. |
| TRD-11-Security-Threat-Model-Crafted | DOCX | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.docx` | Source document for the security threat model. |
| TRD-12-Backend-Runtime-Startup-Crafted | MD | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend runtime startup, readiness signaling, capability reporting, and process initialization behavior. |
| TRD-12-Backend-Runtime-Startup-Crafted | DOCX | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.docx` | Source document for backend runtime startup requirements. |
| TRD-13-Recovery-State-Management-Crafted | MD | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` | Crash recovery, checkpointing, resumability, and persistent build state management. |
| TRD-13-Recovery-State-Management-Crafted | DOCX | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.docx` | Source document for recovery and state management. |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | MD | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | Linting, code quality gates, CI expectations, and pipeline validation requirements. |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | DOCX | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` | Source document for code quality and CI pipeline rules. |
| TRD-15-Agent-Operational-Runbook-Crafted | MD | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operator runbook, runtime procedures, operational diagnostics, and incident handling guidance. |
| TRD-15-Agent-Operational-Runbook-Crafted | DOCX | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.docx` | Source document for the operational runbook. |
| TRD-16-Agent-Testing-and-Validation-Crafted | MD | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Test strategy, validation scope, required coverage, and acceptance criteria across the agent. |
| TRD-16-Agent-Testing-and-Validation-Crafted | DOCX | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.docx` | Source document for testing and validation. |
| TRD-17-Self-Healing-Software-Crafted | MD | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing and iterative fix-loop behavior for build failures and corrective passes. |
| TRD-17-Self-Healing-Software-Crafted | DOCX | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.docx` | Source document for self-healing software behavior. |
| TRD-2-Consensus-Engine-Crafted | MD | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` | ConsensusEngine behavior, provider orchestration, arbitration, and generation flow. |
| TRD-2-Consensus-Engine-Crafted | DOCX | `crafted-docs/TRD-2-Consensus-Engine-Crafted.docx` | Source document for the consensus engine specification. |
| TRD-3-Build-Pipeline-Crafted | MD | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` | BuildPipeline orchestration, confidence gate, PR decomposition, stage sequencing, and routing rules. |
| TRD-3-Build-Pipeline-Crafted | DOCX | `crafted-docs/TRD-3-Build-Pipeline-Crafted.docx` | Source document for the build pipeline specification. |
| TRD-4-Multi-Agent-Coordination-Crafted | MD | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Multi-agent coordination model, worker responsibilities, task decomposition, and orchestration behavior. |
| TRD-4-Multi-Agent-Coordination-Crafted | DOCX | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.docx` | Source document for multi-agent coordination. |
| TRD-5-GitHub-Integration-Crafted | MD | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub API integration, PR creation/update flow, webhook handling, and repository interactions. |
| TRD-5-GitHub-Integration-Crafted | DOCX | `crafted-docs/TRD-5-GitHub-Integration-Crafted.docx` | Source document for GitHub integration. |
| TRD-6-Holistic-Code-Review-Crafted | MD | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Holistic code review system, review synthesis, feedback processing, and quality evaluation. |
| TRD-6-Holistic-Code-Review-Crafted | DOCX | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.docx` | Source document for holistic code review. |
| TRD-7-TRD-Development-Workflow-Crafted | MD | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | TRD-driven development workflow, specification lifecycle, and implementation mapping. |
| TRD-7-TRD-Development-Workflow-Crafted | DOCX | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.docx` | Source document for the TRD development workflow. |
| TRD-8-UIUX-Design-System-Crafted | MD | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system, build cards, gate cards, visual behavior, and operator interaction patterns. |
| TRD-8-UIUX-Design-System-Crafted | DOCX | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.docx` | Source document for the UI/UX design system. |
| TRD-9-Mac-CI-Runner-Crafted | MD | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner behavior, build/test execution environment, and runner-specific controls. |
| TRD-9-Mac-CI-Runner-Crafted | DOCX | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.docx` | Source document for the Mac CI runner. |
| forge_architecture_context | MD | `crafted-docs/forge_architecture_context.md` | Consolidated architecture context, key invariants, protocol references, wire formats, and file naming guidance. |

## Critical Rules — Non-Negotiable
1. Read the owning TRD before changing any component.
2. Keep the architecture as two processes: Swift shell for UI, authentication, and secrets; Python backend for intelligence, generation, and GitHub operations.
3. Communicate between the Swift shell and Python backend only through the authenticated Unix socket using line-delimited JSON.
4. Reject all authentication, cryptographic, identity, and policy failures closed and surface them with context.
5. Treat all external input, including documents, PR comments, and CI output, as untrusted and validate it strictly before use.
6. Never execute generated code, generated shell commands, or generated content through `eval`, `exec`, or subprocess invocation.
7. Keep secrets in the Swift-owned security boundary and never expose secrets in logs, error messages, prompts, or generated code.
8. Validate every file write with `path_security.validate_write_path()` before performing the write.
9. Put context from external documents in the user prompt and never place it in the system prompt.
10. Stop immediately, gate, and log when a `SECURITY_REFUSAL` result is produced.
11. Discard and log unknown XPC message types instead of raising exceptions.
12. Preserve per-PR stage checkpoints so completed work is not rerun after a crash.
13. Keep build memory and build rules persistent and never clear them automatically.
14. Wait indefinitely for operator action at gates and never auto-approve a blocked decision.
15. Use the documented GitHub API behavior for draft PR lifecycle operations and use GraphQL when REST draft-to-ready transitions are unsupported.

## Architecture Overview
- **macOS Application Shell** — Owns UI, authentication, Keychain access, and local process control; called by the operator; calls the Python backend over the authenticated socket and renders streamed cards; must NEVER delegate secret ownership or execute generated code.
- **UI/UX Design System** — Owns SwiftUI views, BuildStreamView presentation, build cards, and gate cards; called by the macOS Application Shell; calls shell state and operator action handlers; must NEVER bypass gate semantics or invent backend state.
- **Backend Runtime Startup** — Owns Python backend initialization, readiness negotiation, capability reporting, and startup contracts; called by the macOS Application Shell; calls subsystem bootstrappers and emits `ready`/status messages; must NEVER report readiness before required dependencies and stores are initialized.
- **Consensus Engine** — Owns two-model generation, arbitration, and result selection with Claude arbitrating outcomes; called by BuildPipeline and review flows; calls provider adapters and returns adjudicated outputs; must NEVER bypass arbitration rules or execute generated content.
- **Build Pipeline** — Owns confidence gating, intent decomposition, PRD planning, typed PR sequencing, lint/fix loops, and orchestration; called by operator-initiated build actions; calls ConsensusEngine, GitHub integration, review, CI, and recovery state; must NEVER skip gates, reorder committed stage semantics, or lose checkpoint state.
- **Multi-Agent Coordination** — Owns decomposition of work across collaborating agent roles and task execution order; called by BuildPipeline; calls worker agents and aggregation logic; must NEVER create unsupervised execution paths outside the pipeline contract.
- **GitHub Integration** — Owns repository operations, draft PR creation, update flows, webhook handling, and merge-state interactions; called by BuildPipeline and operational flows; calls GitHub REST and GraphQL APIs; must NEVER assume unsupported REST behaviors or silently ignore API state mismatches.
- **Holistic Code Review** — Owns synthesized review, issue aggregation, and feedback-driven refinement; called by BuildPipeline after generation and CI stages; calls model-based review and result summarization; must NEVER approve code without running the documented review flow.
- **TRD Development Workflow** — Owns requirement-to-implementation mapping and specification-driven development process; called by contributors and planning logic; calls TRD lookup and decomposition stages; must NEVER allow implementation to drift from the governing TRD.
- **Mac CI Runner** — Owns macOS-native build and test execution environment for validation; called by pipeline validation stages; calls platform build/test tools and returns CI output; must NEVER be treated as trusted input without validation.
- **Document Store** — Owns document ingestion, chunking, embeddings, retrieval, and `doc_status` reporting; called by startup, planning, and generation flows; calls embedding/indexing layers; must NEVER trust malformed documents or return ambiguous document state.
- **Recovery State Management** — Owns checkpoints, resume state, crash recovery, and per-PR restoration; called by BuildPipeline and startup recovery; calls persistent state storage and resume logic; must NEVER rerun completed stages after a recoverable interruption.
- **Code Quality CI Pipeline** — Owns linting, static quality checks, and pipeline quality gates; called by BuildPipeline and CI stages; calls test/lint tools and gating logic; must NEVER silently downgrade a failed quality gate.
- **Agent Operational Runbook** — Owns runtime operating procedures and incident handling expectations; called by operators and maintainers; calls observability and recovery procedures; must NEVER contradict the runtime contracts defined by the TRDs.
- **Agent Testing and Validation** — Owns system-wide validation requirements, acceptance criteria, and required coverage; called by all implementation work; calls unit, integration, negative-path, and benchmark suites; must NEVER accept untested enforcement or critical-path logic.
- **Self-Healing Software** — Owns iterative remediation loops after lint, test, or build failure; called by BuildPipeline failure handlers; calls correction and retry stages; must NEVER mask root-cause failures or continue indefinitely without explicit stage rules.

## Interface Contracts
## Forge Component Interface Contracts

Every Forge component MUST implement these contracts or the component is non-conformant.
These are not guidelines — they are hard requirements enforced at code review.

### CAL Enforcement Contract
- Every entry point that processes an agent action MUST call CTX-ID validation FIRST
- CTX-ID validation failure MUST result in immediate rejection — no partial processing
- Every action MUST be checked against VTZ policy BEFORE execution
- VTZ policy denial MUST produce a VTZEnforcementDecision record with verdict=block
- Every action outcome (allow, restrict, block) MUST emit a TrustFlow event
- TrustFlow emission failure MUST NOT silently continue — log and surface the failure

### TrustFlow Emission Contract
- Every TrustFlow event MUST include: event_id, session_id, ctx_id, ts, event_type, payload_hash
- event_id MUST be globally unique (CSPRNG, not sequential)
- ts MUST be UTC Unix timestamp with millisecond precision
- payload_hash MUST be SHA-256 of the serialized action payload
- Emission MUST be synchronous in the enforcement path — async buffering is not permitted
- Failed emission is a WARN-level audit event, not a silent skip

### CTX-ID Contract
- CTX-ID tokens are IMMUTABLE once issued — no field modification after issuance
- CTX-ID rotation creates a new token; the old one is invalidated immediately
- Expired CTX-ID MUST be rejected — clock skew tolerance is defined per deployment
- CTX-ID MUST be validated against TrustLock public key — software-only validation is rejected
- Missing CTX-ID MUST be treated as UNTRUSTED — never infer identity from context

### VTZ Enforcement Contract
- Every agent session is bound to EXACTLY ONE VTZ at CTX-ID issuance
- Cross-VTZ tool calls require explicit policy authorization — implicit is denied
- VTZ boundaries are structural, not advisory — enforcement cannot be bypassed by application code
- VTZ policy changes take effect at NEXT CTX-ID issuance, not mid-session

### DTL Label Contract
- Labels are assigned at DATA INGESTION and are immutable thereafter
- Label inheritance: derived data inherits the HIGHEST classification of any source
- Unlabeled data MUST be treated as CONFIDENTIAL until explicitly reclassified
- Label verification MUST occur before any data crosses a trust boundary
- Label stripping is a security event that MUST be audited and policy-controlled

### Error Handling Contract
- All trust, identity, policy, and cryptographic failures MUST fail CLOSED
- Fail closed means: reject the action, log the event, surface to caller — never silently continue
- No swallowed exceptions in enforcement paths (try/except/pass is BANNED in enforcement code)
- All errors MUST include: component, operation, failure_reason, ctx_id (if available)
- Error messages MUST NOT include: keys, tokens, secrets, or cleartext payloads

### Audit Contract
- Every security-relevant action MUST generate an audit record BEFORE execution
- Audit records are APPEND-ONLY — no modification or deletion
- Audit failures are NON-FATAL to agent operation but MUST be surfaced immediately
- Audit records MUST NOT contain: secrets, keys, tokens, or cleartext sensitive data
- Replay MUST be possible from the audit stream alone (no external state required)

### Test Requirements Contract
- Every enforcement path MUST have a negative test (what happens on rejection)
- Every cryptographic operation MUST have a test with invalid/expired material
- Every TrustFlow emission MUST be tested for both success and failure paths
- Tests MUST NOT mock the enforcement decision — they may mock the external call but the logic must run
- Test coverage for enforcement paths MUST be >= 90%

## Error Handling Rules
- Fail closed on all trust, identity, authentication, policy, and cryptographic errors.
- Reject the action immediately when CTX-ID validation fails.
- Reject the action immediately when VTZ authorization fails.
- Stop processing and surface the failure when TrustFlow emission fails.
- Log and discard unknown XPC message types.
- Surface every error with component, operation, failure reason, and `ctx_id` when available.
- Remove secrets, tokens, keys, credentials, and cleartext sensitive payloads from all logs and error messages.
- Refuse generated-code execution paths completely instead of sandboxing them opportunistically.
- Gate and log on `SECURITY_REFUSAL` output and do not retry by rephrasing.
- Preserve completed stage state on recoverable failure and resume from the checkpoint instead of replaying finished work.
- Ban silent exception swallowing in enforcement, trust, crypto, pipeline gate, and recovery code.
- Ban implicit success defaults after parse, validation, or transport failures.
- Ban auto-approval, timeout-based approval, or default-allow behavior at operator gates.
- Ban unvalidated file writes and reject writes whose paths fail `path_security.validate_write_path()`.

## Testing Requirements
- Run the existing test suite before making changes.
- Add unit tests, integration tests, and negative-path tests for every security-critical and runtime-critical change.
- Add malformed-input tests for parsing, policy, trust, cryptographic, document-ingestion, PR-comment, and CI-output handling.
- Add regression tests for every material bug.
- Add benchmark tests for network, crypto, policy, and telemetry hot paths.
- Add tests for both success and failure paths of TrustFlow emission.
- Add tests for invalid, expired, rotated, and missing cryptographic or identity material.
- Add resume/recovery tests for per-PR stage checkpoint behavior.
- Add tests that prove generated code is never executed by either process.
- Keep enforcement-path test coverage at or above 90%.
- Mirror test layout to subsystem layout under `tests/<subsystem>/`.
- Do not mock the enforcement decision logic itself.

## File Naming and Directory Layout
- Place Conversation Abstraction Layer components in `src/cal/`.
- Place Data Trust Label components in `src/dtl/`.
- Place TrustFlow audit stream components in `src/trustflow/`.
- Place Virtual Trust Zone enforcement components in `src/vtz/`.
- Place TPM-anchored machine identity components in `src/trustlock/`.
- Place MCP Policy Engine components in `src/mcp/`.
- Place Forge Rewind replay engine components in `src/rewind/`.
- Place Connector SDK components in `sdk/connector/`.
- Mirror `src/` exactly under `tests/` using `tests/<subsystem>/`.
- Keep Python backend orchestration files aligned with the documented names:
  - `src/consensus.py` — `ConsensusEngine`, generation systems, provider arbitration
  - `src/build_director.py` — `BuildPipeline` orchestration, confidence gate, PR-type routing
  - `src/github_tools.py` — `GitHubTool`, webhook handling, repository operations
  - `src/build_ledger.py` — persistent build state and checkpoint tracking
- Preserve the two-process boundary in directory ownership: Swift shell code for UI/auth/secrets, Python code for consensus/pipeline/GitHub/runtime logic.

## Security Checklist — Before Every Commit
## Forge Code Review Checklist

Before any PR is merged, a reviewer MUST confirm:
[ ] CTX-ID validated at every enforcement entry point
[ ] TrustFlow event emitted for every action outcome
[ ] VTZ policy checked before cross-boundary operations
[ ] No silent failure paths in trust/crypto/policy code
[ ] No secrets, keys, or tokens in logs or error messages
[ ] All external input validated before use
[ ] Test coverage includes at least one negative path per security boundary
[ ] FIPS-approved algorithms used for all cryptographic operations

## Where to Find More Detail
- crafted-docs/        — source TRDs and PRDs
- crafted-standards/   — synthesised architecture, interfaces, decisions
- docs/              — branch-specific context