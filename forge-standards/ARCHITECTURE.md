# Architecture — Forge Platform

## System Overview

Forge is a native macOS autonomous software delivery platform built as a **two-process system**:

- **Swift/macOS Shell**
  - Owns native UX, onboarding, authentication, biometric gating, Keychain access, settings, process lifecycle, update/install behavior, notifications, and trusted local orchestration.
- **Python Backend**
  - Owns planning, document retrieval, consensus generation, review/fix cycles, repository analysis, GitHub integration, CI coordination, and documentation regeneration.

The platform is designed around a strict separation of trust domains:

1. **Operator trust domain**
   - Human intent, review approval, local app interaction.
2. **Trusted local shell domain**
   - macOS-native process with UI authority, secrets authority, and backend launch authority.
3. **Constrained backend execution domain**
   - Python orchestration process that performs intelligence and automation but does not own long-term secret storage.
4. **External service domain**
   - LLM providers, GitHub APIs, webhooks, remote repositories, CI systems, and imported specification documents.

Core operating model:

1. Operator imports repository and source specifications (TRDs/PRDs/architecture docs).
2. Document Store ingests and indexes the specs.
3. Operator supplies plain-language intent.
4. Planning converts intent into an ordered PRD plan, then into PR-sized implementation units.
5. For each PR unit, the backend retrieves relevant context, generates code with parallel model providers, arbitrates via consensus, runs review/fix cycles, executes CI, and opens a draft PR.
6. Operator reviews/approves each PR; the system continues to the next unit.
7. On completion, the system may regenerate project documentation, including product context and TRDs.

All generated output is treated as untrusted until it passes explicit review, validation, and operator gate conditions. The system must **never execute generated code**.

Architecturally, Forge follows these rules:

- Trust is asserted and verified explicitly, never inferred implicitly.
- Identity, policy, telemetry, and enforcement are separate concerns with explicit interfaces.
- Enforcement decisions must be explainable, observable, and reproducible.
- Components default to enforcement, not advisory behavior.
- Local flows minimize friction without weakening guarantees.
- Administrative and operator controls remain explicit and understandable.
- Protocols and control logic are designed to scale to broader endpoint/network/cloud/AI-runtime environments.

---

## Subsystem Map

### 1. macOS Application Shell
**What it does**
- Packages the app as a native macOS application.
- Owns first-launch onboarding, settings, navigation, session lifecycle, menu bar/dock behavior, notifications, update/install flows, and crash/logging infrastructure.
- Launches and supervises the Python backend.
- Provides the root trust anchor for local operator interaction.

**What it enforces**
- Native authentication boundaries.
- Session gating before sensitive actions.
- Stable module boundaries and UI state ownership.
- Authenticated local IPC to the backend.
- Explicit operator confirmation at review gates.

---

### 2. Authentication and Secret Management
**What it does**
- Handles biometric gate and local identity checks.
- Stores API credentials and tokens in Keychain.
- Controls secret release to the backend at runtime.
- Manages session unlock/lock lifecycle.

**What it enforces**
- Secrets are never persisted in backend-owned storage.
- Secret access is conditional on authenticated session state.
- Sensitive fields use explicit privacy-safe logging behavior.
- Credential handling follows TRD-11 security controls.

---

### 3. XPC / Local IPC Channel
**What it does**
- Provides authenticated communication between Swift shell and Python backend.
- Uses a local Unix socket with line-delimited JSON messaging.
- Carries commands, state updates, telemetry, and credential delivery.

**What it enforces**
- Backend messages must originate on an authenticated local channel.
- Message framing, schema validity, and process identity checks are explicit.
- The shell remains the controlling side for process startup and credential release.

---

### 4. Process Management and Runtime Supervision
**What it does**
- Starts, monitors, restarts, and terminates the backend process.
- Tracks health, startup readiness, and failure modes.
- Coordinates backend availability with UI state.

**What it enforces**
- Backend is not trusted merely because it is local; it must be launched and verified by the shell.
- Crash/restart paths are deterministic and observable.
- Backend startup sequencing and credential injection are ordered and gated.

---

### 5. SwiftUI UX Layer
**What it does**
- Implements root views, navigation, cards, panels, settings screens, onboarding, project import, scoping UI, review UI, and notifications.
- Surfaces build state, PR progress, CI state, and operator gates.

