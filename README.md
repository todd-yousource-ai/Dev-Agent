# Crafted Dev Agent

A native macOS AI coding agent that turns technical specifications and operator intent into ordered GitHub pull requests using a two-process architecture: a Swift shell and a Python backend.

## What It Does
Crafted Dev Agent is a directed build agent for developers working from TRDs and related specifications. It packages a native macOS application shell with a backend that handles consensus, build pipeline execution, multi-agent coordination, code review, GitHub operations, and recovery. The system is designed so the operator reviews and merges generated pull requests while the agent continues building the next unit of work.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI container for UI, authentication, Keychain secrets, packaging, installation, updates, and orchestration.
- **Consensus Engine** — runs the multi-model generation and arbitration flow used to produce implementation outputs.
- **Build Pipeline** — executes generation, self-correction, lint gates, fix loops, CI flow, and pull request preparation.
- **Multi-Agent Coordination** — decomposes work and manages coordination across agent-driven tasks.
- **GitHub Integration** — handles repository operations, pull request lifecycle, and GitHub API interactions.
- **Holistic Code Review** — performs review of generated changes before handoff.
- **Document Store** — stores and serves the specification and document context used by the agent.
- **Backend Runtime & Startup** — owns backend process lifecycle and runtime initialization.
- **Recovery & State Management** — preserves state and supports restart/recovery behavior.

## Architecture Overview
The system is explicitly two-process: a native Swift shell and a Python backend. The Swift process owns UI, authentication, Keychain, and local orchestration; the Python process owns intelligence, generation, pipeline execution, and GitHub operations. The two processes communicate over an authenticated Unix socket using line-delimited JSON.

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
- Read `CLAUDE.md` before changing any file.
- Find the TRD that owns the component you are modifying and use it as the source of truth.
- Review `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` before touching credentials, external content, generated code, or CI-related behavior.
- Run the existing tests before making changes: `cd src && pytest ../tests/ -v --tb=short`.
- Keep implementations aligned with documented interfaces, error contracts, state machines, and testing requirements.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| README | `forge-docs/README.md` | Product overview and TRD index context |
| AGENTS | `forge-docs/AGENTS.md` | Repository operating rules for AI agents |
| CLAUDE | `forge-docs/CLAUDE.md` | Build and implementation guidance for this codebase |
| TRD-1: macOS Application Shell | `forge-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell responsibilities, packaging, auth, UI orchestration |
| TRD-2: Consensus Engine | `forge-docs/TRD-2-Consensus-Engine-Crafted.md` | Multi-model consensus and arbitration requirements |
| TRD-3: Build Pipeline | `forge-docs/TRD-3-Build-Pipeline-Crafted.md` | Generation pipeline, correction loop, lint and CI flow |
| TRD-4: Multi-Agent Coordination | `forge-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Task decomposition and multi-agent orchestration |
| TRD-5: GitHub Integration | `forge-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub repository and pull request integration |
| TRD-6: Holistic Code Review | `forge-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review requirements for generated changes |
| TRD-7: TRD Development Workflow | `forge-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Specification-driven workflow requirements |
| TRD-8: UI/UX Design System | `forge-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system and interface requirements |
| TRD-9: Mac CI Runner | `forge-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements |
| TRD-10: Document Store | `forge-docs/TRD-10-Document-Store-Crafted.md` | Document ingestion, storage, and retrieval |
| TRD-11: Security Threat Model | `forge-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security controls and threat model governing all components |
| TRD-12: Backend Runtime & Startup | `forge-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Backend process startup and runtime behavior |
| TRD-13: Recovery & State Management | `forge-docs/TRD-13-Recovery-State-Management-Crafted.md` | State persistence and recovery requirements |
| TRD-14: Code Quality & CI Pipeline | `forge-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | Quality gates and CI requirements |
| TRD-15: Agent Operational Runbook | `forge-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures and support guidance |
| TRD-16: Agent Testing & Validation | `forge-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Validation strategy and test requirements |
| TRD-17: Self-Healing Software | `forge-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing and resilience requirements |
| GitHub Integration Lessons Learned | `forge-docs/GitHub-Integration-Lessons-Learned.md` | GitHub API behaviors discovered during build pipeline implementation |
| Architecture Context | `forge-docs/forge_architecture_context.md` | Supplemental architecture context for the system |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `forge-standards/ARCHITECTURE.md` — full system architecture
- `forge-standards/INTERFACES.md` — wire formats and API contracts
- `forge-docs/` — complete TRDs and PRDs