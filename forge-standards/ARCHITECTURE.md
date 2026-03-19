# Architecture — Forge Platform

## System Overview

Forge is a native-first, policy-enforcing AI software delivery platform composed of a macOS shell, a Python backend runtime, multiple generation and review engines, document retrieval infrastructure, source-control and CI integrations, and cross-cutting security controls.

At a high level, Forge performs the following end-to-end workflow:

1. Installs and launches as a notarized macOS application bundle.
2. Authenticates the operator locally and unlocks stored credentials.
3. Starts an embedded Python backend through an authenticated IPC boundary.
4. Validates Swift/Python runtime compatibility through a version handshake.
5. Initializes core backend services in dependency-safe order.
6. Imports and indexes project knowledge documents into the document store.
7. Accepts operator-scoped work such as PRD decomposition, TRD authoring, code generation, review, and fix execution.
8. Runs multi-model consensus generation with arbitration.
9. Executes staged build and review pipelines with explicit operator gates.
10. Interacts with GitHub for branch, PR, status, review, and webhook workflows.
11. Persists telemetry, logs, state, and recoverable artifacts.
12. Enforces security controls against prompt injection, adversarial model output, untrusted content, path escape, dependency injection, and unsafe execution.

Forge architecture follows these platform rules:

- Trust must never be inferred implicitly when it can be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- All control decisions must be explainable, observable, and reproducible.
- Forge components must default to policy enforcement, not policy suggestion.
- Local agents must minimize user friction while preserving strong enforcement guarantees.
- Administrative workflows must be simple, explicit, and understandable in plain language.
- Protocol and enforcement logic must be designed for future scale across endpoint, network, cloud, and AI runtime environments.

The platform is intentionally split into small subsystems with hard boundaries. The shell owns native identity, credential UX, packaging, update, and process orchestration. The backend owns generation, retrieval, GitHub automation, review orchestration, and runtime services. Security policy is cross-cutting, but enforcement points are explicit and subsystem-local.

---

## Subsystem Map

Below, each subsystem includes:
- what it does
- what it enforces

### 1. macOS Application Shell

**What it does**
- Native Swift/SwiftUI host application.
- Packages the product as a `.app` bundle with drag-to-Applications install flow.
- Handles Sparkle-based auto-update, notarization compatibility, and bundle lifecycle.
- Owns onboarding, settings, menu bar integration, dock behavior, and notifications.
- Hosts root navigation and view-model state.
- Launches and monitors the Python backend.
- Establishes the authenticated XPC/IPC channel to backend services.
- Performs local session and credential lifecycle management.

**What it enforces**
- Backend cannot be considered usable until version handshake succeeds.
- Protected settings and credential access require the local identity gate.
- Secrets remain in Keychain-backed storage, never in general UI state.
- UI-triggered backend commands must traverse an authenticated channel.
- Restart and crash handling are controlled by shell policy, not backend self-assertion.
- First-launch, migration, and settings schema changes are serialized and explicit.

---

### 2. Native Identity and Authentication Layer

**What it does**
- Biometric gate integration.
- Session unlock and re-authentication policy.
- Keychain storage and retrieval of API tokens, GitHub credentials, and service secrets.
- Credential delivery to backend at runtime.

**What it enforces**
- Secret material is not persisted in plaintext configuration.
- Backend receives credentials only after an authenticated operator unlock.
- Session lifetime, lock timeout, and re-prompt semantics are shell-controlled.
- Identity proof is local and explicit; backend cannot bypass it.

---

### 3. Swift Module Architecture and UI State System

**What it does**
- Defines module boundaries inside the macOS shell.
- Structures root views, navigation graph, and settings/onboarding hierarchy.
- Owns state containers and view-model concurrency semantics.

**What it enforces**
- UI state ownership remains deterministic and isolated by module.
- Concurrency uses explicit ownership; backend events cannot mutate arbitrary UI state.
- View models consume backend data through typed interfaces rather than raw process output.

---

### 4. IPC / XPC Communication Layer

**What it does**
- Provides the authenticated communication path between Swift shell and Python backend.
- Carries startup readiness, version metadata, command requests, progress updates, and stop signals.

**What it enforces**
- Only authenticated, schema-valid messages cross the boundary.
- Backend readiness is explicit; shell does not infer startup success from process existence.
- Stop/shutdown semantics are protocol-defined.
- Version compatibility is checked before normal operation.

