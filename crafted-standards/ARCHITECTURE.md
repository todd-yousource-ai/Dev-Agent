# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry subsystem defined as the `@main` SwiftUI `App`. It is responsible for declaring the application’s scene structure and injecting shared application models into those scenes.

Primary responsibilities:

- Define the primary application window via `WindowGroup`
- Host `RootView()` as the main UI root
- Inject shared singleton environment objects into the main scene:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Configure primary window presentation and sizing:
  - `.windowStyle(.hiddenTitleBar)`
  - `.defaultSize(width: 1280, height: 800)`
  - `.windowResizability(.contentMinSize)`
- Define a separate `Settings` scene
- Inject `SettingsStore.shared` into `SettingsView()`

Documented window constraints:

- Minimum window size: `1024 × 680`
- Maximum window size: unconstrained

This subsystem is the application shell boundary for the SwiftUI app and corresponds to the shell-oriented identity reflected in the health registry:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

## Component Boundaries

### Inside this subsystem

The subsystem includes the SwiftUI app-shell concerns explicitly shown in the scene architecture:

- `CraftedApp: App`
- Main `WindowGroup`
- `RootView` as the main scene root
- `Settings` scene
- Environment object wiring for:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Window style and sizing policy

### Outside this subsystem

The following are dependencies or adjacent systems, not responsibilities of `CraftedApp` itself:

- Internal behavior of `RootView`
- Internal behavior of `SettingsView`
- State implementation details of:
  - `AppState`
  - `BuildStreamModel`
  - `SettingsStore`
- CI execution and workflow logic, though the shell is registered against:
  - `.github/workflows/crafted-ci.yml`
- Telemetry production and transport, though the shell is associated with:
  - `logs/telemetry.jsonl`
- Repository write-path validation and root allowlisting logic
- Failure-recovery orchestration and retry policy
- GitHub operations tooling

### Repository boundary considerations

For this subsystem’s source placement, CamelCase roots are explicitly relevant. The lessons learned document identifies CamelCase roots such as `CraftedApp` as valid project roots and requires smart root detection matching:

- `^[A-Za-z][A-Za-z0-9_-]*$`

This matters operationally because prior failures occurred when new Swift targets under CamelCase roots were rejected by path security guards.

## Data Flow

### Application startup flow

1. The process enters through `@main struct CraftedApp: App`.
2. SwiftUI evaluates `body`.
3. `WindowGroup` is created as the primary scene.
4. `RootView()` is instantiated.
5. Shared singleton state is injected into the main scene:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
6. Window configuration is applied:
   - hidden title bar
   - default size `1280 × 800`
   - content-minimum-size resizability behavior
7. A separate `Settings` scene is registered.
8. `SettingsView()` is instantiated for the settings window.
9. `SettingsStore.shared` is injected into the settings scene.

### Environment object distribution

Main scene object graph:

- `RootView`
  - receives `AppState.shared`
  - receives `BuildStreamModel.shared`
  - receives `SettingsStore.shared`

Settings scene object graph:

- `SettingsView`
  - receives `SettingsStore.shared`

### Operational metadata flow

From the health registry schema, the app-shell subsystem is associated with:

- repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- telemetry endpoint: `logs/telemetry.jsonl`

These identifiers define operational integration points for the subsystem but do not alter the SwiftUI scene composition itself.

## Key Invariants

### Scene composition invariants

- `CraftedApp` is the sole application entrypoint for this subsystem.
- The main user-facing scene is a `WindowGroup` rooted at `RootView()`.
- The settings experience is a separate `Settings` scene rooted at `SettingsView()`.
- `SettingsStore.shared` must be available in both the main scene and the settings scene.
- `AppState.shared` and `BuildStreamModel.shared` are injected into the main scene.

### Window invariants

- Main window style uses `.hiddenTitleBar`.
- Default window size is `1280 × 800`.
- Minimum window size is `1024 × 680`.
- Maximum size is unconstrained.
- Resizability is governed by `.windowResizability(.contentMinSize)`.

### Security and reliability invariants from Forge context

These apply to the broader operating context in which this subsystem is built and maintained:

- Fail closed on auth, crypto, and identity errors; never degrade silently
- No silent failure paths; every error must surface with context
- Secrets must never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- Generated code is never executed by the agent

### Repository/path invariants

- Writes must be constrained to allowed repository roots.
- CamelCase roots such as `CraftedApp` must be treated as valid roots via smart root detection rather than a static exhaustive allowlist.

This invariant is directly tied to a recorded failure pattern:

- `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection (v38.180)`

## Failure Modes

### 1. Missing allowed-root recognition for CamelCase target directories

Observed failure pattern:

- `Path rejected: CraftedAppShell/`
- Root cause: new Swift target not present in `_ALLOWED_ROOTS`
- Class: `Pipeline`
- Fix: CamelCase root auto-detection

Impact on this subsystem:

- Source changes for `CraftedApp`-related targets may be rejected or fail silently if path validation does not recognize CamelCase roots.

Required mitigation from source documents:

- Allow roots matching `^[A-Za-z][A-Za-z0-9_-]*$`
- Do not rely solely on an exhaustive static allowlist

### 2. Silent or context-free failure is unacceptable

Forge invariants explicitly prohibit:

- silent failure paths
- degradation without surfacing context

Impact on this subsystem:

- startup, scene wiring, and configuration errors must not be swallowed
- operational tooling around this subsystem must surface errors with context

### 3. Biometric-gated settings mismatch

The scene architecture document labels the settings window as:

- “Settings window — separate scene, biometric-gated”

Impact on this subsystem:

- the settings scene is expected to remain a distinct boundary
- any implementation that bypasses or collapses this boundary would violate documented architecture intent

### 4. Pipeline-level retry and escalation ceilings

Relevant operational constraints from Forge context:

- never retry indefinitely
- max `20` local attempts, then move on

Related failure index entry:

- `Self-correction 20-pass cap`

Impact on this subsystem:

- repeated automated repair attempts involving the shell must respect bounded retry behavior

## Dependencies

### Runtime/UI dependencies

Declared directly by the scene architecture:

- SwiftUI `App` lifecycle
- `WindowGroup`
- `Settings`
- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Operational dependencies

From the health registry schema:

- Repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`
- Languages: `swift`, `python`

### Governance and platform dependencies

From Forge architecture context:

- GitHub operations must go through `GitHubTool`
- Paths must be validated before any write
- External inputs are treated as untrusted and validated
- Error handling and escalation are governed by centralized failure-handling rules

These are not UI-level dependencies of `CraftedApp` code itself, but they are mandatory subsystem operating constraints.