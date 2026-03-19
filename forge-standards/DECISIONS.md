# DECISIONS.md

## Native macOS shell as the primary host
**Status:** Accepted  
**Context:** The platform must package, install, authenticate, and orchestrate all subsystems in a way that feels native on macOS, supports drag-to-Applications distribution, integrates with system security primitives, and provides a stable lifecycle boundary around the backend runtime.  
**Decision:** Forge uses a native macOS application shell built with Swift and SwiftUI as the primary host for the platform. The shell owns installation UX, auto-update integration, authentication gates, settings, onboarding, process orchestration, observability hooks, and the user-facing application lifecycle.  
**Consequences:** The product is explicitly macOS-first. Shell behavior, security posture, and UX are optimized for Apple platform primitives rather than cross-platform abstractions. Non-macOS desktop support would require a separate host implementation rather than simple reuse.  
**Rejected alternatives:**  
- Cross-platform desktop shell (for example Electron): rejected because it weakens integration with biometrics, Keychain, launch semantics, and native observability.  
- Browser-only host: rejected because local process control, secret handling, and local runtime orchestration are first-class requirements.

## SwiftUI for application UI
**Status:** Accepted  
**Context:** The shell needs a maintainable, native UI framework with strong support for state-driven rendering, navigation, accessibility, and modern macOS patterns.  
**Decision:** The shell UI is implemented in SwiftUI, with explicit root views, a state-driven navigation model, and view models that separate presentation logic from platform orchestration logic.  
**Consequences:** UI architecture is declarative and state-centric. Teams must design around SwiftUI data flow and lifecycle semantics. Some advanced AppKit integrations may still be needed at the edges.  
**Rejected alternatives:**  
- AppKit-first UI: rejected because it increases implementation complexity for the required app structure and modern reactive state patterns.  
- Mixed ad hoc UI framework usage: rejected because inconsistent ownership and lifecycle rules would increase maintenance risk.

## Modular Swift shell with explicit subsystem boundaries
**Status:** Accepted  
**Context:** The shell owns authentication, settings, onboarding, process management, XPC communication, and logging. Without clear module boundaries, state ownership and change impact become difficult to reason about.  
**Decision:** The shell is split into explicit Swift modules with clear ownership boundaries for identity, settings, process orchestration, communication, and UI composition. Shared contracts are minimized and concurrency-safe interfaces are preferred.  
**Consequences:** Subsystems can evolve independently with clearer testability and reduced coupling. Initial architecture work is higher, and cross-module changes require contract discipline.  
**Rejected alternatives:**  
- Monolithic shell target with informal layering: rejected because orchestration-heavy codebases degrade quickly without hard boundaries.  
- Broad shared singleton model: rejected because it obscures ownership and complicates concurrency correctness.

## Swift concurrency as the shell concurrency model
**Status:** Accepted  
**Context:** The shell coordinates UI state, backend lifecycle events, authentication prompts, and IPC. Concurrency bugs in these flows would directly impact reliability and security.  
**Decision:** Forge adopts Swift concurrency primitives as the primary concurrency model in the shell, with explicit actor or main-actor ownership for mutable state and structured concurrency for lifecycle tasks.  
**Consequences:** Code must follow async/await and actor isolation rules. Legacy callback-style APIs require adaptation. Concurrency behavior becomes more analyzable and less error-prone than manual thread management.  
**Rejected alternatives:**  
- GCD-first concurrency: rejected because it makes ownership and cancellation harder to reason about across multiple subsystems.  
- Unstructured background task usage: rejected because lifecycle-sensitive orchestration requires explicit task hierarchy and cancellation.

## Biometric gate and Keychain-backed secret storage
**Status:** Accepted  
**Context:** The shell must protect user identity, secrets, and session state while operating on a machine that may also hold sensitive development credentials.  
**Decision:** Authentication is fronted by a biometric gate where available, and secrets are stored in the macOS Keychain rather than in application files or preferences. Session lifecycle is managed explicitly by the shell.  
**Consequences:** Access to sensitive operations depends on system authentication capabilities and Keychain access semantics. Secret material is not portable via simple config export. Session transitions must be modeled carefully in the UI and backend orchestration.  
**Rejected alternatives:**  
- Storing secrets in UserDefaults or local files: rejected because it does not meet platform-appropriate security expectations.  
- App-managed password vault without Keychain: rejected because it duplicates mature system functionality and increases risk.