---

### 5. Process Management Subsystem

**What it does**
- Spawns backend process.
- Monitors liveness and readiness.
- Delivers credentials after successful identity gate.
- Restarts backend when policy permits.
- Handles graceful shutdown from shell side.

**What it enforces**
- Startup order is shell-observed and backend-declared.
- Crash loops are detectable and must not cause silent repeated unsafe restarts.
- Credentials are delivered only into a running, compatible backend session.
- Backend termination path must preserve shutdown guarantees where possible.

---

### 6. Backend Runtime Startup and Lifecycle Manager

**What it does**
- Initializes Python backend services in strict order.
- Publishes backend version and capability metadata.
- Signals readiness only when dependencies are actually initialized.
- Handles graceful shutdown and in-flight work teardown.

**What it enforces**
- Services initialize in dependency order.
- No external command routing before core services are ready.
- Incompatible shell/backend versions fail closed.
- Shutdown must persist guaranteed state before process exit.

---

### 7. Command Router

**What it does**
- Entry point for backend-exposed operations.
- Dispatches typed commands to generation, retrieval, GitHub, review, and document workflows.
- Applies startup-state gating and request routing.

**What it enforces**
- Commands cannot execute before runtime ready state.
- Command schema validation is centralized.
- Unauthorized or unsupported commands fail deterministically.
- Internal services are invoked through explicit interfaces, not ad hoc coupling.

---

### 8. Document Store and Retrieval Engine

**What it does**
- Imports TRDs, PRDs, architecture specs, and related documents.
- Parses multiple source formats.
- Extracts metadata.
- Chunks text using semantic-first chunking with fixed-size fallback and overlap.
- Computes embeddings using a local default embedding model.
- Stores searchable vectors and retrieval metadata.
- Retrieves relevant context for generation, review, and decomposition workflows.

**What it enforces**
- Ingested content is normalized and indexed before use in generation contexts.
- Chunking and embedding configuration remain stable and versioned.
- Retrieval is scoped to relevant documents and metadata filters.
- Parsing failures are surfaced explicitly rather than silently skipping content.
- Context assembly must preserve provenance and document attribution.

---

### 9. Embedding Model Service

**What it does**
- Hosts the local embedding model used by Document Store.
- Produces deterministic embeddings for indexed chunks and retrieval queries.
- Provides model availability to startup sequencing.

**What it enforces**
- Document Store initialization may not complete before embedding service is available.
- Embedding model/version mismatch must be detectable.
- Retrieval quality-critical model changes require explicit reindex behavior.

---

### 10. Consensus Engine

**What it does**
- Executes parallel generation against two LLM providers.
- Runs Claude arbitration to select or synthesize the best final output.
- Supports code generation, test generation, PRD generation, and PRD decomposition.
- Acts as the generation core reused by pipeline stages.

**What it enforces**
- Multi-model generation is performed in a structured, reproducible flow.
- Arbitration remains explicit and attributable.
- Outputs are tied to prompt inputs, retrieved context, and provider responses.
- Consensus generation is generation-only; it does not own iterative review policy.

---

### 11. AI Model Router / Token Optimizer

**What it does**
- Selects model/provider routing strategy.
- Optimizes prompt packaging and token budget allocation across retrieved context and task instructions.
- Balances provider capability, cost, and context constraints.

**What it enforces**
- Token limits are honored deterministically.
- Context truncation, prioritization, and provider routing are explicit.
- Oversized prompts fail with explainable policy rather than implicit lossy behavior.
- Model choice does not bypass security or review gates.

---

### 12. Build Pipeline

**What it does**
- Orchestrates the end-to-end implementation flow from scoped task to generated code artifacts.
- Calls the Consensus Engine for implementation and test generation.
- Runs staged generation, validation, improvement, and review flows.
- Produces branch-ready code changes and artifacts for GitHub operations.

**What it enforces**
- Stage ordering is deterministic.
- Each stage has explicit inputs and outputs.
- Review and fix loops occur only at designated stages.
- Pipeline cannot silently skip required controls.

Key referenced stages include:
- **Stage 5: CodeGenerationStage**
- **Stage 6: ThreePassReviewStage**
- **Improvement Pass** and its trigger conditions
- **Operator Review Gate**

---

### 13. Three-Pass Review System