**What it enforces**
- User-facing state transitions are explicit.
- Sensitive actions are not hidden behind implicit side effects.
- Review and approval remain operator-visible and operator-driven.

---

### 6. Planning Engine
**What it does**
- Converts operator intent plus loaded source documents into an ordered implementation plan.
- Generates PRD-level decomposition.
- Splits PRDs into sequenced pull-request-sized work units.

**What it enforces**
- Work is decomposed into logical, reviewable units.
- Planning is constrained by retrieved source specifications.
- Scope confirmation occurs before implementation begins.

---

### 7. Repository Analysis and Scoping
**What it does**
- Inspects repository structure, detects file overlap/conflicts, identifies dependencies, and scopes work before generation.
- Performs project scoping and live sync against repository state.

**What it enforces**
- Pre-start file overlap checks.
- Unmet dependency warning paths.
- File/issue exclusion rules.
- Conflict detection before concurrent or unsafe edits.

---

### 8. Document Store and Retrieval Engine
**What it does**
- Parses source documents in supported formats.
- Extracts metadata.
- Chunks content into retrieval units.
- Embeds chunks into vectors.
- Indexes and retrieves relevant context for planning, generation, review, and documentation tasks.

**What it enforces**
- Context supply is grounded in imported specifications.
- Retrieval quality is a first-class dependency for downstream correctness.
- Ingestion and retrieval apply prompt-injection and context-poisoning defenses.
- Metadata and chunk provenance remain traceable.

---

### 9. Context Assembly Layer
**What it does**
- Builds task-specific prompt context from retrieved chunks, repository state, issue/PR metadata, and workflow stage requirements.
- Produces structured context packages for generation, review, and fix passes.

**What it enforces**
- Only relevant, policy-allowed context is passed downstream.
- Context packages retain source attribution.
- Excluded files/issues/documents are omitted from task context.

---

### 10. Consensus Engine
**What it does**
- Runs multi-model generation and arbitration.
- Uses parallel providers (e.g. Claude and GPT-4o) to produce candidate outputs.
- Uses Claude arbitration to decide result selection and synthesis.

**What it enforces**
- No single provider is the sole source of implementation truth.
- Provider outputs are treated as untrusted candidate artifacts.
- Arbitration is explicit and reproducible.

---

### 11. Provider Adapter Layer
**What it does**
- Normalizes calls to multiple LLM providers.
- Handles provider-specific request/response formats, retry behavior, and error mapping.
- Supports generation and review prompts.

**What it enforces**
- Backend business logic is isolated from provider-specific APIs.
- Provider failures do not silently bypass consensus rules.
- Prompt/response handling respects security filtering.

---

### 12. Pipeline Orchestrator
**What it does**
- Executes the end-to-end build pipeline as ordered stages.
- Coordinates state, handoff, retries, failure handling, and outputs between stages.

**What it enforces**
- Stages execute in defined order.
- Stage contracts are explicit.
- Intermediate artifacts are persisted or surfaced only through controlled interfaces.
- Failure semantics are deterministic.

---

### 13. Code Generation Stage
**What it does**
- Produces code and tests for a PR-sized unit using retrieved context, repository state, and consensus generation.
- Emits structured file patches/artifacts rather than executing code.

**What it enforces**
- Generated output remains inert text/artifact data.
- Generation is grounded in scoping and retrieved specifications.
- No execution of generated code is permitted.

---

### 14. Three-Pass Review Stage
**What it does**
- Runs a structured review sequence over generated work.
- Identifies defects, spec mismatches, safety issues, and implementation gaps.
- Produces fix recommendations and updated artifacts.

**What it enforces**
- Generation cannot proceed directly to PR without review.
- Review is multi-pass, not single-shot.
- Findings are explicit, attributable, and fixable.

---

### 15. Improvement / Fix Pass System
**What it does**
- Executes targeted repair iterations after review findings.
- Creates fix branches where required.
- Re-runs validation after fixes.

**What it enforces**
- Fixes are gated by review output and operator/workflow rules.
- Repair loops are bounded and explicit.
- Improvement prompt content is controlled rather than ad hoc.

---

### 16. Operator Review Gate
**What it does**
- Presents draft PR results for human review.
- Supports scope confirmation, proceed/fix gating, and lens selection for review workflows.

**What it enforces**
- Human approval is required at designated gates.
- The system does not silently merge or finalize work without operator consent.
- Review gates remain explicit workflow barriers.

---

