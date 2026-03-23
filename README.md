# Crafted Dev Agent

A native macOS AI coding agent that builds software autonomously from specifications. You load your TRDs, state your intent, and the agent opens GitHub pull requests — one per logical unit — using a two-model consensus engine (Claude + GPT-4o) with Claude arbitrating every result. You gate, review, and merge. The agent builds the next PR while you read the last one.

---

## What This Is

**Not a chat interface.** Not a code autocomplete. Not a copilot.

This is a directed build agent. You give it a repository, a set of technical specifications (TRDs), and a plain-language intent. It assesses its confidence in the scope before committing to it, decomposes the intent into an ordered PRD plan, decomposes each PRD into a sequence of typed pull requests, generates implementation and tests using two LLM providers in parallel, runs a self-correction pass, a lint gate, and an iterative fix loop, executes CI, and opens a draft PR for your review. When you approve it, the agent builds the next one.

The human is in the loop at every gate. The agent is autonomous between gates. Each run makes the next run faster — the agent learns from its own build history.

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
│  BuildPipeline ─────── confidence gate · pr_type routing   │
│  TRD-3                 self-correction · lint gate · 20-pass fix loop │
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
│                                                             │
│  BuildMemory ────────── cross-run PR pattern persistence    │
│  TRD-13                                                      │
│                                                             │
│  BuildRulesEngine ───── self-improving coding rules         │
│  TRD-13                                                      │
└─────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  Mac CI Runner (self-hosted GitHub Actions)                  │
│  Xcode · xcodebuild · XCTest · swiftc type-check           │
│  TRD-9                                                       │
└─────────────────────────────────────────────────────────────┘
```

The Swift shell owns: UI, Touch ID auth, Keychain secret storage, XPC channel, process launch/monitor/restart. It never executes generated code. It never calls LLM APIs directly.

The Python backend owns: consensus generation, build pipeline orchestration, GitHub operations, ledger coordination, document retrieval, review and TRD workflows, cross-run learning. It receives credentials via XPC only — never reads Keychain directly.

---

## TRD Index

All implementation requirements live in `/forge-docs/`. Read the TRD before touching any component.

| TRD | Title | Language | Key Interfaces |
|-----|-------|----------|----------------|
| TRD-1 | macOS Application Shell | Swift 5.9+ | XPCChannel, AuthManager, KeychainManager, BackendProcess |
| TRD-2 | Consensus Engine | Python 3.12 | ConsensusEngine.run(), ProviderAdapter, TokenBudget |
| TRD-3 | Build Pipeline and Iterative Code Quality Engine | Python 3.12 | BuildDirector, PRSpec (pr_type), confidence gate, ThreadStateStore |
| TRD-4 | Multi-Agent Coordination | Python 3.12 | BuildLedger, claim_next_pr(), mark_pr_done() |
| TRD-5 | GitHub Integration Layer | Python 3.12 | GitHubTool, WebhookReceiver, CIChecker |
| TRD-6 | Holistic Code Review | Python 3.12 | ReviewDirector, LintRunner, FixPRPlan |
| TRD-7 | TRD Development Workflow | Python 3.12 | TRDSession, TRDBoundary, TRDOutline, FOUNDER/ENGINEER/CONSULTANT modes |
| TRD-8 | UI/UX Design System | Swift/SwiftUI | CardModel, GateCardView, NavigatorView, BuildStreamView, Figma pipeline |
| TRD-9 | Mac CI Runner Infrastructure | YAML/bash | crafted-ci-macos.yml, XPC integration test |
| TRD-10 | Document Store and Retrieval | Python 3.12 | DocumentStore, chunk(), embed(), retrieve() |
| TRD-11 | Security Threat Model | All | SEC-CRED-*, SEC-CTX-*, SEC-CODE-*, SEC-LOG-* controls |
| TRD-12 | Backend Runtime and Handshake | Python/Swift | startup_sequence(), version_check(), graceful_shutdown() |
| TRD-13 | Recovery and State Management | Python 3.12 | ThreadStateStore, BuildMemory, BuildRulesEngine, ContextManager |
| TRD-14 | Code Quality and CI Pipeline | Python 3.12 | LintGate, SelfCorrectionLoop, ci_workflow, conftest.py |
| TRD-15 | Agent Operational Runbook | Reference | Clean run checklist, console output reference, key file locations |
| TRD-16 | Agent Testing and Validation | Python 3.12 | FM taxonomy (7 buckets), test_regression_taxonomy.py (35 tests) |

---

## Build Pipeline

The core loop. Triggered by `/prd start <intent>`.

```
Stage 0: Confidence-Gated Scope
         — SCOPE_SYSTEM returns confidence score (0–100) + coverage_gaps
         — Gates at 85%: shows gaps, one-shot re-scope on operator answer