**What it does**
- Performs iterative review of generated output.
- Runs structured review passes over code and tests.
- Calls back into generation mechanisms for fixes when defects are found.

**What it enforces**
- Review is a first-class stage, not an optional post-processing hint.
- Multiple passes must occur in defined order.
- Defects and fixes are attributable to specific review passes.
- Review output does not directly mutate source without pipeline control.

---

### 14. Improvement Pass Engine

**What it does**
- Runs an additional quality improvement pass under defined conditions.
- Applies targeted prompts to refine code quality, maintainability, or completeness.

**What it enforces**
- Improvement pass activation is policy-based, not ad hoc.
- Improvement prompts are bounded and scoped.
- Improvement cannot bypass subsequent review or operator gating.

---

### 15. PRD Generation and Decomposition System

**What it does**
- Generates product requirements documents from high-level scope.
- Decomposes scope statements into ordered PRD lists.
- Supports downstream implementation planning.

**What it enforces**
- Decomposition output is ordered and structured.
- Generated PRDs remain grounded in retrieved project context.
- Scope confirmation occurs before decomposition proceeds.

Referenced controls:
- **Gate 1 — Scope Confirmation**

---

### 16. TRD Generation System

**What it does**
- Generates technical requirements documents from product and project context.
- Produces implementation-grade technical specifications.

**What it enforces**
- TRD generation occurs after required project/product context phases.
- Output structure follows technical-spec generation policy.
- Retrieved context is attributed and constrained.

Referenced phases:
- **Phase 7: PRODUCT_CONTEXT.md Generation**
- **Phase 8: TRD Generation**

---

### 17. Forge Agent

**What it does**
- Serves as the operator-facing intelligent agent coordinating planning, retrieval, generation, review, and fix execution behaviors across the platform.

**What it enforces**
- Agent behavior is mediated by subsystem boundaries; it does not directly own credentials, Git state mutation, or shell controls.
- Agent actions must pass through policy-enforcing services.

---

### 18. Forge CAL

**What it does**
- Platform-level control/coordination abstraction layer for command execution, task orchestration, and future multi-environment extensibility.

**What it enforces**
- Control logic remains explicit, composable, and observable.
- Coordination APIs do not collapse enforcement boundaries between shell, backend, and policy systems.

---

### 19. GitHub Integration Layer

**What it does**
- Performs repository operations, PR creation, branch management, status inspection, review sync, and webhook handling.
- Supports GraphQL API interactions and status queries.
- Creates fix branches and associates generated artifacts with repository state.

**What it enforces**
- GitHub operations require delivered credentials.
- Remote state transitions are tied to explicit workflow stages.
- GraphQL responses and errors are validated and surfaced.
- Branch naming and fix execution follow controlled workflows.

Referenced capabilities:
- **GraphQL API**
- **PR Status Query**
- **GraphQL Error Handling**
- **Webhook Receiver**
- **Fix Branch Creation**
- **Live Sync**

---

### 20. Conflict Detection Subsystem

**What it does**
- Detects overlapping file modifications, workflow conflicts, and operator-interaction conflicts.
- Audits keyboard shortcut conflicts in the shell and file overlap conflicts in code workflows.
- Records conflict telemetry.

**What it enforces**
- Overlapping changes are detected before execution when possible.
- UI command mappings must not collide silently.
- Conflict logging is explicit and queryable.

Referenced controls:
- **Pre-Start File Overlap Check**
- **Keyboard Shortcut Conflict Audit**
- **log_conflict()**

---

### 21. Operator Review and Fix Execution Gates

**What it does**
- Inserts human decision points into critical workflows.
- Presents scope confirmation, proceed-to-fix confirmation, and lens selection.
- Executes fixes only after gate completion.

**What it enforces**
- High-impact actions require explicit operator acknowledgement.
- Review lens / remediation mode is selected intentionally.
- Automated fix execution cannot skip mandatory gates.

Referenced controls:
- **Gate 2 — Proceed to Fix**
- **Gate 3 — Lens Selection**
- **Fix Execution**

---

### 22. Settings and Onboarding Subsystem

**What it does**
- Implements first-launch onboarding.
- Manages settings layout, API key entry, defaults, migrations, and user preferences.
- Persists non-secret state in UserDefaults or equivalent structured storage.