## Authenticated interprocess boundary between shell and backend
**Status:** Accepted  
**Context:** The shell and Python backend have different trust characteristics and failure modes. Their communication channel must prevent spoofing, accidental privilege confusion, and undefined startup behavior.  
**Decision:** Forge uses an authenticated interprocess communication boundary between the Swift shell and Python backend, with the shell treating the backend as a managed child runtime rather than an in-process library. The communication layer must verify peer identity and enforce message contracts.  
**Consequences:** Backend crashes or restarts can be isolated from the UI process. Serialization contracts become a first-class compatibility surface. IPC adds implementation complexity and latency compared with in-process calls.  
**Rejected alternatives:**  
- Embedding Python in-process: rejected because it weakens isolation and complicates crash containment and lifecycle management.  
- Unauthenticated local sockets or loose IPC: rejected because the shell must not trust arbitrary local peers.

## Shell-owned backend process lifecycle
**Status:** Accepted  
**Context:** The backend performs retrieval, generation, and tool orchestration, but the shell is responsible for app lifecycle and user trust. Process startup, monitoring, restart, and stop behavior need a single owner.  
**Decision:** The Swift shell owns launching, monitoring, restarting, and stopping the Python backend. Credential delivery and runtime configuration are mediated by the shell, not self-discovered by the backend from ambient machine state.  
**Consequences:** The shell becomes the authoritative orchestrator and can enforce startup sequencing, user authentication requirements, and compatibility checks. Backend autonomy is constrained in favor of predictable lifecycle management.  
**Rejected alternatives:**  
- Backend self-launch or daemon-first model: rejected because it reduces UI control over session state and trust boundaries.  
- Manual user-run backend process: rejected because it creates inconsistent state and poor install-time ergonomics.

## Sparkle-based automatic updates for the macOS shell
**Status:** Accepted  
**Context:** The shell is distributed as a macOS app bundle and requires safe, user-friendly updates without custom updater infrastructure.  
**Decision:** The macOS shell uses Sparkle for application auto-update, integrated into the native distribution and installation model.  
**Consequences:** Update behavior follows Sparkle’s security and UX model. Release engineering must support signed update artifacts and the associated operational workflow.  
**Rejected alternatives:**  
- Custom updater: rejected because update security and reliability are solved problems better handled by a mature framework.  
- No automatic updates: rejected because it would slow adoption of shell, security, and compatibility fixes.

## First-launch onboarding and versioned settings migrations
**Status:** Accepted  
**Context:** The shell manages onboarding, preferences, and persisted local state. As the product evolves, settings schemas will change and must remain compatible across upgrades.  
**Decision:** Forge implements an explicit first-launch onboarding flow and stores non-secret preferences in a versioned UserDefaults schema with defined migration behavior.  
**Consequences:** Preference evolution is deliberate and testable. Engineers must maintain migration code when settings change. Secret and non-secret persistence remain clearly separated.  
**Rejected alternatives:**  
- Ad hoc settings evolution: rejected because silent schema drift creates upgrade failures.  
- Storing all state in a single opaque blob: rejected because migrations, debugging, and partial resets become difficult.

## Structured observability with os_log and privacy annotations
**Status:** Accepted  
**Context:** The shell handles authentication, process orchestration, and IPC, all of which require diagnosable behavior without leaking sensitive user data into logs.  
**Decision:** The shell uses structured logging based on os_log with privacy annotations, plus crash symbolication support, as the standard observability model.  
**Consequences:** Diagnostics are more actionable and safer by default. Engineers must classify log fields correctly and avoid bypassing the structured logging path.  
**Rejected alternatives:**  
- Free-form string logging: rejected because it is harder to query and more likely to leak sensitive data.  
- Verbose debug-only logging as the primary strategy: rejected because production troubleshooting requires structured, privacy-aware telemetry.