### 17. GitHub Integration
**What it does**
- Interacts with GitHub repositories, pull requests, branches, issues, GraphQL APIs, and webhook events.
- Opens draft PRs, queries PR status, syncs state, and receives remote updates.

**What it enforces**
- Remote repository operations use explicit API contracts.
- GraphQL/API error handling is normalized.
- Draft PR creation happens only after local workflow gates pass.
- Webhook inputs are handled as untrusted external data.

---

### 18. CI Coordination
**What it does**
- Triggers or observes CI runs associated with generated branches and PRs.
- Surfaces build/test state back into the pipeline and UI.

**What it enforces**
- PR readiness depends on validation state, not generation alone.
- CI signals are explicit inputs to workflow progression.
- Generated code is validated through repository-native CI, not local execution of arbitrary generated payloads.

---

### 19. Live Sync Engine
**What it does**
- Synchronizes local workflow state with GitHub and repository changes.
- Updates PR status, issue state, and branch/remote metadata.

**What it enforces**
- UI and orchestration state reflect authoritative external system changes.
- Sync strategy is controlled and observable.
- External changes cannot bypass local operator gates.

---

### 20. Webhook Receiver
**What it does**
- Accepts and processes remote event notifications related to PRs, CI, and repository state.

**What it enforces**
- Webhook authenticity and payload handling must be explicit.
- Events are inputs to state transition logic, not direct mutation authority.
- Untrusted remote content is parsed and validated before use.

---

### 21. Logging, Telemetry, and Observability
**What it does**
- Records structured logs, os_log events, diagnostics, conflict logs, process health, and workflow state transitions.
- Supports crash symbolication and operational debugging.

**What it enforces**
- Security-sensitive values are privacy-annotated or excluded.
- Control decisions and failures are reconstructable.
- Logging does not become a secondary secret exfiltration path.

---

### 22. Security Enforcement Layer
**What it does**
- Implements platform-wide controls from TRD-11.
- Covers path security gates, prompt injection defense, context poisoning defense, dependency code injection mitigation, and adversarial output handling.

**What it enforces**
- Imported documents, repository contents, dependencies, model outputs, and webhook/API payloads are all treated as potentially malicious.
- Three-layer defenses apply where specified.
- Unsafe paths, untrusted content, and policy violations block progression.

---

### 23. Documentation Generation
**What it does**
- Produces `PRODUCT_CONTEXT.md`, TRD regeneration output, and other derived project documentation after build phases complete.

**What it enforces**
- Documentation is derived from the same controlled retrieval/generation pipeline.
- Generated documentation remains reviewable output.
- Documentation generation does not bypass the core safety model.

---

### 24. Packaging, Update, and Distribution
**What it does**
- Builds the macOS application bundle.
- Supports drag-to-Applications install, Sparkle auto-update, notarization, and CI bundling for Python/runtime assets.

**What it enforces**
- Shipping artifacts preserve the shell/backend trust boundary.
- Update channels remain native-app controlled.
- Bundling and notarization flows are explicit and testable.

---

## Enforcement Order

The effective control path of the platform is ordered. Later components cannot weaken guarantees imposed earlier.

### 1. Launch and trust establishment
1. macOS launches the Swift shell.
2. Shell initializes persistent settings, logging, and crash handling.
3. Shell enforces first-launch onboarding and project preconditions.
4. Operator completes biometric/session authentication if required.
5. Shell launches the Python backend under managed process supervision.
6. Shell establishes authenticated local IPC.
7. Shell releases runtime credentials only after session and backend checks pass.

### 2. Repository and document preparation
1. Operator imports repository and source documents.
2. Repository Analysis performs project scoping and overlap/dependency/conflict checks.
3. Document Store parses documents, extracts metadata, chunks, embeds, and indexes them.
4. Security layer scans ingestion inputs for prompt injection and context poisoning patterns.
5. Indexed documents become the retrieval base for all downstream operations.

### 3. Planning and work decomposition
1. Operator submits intent.
2. Planning Engine retrieves relevant specifications.
3. Planning Engine generates ordered PRD plan.
4. Planning Engine decomposes PRD plan into PR-sized work units.
5. Operator scope confirmation gate is applied where required.

