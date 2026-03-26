# Crafted Dev Agent

A native macOS AI coding agent that turns technical specifications and operator intent into staged GitHub pull requests through a two-process Swift shell and Python backend.

## What It Does
Crafted Dev Agent is built to autonomously develop software from specifications, using TRDs as the source of truth and GitHub pull requests as the unit of delivery. It packages a native macOS application shell with a backend runtime that handles consensus, pipeline execution, coordination, review, and GitHub operations. The operator reviews and merges the output; the agent does not execute generated code.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI shell for UI, installation, authentication, Keychain storage, and orchestration.
- **Consensus Engine** — evaluates and arbitrates model output across providers.
- **Build Pipeline** — generates implementation and tests, runs correction loops, and prepares changes for review.
- **Multi-Agent Coordination** — decomposes work and coordinates typed pull requests across the delivery flow.
- **GitHub Integration** — manages repository operations, draft pull requests, and related GitHub API workflows.
- **Holistic Code Review** — performs review of generated changes before human approval.
- **UI/UX Design System** — defines SwiftUI views, cards, panels, and interaction patterns for the macOS app.
- **Document Store** — manages the specification documents and related working context used by the agent.
- **Backend Runtime Startup** — initializes and boots the Python backend runtime and supporting services.
- **Recovery State Management** — persists and restores agent state for recovery and continuity.

## Architecture Overview
The system uses a two-process architecture: a native Swift shell and a Python backend. The Swift process owns UI, authentication, secrets, Keychain access, and local orchestration; the Python process owns intelligence, generation, consensus, pipeline execution, and GitHub operations. The two processes communicate over an authenticated Unix socket using line-delimited JSON.

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
- Review `TRD-11-Security-Threat-Model-Crafted` before touching credentials, external content, generated code, or CI.
- Run the existing tests before and after changes: `cd src && pytest ../tests/ -v --tb=short`.
- Keep implementation aligned with documented interfaces, error contracts, and state machines.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `crafted-docs/AGENTS.md` | Repository-specific instructions for AI agents and contribution guardrails |
| CLAUDE | `crafted-docs/CLAUDE.md` | Build guidance, subsystem ownership, and implementation expectations |
| Repository README | `crafted-docs/README.md` | Product overview and TRD-oriented repository guidance |
| TRD-1: macOS Application Shell | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell, packaging, auth, secrets, UI container, orchestration |
| TRD-2: Consensus Engine | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` | Multi-model consensus and arbitration requirements |
| TRD-3: Build Pipeline | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` | Generation pipeline, correction loops, and delivery flow |
| TRD-4: Multi-Agent Coordination | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Work decomposition and coordinated agent behavior |
| TRD-5: GitHub Integration | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub repository, PR, and API integration requirements |
| TRD-6: Holistic Code Review | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review system requirements for generated changes |
| TRD-7: TRD Development Workflow | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Workflow for developing against technical requirements documents |
| TRD-8: UI/UX Design System | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system, view structure, and interaction patterns |
| TRD-9: Mac CI Runner | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements |
| TRD-10: Document Store | `crafted-docs/TRD-10-Document-Store-Crafted.md` | Specification and document storage model |
| TRD-11: Security Threat Model | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security model and controls governing all components |
| TRD-12: Backend Runtime Startup | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend boot and startup behavior |
| TRD-13: Recovery State Management | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` | Recovery, persistence, and state continuity |
| TRD-14: Code Quality CI Pipeline | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | CI quality gates and pipeline requirements |
| TRD-15: Agent Operational Runbook | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures and runtime guidance |
| TRD-16: Agent Testing and Validation | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Testing and validation requirements |
| TRD-17: Self-Healing Software | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing and remediation behavior |
| GitHub Integration Lessons Learned | `crafted-docs/GitHub-Integration-Lessons-Learned.md` | GitHub API behaviors discovered during build pipeline implementation |
| Architecture Context | `crafted-docs/forge_architecture_context.md` | Additional architecture context for the system |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `crafted-standards/ARCHITECTURE.md` — full system architecture
- `crafted-standards/INTERFACES.md` — wire formats and API contracts
- `crafted-docs/` — complete TRDs and PRDs