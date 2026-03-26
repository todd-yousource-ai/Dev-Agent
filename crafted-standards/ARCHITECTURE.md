# Architecture

## System Overview

**Product:** Crafted Dev Agent / Crafted  
**Platform:** Native macOS application  
**Minimum macOS:** 13.0 (Ventura)

Crafted is a native macOS AI coding agent that builds software autonomously from specifications. The architecture is explicitly **two-process**:

1. **Swift shell**
   - UI
   - authentication
   - Keychain secret storage
   - orchestration
   - XPC-related ownership per repository guidance

2. **Python backend**
   - consensus
   - pipeline execution
   - GitHub operations
   - intelligence and generation

Per the repository documents, the two processes communicate over an **authenticated Unix socket** using **line-delimited JSON**. The documents also state a core execution constraint: **neither process ever executes generated code**.

At the product level, Crafted accepts:
- a repository
- technical specifications (TRDs)
- operator intent in plain language

It then performs a directed build workflow:
- assesses confidence in scope
- decomposes intent into an ordered PRD plan
- decomposes each PRD into typed pull requests
- generates implementation and tests using two LLM providers in parallel
- runs self-correction
- runs a lint gate
- runs an iterative fix loop
- executes CI
- opens a draft pull request for operator review

The shell is the native container that packages, installs, authenticates, and orchestrates all subsystems. TRD-1 defines it as foundational and states it owns:
- installation and distribution
- identity and authentication
- biometric gate
- Keychain secret storage
- session lifecycle

The overall architecture is constrained by the repository instruction set:
- the 16 TRDs are the source of truth
- code must match the TRDs
- TRD-11 governs all security-relevant components
- requirements must not be invented beyond the documents

## Subsystem Map

### 1. macOS Application Shell

**Source:** TRD-1  
**Technology:** Swift 5.9+, SwiftUI  
**Role:** Native macOS container and orchestrator for the product

**Documented responsibilities:**
- package and install the application
- provide the native UI shell
- own authentication
- own biometric gate
- store secrets in Keychain
- manage session lifecycle
- orchestrate subsystems

**Explicit ownership from repository documents:**
- UI
- auth
- Keychain
- orchestration
- XPC ownership appears in repository-level architecture guidance

### 2. SwiftUI Views, Cards, Panels

**Source:** CLAUDE.md references TRD-8 for these components  
**Role:** Presentation subsystem within the Swift shell

**Documented boundary evidence:**
- SwiftUI views, cards, and panels are grouped as a distinct implementation area
- They belong to the Swift side of the architecture

### 3. Identity and Authentication

**Source:** TRD-1  
**Role:** Establish and manage operator identity and access within the shell

**Documented responsibilities:**
- identity and authentication
- biometric gate
- session lifecycle

**Observed identity fields from loaded content:**
- `display_name` stored in `UserDefaults`
- `engineer_id` stored in Keychain as `SecretKey.engineerId`
- `github_username` fetched from GitHub `/user` endpoint on first auth

### 4. Secret Storage

**Source:** TRD-1, repository identity text  
**Role:** Secure storage of secrets in the Swift shell

**Documented responsibilities:**
- Keychain secret storage
- App private key retrieval for GitHub App JWT generation is referenced in the lessons-learned document

### 5. Interprocess Communication Layer

**Source:** AGENTS.md, CLAUDE.md, loaded headings  
**Role:** Communication channel between Swift shell and Python backend

**Documented properties:**
- authenticated Unix socket
- line-delimited JSON protocol

**Observed implementation references from loaded content:**
- `Crafted/XPCBridge.swift`
- `src/xpc_server.py`

**Observed failure modes from loaded content:**
- deadlock in the credential delivery path
- Swift shell crashed before sending credentials
- XPC connection failed to establish

### 6. Python Backend

**Source:** AGENTS.md, CLAUDE.md  
**Technology:** Python 3.12 (bundled)  
**Role:** Non-UI execution engine

**Documented responsibilities:**
- consensus
- pipeline
- GitHub operations
- intelligence
- generation

### 7. Consensus Engine

**Source:** README, CLAUDE.md snippet  
**Role:** Multi-model generation and arbitration subsystem

**Documented behavior:**
- uses two LLM providers in parallel
- README names the strategy as a two-model consensus engine
- Claude + GPT-4o are used, with Claude arbitrating every result

### 8. Provider Adapter Layer

**Source:** CLAUDE.md snippet  
**Role:** Integration layer for model providers used by the consensus engine

**Documented evidence:**
- `ConsensusEngine, ProviderAdapter` are grouped as a subsystem area in repository guidance