## Document store as the shared knowledge foundation
**Status:** Accepted  
**Context:** Retrieval quality affects code generation, PRD generation, reviews, and TRD development. A single subsystem must provide consistent ingestion, indexing, and retrieval behavior across the platform.  
**Decision:** Forge centralizes technical-document knowledge in a Document Store and Retrieval Engine that ingests approved source documents, extracts metadata, chunks content, computes embeddings, and serves retrieval context to downstream agent operations.  
**Consequences:** Retrieval becomes a platform dependency rather than an optional feature. Changes to parsing, chunking, or embedding strategy have system-wide impact and require careful evaluation.  
**Rejected alternatives:**  
- Per-feature retrieval stacks: rejected because duplicated indexing logic would produce inconsistent context quality.  
- Raw keyword search only: rejected because semantic retrieval is required for reliable context matching across varied technical language.

## Semantic-first chunking with fixed-size fallback
**Status:** Accepted  
**Context:** Retrieval quality depends heavily on how documents are split. Pure fixed-length chunking can break meaning, while pure semantic splitting can fail on malformed or underspecified inputs.  
**Decision:** The document store uses semantic chunking as the primary strategy, with bounded chunk sizes, overlap between chunks, and a fixed-size fallback when semantic parsing cannot produce acceptable segments.  
**Consequences:** Retrieval favors coherent technical units while remaining robust to inconsistent source formatting. Chunking logic is more complex and must be validated against downstream relevance quality.  
**Rejected alternatives:**  
- Fixed-size chunking only: rejected because it silently degrades semantic coherence.  
- Semantic chunking without fallback: rejected because ingestion must remain resilient across heterogeneous document inputs.

## Local-default embedding model for retrieval
**Status:** Accepted  
**Context:** The retrieval subsystem needs an embedding model that is available at runtime, consistent across sessions, and not dependent on external API availability for core knowledge access.  
**Decision:** Forge uses a local embedding model by default for document indexing and retrieval. External embedding services are not the baseline dependency for core retrieval behavior.  
**Consequences:** Retrieval remains available offline or under API outage conditions, and embedding behavior is more controllable. Model updates require deliberate version management and possible reindexing.  
**Rejected alternatives:**  
- Cloud-only embeddings: rejected because they introduce network dependency, cost variability, and privacy concerns into a foundational subsystem.  
- Multiple active embedding models by default: rejected because mixed vector spaces complicate retrieval consistency and operations.

## Metadata-rich ingestion for supported document formats
**Status:** Accepted  
**Context:** The document store must ingest multiple technical document formats and preserve enough structure to support relevance, traceability, and debugging.  
**Decision:** Ingestion supports the required source formats and extracts normalized metadata alongside content, including document identity and parsing provenance sufficient for retrieval filtering and auditability. Errors are handled explicitly rather than silently dropping malformed inputs.  
**Consequences:** Retrieval results can be traced back to source documents and filtered with more precision. Parsers and metadata contracts become part of the maintained platform surface.  
**Rejected alternatives:**  
- Content-only ingestion without metadata: rejected because traceability and debugging would be poor.  
- Best-effort silent parsing: rejected because unnoticed ingestion failures would degrade the whole system.

## Treat external content as untrusted by default
**Status:** Accepted  
**Context:** The system consumes TRDs, PR comments, GitHub content, and other external inputs that can influence prompts, generated code, and automation behavior. This creates prompt injection and tool misuse risks not addressed by traditional validation alone.  
**Decision:** Forge treats all external content as untrusted by default unless explicitly designated otherwise by a documented trust boundary. Untrusted content may be processed for retrieval and generation context, but it must not directly redefine system instructions, privileges, or tool policies.  
**Consequences:** Prompt construction, tool invocation, and automation policies must preserve strict separation between instructions and data. Engineers cannot assume that repository or document content is benign just because it is text.  
**Rejected alternatives:**  
- Trust repository and document content implicitly: rejected because the platform’s core attack surface is hostile instruction-like content inside otherwise valid inputs.  
- Rely only on input sanitization: rejected because prompt injection is a control-flow problem, not just a string-cleaning problem.

