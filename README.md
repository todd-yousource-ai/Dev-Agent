# Consensus Dev Agent

A native macOS AI coding agent that builds software autonomously from specifications. You load your TRDs, state your intent, and the agent opens GitHub pull requests — one per logical unit — using a two-model consensus engine (Claude + GPT-4o) with Claude arbitrating every result. You gate, review, and merge. The agent builds the next PR while you read the last one.

---

## What This Is

**Not a chat interface.** Not a code autocomplete. Not a copilot.

This is a directed build agent. You give it a repository, a set of technical specifications (TRDs), and a plain-language intent. It decomposes the intent into an ordered PRD plan, decomposes each PRD into a sequence of pull requests, generates implementation and tests for each PR using two LLM providers in parallel, runs a 3-pass review cycle, executes CI, and opens a draft PR for your review. When you approve it, the agent builds the next one. When the build completes, it optionally regenerates your documentation.

The human is in the loop at every gate. The agent is autonomous between gates.

---

## Architecture

Two-process model. Always. No exceptions.

```
┌─────────────────────────────────────────────────────────────┐
│  Swift Shell (macOS app)                                     │
│  SwiftUI · Touch ID · Keychain · XPC · Process management   │
│  TRD-1 · TRD-8                                              │
└───────────────────────┬─────────────────────────────────────┘
                        │ Unix socket (authenticated, line-delimited JSON)
                        │ TRD-1 Section 6 · TRD-12
┌───────────────────────▼─────────────────────────────────────┐
│  Python Backend                                              │
│                                                             │
│  ConsensusEngine ──── Claude (Anthropic) + GPT-4o (OpenAI) │
│  TRD-2                                                       │
│                                                             │
│  BuildPipeline ─────── 8 stages · 3-pass review · gates    │
│  TRD-3                                                       │
│                                                             │
│  GitHubTool ─────────── PAT · branches · PRs · CI          │
│  TRD-5                                                       │
│                                                             │
│  BuildLedger ────────── multi-engineer coordination         │
│  TRD-4                                                       │
│                                                             │
│  DocumentStore ──────── FAISS · sentence-transformers       │
│  TRD-10                                                      │
│                                                             │
│  HolisticReview ─────── /review start · 5 lenses · fix PRs │
│  TRD-6                                                       │
│                                                             │
│  TRDWorkflow ────────── /trd start · 8-phase facilitation  │
│  TRD-7                                                       │
└─────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  Mac CI Runner (self-hosted GitHub Actions)                  │
│  Xcode 26.3+ · xcodebuild · XCTest · swiftc type-check     │
│  TRD-9                                                       │
└─────────────────────────────────────────────────────────────┘
```

The Swift shell owns: UI, Touch ID auth, Keychain secret storage, XPC channel, process launch/monitor/restart, settings, onboarding, document import. It never executes generated code. It never calls LLM APIs directly.

The Python backend owns: consensus generation, build pipeline orchestration, GitHub operations, ledger coordination, document retrieval, review and TRD workflows. It receives credentials via XPC only — never reads Keychain directly.

---

## TRD Index

All implementation requirements live in `/forge-docs/`. Read the TRD before touching any component.

| TRD | Title | Language | Key Interfaces |
|-----|-------|----------|----------------|
| TRD-1 v1.1 | macOS Application Shell | Swift 5.9+ | XPCChannel, AuthManager, KeychainManager, BackendProcess |
| TRD-2 | Consensus Engine | Python 3.12 | ConsensusEngine.run(), ProviderAdapter, TokenBudget |
| TRD-3 | Build Pipeline and 3-Pass Review | Python 3.12 | PipelineStage, BuildThread, ThreadStateStore, CommandRouter |
| TRD-4 | Multi-Agent Coordination | Python 3.12 | BuildLedger, claim_next_pr(), mark_pr_done() |
| TRD-5 | GitHub Integration Layer | Python 3.12 | GitHubTool (24 methods), WebhookReceiver |
| TRD-6 | Holistic Code Review | Python 3.12 | ReviewDirector, LintRunner, FixPRPlan |
| TRD-7 | TRD Development Workflow | Python 3.12 | TRDSession, TRDBoundary, TRDOutline |
| TRD-8 | UI/UX Design System | Swift/SwiftUI | CardModel, GateCardView, NavigatorView, BuildStreamView |
| TRD-9 | Mac CI Runner Infrastructure | YAML/bash | forge-ci-macos.yml, XPC integration test |
| TRD-10 | Document Store and Retrieval | Python 3.12 | DocumentStore, chunk(), embed(), retrieve() |
| TRD-11 | Security Threat Model | All | SEC-CRED-*, SEC-CTX-*, SEC-CODE-*, SEC-LOG-* controls |
| TRD-12 | Backend Runtime and Handshake | Python/Swift | startup_sequence(), version_check(), graceful_shutdown() |

