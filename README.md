# Crafted Dev Agent

A native macOS AI coding agent that packages a Swift shell and Python backend to autonomously build software from technical specifications and open GitHub pull requests.

## What It Does
Crafted Dev Agent takes a repository, technical requirements documents, and operator intent, then plans work, generates implementation and tests, runs review and validation steps, and opens draft pull requests for review. It is built for a gated, specification-driven development workflow where the operator reviews and merges each logical unit. The system is explicitly split between a native macOS application shell and a Python backend, with GitHub operations, consensus, recovery, testing, and security governed by the TRDs.

## Key Subsystems
- **macOS Application Shell** — native Swift/SwiftUI container for UI, authentication, secrets, installation, and orchestration.
- **Consensus Engine** — parallel multi-model generation and arbitration for implementation decisions.
- **Build Pipeline** — turns intent and specifications into ordered work, generation, validation, and pull requests.
- **Multi-Agent Coordination** — manages agent roles, decomposition, and coordination across work units.
- **GitHub Integration** — repository, branch, pull request, and related GitHub API operations.
- **Holistic Code Review** — performs structured review of generated changes before PR handoff.
- **UI/UX Design System** — defines the SwiftUI views, cards, panels, and user-facing interaction model.
- **Document Store** — stores and serves TRDs and related documents used by the agent.
- **Backend Runtime Startup** — initializes and supervises the Python backend runtime and process startup.
- **Recovery State Management** — persists progress and supports recovery/resume across failures or restarts.

## Architecture Overview
The product uses a two-process architecture: a Swift shell owns the UI, authentication, Keychain, XPC, and local orchestration, while a Python backend owns consensus, pipeline execution, and GitHub operations. The two processes communicate over an authenticated Unix socket using line-delimited JSON. Security requirements are centralized in the Security Threat Model, and generated code is never executed by either process.

## Repository Structure
```text
crafted-docs/          — source TRDs and PRDs
crafted-standards/     — architecture, interfaces, decisions, conventions
CLAUDE.md              — LLM coding instructions (read this first)
src/                   — implementation
tests/                 — test suite
.github/workflows/     — CI
```

## Getting Started
- Read `CLAUDE.md` before making any change.
- Find the TRD that owns the component you are modifying and treat it as the source of truth.
- Read `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` for any change touching credentials, external content, generated code, or CI.
- Review the relevant interface, error, testing, and state-machine requirements in the owning TRD before coding.
- Run the existing test suite from `src/` against `tests/` before and after changes.

## Documentation

| Document | Location | What It Contains |
|---|---|---|
| AGENTS | `crafted-docs/AGENTS.md` | Repository identity, development rules, and agent instructions |
| CLAUDE | `crafted-docs/CLAUDE.md` | Build guidance, architecture summary, and TRD ownership map |
| Repository README | `crafted-docs/README.md` | Product-level overview of Crafted Dev Agent |
| TRD-1: macOS Application Shell | `crafted-docs/TRD-1-macOS-Application-Shell-Crafted.md` | Swift shell responsibilities, packaging, auth, orchestration |
| TRD-2: Consensus Engine | `crafted-docs/TRD-2-Consensus-Engine-Crafted.md` | Multi-model consensus and arbitration requirements |
| TRD-3: Build Pipeline | `crafted-docs/TRD-3-Build-Pipeline-Crafted.md` | End-to-end build flow from intent to PR |
| TRD-4: Multi-Agent Coordination | `crafted-docs/TRD-4-Multi-Agent-Coordination-Crafted.md` | Agent coordination, decomposition, and execution structure |
| TRD-5: GitHub Integration | `crafted-docs/TRD-5-GitHub-Integration-Crafted.md` | GitHub API integration and PR lifecycle handling |
| TRD-6: Holistic Code Review | `crafted-docs/TRD-6-Holistic-Code-Review-Crafted.md` | Review requirements for generated changes |
| TRD-7: TRD Development Workflow | `crafted-docs/TRD-7-TRD-Development-Workflow-Crafted.md` | Workflow for specification-driven development |
| TRD-8: UI/UX Design System | `crafted-docs/TRD-8-UIUX-Design-System-Crafted.md` | SwiftUI design system, screens, cards, and panels |
| TRD-9: Mac CI Runner | `crafted-docs/TRD-9-Mac-CI-Runner-Crafted.md` | macOS CI runner requirements |
| TRD-10: Document Store | `crafted-docs/TRD-10-Document-Store-Crafted.md` | Document storage and retrieval for specifications |
| TRD-11: Security Threat Model | `crafted-docs/TRD-11-Security-Threat-Model-Crafted.md` | Security controls and threat model for all components |
| TRD-12: Backend Runtime Startup | `crafted-docs/TRD-12-Backend-Runtime-Startup-Crafted.md` | Python backend startup, supervision, and runtime behavior |
| TRD-13: Recovery State Management | `crafted-docs/TRD-13-Recovery-State-Management-Crafted.md` | Persistence, resume, and recovery behavior |
| TRD-14: Code Quality CI Pipeline | `crafted-docs/TRD-14-Code-Quality-CI-Pipeline-Crafted.md` | CI quality gates and pipeline requirements |
| TRD-15: Agent Operational Runbook | `crafted-docs/TRD-15-Agent-Operational-Runbook-Crafted.md` | Operational procedures and runbook guidance |
| TRD-16: Agent Testing and Validation | `crafted-docs/TRD-16-Agent-Testing-and-Validation-Crafted.md` | Test and validation requirements |
| TRD-17: Self-Healing Software | `crafted-docs/TRD-17-Self-Healing-Software-Crafted.md` | Self-healing and remediation requirements |
| GitHub Integration Lessons Learned | `crafted-docs/GitHub-Integration-Lessons-Learned.md` | GitHub API behaviors discovered during build pipeline implementation |
| Architecture Context | `crafted-docs/forge_architecture_context.md` | Additional architecture context document included in the repo |

## Where to Go Next
- `CLAUDE.md` — start here before writing any code
- `crafted-standards/ARCHITECTURE.md` — full system architecture
- `crafted-standards/INTERFACES.md` — wire formats and API contracts
- `crafted-docs/` — complete TRDs and PRDs