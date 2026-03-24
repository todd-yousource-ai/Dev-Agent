# CLAUDE.md
Crafted is a native macOS AI coding agent that ingests technical specifications and operator intent, plans and builds software as a sequence of gated GitHub pull requests through a two-process Swift shell and Python backend without ever executing generated code.

## How to Use This File
Use this file as the mandatory baseline for every change in this repository and apply its rules before reading or modifying code. Read `forge-docs/` for authoritative subsystem TRDs and read `forge-standards/` for synthesized architecture, interface, and decision references before implementing subsystem-specific behavior.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `forge-docs/AGENTS.md` | Repository identity, product summary, two-process architecture, and agent instructions for using the TRDs before coding. |
| CLAUDE | MD | `forge-docs/CLAUDE.md` | Existing repository guidance for implementing Crafted, including subsystem-to-TRD mapping and core product behavior. |
| README | MD | `forge-docs/README.md` | Product overview, operator workflow, autonomous build pipeline summary, and repository-level orientation. |
| TRD-1-macOS-Application-Shell-Crafted | MD/DOCX | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `forge-docs/TRD-1-macOS-Application-Shell-Crafted.docx` | macOS Application Shell requirements: Swift/SwiftUI container, packaging, authentication, Keychain, XPC orchestration, and shell-owned responsibilities. |
| TRD-10-Document-Store-Crafted | MD/DOCX | `forge-docs/TRD-10-Document-Store-Crafted.md` / `forge-docs/TRD-10-Document-Store-Crafted.docx` | Document Store requirements for ingesting, indexing, tracking, and serving specification documents to the system. |
| TRD-11-Security-Threat-Model-Crafted | MD/DOCX | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` / `forge-docs/TRD-11-Security-Threat-Model-Crafted.docx` | Security threat model, trust boundaries, credential handling, external input rules, generated code restrictions, and fail-closed security requirements. |
| TRD-12-Backend-Runtime-Startup-Crafted | MD/DOCX | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.docx` | Backend runtime startup, process boot, handshake, readiness, and startup orchestration requirements. |
| TRD-13-Recovery-State-Management-Crafted | MD/DOCX | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` / `forge-docs/TRD-13-Recovery-State-Management-Crafted.docx` | Recovery and state management requirements, including crash recovery, checkpointing, and durable workflow state. |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | MD/DOCX | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` | Code quality gates, linting, CI expectations, and pipeline quality requirements. |
| TRD-15-Agent-Operational-Runbook-Crafted | MD/DOCX | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.docx` | Operational runbook for running, supporting, and diagnosing the agent in practice. |
| TRD-16-Agent-Testing-and-Validation-Crafted | MD/DOCX | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.docx` | Testing and validation strategy, expected test types, and verification requirements across subsystems. |
| TRD-17-Self-Healing-Software-Crafted | MD/DOCX | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` / `forge-docs/TRD-17-Self-Healing-Software-Crafted.docx` | Self-healing software behavior, iterative correction, and automated recovery logic inside the build workflow. |
| TRD-2-Consensus-Engine-Crafted | MD/DOCX | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` / `forge-docs/TRD-2-Consensus-Engine-Crafted.docx` | Consensus Engine requirements for multi-model generation, arbitration, and result selection. |
| TRD-3-Build-Pipeline-Crafted | MD/DOCX | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` / `forge-docs/TRD-3-Build-Pipeline-Crafted.docx` | Build Pipeline requirements for intent decomposition, PRD planning, typed PR sequencing, gates, CI, and PR creation. |
| TRD-4-Multi-Agent-Coordination-Crafted | MD/DOCX | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.docx` | Multi-Agent Coordination requirements for orchestrating specialized agents and coordinating work safely. |
| TRD-5-GitHub-Integration-Crafted | MD/DOCX | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` / `forge-docs/TRD-5-GitHub-Integration-Crafted.docx` | GitHub Integration requirements for repository operations, PR workflows, and GitHub-facing automation. |
| TRD-6-Holistic-Code-Review-Crafted | MD/DOCX | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `forge-docs/TRD-6-Holistic-Code-Review-Crafted.docx` | Holistic Code Review requirements for full-change evaluation, review logic, and quality/security analysis of generated work. |
| TRD-7-TRD-Development-Workflow-Crafted | MD/DOCX | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.docx` | TRD Development Workflow requirements for producing and managing technical requirements documents. |
| TRD-8-UIUX-Design-System-Crafted | MD/DOCX | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` / `forge-docs/TRD-8-UIUX-Design-System-Crafted.docx` | UI/UX Design System requirements for SwiftUI views, cards, panels, and operator-facing interaction patterns. |
| TRD-9-Mac-CI-Runner-Crafted | MD/DOCX | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `forge-docs/TRD-9-Mac-CI-Runner-Crafted.docx` | Mac CI Runner requirements for CI execution on macOS, build/test orchestration, and CI result handling. |
| forge_architecture_context | MD | `forge-docs/forge_architecture_context.md` | Loaded architecture context, product-wide invariants, XPC protocol details, file naming references, and runtime rules. |

## Critical Rules — Non-Negotiable
1. Read the owning TRD before changing any subsystem behavior, interface, state machine, security control, or test.
2. Keep the system as a two-process architecture with the Swift shell owning UI, authentication, secrets, and orchestration, and the Python backend owning consensus, pipeline, and GitHub operations.
3. Communicate between processes only through the authenticated Unix socket using line-delimited JSON and the documented message formats.
4. Reject all authentication, cryptographic, identity, and trust failures immediately and fail closed without partial processing.
5. Treat all external content, including documents, pull request comments, CI output, and tool responses, as untrusted input and validate it before use.
6. Never execute generated code, generated scripts, or generated content through eval, exec, shell execution, or subprocess launch.
7. Never bypass operator gates and wait indefinitely for operator input when a gate is required.
8. Validate every file write path with `path_security.validate_write_path()` before performing the write.
9. Keep context from external documents in the user prompt and never place that context in the system prompt.
10. Stop processing, gate, and log when a `SECURITY_REFUSAL` is produced and never bypass it by rephrasing.
11. Discard and log unknown XPC message types and never raise them as uncaught exceptions.
12. Preserve per-PR stage checkpoints so completed work is not rerun after a crash or restart.
13. Preserve build memory and build rules as persistent learning systems and never clear them automatically.
14. Keep secrets, tokens, credentials, and keys out of logs, error messages, prompts, and generated code.
15. Make every error explicit, attributable, and observable and never allow silent failure paths in runtime-critical or security-critical code.

## Architecture Overview
- **macOS Application Shell** — Native Swift/SwiftUI container for packaging, installation, authentication, Keychain, UI, and orchestration; called by the operator and startup flow; calls the backend runtime over authenticated local IPC and OS services such as biometrics and Keychain; must NEVER delegate shell-owned secrets or authentication authority to the Python backend.
- **UI/UX Design System** — SwiftUI views, cards, panels, and operator interaction patterns such as streamed build cards and blocking gate cards; called by the macOS Application Shell; calls shell view models and XPC-backed orchestration state; must NEVER invent workflow states or bypass gate semantics defined by the pipeline.
- **Backend Runtime Startup** — Python backend boot, readiness, startup sequencing, and handshake lifecycle; called by the macOS Application Shell; calls Consensus Engine, Build Pipeline, Document Store, and GitHub Integration after successful startup; must NEVER report readiness before dependencies and protocol state are valid.
- **Consensus Engine** — Multi-model generation and arbitration using parallel providers with Claude arbitrating outcomes; called by the Build Pipeline and review flows; calls provider adapters and returns structured generation decisions; must NEVER collapse into uncontrolled single-provider behavior or return untraceable decisions.
- **Build Pipeline** — End-to-end orchestration from operator intent to PRD plan to typed pull requests, generation, self-correction, lint, CI, and draft PR creation; called by the backend runtime and operator workflows; calls Consensus Engine, Multi-Agent Coordination, Holistic Code Review, Mac CI Runner, GitHub Integration, and recovery/state services; must NEVER skip required gates, confidence checks, or stage persistence.
- **Multi-Agent Coordination** — Coordination of specialized agents and partitioned work across the build flow; called by the Build Pipeline; calls agent-specific tasks and returns coordinated outputs; must NEVER permit overlapping unsafe writes, ambiguous ownership, or uncontrolled autonomous branching.
- **GitHub Integration** — Repository access, branch management, PR creation, webhook handling, and GitHub-facing automation; called by the Build Pipeline and operational workflows; calls GitHub APIs and webhook endpoints; must NEVER trust GitHub-originated content without validation or expose tokens outside approved secret handling.
- **Holistic Code Review** — Repository-wide evaluation of changes for correctness, quality, and risk before PR advancement; called by the Build Pipeline; calls analysis logic over generated diffs, test results, and requirements context; must NEVER approve changes without traceable evidence against requirements and observed outputs.
- **TRD Development Workflow** — Structured handling of technical requirements documents and their evolution; called by operator and planning flows; calls Document Store and planning logic; must NEVER let implementation drift from authoritative TRD requirements.
- **Mac CI Runner** — macOS-based CI execution for builds, tests, linting, and result capture; called by the Build Pipeline; calls build/test tools and returns CI artifacts and statuses; must NEVER execute unvalidated generated content as arbitrary commands outside the approved CI workflow.
- **Document Store** — Ingestion, indexing, chunking, embedding status, and retrieval of source documents and TRDs; called by startup, planning, and generation flows; calls storage/indexing services and supplies contextual retrieval; must NEVER treat ingestion status as complete when chunking or embedding state is incomplete.
- **Security Threat Model** — Cross-cutting trust boundaries, credential rules, generated-code restrictions, and secure failure behavior; called by every subsystem through design and implementation constraints; calls no runtime subsystem directly but governs all of them; must NEVER be weakened by convenience shortcuts.
- **Recovery State Management** — Durable checkpoints, restart recovery, and prevention of duplicated completed work; called by the Build Pipeline and backend runtime; calls persistent state storage and resume logic; must NEVER replay completed stages or lose authoritative workflow state.
- **Code Quality CI Pipeline** — Lint, code quality gates, and acceptance criteria for changes; called by the Build Pipeline and repository processes; calls tests and validation tooling; must NEVER allow critical warnings or failures to pass silently.
- **Agent Operational Runbook** — Operational procedures, diagnostics, and support expectations; called by human operators and maintainers; calls documented system behaviors and observability outputs; must NEVER be contradicted by hidden runtime behavior.
- **Agent Testing and Validation** — Required unit, integration, negative-path, and validation coverage across the system; called by development and CI processes; calls test harnesses and validation suites; must NEVER be reduced below required enforcement coverage.
- **Self-Healing Software** — Iterative fix loops and automated correction behaviors after failures; called by the Build Pipeline; calls analysis and remediation passes; must NEVER mask root causes, erase checkpoints, or bypass operator control.

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
- Reject auth, crypto, identity, trust, and policy failures immediately and do not continue partial execution.
- Surface every failure to the caller with component, operation, failure reason, and `ctx_id` when available.
- Remove all silent catches, swallowed exceptions, and best-effort continuation from enforcement paths.
- Log unknown XPC message types and discard them without crashing the process.
- Stop the workflow, gate the operator, and log the event when a `SECURITY_REFUSAL` occurs.
- Redact secrets, tokens, keys, credentials, and cleartext sensitive payloads from logs, metrics, audit records, and error messages.
- Validate message bounds, parser inputs, and wire payload sizes before parsing and fail safely on malformed input.
- Preserve durable checkpoints before and after material stage transitions so crash recovery resumes from the last valid state.
- Keep audit failures non-fatal to agent operation but surface them immediately as observable warnings.
- Ban `try/except/pass`, silent `None` fallthroughs, ignored return values in enforcement paths, hidden retries that change semantics, and any fallback that weakens security controls.

## Testing Requirements
- Add unit, integration, and negative-path tests for every security-critical, policy-critical, and runtime-critical code path.
- Add at least one rejection-path test for every enforcement boundary.
- Test every cryptographic operation with invalid, expired, malformed, and unauthorized material.
- Test TrustFlow emission on both success and failure paths.
- Run enforcement logic in tests and mock only external side effects, not the decision itself.
- Maintain enforcement-path coverage at 90% or higher.
- Add regression tests for every material bug, crash-recovery defect, and stage-checkpoint failure.
- Add tests for malformed external content, including documents, PR comments, CI output, wire messages, and parser-driven inputs.
- Add benchmark coverage for network, crypto, policy, and telemetry hot paths.
- Add fuzzing for complex or attacker-controlled parsers and message handlers.
- Verify that completed per-PR stages do not rerun after crash recovery.
- Verify that generated code is never executed anywhere in the system.

## File Naming and Directory Layout
- Place Conversation Abstraction Layer components in `src/cal/`.
- Place Data Trust Label components in `src/dtl/`.
- Place TrustFlow audit stream components in `src/trustflow/`.
- Place Virtual Trust Zone enforcement components in `src/vtz/`.
- Place TrustLock cryptographic machine identity components in `src/trustlock/`.
- Place MCP Policy Engine components in `src/mcp/`.
- Place Forge Rewind replay engine components in `src/rewind/`.
- Place Forge Connector SDK components in `sdk/connector/`.
- Mirror `src/` exactly under `tests/<subsystem>/`.
- Keep Python backend entry and orchestration modules aligned with the loaded architecture context:
  - `src/consensus.py` — `ConsensusEngine`, provider generation systems, and arbitration-related backend logic.
  - `src/build_director.py` — `BuildPipeline` orchestration, confidence gate flow, and PR type routing.
  - `src/github_tools.py` — `GitHubTool` and `WebhookReceiver` integration logic.
  - `src/build_ledger.py` — build state and durable workflow tracking.
- Keep Swift shell code in shell-owned Swift/SwiftUI modules for UI, authentication, Keychain, and local IPC orchestration.
- Keep protocol handlers, policy enforcement, trust boundaries, and critical data flows explicitly documented at their source locations.

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
- forge-docs/        — source TRDs and PRDs
- forge-standards/   — synthesised architecture, interfaces, decisions
- docs/              — branch-specific context