**What it enforces**
- Secret and non-secret settings are separated.
- First-launch flow must complete required prerequisites.
- Settings schema is versioned and migratable.
- Invalid configuration is rejected before backend dependence.

Referenced areas:
- **First-Launch Onboarding**
- **Settings Screen**
- **Settings Layout**
- **API Key Field Specification**

---

### 23. Distribution, Update, and Bundling Pipeline

**What it does**
- Produces the macOS application bundle.
- Bundles Python runtime/components into distributable artifacts.
- Runs CI jobs for Python bundling and notarization.
- Delivers Sparkle-compatible updates.

**What it enforces**
- Bundle contents and runtime dependencies are deterministic.
- CI-produced artifacts are notarization-eligible.
- Update path preserves signed, trusted delivery semantics.

Referenced areas:
- **Bundle Strategy**
- **Python Bundling in CI**
- **Python Caching Steps**
- **Notarization Job**

---

### 24. Observability and Logging

**What it does**
- Captures structured logs from shell and backend.
- Uses `os_log` in the shell with privacy annotations.
- Supports crash symbolication and operational tracing.
- Records conflicts, security events, startup milestones, and workflow outcomes.

**What it enforces**
- Sensitive data must not be emitted in cleartext logs.
- Control decisions are observable.
- Cross-subsystem event correlation is possible.
- Failures are diagnosable without bypassing secret handling constraints.

---

### 25. Notification, Menu Bar, and Dock Integration

**What it does**
- Integrates platform status into menu bar, dock, and notification center.
- Exposes app-level commands through menu structure and shortcuts.

**What it enforces**
- User-visible state reflects actual backend/workflow state.
- Shortcut and menu conflicts are audited.
- Notifications respect platform permission and privacy constraints.

Referenced areas:
- **Application Menu Structure**
- **Dock Integration**
- **Notification Center Integration**

---

### 26. Security Threat Model and Safety Control System

**What it does**
- Defines assets, attacker classes, trust boundaries, and control points.
- Applies safeguards for prompt injection, context poisoning, dependency code injection, path escape, and adversarial LLM output.
- Drives safe handling of external documents, repository content, review comments, and model outputs.

**What it enforces**
- Untrusted content is never implicitly trusted because it appears in project context.
- Prompt construction and tool invocation are policy-filtered.
- Generated code and fixes are treated as untrusted until reviewed and gated.
- Control boundaries remain explicit across shell, backend, models, documents, and GitHub.

Referenced threats and controls:
- **Prompt Injection Defense**
- **Three-Layer Defense**
- **Path Security Gate**
- **File and Issue Exclusion**
- **Dependency Code Injection**
- **Threat: Adversarial LLM Output**
- **Threat: Context Poisoning (Distributed Injection)**

---

### 27. Path and Workspace Security Gate

**What it does**
- Validates file targets, repository paths, and workspace mutations before write operations.
- Prevents traversal, escape, or mutation outside authorized workspace boundaries.

**What it enforces**
- No generated or fix output may write outside approved project scope.
- Path normalization and allowlist validation occur before file mutation.
- Excluded files and issues are protected from accidental or malicious edits.

---

### 28. External Content Ingestion Boundary

**What it does**
- Accepts imported documents, GitHub comments, issues, repository files, and webhook payloads.
- Normalizes them into internal representations for retrieval or workflow use.

**What it enforces**
- Imported content remains classified as untrusted unless and until explicitly transformed by policy.
- Metadata capture preserves source provenance.
- Parse and import errors are visible, not silent.

Referenced area:
- **Document Import**

---

### 29. Testing and Validation Framework

**What it does**
- Verifies startup sequencing, runtime behavior, review flow behavior, and subsystem correctness.
- Includes specific startup sequence unit coverage.

**What it enforces**
- Critical ordering assumptions are tested.
- Regression coverage exists for compatibility handshake and startup readiness.
- Architecture invariants are validated continuously.

Referenced areas:
- **Testing Requirements**
- **Startup Sequence Unit Test**

---

## Enforcement Order

This section describes the dominant control path in execution order. The exact feature path varies by workflow, but enforcement ordering must preserve the following sequence.

### A. Application startup and unlock