### 9. Planning and Decomposition Pipeline

**Source:** README  
**Role:** Convert operator intent into executable implementation units

**Documented stages:**
- confidence assessment in scope
- PRD plan decomposition
- decomposition of each PRD into typed pull requests

### 10. Generation, Self-Correction, and Fix Loop Pipeline

**Source:** README  
**Role:** Produce code and tests, then refine them until pipeline gates pass

**Documented stages:**
- implementation generation
- test generation
- self-correction pass
- lint gate
- iterative fix loop

### 11. GitHub Integration

**Source:** AGENTS.md, CLAUDE.md, GitHub Integration Lessons Learned, README  
**Role:** Repository, pull request, and GitHub API operations

**Documented responsibilities:**
- GitHub operations are owned by the Python backend
- open draft pull requests
- fetch `/user` on first auth for `github_username`

**Documented GitHub API behaviors from lessons learned:**
- draft PRs must be converted to ready-for-review using GraphQL `markPullRequestReadyForReview`
- REST PATCH with `{"draft": false}` is ignored
- merging a draft PR returns 405

**Observed GitHub content handling steps from loaded content:**
- fetch file content from GitHub
- read current file from GitHub to get content and SHA

**Observed GitHub App auth step:**
- generate JWT using App private key from Keychain

### 12. CI Integration

**Source:** README, loaded headings  
**Role:** Verification pipeline executed before operator review and merge progression

**Documented behavior:**
- CI is executed before a pull request is opened for review

**Observed CI jobs/workflows from loaded content:**
- `Forge CI — Python / test`
- `Forge CI — macOS / unit-test`
- `Forge CI — macOS / xpc-integration-test`
- `Crafted CI (ubuntu) — main Python test job`
- `Crafted CI — macOS (Swift) — only triggers for Swift files`

### 13. Installation, Distribution, and Update Subsystem

**Source:** TRD-1  
**Role:** Package and distribute the shell as a macOS application

**Documented responsibilities:**
- `.app` bundle
- drag-to-Applications installation
- Sparkle auto-update

### 14. Build and Release Packaging

**Source:** TRD-1, loaded headings  
**Role:** Produce signed application artifacts for macOS distribution

**Observed packaging/signing evidence:**
- `Developer ID Application: YouSource.ai ({TEAM_ID})`
- `$GITHUB_WORKSPACE/build/Release/Crafted.app`

### 15. Review / Operator Command Surface

**Source:** loaded headings from documentation  
**Role:** Operator-facing command and review controls

**Observed commands and options:**
- `/ledger note <text>`
- `/review start`
- `/review exclude`
- `adjust scope`
- `exclude files`
- `exclude security in src/vendor/`
- `exclude src/legacy/`
- `exclude src/old_api.py`
- `select lenses`

These are documented as operator controls, not autonomous hidden behavior.

## Component Boundaries

### macOS Application Shell must never
- own intelligence, generation, or GitHub operations, which repository documents assign to the Python backend
- execute generated code
- infer requirements outside the TRDs

### SwiftUI presentation components must never
- become the source of truth for authentication, secret storage, or backend pipeline logic
- bypass shell-owned auth and session controls
- execute generated code

### Identity and Authentication subsystem must never
- move secret storage responsibility out of the shell/Keychain boundary
- rely on unstated identity fields beyond those documented
- treat session or biometric gates as backend responsibilities

### Secret Storage subsystem must never
- expose raw secrets to components not documented as secret owners
- relocate private key material outside Keychain-backed storage described by the shell documents

### IPC layer must never
- operate without authentication
- deviate from line-delimited JSON over the documented Unix socket transport
- collapse the process boundary between shell and backend
- execute generated code in transit or as part of message handling

### Python Backend must never
- assume ownership of UI, native authentication, biometric gate, or Keychain storage
- bypass the shell for secrets that the shell owns
- execute generated code

### Consensus Engine must never
- substitute a single-model flow for the documented two-model consensus process where the README specifies parallel generation and arbitration
- bypass arbitration behavior described in the product README

### Provider Adapter layer must never
- redefine product behavior outside provider integration concerns
- bypass consensus/orchestration contracts established by the backend

### Planning and Decomposition Pipeline must never
- skip the documented progression from intent → PRD plan → typed pull requests
- present the product as chat or autocomplete; README explicitly says it is not those things

### Generation / Self-Correction / Fix Loop pipeline must never
- bypass self-correction, lint gating, iterative fixing, or CI where the README lists them as pipeline stages
- execute generated code

### GitHub Integration must never
- attempt unsupported draft-state transitions through the documented non-working REST field update
- merge draft PRs directly
- take ownership of local auth or Keychain responsibilities assigned to the shell

