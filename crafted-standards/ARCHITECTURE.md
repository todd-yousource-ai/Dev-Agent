# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entrypoint and scene shell for the Crafted application.

It is defined as the `@main` `App` and is responsible for:

- Declaring the primary application window via `WindowGroup`
- Hosting `RootView()` as the main UI content
- Injecting shared application-scoped state into the main scene through SwiftUI environment objects:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Configuring primary window presentation and sizing:
  - `.windowStyle(.hiddenTitleBar)`
  - `.defaultSize(width: 1280, height: 800)`
  - `.windowResizability(.contentMinSize)`
- Declaring a separate `Settings` scene
- Providing `SettingsView()` with `SettingsStore.shared`
- Enforcing that the settings window is a distinct scene and is biometric-gated

Within the health registry, this subsystem corresponds to:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`
- `language`: `swift`, `python`

## Component Boundaries

### In Scope

The `CraftedApp` subsystem owns the application shell and scene composition layer:

- SwiftUI `App` entrypoint
- Main window scene construction
- Settings scene construction
- Environment object wiring for app-global shared models/stores
- Window-level UI configuration for the primary scene

Concrete in-scope elements named in the TRDs:

- `CraftedApp: App`
- `WindowGroup`
- `RootView`
- `Settings`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Out of Scope

The subsystem does not own the internal behavior of injected models or views. Based on the provided TRDs, the following are external to `CraftedApp`:

- Business logic inside `RootView`
- State management implementation inside `AppState`
- Build-stream behavior inside `BuildStreamModel`
- Settings persistence or policy inside `SettingsStore`
- The biometric-gating implementation itself; `CraftedApp` only declares the settings scene as biometric-gated in architecture terms
- CI execution, telemetry production, and self-healing logic implementation details
- GitHub write-path validation logic, except where subsystem identity and repository roots affect integration

### Repository / Path Boundary

For repository operations affecting this subsystem, the relevant root boundary is the CamelCase root pattern. Swift/Xcode project roots such as `CraftedApp` must be considered valid by smart root detection:

- Allowed by pattern: `^[A-Za-z][A-Za-z0-9_-]*$`
- Explicit lesson learned: `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection`

This means repository tooling must not reject `CraftedApp`-style roots as invalid project roots.

## Data Flow

### 1. Application Startup

At process launch, `CraftedApp` is instantiated as the `@main` app entrypoint.

Flow:

1. `CraftedApp` constructs its `body`
2. A `WindowGroup` scene is created
3. `RootView()` is instantiated as the primary content view
4. Shared singleton-like state objects are injected into the main scene:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
5. Primary window styling and size constraints are applied

### 2. Main Scene Environment Propagation

The main scene propagates shared objects through SwiftUI environment injection.

Flow into main UI tree:

- `CraftedApp`
  - `WindowGroup`
    - `RootView`
      - receives `AppState.shared`
      - receives `BuildStreamModel.shared`
      - receives `SettingsStore.shared`

This establishes app-level state availability for descendants of `RootView`.

### 3. Settings Scene Flow

A separate settings scene is declared.

Flow:

1. The `Settings` scene is created independently from the main `WindowGroup`
2. `SettingsView()` is instantiated
3. `SettingsStore.shared` is injected into the settings scene
4. Access to the settings window is biometric-gated

This creates a dedicated configuration surface with its own scene boundary while sharing the same settings store instance.

### 4. Operational Metadata Flow

The subsystem is identified in the health registry with the following operational integrations:

- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`
- Escalation policy:
  - `security`: `operator_review`
  - `functional`: `auto_merge`
  - `pipeline`: `engineer_review`

These registry values define how the subsystem is tracked and reviewed in automation, but they do not alter the in-process SwiftUI scene graph.

## Key Invariants

### Scene Construction Invariants

- `CraftedApp` is the sole `@main` application shell for this subsystem.
- The primary UI is hosted in a `WindowGroup`.
- The primary scene content is `RootView()`.
- The settings UI is hosted in a separate `Settings` scene.
- `SettingsView()` receives `SettingsStore.shared`.

### Environment Injection Invariants

- `RootView()` must be provided:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- The settings scene must be provided:
  - `SettingsStore.shared`

The architecture therefore requires shared, app-scoped object injection from the shell rather than ad hoc per-view creation.

### Window Invariants

For the main window:

- Hidden title bar is required: `.windowStyle(.hiddenTitleBar)`
- Default size is required: `1280 × 800`
- Window resizability is constrained by content minimum size: `.windowResizability(.contentMinSize)`

Size constraints called out by the TRD:

- Minimum window size: `1024 × 680`
- Maximum size: unconstrained / resizable

### Security / Reliability Invariants from Forge Context

These repository-wide architectural invariants apply to subsystem operation and integration:

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error must surface with context
- Secrets never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- Generated code is never executed by the agent
- Gates wait indefinitely for operator input; no auto-advance on gated decisions

### Repository Integration Invariants

- All GitHub operations must go through `GitHubTool`
- Paths must be validated before any write
- CamelCase Swift/Xcode roots such as `CraftedApp` must be accepted by root detection
- Dot-prefixed roots like `.github` require explicit allowlisting behavior in path validation contexts

## Failure Modes

### 1. Repository Path Rejection for Subsystem Roots

Documented failure pattern:

- `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection`

Impact:

- Commits touching this subsystem can fail silently or be rejected by path security guards if the project root is not recognized.

Required mitigation from lessons learned:

- Use smart root detection
- Allow any root matching `^[A-Za-z][A-Za-z0-9_-]*$`

This is the primary repository-integration failure mode specifically tied to Crafted app targets.

### 2. Silent or Context-Free Failure Is Forbidden

Repository-wide constraint from Forge Context:

- No silent failure paths
- Every error surfaces with context

Implication for `CraftedApp`:

- Failures around scene setup, settings access, or integration must not be hidden behind degraded behavior without surfaced context.

### 3. Security / Identity Errors Must Fail Closed

If subsystem behavior intersects auth, crypto, or identity-sensitive operations through surrounding infrastructure, errors must fail closed rather than degrade.

This particularly matters for:

- Biometric-gated settings access
- Any identity-sensitive application-shell decision path

### 4. Pipeline Escalation Classification

Per registry policy, failures affecting this subsystem are escalated by class:

- Security failures → `operator_review`
- Functional failures → `auto_merge`
- Pipeline failures → `engineer_review`

This defines handling boundaries once failures are detected by automation.

### 5. Retry / Repair Limits in Automation

Relevant self-healing constraints from Forge Context:

- Never retry indefinitely
- Maximum `20` local attempts, then move on
- Attempt-based escalation rules apply in failure handling

This bounds automated repair loops affecting the subsystem’s CI or code-generation path.

## Dependencies

### Runtime UI Dependencies

The subsystem directly depends on the following named components:

- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

These are required for scene composition and environment wiring.

### Platform / Framework Dependency

Implicit from the TRD code shape, the subsystem depends on:

- SwiftUI application and scene APIs:
  - `App`
  - `Scene`
  - `WindowGroup`
  - `Settings`
  - environment object propagation
  - window style and sizing modifiers

### Operational Dependencies

From the health registry and repository context:

- Repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry sink: `logs/telemetry.jsonl`

### Tooling / Process Dependencies

For repository mutation and automation around this subsystem:

- `GitHubTool` for all GitHub operations
- Path validation before any write
- Root detection supporting CamelCase project roots
- Health registry classification under:
  - `target_id`: `crafted-app-shell`
  - `subsystem`: `CraftedAppShell`

These dependencies govern how the subsystem is built, tracked, and safely modified in the repository.