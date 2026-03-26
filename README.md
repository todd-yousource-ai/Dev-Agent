# Crafted Dev Agent

Crafted Dev Agent is a native macOS AI coding agent that builds software autonomously from technical specifications and opens GitHub pull requests for operator review.

## What It Does
Crafted Dev Agent takes a repository, technical requirements documents (TRDs), and plain-language operator intent, then plans the work, decomposes it into typed pull requests, generates implementation and tests, and opens draft PRs on GitHub. It is designed for a gated, review-first workflow: the agent builds, runs validation and CI, and the operator reviews, approves, and merges. The product is implemented as a two-process system with a native Swift shell and a Python backend.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI container for UI, authentication, Keychain secrets, installation, updates, and orchestration.
- **Consensus Engine** — parallel multi-model generation and arbitration across providers.
- **Build Pipeline** — turns intent and specifications into implementation, validation, fix loops, and PR-ready outputs.
- **Multi-Agent Coordination** — decomposes work into ordered units and coordinates agent execution across them.
- **GitHub Integration** — manages repository operations, branches, pull requests, and related API workflows.
- **Holistic Code Review** — performs review of generated changes before operator handoff.
- **Document Store** — stores and serves the documents the agent uses during planning and execution.
- **Backend Runtime Startup** — boots, configures, and supervises the Python backend runtime.
- **Recovery State Management** — persists state and supports restart and recovery behavior.
- **Security Threat Model** — governs credentials, external content handling, generated code constraints, and CI security controls.

## Architecture Overview
The system is split into two processes: a Swift shell and a Python backend. The Swift process owns UI, authentication, Keychain, and local orchestration; the Python process owns consensus, planning, generation, and GitHub operations. The two communicate over an authenticated Unix socket using line-delimited JSON, and generated code is never executed by either process.

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
- Find the TRD that owns the component you are modifying; the TRDs in `crafted-docs/` are the source of truth.
- Read `TRD-11-Security-Threat-Model-Crafted.md` for any change involving credentials, external content, generated code, or CI.
- Run the existing tests before and after changes: `cd src && pytest ../tests/ -v --tb=short`.
- Keep implementations aligned with documented interfaces, error contracts, state machines, and testing requirements.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `crafted-docs/AGENTS.md` | Repository-specific instructions for contributors and AI agents. |
| CLAUDE | `crafted-docs/CLAUDE.md` | Build guidance, TRD ownership hints, and implementation rules. |
| Repository README | `crafted-docs/README.md` | Product overview and high-level workflow for Crafted Dev Agent. |
| GitHub Integration Lessons Learned | `crafted-docs/GitHub-Integration-Lessons-Learned.md` | GitHub API behaviors and operational lessons from the build pipeline. |
| TRD-1: macOS Application Shell | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell responsibilities, packaging, auth, secrets, and orchestration. |
| TRD-2: Consensus Engine | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` | Multi-model consensus and arbitration requirements. |
| TRD-3: Build Pipeline | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` | Build flow from intent to generated changes, validation, and PR output. |
| TRD-4: Multi-Agent Coordination | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Work decomposition and coordination across agent tasks. |
| TRD-5: GitHub Integration | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub repository, branch, and pull request integration requirements. |
| TRD-6: Holistic Code Review | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review requirements for generated code and change sets. |
| TRD-7: TRD Development Workflow | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Workflow for creating and maintaining technical requirements documents. |
| TRD-8: UI/UX Design System | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI views, cards, panels, and design system rules. |
| TRD-9: Mac CI Runner | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements and execution model. |
| TRD-10: Document Store | `crafted-docs/TRD-10-Document-Store-Crafted.md` | Document storage and retrieval requirements. |
| TRD-11: Security Threat Model | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security model and controls for all components. |
| TRD-12: Backend Runtime Startup | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend startup, configuration, and runtime behavior. |
| TRD-13: Recovery State Management | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery, restart, and persisted state requirements. |
| TRD-14: Code Quality CI Pipeline | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | CI quality gates and pipeline expectations. |
| TRD-15: Agent Operational Runbook | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures for running and supporting the agent. |
| TRD-16: Agent Testing and Validation | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Testing and validation requirements. |
| TRD-17: Self-Healing Software | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing and recovery behavior requirements. |
| Architecture Context | `crafted-docs/forge_architecture_context.md` | Additional architecture context for the system. |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `crafted-standards/ARCHITECTURE.md` — full system architecture
- `crafted-standards/INTERFACES.md` — wire formats and API contracts
- `crafted-docs/` — complete TRDs and PRDs