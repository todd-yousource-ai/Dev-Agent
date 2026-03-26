# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry subsystem for the Crafted application shell.

It defines the top-level SwiftUI scene configuration:

- Declares the application entry point with `@main struct CraftedApp: App`
- Creates the primary app window through a `WindowGroup`
- Installs shared application models into the SwiftUI environment:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- Configures primary window behavior:
  - `.windowStyle(.hiddenTitleBar)`
  - `.defaultSize(width: 1280, height: 800)`
  - `.windowResizability(.contentMinSize)`
- Declares a separate `Settings` scene
- Applies `SettingsStore.shared` to the settings UI environment

This subsystem is the application-shell boundary that wires global state into the UI scene graph and establishes the top-level windowing model for the macOS app.

Related subsystem identity from the health registry associates the shell with:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

## Component Boundaries

### In Scope

The subsystem owns:

- Application bootstrap via the SwiftUI `App` protocol
- Scene declaration for:
  - the main application window
  - the settings window
- Injection of shared singleton-backed environment objects into scenes
- Window-level presentation configuration for the main scene

### Out of Scope

The subsystem does not define:

- Internal behavior of `RootView`
- Internal behavior of `SettingsView`
- The data model internals of:
  - `AppState`
  - `BuildStreamModel`
  - `SettingsStore`
- CI workflow behavior, except registry linkage to `.github/workflows/crafted-ci.yml`
- Telemetry implementation, except registry linkage to `logs/telemetry.jsonl`
- Any direct GitHub operations, document processing, code generation, or self-healing logic

### Scene Boundary

The main scene and settings scene are intentionally separate:

- `WindowGroup` hosts `RootView` for the primary application experience
- `Settings` hosts `SettingsView` for settings management
- The settings window is specified as a separate scene and is described as biometric-gated in the TRD

### Repository Boundary

The subsystem exists within a repository structure that must permit CamelCase roots. `CraftedApp` is explicitly consistent with the smart root-detection rule allowing roots matching:

```regex
^[A-Za-z][A-Za-z0-9_-]*$
```

This avoids path rejection for Swift/Xcode-style roots such as `CraftedApp`, `CraftedTests`, and `ForgeAgent`.

## Data Flow

### Application Startup Flow

1. The process enters through `@main struct CraftedApp: App`
2. SwiftUI evaluates `body`
3. `WindowGroup` creates the main application scene
4. `RootView()` is instantiated
5. Shared models are injected into `RootView` via environment objects:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
6. Window configuration is applied:
   - hidden title bar
   - default size `1280×800`
   - content-min-size resizability
7. A separate `Settings` scene is registered
8. `SettingsView()` is instantiated when the settings scene is opened
9. `SettingsStore.shared` is injected into the settings scene

### Environment Object Distribution

The main scene receives three shared objects:

- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

The settings scene receives one shared object:

- `SettingsStore.shared`

This establishes `SettingsStore.shared` as the shared configuration/state object spanning both scenes, while `AppState.shared` and `BuildStreamModel.shared` are only guaranteed at the main scene boundary.

### Registry-Level Operational Flow

From the health registry schema, the shell is connected operationally to:

- repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- telemetry endpoint: `logs/telemetry.jsonl`

These are operational integration points for the subsystem but are not implemented by the scene declaration itself.

## Key Invariants

### Scene Construction Invariants

- The application entry point is `CraftedApp`
- The primary UI scene is always created via `WindowGroup`
- The settings UI is always exposed as a separate `Settings` scene
- `RootView` must receive:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- `SettingsView` must receive:
  - `SettingsStore.shared`

### Windowing Invariants

- Main window style is `.hiddenTitleBar`
- Main window default size is `1280 × 800`
- Main window resizability is `.contentMinSize`
- Minimum window size is `1024 × 680`
- Maximum window size is unconstrained

### Security / Access Invariants

Derived from Forge architecture context:

- Fail closed on auth, crypto, and identity errors
- No silent failure paths; every error must surface with context
- Secrets must never appear in logs, error messages, or generated code
- All external input is untrusted and validated
- Generated code is never executed by the agent

Applied to this subsystem boundary, these invariants mean the app shell must not introduce silent degradation or unsafe handling at the scene/bootstrap layer when interacting with broader platform services.

### Repository Path Invariants

- `CraftedApp` must remain under an allowed repository root
- CamelCase roots are valid and must be accepted by path validation
- Path validation must not reject `CraftedAppShell/`-style roots due to stale explicit allowlists

This is reinforced by the recorded failure pattern:

- `Path rejected: CraftedAppShell/ | New Swift target not in _ALLOWED_ROOTS | Pipeline | CamelCase root auto-detection (v38.180)`

## Failure Modes

### Scene Wiring Failures

- Missing environment object injection for `RootView`
  - Effect: main scene cannot rely on expected shared state providers
- Missing `SettingsStore.shared` injection for `SettingsView`
  - Effect: settings scene loses access to shared settings state
- Misconfigured separate settings scene
  - Effect: settings behavior diverges from the intended dedicated scene model, including the documented biometric-gated design

### Window Configuration Failures

- Incorrect default size
  - Effect: startup window geometry does not match shell specification
- Incorrect min-size enforcement
  - Effect: UI may resize below supported content constraints
- Missing hidden title bar style
  - Effect: shell presentation no longer matches the defined application chrome

### Repository / Pipeline Failures

- Path rejection for CamelCase shell targets
  - Known pattern: `Path rejected: CraftedAppShell/`
  - Root cause: new Swift target not present in `_ALLOWED_ROOTS`
  - Fix captured in TRD: CamelCase root auto-detection

This is the primary documented subsystem-adjacent failure mode tied to `CraftedAppShell`.

### General Operational Failures from Forge Context

If this subsystem participates in broader automated build or integration flows, the following handling rules apply at system level:

- No indefinite retry loops
- Maximum 20 local attempts before moving on
- 403 responses use exponential backoff
- 429 responses respect `Retry-After`
- CI output is truncated automatically
- Context is auto-trimmed automatically

These are operational constraints around the subsystem rather than logic implemented in the scene shell itself.

## Dependencies

### Runtime/UI Dependencies

Directly referenced by the scene architecture:

- SwiftUI `App` scene model
- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Operational Dependencies

From the health registry schema:

- Repository: `todd-yousource-ai/Dev-Agent`
- CI workflow: `.github/workflows/crafted-ci.yml`
- Telemetry endpoint: `logs/telemetry.jsonl`

### Repository Infrastructure Dependencies

From allowed-root and pipeline lessons learned:

- Path validation must support standard roots
- Path validation must explicitly support dot-prefixed roots such as `.github`
- Path validation must support CamelCase roots via regex-based smart root detection

Relevant rule:

```regex
^[A-Za-z][A-Za-z0-9_-]*$
```

This dependency is important for maintaining the shell target and related Swift/Xcode project roots without pipeline rejection.