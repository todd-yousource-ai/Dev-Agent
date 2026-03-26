# AGENTS.md
Crafted Dev Agent is a native macOS AI coding agent that reads technical specifications, plans work into typed pull requests, generates and validates implementations through a two-process architecture, and opens gated GitHub PRs without ever executing generated code.

## How to Use This File
Use this file as the mandatory baseline before changing any code in this repository. Read the owning TRD in `crafted-docs/` for subsystem-specific requirements and read `crafted-standards/` for synthesized architecture, interface, and decision guidance before you implement.

## Document Index
| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `crafted-docs/AGENTS.md` | Repository identity, product architecture, pre-change workflow, and agent operating instructions. |
| CLAUDE | MD | `crafted-docs/CLAUDE.md` | Existing high-level implementation guidance, TRD authority mapping, and repository-specific coding rules. |
| GitHub-Integration-Lessons-Learned | DOCX/MD | `crafted-docs/GitHub-Integration-Lessons-Learned.md` / `crafted-docs/GitHub-Integration-Lessons-Learned.docx` | Observed GitHub API behaviors and production lessons for draft PR lifecycle and automation. |
| README | MD | `crafted-docs/README.md` | Product overview, operating model, repository purpose, and TRD-driven workflow context. |
| TRD-1-macOS-Application-Shell-Crafted | DOCX/MD | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` / `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.docx` | Swift macOS application shell, UI host, authentication, Keychain handling, and shell responsibilities. |
| TRD-10-Document-Store-Crafted | DOCX/MD | `crafted-docs/TRD-10-Document-Store-Crafted.md` / `crafted-docs/TRD-10-Document-Store-Crafted.docx` | Document ingestion, storage, chunking, embedding status, and document context management. |
| TRD-11-Security-Threat-Model-Crafted | DOCX/MD | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` / `crafted-docs/TRD-11-Security-Threat-Model-Crafted.docx` | Security model, trust boundaries, threat assumptions, failure handling, and security controls. |
| TRD-12-Backend-Runtime-Startup-Crafted | DOCX/MD | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` / `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.docx` | Python backend startup, runtime initialization, process readiness, and startup lifecycle. |
| TRD-13-Recovery-State-Management-Crafted | DOCX/MD | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` / `crafted-docs/TRD-13-Recovery-State-Management-Crafted.docx` | Recovery, crash resilience, stage checkpoints, and persistent state management. |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | DOCX/MD | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` / `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` | Linting, quality gates, CI expectations, and code quality enforcement. |
| TRD-15-Agent-Operational-Runbook-Crafted | DOCX/MD | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` / `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.docx` | Operational procedures, runbook behavior, and production handling expectations. |
| TRD-16-Agent-Testing-and-Validation-Crafted | DOCX/MD | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` / `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.docx` | Testing strategy, validation requirements, negative-path testing, and acceptance criteria. |
| TRD-17-Self-Healing-Software-Crafted | DOCX/MD | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` / `crafted-docs/TRD-17-Self-Healing-Software-Crafted.docx` | Self-healing behavior, remediation loops, and automated correction constraints. |
| TRD-2-Consensus-Engine-Crafted | DOCX/MD | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` / `crafted-docs/TRD-2-Consensus-Engine-Crafted.docx` | ConsensusEngine, provider orchestration, multi-model generation, and arbitration behavior. |
| TRD-3-Build-Pipeline-Crafted | DOCX/MD | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` / `crafted-docs/TRD-3-Build-Pipeline-Crafted.docx` | BuildPipeline orchestration, confidence gate, PR decomposition, and staged execution. |
| TRD-4-Multi-Agent-Coordination-Crafted | DOCX/MD | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` / `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.docx` | Multi-agent coordination, typed work delegation, and inter-agent workflow management. |
| TRD-5-GitHub-Integration-Crafted | DOCX/MD | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` / `crafted-docs/TRD-5-GitHub-Integration-Crafted.docx` | GitHub API integration, PR creation/update flows, and repository automation behavior. |
| TRD-6-Holistic-Code-Review-Crafted | DOCX/MD | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` / `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.docx` | Code review system, holistic review passes, and quality assessment behavior. |
| TRD-7-TRD-Development-Workflow-Crafted | DOCX/MD | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` / `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.docx` | TRD-driven workflow, requirements decomposition, and implementation process. |
| TRD-8-UIUX-Design-System-Crafted | DOCX/MD | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` / `crafted-docs/TRD-8-UIUX-Design-System-Crafted.docx` | SwiftUI design system, cards, panels, build stream views, and operator interaction patterns. |
| TRD-9-Mac-CI-Runner-Crafted | DOCX/MD | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` / `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.docx` | macOS CI runner integration, CI execution behavior, and runner-specific constraints. |
| forge_architecture_context | MD | `crafted-docs/forge_architecture_context.md` | Consolidated architecture invariants, protocol references, wire formats, and key file mappings. |

