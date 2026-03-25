# Crafted Dev Agent

A native macOS AI coding agent that packages a Swift shell and Python backend to autonomously build software from specifications and open GitHub pull requests.

## What It Does
Crafted Dev Agent takes a repository, technical requirements documents, and operator intent, then plans work, generates implementation and tests, runs review and validation gates, executes CI, and opens draft pull requests for review. It is built for a gated workflow where the agent prepares changes and the operator reviews and merges them. The system is specified by the TRDs in `crafted-docs/`, with security requirements governed by TRD-11.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI container for UI, installation, authentication, secrets, and orchestration.
- **Consensus Engine** — coordinates multi-model generation and arbitration for implementation decisions.
- **Build Pipeline** — turns planned work into generated code, validation passes, and pull request output.
- **Multi-Agent Coordination** — manages task decomposition and coordination across agent activities.
- **GitHub Integration** — handles repository operations, pull request lifecycle, and GitHub API interactions.
- **Holistic Code Review** — evaluates generated changes before they are surfaced for operator review.
- **UI/UX Design System** — defines the SwiftUI views, cards, panels, and application interaction patterns.
- **Document Store** — stores and serves the specification inputs and related working documents.
- **Backend Runtime Startup** — owns Python backend startup, runtime initialization, and process bootstrapping.
- **Recovery State Management** — manages recovery behavior and persisted state across failures or restarts.

## Architecture Overview
Crafted uses a two-process architecture: a native Swift shell for UI, authentication, Keychain, and system integration, and a Python backend for consensus, pipeline execution, and GitHub operations. The processes communicate over an authenticated Unix socket using line-delimited JSON. The shell orchestrates lifecycle and trust boundaries, while the backend performs planning, generation, validation, and repository automation.

## Repository Structure
```text
crafted-docs/          — source TRDs and PRDs
crafted-standards/     — architecture, interfaces, decisions, conventions
CLAUDE.md            — LLM coding instructions (read this first)
src/                 — implementation
tests/               — test suite
.github/workflows/   — CI
```

## Getting Started
- Read `CLAUDE.md` and `crafted-docs/AGENTS.md` before making changes.
- Find the TRD for the subsystem you are touching and treat it as the source of truth.
- Review `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` for any change involving credentials, external content, generated code, or CI.
- Run the existing tests before and after changes: `cd src && pytest ../tests/ -v`.
- Keep implementation aligned with the documented interfaces, error contracts, and state machines.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `crafted-docs/AGENTS.md` | Repository-specific instructions for contributors and AI agents |
| CLAUDE | `crafted-docs/CLAUDE.md` | Build and implementation guidance mapped to TRDs |
| Repository README | `crafted-docs/README.md` | Product overview and TRD-oriented repository guidance |
| TRD-1: macOS Application Shell | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell responsibilities, packaging, authentication, orchestration |
| TRD-2: Consensus Engine | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` | Multi-model consensus and arbitration behavior |
| TRD-3: Build Pipeline | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` | End-to-end build flow from planning through PR creation |
| TRD-4: Multi-Agent Coordination | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Coordination model for agent task decomposition and execution |
| TRD-5: GitHub Integration | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub repository, branch, and pull request operations |
| TRD-6: Holistic Code Review | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review requirements for generated changes |
| TRD-7: TRD Development Workflow | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Workflow for developing against TRDs |
| TRD-8: UI/UX Design System | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system, views, cards, and panels |
| TRD-9: Mac CI Runner | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements and behavior |
| TRD-10: Document Store | `crafted-docs/TRD-10-Document-Store-Crafted.md` | Document storage and retrieval subsystem |
| TRD-11: Security Threat Model | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security controls, boundaries, and threat model |
| TRD-12: Backend Runtime Startup | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend startup and initialization requirements |
| TRD-13: Recovery State Management | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery and state persistence behavior |
| TRD-14: Code Quality CI Pipeline | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | CI quality gates and validation expectations |
| TRD-15: Agent Operational Runbook | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures for running and supporting the agent |
| TRD-16: Agent Testing and Validation | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Test and validation requirements |
| TRD-17: Self-Healing Software | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing and corrective runtime behavior |
| GitHub Integration Lessons Learned | `crafted-docs/GitHub-Integration-Lessons-Learned.md` | GitHub API behaviors discovered during build pipeline implementation |
| Architecture Context | `crafted-docs/forge_architecture_context.md` | Additional architecture context for the system |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `crafted-standards/ARCHITECTURE.md` — full system architecture
- `crafted-standards/INTERFACES.md` — wire formats and API contracts
- `crafted-docs/` — complete TRDs and PRDs