1. **macOS Application Shell** launches.
2. **Settings/Onboarding Subsystem** checks first-launch state, settings schema version, and required configuration.
3. **Native Identity and Authentication Layer** performs biometric/session gate as required.
4. **Keychain-backed secrets** are unlocked for active session use.
5. **Process Management Subsystem** starts the Python backend.
6. **IPC / XPC Communication Layer** establishes transport.
7. **Backend Runtime Startup Manager** initializes services in strict dependency order:
   - config/state
   - logging/telemetry
   - embedding model service
   - document store
   - credential-dependent integrations
   - command router
8. **Backend Runtime** publishes version metadata.
9. **Shell** validates the **Swift/Python version handshake**.
10. On success, shell delivers credentials to backend over authenticated channel.
11. Backend marks ready.
12. UI exposes normal operations, notifications, and command surfaces.

### B. Document ingestion and indexing

1. Operator imports documents or project sync discovers them.
2. **External Content Ingestion Boundary** classifies content as untrusted.
3. **Document Store** parses supported formats and extracts metadata.
4. **Chunking subsystem** performs semantic chunking, with fixed-size fallback and overlap.
5. **Embedding Model Service** computes embeddings.
6. **Document Store** persists chunks, vectors, and provenance metadata.
7. Retrieval index becomes available to generation flows.

### C. Generation workflow

1. Operator selects task or scope.
2. **Operator Gate 1 — Scope Confirmation** must pass where required.
3. **Command Router** accepts request.
4. **Security Control System** applies context filtering, prompt injection defenses, exclusions, and path/workspace constraints.
5. **Document Store** retrieves relevant context.
6. **AI Model Router / Token Optimizer** assembles prompt budget and provider routing.
7. **Consensus Engine** runs dual-provider generation and Claude arbitration.
8. **Build Pipeline** consumes generated outputs in stage order.
9. **CodeGenerationStage** emits candidate implementation and tests.
10. **ThreePassReviewStage** performs iterative review.
11. **Improvement Pass Engine** runs if policy conditions are met.
12. If defects require changes, **Operator Gate 2 — Proceed to Fix** and **Gate 3 — Lens Selection** are evaluated where applicable.
13. **Fix Execution** applies bounded changes through path security and repository controls.
14. Outputs are prepared for branch/PR actions.

### D. GitHub workflow

1. **GitHub Integration Layer** confirms credential presence and repository context.
2. **Conflict Detection** runs pre-start file overlap checks.
3. Branch or fix branch is created.
4. Generated changes are committed through controlled repository mutation flow.
5. PR creation/status queries use REST/GraphQL integration.
6. Review comments, statuses, and webhook events re-enter through the **External Content Ingestion Boundary** as untrusted content.
7. Follow-up review/fix cycles re-enter the generation workflow under the same security controls.

### E. Shutdown

1. Shell or operator initiates stop.
2. **IPC / XPC Layer** sends stop signal.
3. **Backend Runtime** stops accepting new commands.
4. In-flight work is drained or canceled according to graceful shutdown policy.
5. Guaranteed persisted state is flushed.
6. Backend exits.
7. Shell updates UI/notifications and releases session resources as appropriate.

---

## Component Boundaries

This section defines what each subsystem must never do.

### macOS Application Shell must never
- Implement generation logic or retrieval algorithms.
- Store secrets in plaintext preferences or UI model state.
- Assume backend readiness from process liveness alone.
- Bypass version compatibility checks.
- Allow UI actions to mutate repository state without backend policy path.

### Native Identity and Authentication Layer must never
- Delegate trust decisions about local identity to the backend.
- Expose raw secrets to logs, notifications, or non-secure storage.
- Convert biometric success into indefinite authorization without session policy.

### IPC / XPC Layer must never
- Act as a free-form message bus without schema validation.
- Treat unauthenticated backend output as trusted commands.
- Collapse shell and backend privilege domains.

### Process Management must never
- Deliver credentials before successful identity gate and compatibility validation.
- Restart indefinitely without loop detection or operator visibility.
- Mark backend healthy solely because the process exists.

### Backend Runtime Startup Manager must never
- Start command handling before required dependencies initialize.
- Report ready before document store, embedding model, and credential-dependent services are valid.
- Continue normal operation after incompatible version handshake failure.

### Command Router must never
- Execute commands before runtime readiness.
- Allow direct unvalidated access to internal services.
- Treat arbitrary external payloads as typed internal commands.

### Document Store must never
- Silently ingest malformed content without surfaced error state.
- Lose source provenance for indexed chunks.
- Return retrieval context without metadata needed for attribution.
- Depend on an unavailable embedding model.