## Critical Rules — Non-Negotiable
1. Read the owning TRD before you modify any subsystem.
2. Preserve the two-process boundary: keep UI, authentication, and Keychain ownership in Swift and keep intelligence, generation, and GitHub operations in Python.
3. Communicate between Swift and Python only through the authenticated Unix socket using line-delimited JSON.
4. Validate all external input, including documents, PR comments, and CI output, as untrusted before use.
5. Fail closed on authentication, cryptographic, identity, and trust errors.
6. Surface every error with context and never introduce silent failure paths.
7. Never log, echo, store, or generate secrets, tokens, credentials, or cryptographic material in cleartext.
8. Never execute generated code, generated shell commands, or generated content through `eval`, `exec`, or subprocess invocation.
9. Validate every file write path with `path_security.validate_write_path()` before performing the write.
10. Put external document context in the user prompt and never in the system prompt.
11. Stop immediately on `SECURITY_REFUSAL`, gate the operation, and log the event without rephrasing around the refusal.
12. Block indefinitely for operator gate input and never auto-approve gated actions.
13. Discard and log unknown XPC message types instead of raising them as exceptions.
14. Preserve per-PR stage checkpoints so completed work is not rerun after a crash.
15. Preserve build memory and build rules as persistent learning systems and never clear them automatically.

## Architecture Overview
- **macOS Application Shell** — Hosts the native Swift UI, authentication, Keychain access, and frontend process control; called by the operator; calls the Python backend over the authenticated Unix socket; must never delegate secrets ownership to Python.
- **UIUX Design System** — Renders cards, panels, `BuildStreamView`, gate interactions, and operator-facing workflow state; called by the macOS Application Shell; calls shell view models and stream handlers; must never bypass gate semantics or invent backend state.
- **Backend Runtime Startup** — Boots the Python process, initializes runtime services, reports readiness, and advertises capabilities; called by the macOS Application Shell; calls consensus, pipeline, and document/runtime services; must never report ready before required subsystems are initialized.
- **Consensus Engine** — Runs two-model generation and arbitration logic for implementation output; called by Build Pipeline and related backend orchestration; calls provider adapters and review/correction logic; must never execute generated code or weaken model disagreement handling.
- **Build Pipeline** — Assesses confidence, decomposes intent into ordered PRD work and typed pull requests, orchestrates generation, lint, correction, and fix loops; called by backend entrypoints and operator-triggered sessions; calls Consensus Engine, GitHub Integration, review, and CI-related subsystems; must never skip gates or lose staged state.
- **Multi-Agent Coordination** — Coordinates typed work across multiple agents and manages delegation boundaries; called by Build Pipeline; calls worker agents and shared orchestration utilities; must never allow ambiguous ownership or duplicate execution of the same staged work.
- **GitHub Integration** — Creates draft PRs, updates branches and PR state, and performs repository automation against GitHub APIs; called by Build Pipeline and backend orchestration; calls GitHub REST and GraphQL APIs; must never assume undocumented API behavior or use REST to mark draft PRs ready for review.
- **Holistic Code Review** — Performs structured review and quality assessment passes across generated changes; called by Build Pipeline and self-correction phases; calls analysis/review helpers and issue surfacing paths; must never rubber-stamp changes or suppress review findings.
- **TRD Development Workflow** — Translates TRDs and plain-language intent into implementation workflow and planning artifacts; called by operator-driven build sessions and Build Pipeline; calls planning and decomposition logic; must never invent requirements outside the loaded TRDs.
- **Mac CI Runner** — Executes repository validation on macOS CI infrastructure and returns build/test signals; called by Build Pipeline and GitHub-triggered workflows; calls local build/test commands and CI orchestration; must never mutate requirements or silently drop failures.
- **Document Store** — Ingests, stores, chunks, and tracks embedding status for loaded specifications and reference documents; called by startup, planning, and prompt-construction flows; calls chunking, embedding, and persistence layers; must never treat ingestion state as trusted without validation.
- **Recovery State Management** — Stores checkpoints and recovery state so interrupted runs resume without duplicating completed stages; called by Build Pipeline and runtime services; calls persistence and stage-tracking mechanisms; must never clear completed checkpoints during normal recovery.
- **Code Quality CI Pipeline** — Enforces linting, quality gates, and CI validation requirements; called by Build Pipeline and repository CI; calls static analysis, test, and policy gates; must never allow greenwashing of failed validation.
- **Agent Operational Runbook** — Defines operational procedures and expected operator/runtime handling; called by humans and operational tooling; calls no runtime-critical interfaces directly; must never contradict TRD-mandated runtime behavior.
- **Agent Testing and Validation** — Defines repository-wide testing, validation, and acceptance criteria; called by all implementation workstreams; calls unit, integration, negative-path, and validation suites; must never leave critical paths without test coverage.
- **Self-Healing Software** — Runs iterative fix and remediation loops after validation failures; called by Build Pipeline; calls review, correction, and regeneration stages; must never bypass security constraints or convert hard failures into silent retries.