### 4. Per-PR execution pipeline
1. Pipeline Orchestrator selects next work unit.
2. Repository Analysis re-checks repository state and file overlap/conflict conditions.
3. Context Assembly gathers task-specific retrieved specs and repo context.
4. Code Generation Stage requests candidate implementations through Provider Adapters.
5. Consensus Engine runs parallel generation and arbitration.
6. Generated artifacts are materialized as controlled file changes.
7. Three-Pass Review Stage evaluates output.
8. Improvement/Fix Pass applies bounded corrections if needed.
9. Validation/CI coordination determines readiness.
10. Operator Review Gate presents draft result.
11. GitHub Integration creates/updates draft PR after gates pass.

### 5. Post-PR and completion flows
1. Live Sync tracks PR and CI state.
2. Webhook Receiver updates external event state through validated handlers.
3. On operator approval/merge progression, orchestrator advances to next PR unit.
4. When the full build completes, Documentation Generation may produce updated context/TRD outputs.
5. Packaging/update/distribution flows apply to the product itself, not to generated target-repo code.

---

## Component Boundaries

### macOS Application Shell must never
- Generate code logic itself.
- Persist provider secrets outside approved secret stores.
- Trust backend messages without authenticated IPC validation.
- Allow hidden workflow progression around operator gates.

### Authentication and Secret Management must never
- Delegate long-term secret custody to the backend.
- Log raw credentials or tokens.
- Release credentials before session and policy checks complete.

### Python Backend must never
- Be treated as the root of trust.
- Store canonical secrets in its own persistent storage.
- Execute generated code, generated tests, or dependency payloads.
- Bypass shell-controlled approval or launch sequencing.

### Document Store must never
- Treat imported documents as trusted instructions.
- Lose provenance of chunks used for retrieval.
- Mix excluded or poisoned content into retrieval context without controls.

### Planning Engine must never
- Invent requirements that contradict source specifications.
- Skip decomposition and produce unreviewable monolithic work.
- Ignore repository scoping constraints.

### Context Assembly must never
- Include policy-excluded files or issues.
- Drop source attribution for retrieved content.
- Pass raw unfiltered external text into prompts where defenses are required.

### Consensus Engine must never
- Accept a single provider response as implicitly authoritative when consensus/arbitration is required.
- Hide disagreement or uncertainty.
- Execute or validate code by running it.

### Provider Adapter Layer must never
- Leak provider-specific failures as silent success.
- Smuggle unsafe prompt content around security controls.
- Own workflow policy.

### Pipeline Orchestrator must never
- Reorder mandatory stages.
- Advance on ambiguous stage state.
- Suppress failure conditions that should block PR creation.

### Code Generation Stage must never
- Execute generated code.
- Modify files outside scoped and approved target sets.
- Ignore conflict and path security gates.

### Review and Improvement subsystems must never
- Mark work complete without explicit review evidence.
- Enter unbounded self-repair loops.
- Treat model self-assertion as proof of correctness.

### GitHub Integration must never
- Merge autonomously without operator authority.
- Trust remote payloads without validation.
- Let API transport failures masquerade as repository state truth.

### Webhook Receiver must never
- Apply direct state mutation from unauthenticated or malformed events.
- Treat event payload content as trusted prompt context.

### Logging and Telemetry must never
- Exfiltrate secrets or private repository content unnecessarily.
- Become the sole persistence mechanism for critical workflow state.
- Omit enough detail that enforcement decisions are not reconstructable.

### Security Enforcement Layer must never
- Be optional on untrusted-input paths.
- Depend solely on provider behavior for safety.
- Convert hard policy violations into warnings when blocking is required.

### Documentation Generation must never
- Be considered source of truth over imported specifications unless explicitly designated.
- Bypass retrieval grounding and review expectations.

### Packaging and Distribution must never
- Collapse shell/backend isolation for convenience.
- Ship unsigned/unnotarized artifacts where notarization is required.
- Break Python bundling assumptions defined by build and CI flows.

---

## Key Data Flows

### 1. Credential flow
1. Operator authenticates in the shell.
2. Secrets are loaded from Keychain by the shell.
3. Shell launches backend and establishes authenticated IPC.
4. Shell delivers only required runtime credentials over the local authenticated channel.
5. Backend uses credentials for provider/GitHub access without becoming the source of truth for stored secrets.

**Invariant:** credentials originate and persist in the shell-controlled secret domain.

---

### 2. Document ingestion flow
1. Operator imports TRDs/PRDs/architecture docs.
2. Document Store parses supported formats and extracts metadata.
3. Content is chunked according to retrieval policy.
4. Chunks are embedded and indexed.
5. Security defenses inspect for prompt injection / poisoning patterns.
6. Retrieval-ready records are stored with provenance.

