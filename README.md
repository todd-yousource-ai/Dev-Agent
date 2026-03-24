# Crafted Dev Agent

A native macOS AI coding agent that builds software autonomously from specifications using a two-process architecture: a Swift shell and a Python backend.

## What It Does

Crafted Dev Agent lets a developer load technical requirements, state an intent, and have the system generate implementation work and open GitHub pull requests for review. The Swift shell handles UI, authentication, secrets, installation, and orchestration, while the Python backend handles consensus, generation, pipeline execution, document retrieval, and GitHub operations. It is designed as a directed build agent rather than a chat interface or code autocomplete tool.

## Key Subsystems

- **macOS Application Shell** — native Swift/SwiftUI container for packaging, installation, authentication, secrets, UI, and orchestration.
- **Consensus Engine** — coordinates two-model generation and arbitration for implementation results.
- **Build Pipeline** — decomposes work and executes generation, correction, lint, fix, and CI stages.
- **Multi-Agent Coordination** — manages agent roles and coordination across build activities.
- **GitHub Integration** — performs repository operations and opens pull requests.
- **Holistic Code Review** — reviews generated changes with broader code and document context.
- **TRD Development Workflow** — defines the specification-driven workflow for building from TRDs.
- **UI/UX Design System** — governs SwiftUI views, cards, panels, and application interaction patterns.
- **Document Store and Retrieval Engine** — ingests project documents and provides retrieval context to generation and review.
- **Backend Runtime Startup** — boots and supervises the Python backend runtime.

## Architecture Overview

The system is split into two processes: a native macOS Swift shell and a Python 3.12 backend. They communicate over an authenticated Unix socket using line-delimited JSON, with the shell owning UI, auth, Keychain, and orchestration, and the backend owning intelligence, document retrieval, pipeline execution, and GitHub operations. The TRDs in `forge-docs/` are the source of truth for interfaces, state machines, error contracts, and security controls.

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

- Read `CLAUDE.md` before making any change.
- Find the TRD that owns the component you are modifying in `forge-docs/`.
- For security-relevant changes, read **TRD-11** first, as referenced by the repo guidance.
- Run the existing tests before and after changes: `cd src && pytest ../tests/ -v`.
- Match implementation to the TRDs exactly; do not invent interfaces, behaviors, or requirements.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `forge-docs/AGENTS.md` | Repository identity, workflow rules, and agent instructions |
| CLAUDE | `forge-docs/CLAUDE.md` | Build guidance, architecture summary, and TRD routing by subsystem |
| README | `forge-docs/README.md` | Product overview and high-level behavior |
| TRD-1: macOS Application Shell | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell responsibilities, app structure, auth, secrets, UI, and orchestration |
| TRD-2: Consensus Engine | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` | Consensus generation and arbitration requirements |
| TRD-3: Build Pipeline | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` | Pipeline stages and execution flow |
| TRD-4: Multi-Agent Coordination | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Agent coordination model and responsibilities |
| TRD-5: GitHub Integration | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub operations and pull request behavior |
| TRD-6: Holistic Code Review | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Code review subsystem requirements |
| TRD-7: TRD Development Workflow | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Specification-driven development workflow |
| TRD-8: UI/UX Design System | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` | View system, cards, panels, and design rules |
| TRD-9: Mac CI Runner | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements |
| TRD-10: Document Store and Retrieval Engine | `forge-docs/TRD-10-Document-Store-Crafted.md` | Document ingestion, storage, retrieval, and context injection |
| TRD-12: Backend Runtime Startup | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend startup and supervision |
| TRD-13: Recovery State Management | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery and state management behavior |
| TRD-14: Code Quality CI Pipeline | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | Quality gates and CI requirements |
| TRD-15: Agent Operational Runbook | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational guidance for running the agent |
| TRD-16: Agent Testing and Validation | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Testing and validation requirements |
| TRD-17: Self-Healing Software | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing behavior and operational recovery expectations |
| Architecture Context | `forge-docs/forge_architecture_context.md` | Supporting architecture context for the system |

## Where to Go Next

- `CLAUDE.md` — start here before writing any code
- `forge-standards/ARCHITECTURE.md` — full system architecture
- `forge-standards/INTERFACES.md` — wire formats and API contracts
- `forge-docs/` — complete TRDs and PRDs