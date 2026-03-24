# CLAUDE.md

Crafted is a native macOS AI coding agent that ingests technical specifications and operator intent, then autonomously plans, implements, validates, and opens gated GitHub pull requests through a two-process Swift shell and Python backend architecture.

## How to Use This File

Use this file as the mandatory baseline for every code change in this repository. Read the owning subsystem TRD in `forge-docs/` for exact requirements and consult `forge-standards/` for synthesised architecture, interface, and decision references before you implement anything.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `forge-docs/AGENTS.md` | Repository identity, agent working rules, TRD-first workflow, testing expectations, and security reminders for contributors. |
| CLAUDE | MD | `forge-docs/CLAUDE.md` | Existing implementation guidance for Crafted, including product summary, subsystem-to-TRD lookup, and coding expectations. |
| README | MD | `forge-docs/README.md` | Product overview, operator workflow, TRD-driven build model, and repository-level purpose. |
| TRD-1-macOS-Application-Shell-Crafted | DOCX / MD | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `forge-docs/TRD-1-macOS-Application-Shell-Crafted.docx` | macOS Application Shell requirements: Swift shell, SwiftUI container, packaging, auth, Keychain, XPC, orchestration, and foundational module boundaries. |
| TRD-10-Document-Store-Crafted | DOCX / MD | `forge-docs/TRD-10-Document-Store-Crafted.md` / `forge-docs/TRD-10-Document-Store-Crafted.docx` | Document Store requirements: ingestion, chunking, embedding status, document lifecycle, and retrieval support for TRD-backed generation. |
| TRD-12-Backend-Runtime-Startup-Crafted | DOCX / MD | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.docx` | Backend runtime startup sequencing, process boot, handshake expectations, readiness reporting, and startup integrity rules. |
| TRD-13-Recovery-State-Management-Crafted | DOCX / MD | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` / `forge-docs/TRD-13-Recovery-State-Management-Crafted.docx` | Recovery and state management: checkpoints, crash recovery, persistence, restart behavior, and resumability constraints. |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | DOCX / MD | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` | Code quality gates, linting, validation loops, CI policy, and quality enforcement rules for generated changes. |
| TRD-15-Agent-Operational-Runbook-Crafted | DOCX / MD | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.docx` | Operational runbook, support procedures, runtime expectations, and operator-facing recovery and intervention workflows. |
| TRD-16-Agent-Testing-and-Validation-Crafted | DOCX / MD | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.docx` | Testing and validation strategy across subsystems, including unit, integration, failure-path, and acceptance requirements. |
| TRD-17-Self-Healing-Software-Crafted | DOCX / MD | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` / `forge-docs/TRD-17-Self-Healing-Software-Crafted.docx` | Self-healing behavior, fault response, retry or repair orchestration, and controlled automated recovery behavior. |
| TRD-2-Consensus-Engine-Crafted | DOCX / MD | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` / `forge-docs/TRD-2-Consensus-Engine-Crafted.docx` | Consensus Engine requirements: multi-model generation, arbitration, provider adapters, confidence handling, and generation contracts. |
| TRD-3-Build-Pipeline-Crafted | DOCX / MD | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` / `forge-docs/TRD-3-Build-Pipeline-Crafted.docx` | Build Pipeline requirements: intent decomposition, PR planning, staged execution, gating, fix loops, CI orchestration, and PR creation flow. |
| TRD-4-Multi-Agent-Coordination-Crafted | DOCX / MD | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.docx` | Multi-Agent Coordination requirements: agent roles, task handoffs, orchestration policy, shared context, and structured coordination behavior. |
| TRD-5-GitHub-Integration-Crafted | DOCX / MD | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` / `forge-docs/TRD-5-GitHub-Integration-Crafted.docx` | GitHub integration: repository operations, PR creation, webhooks, authentication handling, and GitHub-side workflow constraints. |
| TRD-6-Holistic-Code-Review-Crafted | DOCX / MD | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `forge-docs/TRD-6-Holistic-Code-Review-Crafted.docx` | Holistic code review system: review passes, defect detection, quality evaluation, and review-driven acceptance criteria. |
| TRD-7-TRD-Development-Workflow-Crafted | DOCX / MD | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.docx` | TRD development workflow: how specifications are loaded, interpreted, and translated into implementation plans and PRDs. |
| TRD-8-UIUX-Design-System-Crafted | DOCX / MD | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` / `forge-docs/TRD-8-UIUX-Design-System-Crafted.docx` | UI/UX Design System: SwiftUI views, cards, panels, operator experience, build stream presentation, and interaction patterns. |
| TRD-9-Mac-CI-Runner-Crafted | DOCX / MD | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `forge-docs/TRD-9-Mac-CI-Runner-Crafted.docx` | Mac CI Runner requirements: local CI execution, sandboxing expectations, runner lifecycle, and integration with pipeline validation. |
| forge_architecture_context | MD | `forge-docs/forge_architecture_context.md` | Loaded architecture context, protocol invariants, wire formats, startup and gating rules, persistence invariants, and file-level references. |

