# Crafted Dev Agent

A native macOS AI coding agent that packages a Swift/SwiftUI shell and a Python backend to autonomously build software from technical specifications and open GitHub pull requests.

## What It Does
Crafted is a directed build agent for macOS: you provide a repository, technical requirements documents, and an intent, and it plans work, generates implementation and tests, runs validation, and opens draft pull requests for review. The Swift shell owns UI, authentication, Keychain secrets, and process orchestration, while the Python backend owns consensus, pipeline execution, document retrieval, review, and GitHub operations. The system is specified by the TRDs in `forge-docs/`, with TRD-11 defining the security model for all components.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI container for installation, authentication, secrets, UI, and orchestration.
- **Consensus Engine** — two-model generation and arbitration subsystem used for implementation decisions.
- **Build Pipeline** — decomposes work and executes generation, validation, correction, and delivery stages.
- **Multi-Agent Coordination** — manages agent roles, sequencing, and coordinated task execution.
- **GitHub Integration** — handles repository operations, pull request creation, and related GitHub workflows.
- **Holistic Code Review** — performs review with project and document context before handoff.
- **TRD Development Workflow** — defines how technical requirements drive planning and execution.
- **UIUX Design System** — governs SwiftUI views, cards, panels, and application UX structure.
- **Document Store and Retrieval Engine** — ingests project documents and provides retrieval context to backend generation and review.
- **Backend Runtime Startup** — defines Python backend startup, runtime initialization, and process lifecycle.

## Architecture Overview
Crafted uses a two-process architecture: a native Swift shell and a Python 3.12 backend. The processes communicate over an authenticated Unix socket using line-delimited JSON, with the shell owning user-facing and security-sensitive responsibilities and the backend owning intelligence, retrieval, generation, review, and GitHub execution. Recovery, CI, testing, and self-healing behavior are defined in dedicated TRDs.

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
- Read `CLAUDE.md` and `forge-docs/AGENTS.md` before changing code.
- Find the TRD that owns the component you are modifying; the TRDs in `forge-docs/` are the source of truth.
- Review TRD-11 before touching credentials, external content, generated code, or CI behavior.
- Run the existing test suite before and after changes.
- Keep interfaces, error contracts, state behavior, and security controls aligned with the owning TRD.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `forge-docs/AGENTS.md` | Repository identity, workflow expectations, and contribution rules for AI agents |
| CLAUDE | `forge-docs/CLAUDE.md` | Build guidance, architecture summary, and TRD ownership map |
| README | `forge-docs/README.md` | Product-level overview of Crafted Dev Agent |
| TRD-1: macOS Application Shell | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell architecture, packaging, auth, UI ownership, and orchestration |
| TRD-2: Consensus Engine | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` | Consensus and arbitration behavior for model-driven generation |
| TRD-3: Build Pipeline | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` | Pipeline stages for planning, generation, validation, and correction |
| TRD-4: Multi-Agent Coordination | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Agent coordination model and task sequencing |
| TRD-5: GitHub Integration | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub repository and pull request operations |
| TRD-6: Holistic Code Review | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review subsystem requirements and context-aware review behavior |
| TRD-7: TRD Development Workflow | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Requirements-driven workflow for development and execution |
| TRD-8: UIUX Design System | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system, view structure, and UX patterns |
| TRD-9: Mac CI Runner | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements |
| TRD-10: Document Store and Retrieval Engine | `forge-docs/TRD-10-Document-Store-Crafted.md` | Document ingestion, storage, retrieval, and context injection |
| TRD-11: Security Threat Model | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security model and controls governing all components |
| TRD-12: Backend Runtime Startup | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend bootstrap, runtime startup, and lifecycle |
| TRD-13: Recovery State Management | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery and state management behavior |
| TRD-14: Code Quality CI Pipeline | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | CI quality gates and pipeline expectations |
| TRD-15: Agent Operational Runbook | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures for running and supporting the agent |
| TRD-16: Agent Testing and Validation | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Testing and validation requirements |
| TRD-17: Self-Healing Software | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing behavior and remediation requirements |
| Architecture Context | `forge-docs/forge_architecture_context.md` | Supplemental architecture context across the system |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `forge-standards/ARCHITECTURE.md` — full system architecture
- `forge-standards/INTERFACES.md` — wire formats and API contracts
- `forge-docs/` — complete TRDs and PRDs