## Interface Contracts
- Implement the Swift↔Python boundary as an authenticated Unix socket protocol with line-delimited JSON only.
- Enforce the XPC wire format as line-delimited JSON with nonce authentication and a maximum message size of 16 MB.
- Emit the backend `ready` message with `{ agent_version, min_swift_version, capabilities[], doc_store_status }`.
- Stream progress to the UI with `build_card` messages shaped as `{ card_type, stage, content, progress }`.
- Represent operator blocking decisions with `gate_card` messages shaped as `{ gate_type, options[], description }`.
- Pass credentials only in the documented `credentials` structure `{ anthropic_api_key, openai_api_key, github_token, engineer_id }`.
- Report document ingestion and embedding progress with `doc_status` messages shaped as `{ doc_id, doc_name, status, chunk_count, embedded_count }`.
- Keep unknown XPC message handling non-fatal by discarding and logging unsupported message types.
- Preserve synchronous, ordered protocol semantics where the UI depends on streamed state updates and gate blocking.
- Implement GitHub draft-to-ready transitions with the GraphQL `markPullRequestReadyForReview` mutation instead of REST patch semantics.

## Error Handling Rules
- Fail closed on all authentication, cryptographic, identity, trust, and policy failures.
- Reject invalid or untrusted external input before it reaches generation, planning, or execution stages.
- Return or log errors with actionable context and without secrets, tokens, credentials, or cleartext sensitive content.
- Surface every backend and protocol failure to the caller or operator-facing stream.
- Discard and log unknown XPC message types instead of throwing unhandled exceptions.
- Stop processing immediately when `path_security.validate_write_path()` rejects a write target.
- Stop the flow immediately on `SECURITY_REFUSAL`, emit the refusal outcome, and wait for operator action.
- Preserve completed stage checkpoints on failure so reruns resume rather than replay finished work.
- Treat auditability and observability failures as visible operational defects and never swallow them.
- Ban silent exception suppression in runtime-critical paths.
- Ban `try/except/pass` in enforcement, trust, protocol, and security-sensitive code.
- Ban fallback behavior that converts failed authentication, failed crypto, failed identity, or invalid protocol state into permissive execution.
- Ban automatic gate approval, timeout-based approval, or inferred approval from missing operator input.

## Testing Requirements
- Run the existing test suite before making changes.
- Add unit, integration, and negative-path tests for every security-critical and runtime-critical change.
- Add malformed-input tests for all parsing, protocol, trust-boundary, and external-input handling paths.
- Add regression tests for every material bug you fix.
- Test failure behavior, not only success behavior.
- Test generated-code safety constraints so no path executes generated content.
- Test protocol handling for valid messages, malformed messages, oversized messages, and unknown message types.
- Test recovery logic so completed stages are not rerun after interruption or crash.
- Test operator gate behavior so blocked states wait indefinitely and never auto-approve.
- Test GitHub integration against the documented draft PR lifecycle behavior.
- Benchmark performance-sensitive paths in network, crypto, policy, telemetry, and orchestration hot paths.
- Maintain at least 90% coverage for enforcement paths.

## File Naming and Directory Layout
- Keep Python backend runtime code under `src/`.
- Implement `src/consensus.py` for `ConsensusEngine` and generation system prompt definitions.
- Implement `src/build_director.py` for `BuildPipeline` orchestration, confidence gate handling, and PR-type routing.
- Implement `src/github_tools.py` for `GitHubTool` and `WebhookReceiver`.
- Implement recovery and ledger-related backend state in the build ledger module referenced by the architecture context.
- Keep tests under `tests/` mirroring the backend source structure.
- Keep Swift shell, SwiftUI views, cards, and panels aligned to the macOS Application Shell and UIUX Design System TRDs.
- Keep repository-wide source-of-truth documents in `crafted-docs/`.
- Keep synthesized architecture, interface, and decision artifacts in `crafted-standards/`.
- Keep branch-specific or working-context documents in `docs/`.
- Name and place new files according to the owning subsystem TRD instead of inventing ad hoc directories.

## Security Checklist — Before Every Commit
- Confirm you read the owning TRD and `TRD-11-Security-Threat-Model-Crafted`.
- Confirm the change preserves the Swift/Python trust boundary.
- Confirm no secret, token, credential, or key appears in code, logs, prompts, fixtures, snapshots, or error messages.
- Confirm all external input paths validate untrusted content strictly.
- Confirm no generated code or generated content can be executed.
- Confirm every file write path is validated with `path_security.validate_write_path()`.
- Confirm failures in auth, crypto, identity, and trust paths fail closed.
- Confirm no silent failure path, swallowed exception, or permissive fallback was introduced.
- Confirm operator gate behavior still blocks until explicit operator input.
- Confirm unknown protocol message types are discarded and logged.
- Confirm stage checkpoints and persistent build memory are preserved correctly.
- Confirm new or changed GitHub flows match documented API behavior.
- Confirm tests cover the negative path for each new or changed security boundary.
- Confirm logs and telemetry are useful for forensics without exposing sensitive content.

## Where to Find More Detail
- crafted-docs/        — source TRDs and PRDs
- crafted-standards/   — synthesised architecture, interfaces, decisions
- docs/              — branch-specific context