## Critical Rules — Non-Negotiable

1. Read the owning TRD before you modify any subsystem.
2. Preserve the two-process architecture: Swift owns UI, authentication, Keychain, and orchestration; Python owns consensus, pipeline, and GitHub operations.
3. Communicate between Swift and Python only through the authenticated Unix socket using line-delimited JSON.
4. Validate every external input as untrusted, including documents, PR comments, CI output, and protocol messages.
5. Execute no generated code under any circumstance, including through `eval`, `exec`, or subprocess invocation of generated content.
6. Fail closed on authentication, cryptographic, identity, and policy errors.
7. Surface every error with context and allow no silent failure paths.
8. Log no secrets, keys, tokens, credentials, or cleartext sensitive payloads.
9. Require operator action for every gate and never auto-approve.
10. Wait indefinitely for operator input at gates and never bypass a blocking gate with timeout-based approval.
11. Validate every file write path through `path_security.validate_write_path()` before writing.
12. Put external document context only in the user prompt and never in the system prompt.
13. Stop immediately on `SECURITY_REFUSAL`, gate the operation, and log the event without rephrasing around the refusal.
14. Discard and log unknown XPC message types without raising them as exceptions.
15. Preserve per-PR stage checkpoints and persistent build memory and never clear them automatically.

## Architecture Overview

- **macOS Application Shell** — Provides the native Swift/SwiftUI container, installation, auth, Keychain access, XPC/socket orchestration, and session lifecycle; called by the operator and startup flow; calls the Python backend and UI subsystems; must never move secrets or authentication ownership into Python.
- **UI/UX Design System** — Renders SwiftUI views, cards, panels, build stream, and operator gates; called by the macOS Application Shell; calls orchestration state and build stream rendering; must never implement backend business logic or bypass gate semantics.
- **Consensus Engine** — Runs parallel model generation and arbitration across providers; called by the Build Pipeline and coordination flows; calls provider adapters and review/correction stages; must never become the authority for shell-owned identity, secrets, or code execution.
- **Build Pipeline** — Decomposes intent into PRDs and typed pull requests, stages generation, lint/fix/CI loops, and draft PR creation; called by the operator workflow and orchestration; calls Consensus Engine, GitHub Integration, review, CI, recovery, and document retrieval; must never skip required gates or rerun completed stages without checkpoint rules.
- **Multi-Agent Coordination** — Coordinates specialized agents, task delegation, and shared state across build work; called by the Build Pipeline; calls agent roles, consensus tasks, and shared context mechanisms; must never allow uncontrolled parallel changes or ambiguous task ownership.
- **GitHub Integration** — Performs repository operations, webhook handling, branch/PR management, and GitHub API workflows; called by the Build Pipeline and operational flows; calls GitHub APIs and webhook receivers; must never expose tokens or permit unaudited repository mutation.
- **Holistic Code Review** — Performs structured review and defect detection over generated changes; called by the Build Pipeline and validation stages; calls analysis passes and review result synthesis; must never silently waive critical findings.
- **TRD Development Workflow** — Governs how TRDs are loaded, interpreted, and translated into executable planning context; called by operator setup and planning stages; calls Document Store and planning logic; must never invent requirements beyond loaded specifications.
- **Mac CI Runner** — Executes local macOS validation and CI tasks for candidate changes; called by the Build Pipeline; calls build/test/lint tooling under controlled execution; must never execute generated code directly or outside defined validation workflows.
- **Document Store** — Ingests, chunks, tracks embedding status, and retrieves source specifications and supporting documents; called by TRD workflow, planning, and generation context assembly; calls storage and embedding pipelines; must never treat ingestion content as trusted executable instructions.
- **Backend Runtime Startup** — Boots the Python runtime, emits readiness state, and enforces startup handshake sequencing; called by the macOS Application Shell; calls backend initialization and protocol readiness reporting; must never report readiness before required startup invariants hold.
- **Recovery State Management** — Persists stage checkpoints, resumable state, and crash recovery metadata; called by the Build Pipeline, startup, and self-healing flows; calls durable state storage and resume logic; must never lose completed-stage state or replay work unsafely after a crash.
- **Code Quality CI Pipeline** — Enforces lint, quality gates, fix loops, and CI pass criteria; called by the Build Pipeline and runner stages; calls analysis tools and CI orchestration; must never downgrade security or correctness gates for speed.
- **Agent Operational Runbook** — Defines operational intervention, support, and runtime handling procedures; called by operators and operational tooling; calls documented workflows rather than code paths; must never be contradicted by hidden runtime behavior.
- **Agent Testing and Validation** — Defines repository-wide validation obligations and acceptance criteria; called by every implementation effort; calls unit, integration, and failure-path suites; must never permit untested security-critical changes.
- **Self-Healing Software** — Detects eligible failures and performs controlled recovery actions; called by runtime monitoring and recovery flows; calls Recovery State Management and operational recovery mechanisms; must never mask root-cause failures or mutate completed work without traceability.

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