**Invariant:** every retrieved chunk can be traced back to an imported source document and ingestion path.

---

### 3. Intent-to-plan flow
1. Operator submits plain-language intent.
2. Planning Engine queries Document Store for relevant specs.
3. Retrieved context plus repository state produce an ordered PRD plan.
4. Plan is decomposed into PR-sized tasks.
5. Scope confirmation gate validates direction before execution.

**Invariant:** implementation planning is grounded in source specifications and constrained by repository reality.

---

### 4. Per-PR generation flow
1. Orchestrator selects next PR unit.
2. Repository analysis verifies no unsafe overlap or conflicts.
3. Context Assembly builds generation package.
4. Provider Adapters call multiple LLMs in parallel.
5. Consensus Engine arbitrates outputs.
6. Candidate file changes are produced.
7. Review and fix passes iterate as needed.
8. CI status is checked.
9. Draft PR is created on GitHub.
10. Operator reviews and approves progression.

**Invariant:** no PR is produced from raw model output alone; all outputs traverse review and validation.

---

### 5. GitHub sync flow
1. Backend queries GitHub GraphQL/API for PR and repository state.
2. Webhooks provide asynchronous updates.
3. Live Sync reconciles remote truth with local workflow state.
4. UI reflects current status and available operator actions.

**Invariant:** remote state informs workflow but does not erase local enforcement or operator approval requirements.

---

### 6. Documentation regeneration flow
1. Completion of implementation phases triggers doc-generation eligibility.
2. Document generation retrieves current specs, implementation context, and repository outcomes.
3. Generated docs are emitted as reviewable artifacts.
4. Optional TRD and product-context outputs are produced.

**Invariant:** generated documentation is downstream of controlled context retrieval and generation, not freeform synthesis.

---

### 7. Packaging/update flow
1. CI builds application bundle and bundled Python runtime.
2. Caching and bundling steps produce distributable artifacts.
3. Notarization job signs and notarizes the app.
4. Sparkle/update metadata enables field updates.

**Invariant:** distributed binaries preserve native shell authority and deployment integrity.

---

## Critical Invariants

1. **The shell is the local root of trust.**
   - The Swift/macOS process owns UI authority, session authority, secret authority, and backend launch authority.

2. **The backend is orchestrator, not trust anchor.**
   - Python owns intelligence and automation, but not long-term secret custody or operator identity.

3. **Generated code is never executed by Forge.**
   - The system may write, review, diff, validate through repository-native CI, and prepare PRs, but it must not run generated code locally as part of generation.

4. **All external content is untrusted by default.**
   - Imported documents, repository files, dependencies, model outputs, webhook payloads, and API responses all require explicit validation and policy handling.

5. **Retrieval quality is a correctness dependency.**
   - Document parsing, chunking, metadata extraction, embedding, and retrieval directly affect planning, generation, review, and documentation quality.

6. **Consensus is mandatory where specified.**
   - Multi-model generation with Claude arbitration is part of the product architecture, not an optimization.

7. **Review is mandatory before PR creation.**
   - Raw generation output cannot go directly to a final PR artifact without structured review/fix passes.

8. **Operator approval remains explicit.**
   - Human review gates are first-class control points and cannot be bypassed by automation convenience.

9. **Stage ordering is enforced.**
   - Planning precedes generation; generation precedes review; review precedes PR creation; operator approval governs progression.

10. **Provenance must be preserved.**
    - Retrieved chunks, generated artifacts, review findings, and workflow state transitions must remain attributable.

11. **Security controls are cross-cutting and blocking.**
    - Path security, injection defense, dependency injection defense, and adversarial-output controls apply across ingestion, prompting, generation, and integration surfaces.

12. **Logging must be useful without becoming a leak.**
    - Observability must support auditability and reproducibility while preserving privacy and secret safety.

13. **GitHub state is integrated, not sovereign.**
    - Remote state drives synchronization but cannot override local enforcement, policy, or operator intent.

14. **Work units must stay reviewable.**
    - Planning and implementation are decomposed into logical PR units to preserve correctness, traceability, and human oversight.

15. **Packaging must preserve architecture.**
    - Distribution, Python bundling, notarization, and updates must not weaken process isolation or trust boundaries.