### CI Integration must never
- be treated as optional in the documented PR production path, since README places CI before draft PR review
- collapse Python and macOS test concerns into a single undocumented job model

### Installation / Distribution / Update subsystem must never
- own backend intelligence or GitHub workflow logic
- bypass the native `.app`/drag-to-Applications/Sparkle packaging responsibilities documented in TRD-1

### Build and Release Packaging must never
- produce unsigned or differently attributed release artifacts beyond the documented signing context present in loaded materials
- redefine install/update policy independently of the shell specification

### Operator Command Surface must never
- silently mutate scope outside the explicit operator commands shown in the documents
- hide exclusions or lens selections from the operator, since the loaded content presents these as explicit commands

## Key Data Flows

### 1. Operator intent to pull request

1. Operator provides:
   - repository
   - TRDs
   - plain-language intent
2. System assesses confidence in the scope
3. System decomposes intent into an ordered PRD plan
4. Each PRD is decomposed into typed pull requests
5. Python backend performs generation using two model providers in parallel
6. Consensus/arbitration is applied
7. Self-correction runs
8. Lint gate runs
9. Iterative fix loop runs
10. CI executes
11. GitHub integration opens a **draft PR**
12. Operator reviews, gates, and merges

### 2. Shell-to-backend startup and credential path

1. Swift shell starts and orchestrates backend lifecycle
2. Python backend is started with a socket path and nonce per loaded test/startup references
3. Shell and backend communicate over an authenticated Unix socket
4. Messages use line-delimited JSON
5. Credential delivery traverses this boundary

**Documented failure sensitivity:**
- deadlock in credential delivery
- shell crash before credential send
- connection establishment failure

### 3. Authentication and identity flow

1. Shell owns authentication and biometric gate
2. Shell manages session lifecycle
3. Secret material is stored in Keychain
4. Identity-related values are persisted/fetched as documented:
   - `display_name` in `UserDefaults`
   - `engineer_id` in Keychain
   - `github_username` from GitHub `/user` on first auth

### 4. GitHub App/API flow

1. App private key is retrieved from Keychain
2. JWT is generated using the App private key
3. GitHub API operations are executed by the backend
4. PRs are opened as draft
5. Draft → ready-for-review transition uses GraphQL mutation
6. Draft PR merge is not attempted directly because documented behavior returns 405

### 5. Installation and update flow

1. Product is delivered as a macOS `.app` bundle
2. User installs via drag-to-Applications
3. Auto-update is provided by Sparkle

### 6. CI verification flow

1. Generated changes enter verification gates
2. CI runs Python and macOS test workflows as applicable
3. Draft PR is opened after CI execution in the documented product flow

## Critical Invariants

1. **Two-process architecture is mandatory.**  
   The system is split into a Swift shell and Python backend.

2. **Responsibility split is mandatory.**  
   - Swift owns UI, authentication, Keychain, orchestration.
   - Python owns consensus, pipeline, GitHub operations, intelligence, generation.

3. **IPC must be authenticated.**  
   Communication between the two processes uses an authenticated Unix socket.

4. **IPC message framing is fixed.**  
   Messages are line-delimited JSON.

5. **Generated code must never be executed.**  
   This prohibition applies to both processes.

6. **The shell is the security and identity anchor.**  
   Authentication, biometric gating, Keychain storage, and session lifecycle remain shell-owned.

7. **The backend is the execution engine for intelligence and GitHub actions.**  
   These concerns do not migrate into the shell.

8. **The product is a directed build agent, not a chat UI or code autocomplete tool.**  
   This is an architectural product constraint stated in the README.

9. **Draft pull requests are part of the normal workflow.**  
   The system opens every PR as draft before operator review.

10. **Draft PR state changes must follow documented GitHub behavior.**  
    Converting draft → ready-for-review requires GraphQL `markPullRequestReadyForReview`; direct REST field mutation is not valid for this purpose.

11. **Draft PRs must not be merged directly.**  
    The loaded GitHub behavior document states this returns 405.

12. **CI is part of the PR production path.**  
    The README places CI before opening a draft PR for review.

13. **TRDs are authoritative.**  
    The architecture, interfaces, error contracts, state machines, security controls, and performance requirements are defined in the TRDs and must not be invented outside them.

14. **Security-relevant work is governed by TRD-11.**  
    Repository instructions explicitly require TRD-11 for credentials, external content, generated code, or CI-related security work.

15. **Operator control must remain explicit.**  
    Scope adjustments, exclusions, and lens selection are surfaced as explicit operator commands in the loaded documents.