# Architecture - CraftedApp

## What This Subsystem Does

`CraftedApp` is the macOS application entry-point and scene shell for the Crafted application.

It is defined as the `@main` `App` and is responsible for:

- constructing the primary application scene,
- attaching shared environment state required by the main UI,
- defining window presentation behavior for the main window, and
- exposing a separate Settings scene.

The subsystem creates:

1. a main `WindowGroup` scene hosting `RootView`, and
2. a distinct `Settings` scene hosting `SettingsView`.

Within the main scene, `CraftedApp` injects the following shared singleton-backed environment objects:

- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

Within the settings scene, it injects:

- `SettingsStore.shared`

The main application window uses:

- `.windowStyle(.hiddenTitleBar)`
- `.defaultSize(width: 1280, height: 800)`
- `.windowResizability(.contentMinSize)`

Documented window sizing constraints are:

- minimum: `1024 × 680`
- maximum: unconstrained / resizable

The settings window is explicitly described as a separate scene and biometric-gated.

## Component Boundaries

### In Scope

`CraftedApp` owns only application-shell concerns at the scene level:

- SwiftUI `App` entry-point declaration
- scene composition
- root view selection
- environment object wiring into scenes
- main window style and default sizing
- settings scene registration

### Out of Scope

The subsystem does not define or implement:

- `RootView` internals
- `SettingsView` internals
- business logic inside `AppState`
- build-stream processing inside `BuildStreamModel`
- settings persistence or storage internals inside `SettingsStore`
- biometric implementation details for the settings gate
- CI behavior, telemetry writing, or health-registry mutation
- repository path validation logic

### Repository / Target Boundary

The self-healing registry identifies the related shell subsystem as:

- `target_id`: `crafted-app-shell`
- `subsystem`: `CraftedAppShell`

A recorded pipeline failure pattern shows `CraftedAppShell/` as a Swift target root that must be accepted by root validation. The repository rule for allowed roots requires smart root detection for CamelCase roots matching:

- `^[A-Za-z][A-Za-z0-9_-]*$`

This establishes a repository boundary relevant to this subsystem: files for the Crafted application shell may live under CamelCase roots and must not be rejected by path guards solely because the root is not in a static lowercase allowlist.

## Data Flow

### Application Startup

1. The process enters through `@main struct CraftedApp: App`.
2. SwiftUI evaluates `body`.
3. `CraftedApp` instantiates the main `WindowGroup`.
4. `RootView()` is mounted as the main scene content.
5. Shared environment objects are injected into the main scene:
   - `AppState.shared`
   - `BuildStreamModel.shared`
   - `SettingsStore.shared`
6. Window presentation rules are applied:
   - hidden title bar
   - default size `1280 × 800`
   - content-min-size resizability

### Settings Flow

1. The application declares a separate `Settings` scene.
2. `SettingsView()` is mounted in that scene.
3. `SettingsStore.shared` is injected into the settings scene.
4. Access to the settings window is biometric-gated, per the TRD.

### Operational Metadata Association

The shell subsystem is associated in the health registry with:

- repository: `todd-yousource-ai/Dev-Agent`
- languages: `swift`, `python`
- CI workflow: `.github/workflows/crafted-ci.yml`
- telemetry endpoint: `logs/telemetry.jsonl`

This metadata describes operational integration around the shell subsystem, but not runtime UI data exchange inside `CraftedApp` itself.

## Key Invariants

The following invariants are directly supported by the provided TRDs and repository architecture context.

### Scene and Injection Invariants

- The main application scene must host `RootView`.
- `RootView` must receive:
  - `AppState.shared`
  - `BuildStreamModel.shared`
  - `SettingsStore.shared`
- The settings scene must host `SettingsView`.
- `SettingsView` must receive `SettingsStore.shared`.
- The settings scene remains separate from the main `WindowGroup`.

### Window Invariants

- Main window style uses `hiddenTitleBar`.
- Main window default size is `1280 × 800`.
- Main window minimum content size must respect the documented minimum of `1024 × 680`.
- Maximum window size is unconstrained.

### Security and Trust Invariants

From Forge architecture context, the subsystem operates under repository-wide invariants:

- fail closed on auth, crypto, and identity errors,
- no silent failure paths,
- secrets never appear in logs, error messages, or generated code,
- all external input is untrusted and validated,
- generated code is never executed by the agent.

For `CraftedApp`, the most directly relevant explicit security invariant in the TRD set is:

- the Settings window is biometric-gated.

### Repository Path Invariants

- CamelCase Swift/Xcode roots are valid project roots.
- Root validation must allow roots matching `^[A-Za-z][A-Za-z0-9_-]*$`.
- Dot-prefixed roots such as `.github` require explicit allowlisting.
- Writes outside allowed roots are invalid.

These path invariants matter to `CraftedApp` because the shell target has already produced a recorded failure when its CamelCase root was not recognized.

## Failure Modes

### 1. Missing Allowed Root for CraftedApp Shell Files

Recorded failure pattern:

- `Path rejected: CraftedAppShell/`
- root cause: new Swift target not in `_ALLOWED_ROOTS`
- class: `Pipeline`
- fix: CamelCase root auto-detection (`v38.180`)

Impact on this subsystem:

- shell files for the Crafted app target may fail to commit or update,
- changes can be silently blocked or rejected by path security guards if root detection is too strict.

Expected enforcement:

- use smart root detection rather than an exhaustive static root allowlist.

### 2. Silent or Context-Free Error Handling

Repository-wide architecture explicitly forbids silent failure paths. For this subsystem, failures in scene setup, settings access control, or shell wiring must surface with context rather than degrade silently.

### 3. Incorrect Environment Wiring

If the main or settings scene does not receive the required shared environment objects, dependent views will not have the application state they are architected to consume.

At minimum, wiring errors would affect:

- global app state access,
- build stream state access,
- settings state access.

### 4. Settings Access Control Regression

The settings window is specified as biometric-gated. Any implementation that exposes settings without that gate violates the subsystem contract.

### 5. Window Configuration Drift

Changes that alter:

- hidden title bar behavior,
- default size `1280 × 800`,
- minimum size expectations,
- separate settings-scene registration,

constitute shell-level architectural drift from the TRD-defined scene contract.

### 6. Pipeline Attempt Exhaustion

From the failure-handling architecture:

- never retry indefinitely,
- maximum 20 local attempts, then move on.

This affects remediation around shell-related failures during automated repair or generation workflows.

## Dependencies

### Runtime UI Dependencies

`CraftedApp` directly depends on:

- `SwiftUI App` scene model
- `RootView`
- `SettingsView`
- `AppState.shared`
- `BuildStreamModel.shared`
- `SettingsStore.shared`

### Operational Dependencies

The associated shell subsystem is linked to:

- CI workflow: `.github/workflows/crafted-ci.yml`
- telemetry endpoint: `logs/telemetry.jsonl`

### Repository / Platform Dependencies

The subsystem depends on repository behaviors and constraints defined in the architecture context:

- all GitHub operations go through `GitHubTool`,
- paths are validated before any write,
- CamelCase target roots must be accepted by path validation,
- external input is treated as untrusted and validated.

### Language Boundary

Health registry metadata declares the shell subsystem language set as:

- `swift`
- `python`

For `CraftedApp` specifically, the scene shell definition provided in the TRD is Swift-based. Python appears as part of the broader subsystem operational context rather than the SwiftUI scene declaration itself.