## Explicit asset inventory and trust boundaries drive security controls
**Status:** Accepted  
**Context:** The platform touches sensitive assets including secrets, signing credentials, source code, generated code, repository access, and local execution capability. Security controls must map to what is being protected and where trust changes.  
**Decision:** Security design is driven by an explicit asset inventory and documented trust boundaries between shell, backend, local machine resources, external documents, GitHub content, CI, and model/API providers. Controls are specified relative to those boundaries rather than as generic hardening checklists.  
**Consequences:** Security reviews and implementation work must name assets, boundaries, and attacker capabilities explicitly. Architectural changes that alter a trust boundary require security reconsideration, not just code changes.  
**Rejected alternatives:**  
- Generic baseline hardening without system-specific threat modeling: rejected because the main risks arise from this product’s unique AI-agent behavior.  
- Implicit boundary assumptions: rejected because unclear trust transitions create inconsistent control enforcement.

## Principle of least privilege for tools, credentials, and automation
**Status:** Accepted  
**Context:** The system can call APIs, manipulate repositories, and run code in CI on machines that may also hold sensitive credentials. Broad access would amplify the impact of prompt injection or component compromise.  
**Decision:** Forge applies least privilege across tool access, credential scope, process capabilities, and automation actions. Components receive only the permissions required for their role, and sensitive credentials are mediated rather than broadly exposed.  
**Consequences:** Integration work may require more explicit permission wiring and policy checks. Some workflows become less convenient, but compromise blast radius is reduced.  
**Rejected alternatives:**  
- Broad shared credentials for all subsystems: rejected because compromise of one path would expose the entire environment.  
- Convenience-first unrestricted automation: rejected because the platform operates in a high-consequence development context.

## Ordered backend startup with readiness only after critical initialization
**Status:** Accepted  
**Context:** Backend initialization order matters. Retrieval cannot function before the embedding model and document store are ready, and other tools may depend on prior setup. Premature readiness signals would create race conditions and partial-failure states.  
**Decision:** The Python backend starts subsystems in a defined sequence and emits a ready signal only after all critical startup dependencies have initialized successfully. Partial startup is not considered ready.  
**Consequences:** Startup may take longer, but post-ready behavior is more predictable. Initialization dependencies must be explicit, and failures must surface as startup failures rather than deferred runtime surprises.  
**Rejected alternatives:**  
- Opportunistic parallel startup with early ready signal: rejected because consumers cannot safely infer capability availability.  
- Lazy initialization of all subsystems after ready: rejected because it shifts deterministic startup failures into harder-to-debug runtime failures.

## Explicit shell-backend version compatibility handshake
**Status:** Accepted  
**Context:** The Swift shell and Python backend evolve separately but must interoperate across IPC contracts, startup semantics, and capability expectations.  
**Decision:** On startup, the backend reports its version and compatibility information to the shell, and the shell validates that the pair is supported before proceeding. Incompatible versions fail closed rather than attempting undefined operation.  
**Consequences:** Version compatibility becomes a managed contract. Release processes must define supported pairings and upgrade behavior. Users may be blocked from operation until versions are aligned, but undefined runtime behavior is avoided.  
**Rejected alternatives:**  
- Best-effort compatibility without handshake: rejected because contract drift would fail unpredictably.  
- Strict single-build lockstep with no protocol declaration: rejected because explicit compatibility signaling is clearer and more diagnosable.

## Graceful backend shutdown with in-flight work handling and persistence guarantees
**Status:** Accepted  
**Context:** The backend may be indexing documents, serving retrieval, or performing generation-related work when the shell requests shutdown or the app exits. Abrupt termination risks data corruption and inconsistent state.  
**Decision:** The backend implements graceful shutdown semantics: it responds to stop signals by halting new work, handling or cancelling in-flight work according to policy, and persisting guaranteed state before exit. The shell treats shutdown as a protocol, not just a kill action.  
**Consequences:** Stop behavior is slower but safer. Long-running work must be cancellable or checkpointed, and shutdown guarantees must be documented per subsystem.  
**Rejected alternatives:**  
- Immediate process termination on exit: rejected because it risks corrupting indexes and losing important state.  
- Unlimited drain time on shutdown: rejected because the shell must preserve a responsive and predictable app lifecycle.