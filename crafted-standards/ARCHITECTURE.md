# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry subsystem implemented as the `@main` SwiftUI `App`. It defines the top-level scene architecture for the application shell and is responsible for:

- Launching the primary application window via a `WindowGroup`
- Hosting `RootView` as the main UI root
- Injecting shared application-wide state into the main scene:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Defining primary window presentation constraints:
  - hidden title bar
  - default size `1280 × 800`
  - content minimum size enforcement
- Exposing a separate `Settings` scene
- Wiring the settings scene to `SettingsStore.shared`

The subsystem is part of the application shell identified in the health registry as:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

The implementation language context for the shell is registered as:

- `swift`
- `python`

## Component Boundaries

### In Scope

`CraftedApp` owns only top-level app and scene composition concerns:

- SwiftUI `App` entrypoint
- Main window scene declaration
- Settings window scene declaration
- Environment object injection into scenes
- Window style and sizing policy

Concrete scene composition from the TRD:

- Main scene:
  - `WindowGroup`
  - `RootView`
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Settings scene:
  - `Settings`
  - `SettingsView`
  - `SettingsStore.shared`

### Out of Scope

This subsystem does not own:

- Internal behavior of `RootView`
- Internal behavior of `SettingsView`
- State model internals for `AppState`, `BuildStreamModel`, or `SettingsStore`
- CI execution
- telemetry emission logic
- self-healing orchestration
- repository write validation logic
- GitHub API operations
- authentication, crypto, or identity implementation details

Those concerns are governed elsewhere by repository-wide or adjacent subsystem rules.

### Repository Boundary Notes

The repository permits CamelCase roots through smart root detection using the pattern:

- `^[A-Za-z][A-Za-z0-9_-]*$`

This matters for this subsystem because Swift/Xcode targets such as `CraftedApp` are expected to exist at CamelCase roots and must not be rejected by path security guards. A recorded failure pattern explicitly identifies rejection of `CraftedAppShell/` when new Swift targets were not included in allowed roots; the corrective invariant is CamelCase root auto-detection.

## Data Flow

### Application Startup Flow

1. Process enters `CraftedApp` as the `@main` application.
2. `body` constructs the primary `WindowGroup`.
3. `RootView` is instantiated.
4. Shared singleton state is injected into `RootView`:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
5. Window configuration is applied:
   - `.windowStyle(.hiddenTitleBar)`
   - `.defaultSize(width: 1280, height: 800)`
   - `.windowResizability(.contentMinSize)`
6. A separate `Settings` scene is registered.
7. `SettingsView` is instantiated for the settings scene.
8. `SettingsStore.shared` is injected into `SettingsView`.

### Settings Data Flow

The only explicitly declared shared dependency for the settings scene is:

- `SettingsStore.shared`

This establishes `SettingsStore` as the configuration/state source shared between the main application scene and the settings scene.

### Operational Metadata Flow

From the health registry, the shell is associated with:

- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`

These are registry-level integration points for the shell, but the TRDs do not assign direct ownership of writing CI or telemetry data to `CraftedApp` itself.

## Key Invariants

### Scene Composition Invariants

- `CraftedApp` is the sole app entrypoint for this subsystem.
- The main scene must be a `WindowGroup`.
- The root content of the main scene must be `RootView()`.
- The main scene must inject:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- A separate `Settings` scene must exist.
- The settings scene must host `SettingsView()`.
- The settings scene must inject `SettingsStore.shared`.

### Windowing Invariants

- Window style must be `.hiddenTitleBar`.
- Default window size must be `1280 × 800`.
- Window resizability must be `.contentMinSize`.
- Minimum window size is `1024 × 680`.
- Maximum window size is unconstrained.

### Security and Reliability Invariants

From Forge architecture context, the subsystem operates under repository-wide invariants:

- Fail closed on auth, crypto, and identity errors; never degrade silently.
- No silent failure paths; every error must surface with context.
- Secrets must never appear in logs, error messages, or generated code.
- All external input is untrusted and validated.
- Generated code is never executed by the agent.
- Gates wait indefinitely for operator input; no automatic timeout-based bypass.

### Repository Write/Path Invariants

- Paths must be validated before any write.
- CamelCase roots such as `CraftedApp` must be accepted by smart root detection using `^[A-Za-z][A-Za-z0-9_-]*$`.
- Dot-prefixed roots like `.github` require explicit allowlisting.

These path invariants are critical to the shell because its target and related Swift/Xcode roots may otherwise be rejected by path security guards.

## Failure Modes

### Scene Wiring Failures

Potential failures within this subsystem’s boundary are structural misconfigurations of app composition, including:

- Missing `RootView` in the main `WindowGroup`
- Missing required environment object injection for the main scene
- Missing `Settings` scene
- Missing `SettingsStore.shared` injection into `SettingsView`
- Incorrect window style or sizing policy

Because repository policy forbids silent failures, these conditions must surface with context rather than degrading behavior silently.

### Root Directory Rejection

Documented failure pattern:

- `Path rejected: CraftedAppShell/`
- Root cause: new Swift target not in `_ALLOWED_ROOTS`
- Class: `Pipeline`
- Fix: CamelCase root auto-detection

This is an integration failure at the repository/pipeline boundary that directly affects the subsystem’s ability to be created, modified, or committed when housed in CamelCase roots.

### Attempt Exhaustion in Self-Healing Context

A documented failure pattern exists for retry limits:

- `Self-correction 20-pass cap`
- Class: `Pipeline`

Repository behavior also states:

- Never retry indefinitely
- Maximum 20 local attempts, then move on

This is not owned by `CraftedApp`, but it constrains automated recovery affecting changes to this subsystem.

### CI/Pipeline Guard Failures

Relevant adjacent failure patterns include:

- `UnboundLocalError: ci_result` when docs PRs skip CI gate
- `AGENTS.md merge conflict` due to branch-protection bypass

These are not scene-architecture failures, but they define operational failure classes that can block delivery of `CraftedApp` changes.

## Dependencies

### Direct SwiftUI Composition Dependencies

Declared directly in the scene architecture:

- `SwiftUI App` lifecycle
- `WindowGroup`
- `Settings`
- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Registered Operational Dependencies

From the health registry schema for the shell:

- Repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`

### Repository-Level Platform Dependencies

Applicable constraints from Forge context:

- All GitHub operations go through `GitHubTool`
- Path validation is required before any write
- Failure handling uses typed strategy selection by failure class and attempt count
- Polling behavior uses ETag caching
- Backoff behavior applies for `403` and `429`
- Context trimming and CI log truncation are automatic platform behaviors

These are environmental dependencies and constraints around the subsystem, not logic implemented by `CraftedApp` itself.