## Error Handling Rules

- Fail closed on all trust, identity, authentication, authorization, policy, and cryptographic failures.
- Reject the action, log the event, and surface the failure to the caller on every fail-closed path.
- Include `component`, `operation`, `failure_reason`, and `ctx_id` when available in every enforcement-path error.
- Exclude keys, tokens, secrets, credentials, and cleartext payloads from every error message and log entry.
- Discard and log unknown XPC message types instead of raising uncaught exceptions.
- Reject malformed, oversized, or protocol-invalid line-delimited JSON messages instead of attempting partial recovery.
- Stop processing immediately when CTX-ID validation fails.
- Stop processing immediately when VTZ policy denies an action.
- Stop processing immediately when required TrustFlow emission cannot complete silently; log and surface the failure.
- Gate and log every `SECURITY_REFUSAL` and do not retry by paraphrasing the same unsafe request.
- Preserve completed stage state through checkpoints and resume from persisted state after crashes instead of re-running prior completed stages.
- Keep audit records append-only and never modify or delete prior security-relevant records.
- Ban swallowed exceptions in enforcement paths.
- Ban `try/except/pass` in trust, crypto, policy, and enforcement code.
- Ban silent retries that hide first-failure context.
- Ban fallback behavior that weakens authentication, policy, validation, or cryptographic guarantees.

## Testing Requirements

- Run the existing test suite before making changes.
- Add tests that map directly to the owning TRD requirements for the subsystem you changed.
- Test every security-critical logic path with unit, integration, and negative-path coverage.
- Test malformed external input, parser boundaries, protocol failures, and attacker-controlled content.
- Test failure behavior, not only success behavior.
- Add regression tests for every material bug.
- Add benchmark tests for performance-sensitive paths, especially network, crypto, policy, and telemetry paths.
- Add fuzzing where inputs are complex, parser-driven, or attacker-controlled.
- Add a negative test for every enforcement path.
- Add tests for invalid or expired cryptographic material for every cryptographic operation.
- Test TrustFlow emission success and TrustFlow emission failure paths.
- Do not mock the enforcement decision logic; mock only the external dependency when necessary.
- Maintain enforcement-path test coverage at or above 90%.
- Verify startup, recovery, and checkpoint behavior with restart and crash-resume tests.
- Verify that generated code is never executed as part of runtime behavior.

## File Naming and Directory Layout

- Follow the Forge subsystem layout exactly for enforcement-related components:
  - `src/cal/` — Conversation Abstraction Layer components
  - `src/dtl/` — Data Trust Label components
  - `src/trustflow/` — TrustFlow audit stream components
  - `src/vtz/` — Virtual Trust Zone enforcement
  - `src/trustlock/` — Cryptographic machine identity (TPM-anchored)
  - `src/mcp/` — MCP Policy Engine
  - `src/rewind/` — Forge Rewind replay engine
  - `sdk/connector/` — Forge Connector SDK
  - `tests/<subsystem>/` — Tests mirror `src/` structure exactly
- Preserve the documented Python backend file naming from the architecture context:
  - `src/consensus.py` — ConsensusEngine and generation system entry points
  - `src/build_director.py` — BuildPipeline orchestration, confidence gate, and PR routing
  - `src/github_tools.py` — GitHub integration and webhook handling
  - `src/build_ledger.py` — Build state and ledger-related persistence
- Keep Swift shell code in the macOS Application Shell structure defined by TRD-1.
- Keep SwiftUI view and design-system code in the UI/UX Design System structure defined by TRD-8.
- Place new files in the subsystem that owns the behavior instead of creating cross-cutting utility dumping grounds.
- Mirror every new source subsystem with corresponding tests under `tests/`.

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