### Embedding Model Service must never
- Change model identity silently without invalidating or reindexing affected vectors.
- Accept startup sequencing that allows retrieval before model readiness.

### Consensus Engine must never
- Own repository mutation or shell identity logic.
- Bypass prompt safety filters or retrieval provenance requirements.
- Conflate arbitration with review-stage defect validation.

### AI Model Router / Token Optimizer must never
- Hide truncation or context dropping implicitly.
- Route around policy because a model has larger context.
- Treat token constraints as advisory.

### Build Pipeline must never
- Skip required stages silently.
- Apply fixes outside explicit stage and gate policy.
- Mutate files outside path security enforcement.

### Three-Pass Review System must never
- Present review as complete if required passes did not run.
- Directly publish changes without pipeline control.
- Treat generated code as trusted because it passed one model review.

### Improvement Pass Engine must never
- Run outside defined trigger conditions.
- Override operator or review gates.
- Expand task scope beyond bounded improvement objectives.

### PRD Generation and Decomposition must never
- Proceed on ambiguous scope without confirmation.
- Generate planning artifacts detached from project context.

### TRD Generation System must never
- Skip prerequisite context-generation phases.
- Present architectural constraints without traceable source context.

### GitHub Integration Layer must never
- Operate without validated credentials.
- Accept webhook/review content as trusted instructions.
- Write arbitrary repository paths outside workspace guardrails.
- Hide GraphQL or API errors from orchestration.

### Conflict Detection must never
- Allow known overlapping mutations to proceed silently.
- Treat shortcut conflicts as benign if they impair operator control.

### Operator Review Gates must never
- Auto-approve on behalf of the user.
- Be bypassed by retry, webhook, or fix-loop side effects.

### Settings and Onboarding must never
- Store API secrets in UserDefaults.
- Leave schema migrations implicit or partially applied.
- Allow invalid config to propagate into backend startup.

### Distribution / Update / Bundling must never
- Ship unsigned or non-notarized production artifacts where notarization is required.
- Produce nondeterministic bundle contents.
- Break runtime compatibility silently across app/backend versions.

### Observability and Logging must never
- Emit secret values, prompt contents with sensitive material, or raw credentials without redaction policy.
- Sacrifice explainability of control decisions.
- Conflate audit telemetry with mutable business logic.

### Security Threat Model and Safety Control System must never
- Infer trust from repository membership, document location, or LLM fluency.
- Delegate final policy enforcement to models.
- Treat generated code as safe by default.
- Allow untrusted text to directly author tool invocation semantics.

### Path and Workspace Security Gate must never
- Permit path traversal or writes outside authorized project root.
- Ignore exclusion rules for files or issues.
- Trust model-generated file paths without normalization and validation.

---

## Key Data Flows

## 1. Shell startup and backend readiness flow

**Primary path**
- App launch
- onboarding/settings validation
- biometric/session unlock
- backend process spawn
- IPC establishment
- backend startup sequence
- version handshake
- credential delivery
- ready state publication

**Data exchanged**
- session state
- shell version
- backend version/capability metadata
- readiness status
- credential envelope
- startup diagnostics

**Critical properties**
- secrets flow only after identity and compatibility checks
- readiness is explicit
- startup failures are diagnosable and surfaced to UI

---

## 2. Document ingestion and indexing flow

**Primary path**
- imported document
- parser
- metadata extraction
- chunker
- embedder
- vector/index persistence

**Data exchanged**
- raw document bytes/text
- parsed structured content
- metadata: type, source, timestamps, provenance
- chunk records
- embedding vectors
- indexing status/errors

**Critical properties**
- untrusted content classification preserved
- chunk provenance retained
- embedding/version consistency maintained

---

## 3. Retrieval-augmented generation flow

**Primary path**
- task request
- security filter/exclusion rules
- retrieval query
- ranked chunks
- token optimization
- dual-provider generation
- arbitration
- candidate output

**Data exchanged**
- task prompt
- scoped project context
- retrieval metadata
- prompt package
- provider responses
- arbitration rationale/output

**Critical properties**
- context is attributable
- token truncation is controlled
- provider outputs remain untrusted until downstream review

---

## 4. Build and review pipeline flow

**Primary path**
- candidate implementation
- test generation
- code generation stage
- review pass 1
- review pass 2
- review pass 3
- optional improvement pass
- operator gates
- fix execution
- final artifact set

