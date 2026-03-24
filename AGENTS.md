# AGENTS.md

Crafted Dev Agent is a native macOS AI coding agent that turns technical specifications and operator intent into sequenced GitHub pull requests through a two-process architecture with a Swift shell and a Python backend.

## How to Use This File
Use this file as the baseline operational contract before you read, modify, or add any code in this repository. Read `forge-docs/` for authoritative subsystem requirements and read `forge-standards/` for synthesised architecture, interface, and decision guidance.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `forge-docs/AGENTS.md` | Repository identity, coding workflow, TRD-first implementation rules, and agent operating instructions. |
| CLAUDE | MD | `forge-docs/CLAUDE.md` | Prior repository-level implementation guidance, subsystem lookup guidance, and high-level architecture constraints. |
| GitHub-Integration-Lessons-Learned | DOCX / MD | `forge-docs/GitHub-Integration-Lessons-Learned.md` / `forge-docs/GitHub-Integration-Lessons-Learned.docx` | Production GitHub API behavior, draft PR lifecycle constraints, and integration edge cases discovered in the build pipeline. |
| README | MD | `forge-docs/README.md` | Product overview, operator workflow, TRD index, and end-to-end behavior of the directed build agent. |
| TRD-1-macOS-Application-Shell-Crafted | DOCX / MD | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `forge-docs/TRD-1-macOS-Application-Shell-Crafted.docx` | Native macOS application shell, Swift process responsibilities, UI/auth/Keychain/XPC ownership, and shell-side interfaces. |
| TRD-10-Document-Store-Crafted | DOCX / MD | `forge-docs/TRD-10-Document-Store-Crafted.md` / `forge-docs/TRD-10-Document-Store-Crafted.docx` | Document ingestion, storage, indexing, and retrieval behavior for specification context. |
| TRD-11-Security-Threat-Model-Crafted | DOCX / MD | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` / `forge-docs/TRD-11-Security-Threat-Model-Crafted.docx` | Security model, trust boundaries, threat assumptions, credential handling, generated-code prohibitions, and fail-closed rules. |
| TRD-12-Backend-Runtime-Startup-Crafted | DOCX / MD | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.docx` | Python backend startup, runtime initialization, readiness signaling, and process bring-up contracts. |
| TRD-13-Recovery-State-Management-Crafted | DOCX / MD | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` / `forge-docs/TRD-13-Recovery-State-Management-Crafted.docx` | Crash recovery, stage checkpoints, persistent state handling, and resumability requirements. |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | DOCX / MD | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` | Code quality gates, linting, CI expectations, and merge-quality enforcement. |
| TRD-15-Agent-Operational-Runbook-Crafted | DOCX / MD | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.docx` | Operational procedures, runtime handling, operator workflows, and troubleshooting guidance. |
| TRD-16-Agent-Testing-and-Validation-Crafted | DOCX / MD | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.docx` | Testing strategy, validation rules, failure-path expectations, and quality thresholds across the system. |
| TRD-17-Self-Healing-Software-Crafted | DOCX / MD | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` / `forge-docs/TRD-17-Self-Healing-Software-Crafted.docx` | Self-healing behavior, automatic recovery loops, and safe remediation boundaries. |
| TRD-2-Consensus-Engine-Crafted | DOCX / MD | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` / `forge-docs/TRD-2-Consensus-Engine-Crafted.docx` | Consensus engine design, multi-model generation flow, arbitration rules, and provider orchestration. |
| TRD-3-Build-Pipeline-Crafted | DOCX / MD | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` / `forge-docs/TRD-3-Build-Pipeline-Crafted.docx` | Build pipeline orchestration, confidence gating, PR typing, staged execution, and implementation flow control. |
| TRD-4-Multi-Agent-Coordination-Crafted | DOCX / MD | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.docx` | Multi-agent coordination, task decomposition, role separation, and cross-agent execution behavior. |
| TRD-5-GitHub-Integration-Crafted | DOCX / MD | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` / `forge-docs/TRD-5-GitHub-Integration-Crafted.docx` | GitHub integration, PR lifecycle, webhook and API interactions, and repository automation constraints. |
| TRD-6-Holistic-Code-Review-Crafted | DOCX / MD | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `forge-docs/TRD-6-Holistic-Code-Review-Crafted.docx` | Holistic code review system behavior, review loops, evaluation criteria, and quality enforcement. |
| TRD-7-TRD-Development-Workflow-Crafted | DOCX / MD | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.docx` | TRD-driven development workflow, specification decomposition, and planning-to-implementation process. |
| TRD-8-UIUX-Design-System-Crafted | DOCX / MD | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` / `forge-docs/TRD-8-UIUX-Design-System-Crafted.docx` | SwiftUI views, cards, panels, build stream presentation, and UI/UX system requirements. |
| TRD-9-Mac-CI-Runner-Crafted | DOCX / MD | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `forge-docs/TRD-9-Mac-CI-Runner-Crafted.docx` | macOS CI runner behavior, build/test execution environment, and CI-side operational constraints. |
| forge_architecture_context | MD | `forge-docs/forge_architecture_context.md` | Cross-cutting architecture context, invariants, XPC protocol schema, file naming anchors, and process-level behavioral rules. |

## Critical Rules — Non-Negotiable

1. Read the owning TRD before you modify any subsystem.
2. Keep the architecture split intact: implement UI, authentication, Keychain, and XPC ownership in the Swift shell and implement consensus, pipeline, and GitHub operations in the Python backend.
3. Communicate between the Swift shell and Python backend only through the authenticated Unix socket using line-delimited JSON.
4. Never execute generated code under any circumstance.
5. Treat all external input, including documents, PR comments, and CI output, as untrusted and validate it before use.
6. Fail closed on all authentication, cryptographic, identity, and policy errors.
7. Surface every failure with context and never introduce a silent failure path.
8. Keep secrets, keys, tokens, credentials, and cryptographic material out of logs, error messages, prompts, and generated code.
9. Wait indefinitely for operator gate input and never auto-approve a gate.
10. Validate every file write path with `path_security.validate_write_path()` before performing the write.
11. Put external document context only in the user prompt and never in the system prompt.
12. Stop immediately, gate, and log when a `SECURITY_REFUSAL` condition occurs.
13. Discard unknown XPC message types and log them instead of raising process-breaking exceptions.
14. Preserve per-PR stage checkpoints and resume from them instead of rerunning completed work after a crash.
15. Preserve build memory and build rules as persistent learning systems and never clear them automatically.

## Architecture Overview

- **macOS Application Shell** — Owns the native Swift app, UI, authentication, Keychain access, and XPC/socket boundary; called by the operator; calls the Python backend over the authenticated local protocol; must never own consensus, generation orchestration, or GitHub automation logic.
- **UI/UX Design System** — Owns SwiftUI views, cards, panels, `BuildStreamView`, streamed `build_card` rendering, and gate presentation; called by the macOS Application Shell; calls shell-side state and transport adapters; must never bypass gate semantics or obscure operator decisions.
- **Backend Runtime Startup** — Owns Python backend initialization, capability advertisement, readiness signaling, and runtime bring-up; called by the macOS Application Shell at backend launch; calls subsystem initializers and emits the `ready` message; must never report ready before dependencies and state are initialized.
- **Consensus Engine** — Owns multi-model generation, arbitration, and provider orchestration across Claude and GPT-4o with Claude arbitration; called by the Build Pipeline and review flows; calls provider adapters and prompt assembly; must never execute generated content or invent authority outside the TRDs.
- **Build Pipeline** — Owns confidence gating, PRD planning, PR typing, staged implementation, self-correction, lint/fix loops, and orchestration across work units; called by operator intent and backend control flow; calls Consensus Engine, Multi-Agent Coordination, GitHub Integration, review, and persistence layers; must never skip gates, bypass checkpoints, or mutate completed stage history silently.
- **Multi-Agent Coordination** — Owns role decomposition and coordinated execution across agent participants; called by the Build Pipeline; calls task-specific generation and coordination paths; must never collapse role boundaries in ways that hide accountability or traceability.
- **GitHub Integration** — Owns GitHub API and webhook behavior, branch/PR lifecycle, draft PR handling, and repository-side automation; called by the Build Pipeline and backend services; calls GitHub REST and GraphQL APIs; must never assume unsupported REST behavior where GraphQL is required and must never merge draft-state transitions incorrectly.
- **Holistic Code Review** — Owns review passes, evaluation criteria, review outputs, and correction-triggering decisions; called by the Build Pipeline before PR advancement; calls Consensus Engine and repository analysis tools; must never approve code that violates TRD contracts or security invariants.
- **TRD Development Workflow** — Owns the specification-to-implementation workflow, intent decomposition, and PRD/PR sequencing model; called by planning stages in the Build Pipeline; calls Document Store retrieval and planning logic; must never invent requirements that are absent from the loaded specifications.
- **Document Store** — Owns ingestion, chunking, embedding status, storage, and retrieval of TRDs and related documents; called by planning, consensus, and review components; calls persistence and indexing layers; must never return untracked document state or lose document provenance.
- **Mac CI Runner** — Owns macOS-native CI execution for builds and tests; called by CI and PR validation flows; calls local build/test tooling; must never run outside the controlled CI contract or hide failing output.
- **Recovery State Management** — Owns per-PR stage checkpoints, resumability, and crash recovery state; called by the Build Pipeline and backend runtime; calls persistent state storage; must never re-run completed stages after crash recovery without explicit need.
- **Code Quality CI Pipeline** — Owns linting, quality gates, policy checks, and merge readiness criteria; called by CI and pipeline quality stages; calls tests, linters, and validation tools; must never treat security-critical failures as warnings.
- **Agent Operational Runbook** — Owns operational procedures and runtime incident handling guidance; called by operators and maintainers; calls documented recovery and troubleshooting steps; must never override system-enforced safeguards.
- **Agent Testing and Validation** — Owns validation strategy, required test forms, and subsystem test expectations; called by all implementation work; calls unit, integration, negative-path, and other validation suites; must never accept success-only coverage for security-critical behavior.
- **Self-Healing Software** — Owns safe automatic remediation and bounded recovery loops; called by runtime and pipeline fault handling; calls recovery and retry mechanisms; must never convert a hard security stop into an automatic continue path.

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

- Fail closed on authentication, identity, cryptographic, policy, and trust failures.
- Reject the action immediately when CTX-ID validation fails.
- Reject the action immediately when VTZ authorization fails.
- Stop processing and surface the failure when TrustFlow emission fails.
- Stop processing and gate when a `SECURITY_REFUSAL` condition is reached.
- Discard and log unknown XPC message types instead of raising transport-breaking exceptions.
- Return structured errors that include `component`, `operation`, `failure_reason`, and `ctx_id` when available.
- Keep secrets, tokens, keys, credentials, and cleartext sensitive payloads out of all errors.
- Ban swallowed exceptions in enforcement, identity, policy, crypto, and transport-critical code.
- Ban partial processing after validation failure at a trust boundary.
- Ban fallback behavior that weakens authentication, authorization, crypto validation, or operator gating.
- Preserve checkpoints before advancing stages so recovery can resume deterministically after a crash.

## Testing Requirements

- Run the existing test suite before making material changes.
- Add unit, integration, and negative-path tests for every security-critical logic path.
- Add malformed-input tests for parsing, policy, trust, cryptographic, document, PR comment, and CI-output handling.
- Add regression tests for every material bug.
- Add benchmark coverage for performance-sensitive network, crypto, policy, and telemetry paths.
- Test both success and failure paths for TrustFlow emission.
- Test invalid, expired, missing, and rotated CTX-ID material anywhere CTX-ID is enforced.
- Test crash recovery against per-PR stage checkpoints.
- Test GitHub draft PR lifecycle behavior against the documented GraphQL transition requirements.
- Keep enforcement-path test coverage at or above 90%.
- Do not mock away the enforcement decision logic itself.
- Verify that generated code is never executed in tests, runtime flows, or helper tooling.

## File Naming and Directory Layout

- Place Conversation Abstraction Layer components in `src/cal/`.
- Place Data Trust Label components in `src/dtl/`.
- Place TrustFlow audit stream components in `src/trustflow/`.
- Place Virtual Trust Zone enforcement in `src/vtz/`.
- Place cryptographic machine identity components in `src/trustlock/`.
- Place MCP Policy Engine components in `src/mcp/`.
- Place Forge Rewind replay engine components in `src/rewind/`.
- Place Forge Connector SDK code in `sdk/connector/`.
- Mirror `src/` exactly under `tests/<subsystem>/`.
- Keep Python backend anchors consistent with the architecture context:
  - `src/consensus.py` — `ConsensusEngine`, generation system prompts, and provider-side generation orchestration.
  - `src/build_director.py` — `BuildPipeline` orchestration, confidence gate handling, and PR-type routing.
  - `src/github_tools.py` — `GitHubTool` and `WebhookReceiver`.
  - `src/build_ledger.py` — build state and checkpoint-related persistence logic.
- Keep Swift shell code aligned with TRD-1 and UI code aligned with TRD-8.
- Keep recovery, document-store, GitHub, and CI-related modules separated by subsystem boundary and documented by owning TRD.

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