---

## Build Pipeline

The core loop. Triggered by `/prd start <intent>`.

```
Stage 1: Scope       — confirms subsystem, docs, branch prefix with operator
Stage 2: PRD Plan    — decomposes intent into ordered PRD list
Stage 3: PRD Gen     — generates each PRD document (both models, Claude wins)
Stage 4: PR Plan     — decomposes each PRD into ordered PR specs
Stage 5: Code Gen    — implements each PR (parallel generation, arbitration)
Stage 6: 3-Pass Review — correctness → performance → security (per PR)
Stage 7: Test + CI   — local tests, ruff/mypy, CI gate via webhook
Stage 8: Gate        — operator approves or corrects before merge
```

Every stage has a max cyclomatic complexity of 15. Every state transition is checkpointed. Every gate decision is logged to the audit trail.

---

## Consensus Engine

Both models generate in parallel. Claude scores both. The winner goes through an improvement pass if the race is close. Final code is committed.

```
Claude generates  ──┐
                    ├──▶ Comparative evaluation (Claude arbitrates) ──▶ Winner
GPT-4o generates ──┘                                                      │
                                                                           ▼
                                                          Improvement pass (if score delta < 2)
                                                                           │
                                                                           ▼
                                                                    Final code committed
```

Token budget: configurable per session. Hard stop at limit — no silent overruns. OI-13 gate blocks endpoint components until operator explicitly authorizes.

---

## CI Routing

Python/Go/TypeScript/Rust → `ubuntu-latest` (`.github/workflows/forge-ci.yml`)

Swift/Xcode → `[self-hosted, macos, xcode, x64]` (`.github/workflows/forge-ci-macos.yml`)

The Mac runner must be running on the developer MacBook for Swift PRs to be validated. See TRD-9 for setup.

---

## Security

This agent reads external documents (TRDs, PRDs) and uses them to generate code. That is a prompt injection surface.

**Mandatory before loading any external document:** Read TRD-11.

Key controls:
- All credentials stored in macOS Keychain. Never in env vars, UserDefaults, or source.
- Python backend receives credentials via XPC delivery only — never reads Keychain.
- All loaded document chunks are injection-scanned and wrapped in context delimiters.
- Generated code is never executed by the agent. Never `eval()`. Never `exec()`.
- Every PR requires operator gate approval before merge.
- Pre-release: run the TRD-11 Section 15 security checklist.

---

## Repository Layout

```
forge-docs/          — all TRDs and PRDs (source of truth)
forge-standards/     — ARCHITECTURE.md, INTERFACES.md, DECISIONS.md, CONVENTIONS.md
src/                 — Python backend implementation
ForgeAgent/          — Swift/SwiftUI application shell
ForgeAgentTests/     — XCTest suites
tests/               — Python test suite (pytest)
.github/workflows/   — forge-ci.yml (Ubuntu) + forge-ci-macos.yml (Mac runner)
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/prd start <intent>` | Begin a directed build from plain-language intent |
| `/prd start` | Begin with interactive scope confirmation |
| `/patch <description>` | Apply a targeted fix to an existing PR |
| `/review start <branch>` | Run holistic code review — 5 lenses, fix PRs |
| `/trd start` | Begin TRD development workflow — 8 phases |
| `/write <path>` | Generate and commit a file directly to main |
| `/ledger` | Show build ledger — engineers, PRDs, PR status |
| `/stop` | Graceful shutdown — flushes state before exit |

---

## Requirements

- macOS 13.0 (Ventura) or later
- Xcode 15.0+ (for building the Swift shell)
- Python 3.12 (bundled in the .app for the backend)
- Anthropic API key (Claude)
- OpenAI API key (GPT-4o)
- GitHub Personal Access Token (repo scope)
- Self-hosted Mac runner (required for Swift CI validation — TRD-9)
