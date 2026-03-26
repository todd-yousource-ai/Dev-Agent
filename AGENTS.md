# AGENTS.md

Crafted Dev Agent is a native macOS AI coding agent that autonomously builds software from technical specifications using a two-process architecture (Swift shell + Python backend) with a two-model consensus engine, opening GitHub pull requests that operators gate, review, and merge.

## How to Use This File

This file is the authoritative baseline for every AI agent and human engineer working in this repository — read it completely before touching any code. For subsystem-specific detail, see `crafted-docs/` for the full TRDs and `crafted-standards/` for synthesised architecture, interface, and decision documents.

## Document Index

| Document Name | Type | Repo Path | What It Covers |
|---|---|---|---|
| AGENTS | MD | `crafted-docs/AGENTS.md` | Instructions for AI agents working in this repo; component-to-TRD mapping, pre-coding checklist |
| CLAUDE | MD | `crafted-docs/CLAUDE.md` | Master context file; architecture summary, TRD authority table, critical invariants |
| GitHub-Integration-Lessons-Learned | DOCX/MD | `crafted-docs/GitHub-Integration-Lessons-Learned.docx` / `crafted-docs/GitHub-Integration-Lessons-Learned.md` | Hard-won GitHub API edge cases: draft PR lifecycle, GraphQL mutations, merge behaviour |
| README | MD | `crafted-docs/README.md` | Product overview, build instructions, operator workflow, high-level architecture |
| TRD-1-macOS-Application-Shell-Crafted | DOCX/MD | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.docx` / `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell: UI process, Keychain, XPC host, authentication, app lifecycle |
| TRD-2-Consensus-Engine-Crafted | DOCX/MD | `crafted-docs/TRD-2-Consensus-Engine-Crafted.docx` / `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` | ConsensusEngine: dual-provider generation (Claude + GPT-4o), arbitration, provider adapters |
| TRD-3-Build-Pipeline-Crafted | DOCX/MD | `crafted-docs/TRD-3-Build-Pipeline-Crafted.docx` / `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` | BuildPipeline orchestration: PR-type routing, confidence gates, stage sequencing |
| TRD-4-Multi-Agent-Coordination-Crafted | DOCX/MD | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.docx` / `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Multi-agent coordination: task decomposition, agent-to-agent protocol, concurrency |
| TRD-5-GitHub-Integration-Crafted | DOCX/MD | `crafted-docs/TRD-5-GitHub-Integration-Crafted.docx` / `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHubTool: PR creation, branch management, webhook receiver, API error handling |
| TRD-6-Holistic-Code-Review-Crafted | DOCX/MD | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.docx` / `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Holistic code review: self-correction pass, lint gate, iterative fix loop, quality scoring |
| TRD-7-TRD-Development-Workflow-Crafted | DOCX/MD | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.docx` / `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | TRD-driven development workflow: spec-first process, PRD decomposition, intent mapping |
| TRD-8-UIUX-Design-System-Crafted | DOCX/MD | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.docx` / `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` | UI/UX design system: BuildStreamView, build_card/gate_card rendering, SwiftUI components |
| TRD-9-Mac-CI-Runner-Crafted | DOCX/MD | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.docx` / `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` | Mac CI runner: local CI execution, sandbox, test orchestration, artifact management |
| TRD-10-Document-Store-Crafted | DOCX/MD | `crafted-docs/TRD-10-Document-Store-Crafted.docx` / `crafted-docs/TRD-10-Document-Store-Crafted.md` | Document store: TRD embedding, chunk indexing, retrieval for context injection |
| TRD-11-Security-Threat-Model-Crafted | DOCX/MD | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.docx` / `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security & threat model: trust boundaries, credential handling, prompt injection defence, audit |
| TRD-12-Backend-Runtime-Startup-Crafted | DOCX/MD | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.docx` / `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Backend runtime: Python process startup, venv bootstrap, health check, shutdown |
| TRD-13-Recovery-State-Management-Crafted | DOCX/MD | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.docx` / `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery & state management: per-PR stage checkpoints, crash recovery, idempotent resume |
| TRD-14-Code-Quality-CI-Pipeline-Crafted | DOCX/MD | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.docx` / `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | Code quality CI pipeline: lint, type-check, test gates, quality thresholds |
| TRD-15-Agent-Operational-Runbook-Crafted | DOCX/MD | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.docx` / `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational runbook: diagnostics, failure recovery procedures, operator escalation |
| TRD-16-Agent-Testing-and-Validation-Crafted | DOCX/MD | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.docx` / `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Testing & validation: test strategy, coverage requirements, integration/E2E test plans |
| TRD-17-Self-Healing-Software-Crafted | DOCX/MD | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.docx` / `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing: build memory, build rules, automatic error pattern detection, persistent learning |
| forge_architecture_context | MD | `crafted-docs/forge_architecture_context.md` | Architecture context: XPC wire format, protocol messages, system prompt structure, key invariants |

## Critical Rules — Non-Negotiable

1. **Never execute generated code.** No `eval`, no `exec`, no `subprocess` of any LLM output — in either process.
2. **Fail closed on all auth, crypto, identity, and credential errors.** Reject the action, log the event, surface to the caller — never silently degrade.
3. **Never expose secrets in logs, error messages, or generated code.** API keys, tokens, and credentials must only exist in Keychain (Swift) or in-memory after XPC credential delivery.
4. **All external input is untrusted.** Documents, PR comments, CI output, and webhook payloads must be validated before use. External document context goes in the USER prompt — never the SYSTEM prompt.
5. **Gates wait indefinitely for operator input.** No auto-approve, no timeout-to-approve, no bypass. A `gate_card` blocks until the operator explicitly responds.
6. **All file writes must be path-validated via `path_security.validate_write_path()` before execution.** No file I/O without explicit path validation.
7. **XPC unknown message types are discarded and logged — never raised as exceptions.** The XPC handler must be tolerant of unrecognized messages from future versions.
8. **Per-PR stage checkpoints prevent re-running completed work after a crash.** The build ledger is the source of truth for pipeline state; honour it on resume.
9. **Build memory and build rules are never cleared automatically.** They are persistent learning systems that accumulate across sessions (TRD-17).
10. **`SECURITY_REFUSAL` output from any provider is terminal.** Never rephrase, retry, or bypass — stop, gate, log.
11. **Draft PRs must be converted to ready-for-review using the GraphQL `markPullRequestReadyForReview` mutation only.** REST PATCH with `{"draft": false}` silently fails.
12. **Claude arbitrates every consensus result.** GPT-4o is a secondary generator; Claude is the final authority in the ConsensusEngine (TRD-2).
13. **Every TRD in `forge-docs/` is the source of truth for its subsystem.** Code must match the TRD. When a TRD and the code disagree, the TRD wins — update the code.
14. **No silent failure paths anywhere.** Every error must surface with component name, operation, failure reason, and context. `try/except/pass` is banned in all enforcement and pipeline code.
15. **Credential delivery happens exactly once per session via XPC.** The Python backend never reads credentials from disk, environment variables, or config files.

## Architecture Overview

Crafted Dev Agent is a **two-process** macOS application:

```
┌─────────────────────────────┐     XPC (Unix socket, line-delimited JSON)     ┌──────────────────────────────┐
│       Swift Shell           │ ◄──────────────────────────────────────────────► │       Python Backend         │
│  (UI, Auth, Keychain, XPC)  │                                                 │  (Consensus, Pipeline, Git)  │
└─────────────────────────────┘                                                 └──────────────────────────────┘
```

### Subsystem Map

| Subsystem | What It Does | Called By | Calls | Must NEVER Do |
|---|---|---|---|---|
| **macOS Application Shell** (TRD-1) | Hosts SwiftUI, manages app lifecycle, owns Keychain, runs XPC host | User interaction, macOS | XPC → Python backend | Execute generated code; store secrets outside Keychain |
| **ConsensusEngine** (TRD-2) | Runs dual-provider generation (Claude + GPT-4o) in parallel, Claude arbitrates | BuildPipeline | Provider adapters (Anthropic, OpenAI) | Use a single provider without consensus; auto-select without arbitration |
| **BuildPipeline** (TRD-3) | Orchestrates PR lifecycle: confidence assessment → decomposition → generation → review → PR | Operator intent via XPC | ConsensusEngine, GitHubTool, HolisticReview, BuildLedger | Skip confidence gate; merge without operator approval |
| **Multi-Agent Coordination** (TRD-4) | Decomposes large intents into ordered tasks, coordinates parallel agent work | BuildPipeline | ConsensusEngine, GitHubTool | Allow agents to share mutable state without coordination protocol |
| **GitHubTool** (TRD-5) | Creates branches, opens draft PRs, manages webhooks, handles GitHub API | BuildPipeline, WebhookReceiver | GitHub REST/GraphQL API | Use REST PATCH to convert draft PRs; commit directly to main |
| **Holistic Code Review** (TRD-6) | Self-correction pass, lint gate, iterative fix loop, quality scoring | BuildPipeline (post-generation) | ConsensusEngine, linters | Skip lint gate; accept code below quality threshold |
| **TRD Development Workflow** (TRD-7) | Spec-first process: intent → PRD plan → PR sequence | Operator | BuildPipeline | Generate code without a governing TRD or PRD |
| **UI/UX Design System** (TRD-8) | `build_card` and `gate_card` rendering, BuildStreamView, SwiftUI components | macOS Shell (SwiftUI) | XPC messages from backend | Auto-dismiss gate cards; render without streaming |
| **Mac CI Runner** (TRD-9) | Local CI execution in sandbox, test orchestration, artifact management | BuildPipeline (post-PR) | Xcode toolchain, pytest | Run CI outside sandbox; allow network access during test |
| **Document Store** (TRD-10) | TRD embedding, chunk indexing, semantic retrieval for context injection | ConsensusEngine (context), BuildPipeline | Embedding model, local vector store | Inject document content into SYSTEM prompt; skip chunking |
| **Security & Threat Model** (TRD-11) | Defines trust boundaries, credential handling, prompt injection defences, audit requirements | All subsystems | N/A (policy document) | Be overridden by convenience; allow implicit trust |
| **Backend Runtime & Startup** (TRD-12) | Python process bootstrap: venv creation, dependency install, health check, shutdown | macOS Shell (process launch) | pip, Python stdlib | Start without health check; use system Python |
| **Recovery & State Management** (TRD-13) | Per-PR stage checkpoints, crash recovery, idempotent resume | BuildPipeline (on crash/restart) | BuildLedger | Re-run completed stages; clear checkpoint state |
| **Code Quality CI Pipeline** (TRD-14) | Lint, type-check, test gates with configurable quality thresholds | BuildPipeline, CI Runner | ruff, mypy, pytest | Merge below threshold; skip type checking |
| **Agent Operational Runbook** (TRD-15) | Diagnostics, failure recovery procedures, operator escalation paths | Operators (manual reference) | N/A | N/A |
| **Agent Testing & Validation** (TRD-16) | Test strategy, coverage requirements, integration and E2E test plans | CI, developers | pytest, XPC test harness | Ship without negative-path tests for security boundaries |
| **Self-Healing / Build Memory** (TRD-17) | Persistent build memory, build rules, automatic error pattern detection | BuildPipeline (on failure) | BuildLedger, ConsensusEngine | Auto-clear build memory; ignore accumulated rules |

## Interface Contracts

### XPC Wire Protocol
- **Format:** Line-delimited JSON over authenticated Unix domain socket.
- **Max message size:** 16 MB per message.
- **Authentication:** Nonce-authenticated handshake at connection start.
- **Unknown message types:** Discard and log — never raise exceptions.

### XPC Message Types

| Message | Direction | Required Fields | Purpose |
|---|---|---|---|
| `ready` | Backend → Shell | `agent_version`, `min_swift_version`, `capabilities[]`, `doc_store_status` | Backend signals readiness after startup |
| `credentials` | Shell → Backend | `anthropic_api_key`, `openai_api_key`, `github_token`, `engineer_id` | One-time credential delivery per session |
| `build_card` | Backend → Shell | `card_type`, `stage`, `content`, `progress` | Streamed progress update to BuildStreamView |
| `gate_card` | Backend → Shell | `gate_type`, `options[]`, `description` | Blocks pipeline until operator responds |
| `doc_status` | Backend → Shell | `doc_id`, `doc_name`, `status`, `chunk_count`, `embedded_count` | Document embedding progress |

### ConsensusEngine Contract
- Every generation request runs both Claude and GPT-4o in parallel.
- Claude arbitrates the final result — GPT-4o output is advisory.
- If either provider returns `SECURITY_REFUSAL`, the pipeline stops, logs the event, and surfaces a gate card.
- Provider adapter failures are retried with exponential backoff; after max retries, the stage fails closed.

### BuildPipeline Stage Contract
- Each PR progresses through defined stages: `confidence → decompose → generate → review → lint → fix → pr_open → gate`.
- Stage transitions are recorded in the BuildLedger as checkpoints.
- A stage that has a checkpoint recorded is never re-executed on resume.
- Confidence assessment must complete before any generation begins.

### GitHubTool Contract
- All PRs are opened as drafts.
- Draft → ready conversion uses GraphQL `markPullRequestReadyForReview` mutation only.
- Branch names follow the pattern defined in TRD-5.
- All GitHub API calls must handle rate limiting (HTTP 403/429) with backoff.
- Webhook payloads are untrusted external input — validate before processing.

### Document Store Contract
- Documents are chunked before embedding — never embedded whole.
- Retrieved context is injected into the USER prompt — never the SYSTEM prompt.
- `doc_status` messages are emitted for each document as embedding progresses.
- Document store status is reported in the `ready` message at startup.

## Error Handling Rules

### Fail-Closed Mandate
All errors in authentication, credential handling, cryptographic operations, identity verification, prompt injection detection, and policy enforcement **must fail closed**: reject the action, log structured context, surface the failure to the operator.

### Required Error Context
Every error must include:
- **Component name** (which subsystem raised it)
- **Operation** (what was being attempted)
- **Failure reason** (what went wrong)
- **Session/PR context** (if available)

### Banned Patterns
- `try/except/pass` — banned in all pipeline and enforcement code.
- `except Exception: pass` — banned everywhere.
- Swallowing XPC errors — every XPC failure must be logged and surfaced.
- Returning default/fallback values on security failures — fail, do not degrade.
- Logging secrets, tokens, API keys, or credentials in any error path.
- Raising generic `Exception` without specific failure context.

### Specific Failure Behaviours

| Failure Type | Required Behaviour |
|---|---|
| XPC connection lost | Backend enters shutdown sequence; Shell shows disconnected state |
| Provider API timeout | Retry with exponential backoff; after max retries, fail the stage |
| Provider SECURITY_REFUSAL | Stop immediately, log event, surface gate card to operator |
| GitHub API rate limit (403/429) | Back off per Retry-After header; do not retry immediately |
| GitHub draft→ready REST PATCH | Do not use — use GraphQL mutation instead |
| Credential delivery missing fields | Reject session start; do not proceed with partial credentials |
| Path validation failure | Reject the file write; log the attempted path; do not fall back |
| Checkpoint found for stage | Skip the stage; do not re-execute |
| Document embedding failure | Report via `doc_status`; do not inject un-embedded content |
| Build memory rule match | Apply the rule; log which rule fired and why |

## Testing Requirements

### Coverage Rules
- Enforcement paths (security, credentials, path validation, XPC auth): **≥ 90% coverage**.
- Pipeline stages: every stage must have