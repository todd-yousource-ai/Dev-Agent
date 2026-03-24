# Crafted Dev Agent

A native macOS AI coding agent that builds software autonomously from specifications using a two-process architecture: a Swift shell and a Python backend.

## What It Does
Crafted Dev Agent takes a repository, technical specifications, and user intent, then plans and produces implementation work as pull requests. It uses a two-model consensus engine, a build pipeline, GitHub integration, review flows, and document retrieval to generate code and tests without executing generated code. The system is designed for developers who want a directed build agent rather than a chat interface or autocomplete tool.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI container for UI, authentication, Keychain storage, installation, and orchestration.
- **Consensus Engine** — coordinates two-model generation and arbitration for implementation results.
- **Build Pipeline** — decomposes work and drives generation, correction, gating, and iterative fix loops.
- **Multi-Agent Coordination** — manages coordination across agent roles and execution units.
- **GitHub Integration** — handles repository operations and pull request workflows.
- **Holistic Code Review** — reviews generated changes with broader project context.
- **TRD Development Workflow** — defines how specifications are loaded and used as the source of truth.
- **UI/UX Design System** — defines SwiftUI views, cards, panels, and application interaction patterns.
- **Document Store and Retrieval Engine** — ingests project documents and provides retrieval context to generation and review stages.

## Architecture Overview
Crafted Dev Agent is a two-process system: the Swift shell owns UI, authentication, secrets, and local orchestration, while the Python backend owns intelligence, generation, document retrieval, and GitHub operations. The two processes communicate over an authenticated Unix socket using line-delimited JSON. The TRDs in `forge-docs/` are the source of truth for interfaces, behavior, security, and testing.

## Repository Structure
```text
forge-docs/          — source TRDs and PRDs
forge-standards/     — architecture, interfaces, decisions, conventions
CLAUDE.md            — LLM coding instructions (read this first)
src/                 — implementation
tests/               — test suite
.github/workflows/   — CI
```

## Getting Started
- Read `CLAUDE.md` and `forge-docs/AGENTS.md` before making changes.
- Find the TRD that owns the subsystem you are modifying and use it as the source of truth.
- Review `TRD-11-Security-Threat-Model-Crafted` for any change involving credentials, external content, generated code, or CI.
- Run the existing tests before and after changes: `cd src && pytest ../tests/ -v --tb=short`
- Do not invent interfaces, states, or requirements that are not defined in the TRDs.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `forge-docs/AGENTS.md` | Repository identity, contribution rules, and implementation guardrails for AI agents |
| CLAUDE | `forge-docs/CLAUDE.md` | Build guidance, subsystem-to-TRD mapping, and coding instructions |
| README | `forge-docs/README.md` | Product overview and TRD-oriented repository guidance |
| TRD-1: macOS Application Shell | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell architecture, packaging, auth, Keychain, orchestration, and UI container requirements |
| TRD-2: Consensus Engine | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` | Two-model consensus and arbitration requirements |
| TRD-3: Build Pipeline | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` | Generation pipeline, correction, lint gates, and fix-loop behavior |
| TRD-4: Multi-Agent Coordination | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Coordination model across multiple agent roles and tasks |
| TRD-5: GitHub Integration | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` | Repository operations and pull request workflow requirements |
| TRD-6: Holistic Code Review | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review system requirements using broader project and document context |
| TRD-7: TRD Development Workflow | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Workflow for using TRDs as executable project specifications |
| TRD-8: UI/UX Design System | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system, views, panels, and interaction requirements |
| TRD-9: Mac CI Runner | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements |
| TRD-10: Document Store and Retrieval Engine | `forge-docs/TRD-10-Document-Store-Crafted.md` | Document ingestion, storage, retrieval, and generation context injection |
| TRD-11: Security Threat Model | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security controls and threat model governing all components |
| TRD-12: Backend Runtime Startup | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend startup and runtime requirements |
| TRD-13: Recovery State Management | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery flows and persisted state behavior |
| TRD-14: Code Quality CI Pipeline | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | CI quality requirements and pipeline expectations |
| TRD-15: Agent Operational Runbook | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures for running and maintaining the agent |
| TRD-16: Agent Testing and Validation | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Test strategy and validation requirements |
| TRD-17: Self-Healing Software | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing behavior and related operational requirements |
| Architecture Context | `forge-docs/forge_architecture_context.md` | Supplemental architecture context for the overall system |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `forge-standards/ARCHITECTURE.md` — full system architecture
- `forge-standards/INTERFACES.md` — wire formats and API contracts
- `forge-docs/` — complete TRDs and PRDs