Stage 1: PRD Plan    — decomposes intent into ordered PRD list
Stage 2: PRD Gen     — generates each PRD document (both models, Claude wins)
Stage 3: PR Plan     — decomposes each PRD into typed PR specs (implementation/documentation/test)

Stage 4: Code Gen (per PR, interleaved with PRD generation)
         4a. Repo Context Fetch   — existing file content before generation
         4b. Build Memory Inject  — prior run patterns in context
         4c. Self-Correction      — LLM reviews its own output (up to 10 passes)
         4d. Lint Gate            — ast.parse → ruff → import check
         4e. Fix Loop             — pytest up to 20 attempts, failure-type-aware strategy

Stage 5: Test + CI   — crafted-ci.yml on ubuntu-latest, crafted-ci-macos.yml for Swift
Stage 6: Gate        — operator approves or corrects before merge
```

Every stage has a max cyclomatic complexity of 15. Every state transition is checkpointed (including per-PR stages: branch_opened → code_generated → tests_passed → committed → ci_passed). Every gate decision is logged to the audit trail. Crashes mid-PR resume from the last stage checkpoint — not from code generation restart.

---

## Consensus Engine

Both models generate in parallel. Claude scores both. The winner goes through an improvement pass if the race is close. Fix arbitration uses assertion token overlap, not response length.

```
Claude generates  ──┐
                    ├──▶ Comparative evaluation (Claude arbitrates) ──▶ Winner
GPT-4o generates ──┘                                                      │
                                                                           ▼
                                              Improvement pass (if score delta < 2)
                                                                           │
                                                                           ▼
                                              Self-correction → Lint gate → Fix loop
                                                                           │
                                                                           ▼
                                                                 Final code committed
```

---

## Cross-Run Learning

The agent learns from its own history across runs:

**Build Memory** (`workspace/{engineer_id}/build_memory.json`): Records what was built in each PR — signatures, CI clean rate, fix attempt count. Injected at startup and into each PR's generation context. Survives fresh installs. Never cleared automatically.

**Build Rules** (`Mac-Docs/build_rules.md`): After each build run, if 3+ PRs show the same failure pattern, the agent synthesizes actionable coding rules and writes them to Mac-Docs. DocumentStore loads them automatically on the next run alongside TRDs. The agent starts each run with more project-specific guidance.

---

## CI Routing

Python/Go/TypeScript/Rust → `ubuntu-latest` (`.github/workflows/crafted-ci.yml`)

Swift/Xcode → `[self-hosted, macos, xcode, x64]` (`.github/workflows/crafted-ci-macos.yml`)

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
forge-docs/          — all TRDs and PRDs (source of truth, 16 TRDs)
forge-standards/     — ARCHITECTURE.md, INTERFACES.md, DECISIONS.md, CONVENTIONS.md
                       build_rules.md (auto-generated — do not delete)
src/                 — Python backend implementation
Crafted/             — Swift/SwiftUI application shell
CraftedTests/        — XCTest suites
tests/               — Python test suite (pytest, 17 files)
FAILURE_TAXONOMY.md  — 7 FM root cause buckets — v39 no-regression specification
conftest.py          — pytest src/ import resolution (auto-committed by ci_workflow)
.github/workflows/   — crafted-ci.yml (Ubuntu) + crafted-ci-macos.yml (Mac runner)
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/prd start <intent>` | Begin a directed build from plain-language intent |
| `/prd start` | Begin with interactive scope confirmation (confidence-gated) |
| `/patch <description>` | Apply a targeted fix to an existing PR |
| `/review start <branch>` | Run holistic code review — 5 lenses, fix PRs |
| `/trd start` | Begin TRD development workflow — 8 phases, FOUNDER/ENGINEER/CONSULTANT modes |
| `/write <path>` | Generate and commit a file directly to main |
| `/ledger` | Show build ledger — engineers, PRDs, PR status |
| `/verbose [0|1|2]` | Set LLM trace verbosity (0=silent, 1=preview, 2=full) |
| `/status` | Show current build thread state (phase, PRD count, PR count) |
| `/stop` | Graceful shutdown — flushes state before exit |

---

## Requirements

- macOS 13.0 (Ventura) or later
- Xcode 15.0+ (for building the Swift shell)
- Python 3.12 (bundled in the .app for the backend)
- Anthropic API key (Claude)
- OpenAI API key (GPT-4o)
- GitHub Personal Access Token (repo + workflow scopes)
- Self-hosted Mac runner (required for Swift CI validation — TRD-9)