**Data exchanged**
- source file deltas
- test artifacts
- review findings
- fix plans
- operator decisions
- pipeline status telemetry

**Critical properties**
- stage order fixed
- operator decisions are explicit inputs
- fixes are bounded by path/workspace constraints

---

## 5. GitHub synchronization flow

**Primary path**
- repository context validation
- branch creation
- commit
- PR creation
- status query
- review sync
- webhook ingest
- follow-up fix loop

**Data exchanged**
- git refs/branch names
- commit metadata
- PR metadata
- GraphQL query/response payloads
- review comments
- webhook event bodies

**Critical properties**
- all inbound remote text is untrusted
- API errors are surfaced
- branch and fix workflows are explicit and reproducible

---

## 6. Settings and secret flow

**Primary path**
- user edits settings
- validation
- non-secret preference persistence
- secret entry via secure field
- Keychain write
- on unlock, credential delivery to backend

**Data exchanged**
- preference values
- schema version
- secret references/handles
- validation errors

**Critical properties**
- secret/non-secret separation
- migration safety
- no plaintext credential persistence in general config stores

---

## 7. Shutdown flow

**Primary path**
- stop request
- backend quiesce
- in-flight work drain/cancel
- persisted state flush
- process exit
- shell cleanup

**Data exchanged**
- stop signal
- task cancellation notices
- final status
- persisted checkpoints/logs

**Critical properties**
- no acceptance of new work during shutdown
- guaranteed persisted state is written before exit
- shell reflects terminal state correctly

---

## Critical Invariants

The following invariants are mandatory across the Forge platform.

### Identity and secret invariants
1. No production secret is stored in plaintext UserDefaults or ordinary app state.
2. Backend credentials are delivered only after successful local identity gate.
3. Secret access is session-scoped and revocable.
4. Logs and notifications must not disclose secrets.

### Startup and compatibility invariants
5. Backend readiness must be explicit, not inferred from process liveness.
6. Command routing must not begin before startup dependencies complete.
7. Embedding service must be available before document store retrieval is considered ready.
8. Shell/backend version compatibility must be checked before normal operation.
9. Incompatible versions fail closed.

### Retrieval and context invariants
10. All retrieved chunks must retain provenance metadata.
11. Parsing or indexing failures must be surfaced explicitly.
12. Embedding model identity/version must be known for indexed vectors.
13. Prompt context assembly must be bounded, attributable, and token-budgeted.
14. Repository content, PR comments, issues, and imported documents are untrusted inputs.

### Generation and review invariants
15. Consensus generation always produces output through explicit multi-provider + arbitration flow when that engine is selected.
16. Generated output is untrusted until it passes pipeline review and required gates.
17. Review passes must execute in defined order and be auditable.
18. Improvement pass may run only under explicit trigger conditions.
19. Operator gates cannot be auto-satisfied by internal automation.

### Repository and workspace invariants
20. No file write may occur outside the authorized project/workspace root.
21. Excluded files and issues must remain excluded from automated mutation.
22. Pre-start overlap/conflict checks must run where required before repository mutation.
23. GitHub operations require validated credentials and explicit workflow state.

### Security invariants
24. Trust is never inferred from document location, repository origin, or model confidence.
25. LLM output never directly defines enforcement policy.
26. Prompt injection defenses must apply to all untrusted external content.
27. Dependency/code injection controls must apply before execution or inclusion of generated changes.
28. Path normalization and security gates must precede any file mutation.
29. Security control failure defaults to deny, not warn-only.

### Observability invariants
30. All critical control decisions must be observable in logs/telemetry.
31. Auditability must not depend on secret disclosure.
32. Conflicts, startup failures, handshake failures, and security denials must be recorded explicitly.
33. Telemetry and enforcement remain separable: logging reports decisions but does not make them.

### Packaging and delivery invariants
34. Production bundle contents must be deterministic and signable.
35. Update delivery must preserve trust chain requirements.
36. Python runtime bundling and notarization must remain compatible with shell distribution semantics.

### Architectural invariants
37. Shell owns native identity, packaging, and process orchestration.
38. Backend owns generation, retrieval, and repository automation.
39. Security policy is cross-cutting, but enforcement points must remain explicit and local to subsystems.
40. No subsystem may silently expand its authority across a trust boundary.