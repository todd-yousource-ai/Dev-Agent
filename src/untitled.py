// Project.swift
// Tuist manifest defining the MacConsensusDevAgent macOS app target.
// Allocation: Single project descriptor — no runtime allocation, build-time only.

import ProjectDescription

let project = Project(
    name: "MacConsensusDevAgent",
    organizationName: "Forge",
    settings: .settings(
        base: [
            // Deny-by-default: harden all builds
            "ENABLE_HARDENED_RUNTIME": "YES",
            "ENABLE_APP_SANDBOX": "YES",
            // No network by default — fail closed on entitlements
            "com.apple.security.network.client": "NO",
            // Strip debug symbols in release
            "SWIFT_COMPILATION_MODE": "wholemodule",
        ],
        configurations: [
            .debug(name: "Debug", settings: [
                "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG",
            ]),
            .release(name: "Release", settings: [
                "SWIFT_OPTIMIZATION_LEVEL": "-O",
            ]),
        ]
    ),
    targets: [
        .target(
            name: "MacConsensusDevAgent",
            destinations: .macOS,
            product: .app,
            bundleId: "com.forge.MacConsensusDevAgent",
            deploymentTargets: .macOS("14.0"),
            infoPlist: .extendingDefault(with: [
                "CFBundleDisplayName": "Mac Consensus Dev Agent",
                "CFBundleShortVersionString": "0.1.0",
                "CFBundleVersion": "1",
                "LSMinimumSystemVersion": "14.0",
                // Security: disable outbound URL schemes by default
                "LSApplicationQueriesSchemes": .array([]),
                // Accessibility: declare no document types until explicitly needed
                "CFBundleDocumentTypes": .array([]),
            ]),
            sources: ["App/**/*.swift"],
            resources: ["App/Resources/**"],
            entitlements: .file(path: "App/MacConsensusDevAgent.entitlements"),
            dependencies: []
        ),
        .target(
            name: "MacConsensusDevAgentTests",
            destinations: .macOS,
            product: .unitTests,
            bundleId: "com.forge.MacConsensusDevAgent.Tests",
            deploymentTargets: .macOS("14.0"),
            sources: ["Tests/**/*.swift"],
            dependencies: [
                .target(name: "MacConsensusDevAgent"),
            ]
        ),
    ]
)

// App/MacConsensusDevAgent.entitlements
// <?xml version="1.0" encoding="UTF-8"?>
// <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
// <plist version="1.0">
// <dict>
//     <key>com.apple.security.app-sandbox</key>
//     <true/>
//     <key>com.apple.security.network.client</key>
//     <false/>
//     <key>com.apple.security.files.user-selected.read-only</key>
//     <false/>
// </dict>
// </plist>

// App/MacConsensusDevAgentApp.swift
// @main entry point for the MacConsensusDevAgent application.
// Security assumption: This is the composition root. No subsystem is instantiated
// until explicitly wired here. Fail closed — if AppState cannot initialize,
// the app presents an error and does not proceed to any functional UI.
// Allocation: Single AppState instance held as @StateObject — minimal footprint.

import SwiftUI
import os

/// OS logger for application-level lifecycle events. No secrets in log output.
private let appLogger = Logger(
    subsystem: "com.forge.MacConsensusDevAgent",
    category: "App"
)

/// The primary application entry point for Mac Consensus Dev Agent.
/// Hosts the single WindowGroup and owns the root AppState lifecycle.
@main
struct MacConsensusDevAgentApp: App {
    /// Root application state — the single shared mutable state container.
    /// Allocated once at launch; no lazy caches or buffers.
    @StateObject private var appState = AppState()

    init() {
        appLogger.info("MacConsensusDevAgentApp composition root initializing")
    }

    /// Application body defining the window scene.
    var body: some Scene {
        WindowGroup {
            LaunchView()
                .environmentObject(appState)
                .frame(
                    minWidth: 800,
                    minHeight: 600
                )
        }
        .windowStyle(.titleBar)
        .defaultSize(width: 1024, height: 768)
    }
}

// App/Models/AppState.swift
// Root observable state container for the application.
// Security: All state mutations are MainActor-isolated. No shared mutable state
// escapes this actor boundary. External input is never stored without validation.
// Allocation: Flat value properties only — no caches, no buffers. OI-13 compliant.

import SwiftUI
import os

/// Application lifecycle phase enumeration.
/// Represents the current high-level state of the application shell.
enum AppLifecyclePhase: String, Sendable {
    /// Application is initializing subsystems.
    case launching
    /// Application is ready for user interaction.
    case ready
    /// Application encountered a fatal initialization error.
    case failed
}

/// Root application state shared via @EnvironmentObject.
/// All mutations occur on MainActor — no concurrent writes possible.
@MainActor
final class AppState: ObservableObject {
    // MARK: - Published State

    /// Current lifecycle phase of the application.
    /// Allocation: Single enum value — 1 byte.
    @Published private(set) var lifecyclePhase: AppLifecyclePhase = .launching

    /// Human-readable error message if lifecyclePhase == .failed.
    /// Allocation: Optional String — nil unless error occurs.
    @Published private(set) var launchErrorMessage: String?

    // MARK: - Private

    /// OS logger for structured diagnostics. No secrets in log messages.
    private let logger = Logger(
        subsystem: "com.forge.MacConsensusDevAgent",
        category: "AppState"
    )

    /// Tracks whether the launch sequence has been initiated.
    /// Prevents double-launch if init is called in test vs. production contexts.
    private var launchSequenceStarted = false

    // MARK: - Initialization

    /// Initializes application state and triggers the launch sequence.
    init() {
        logger.info("AppState initializing — lifecycle phase: launching")
        // Launch sequence is deferred to an async task to avoid blocking init.
        // Subsystem initialization will be wired here in future PRs.
        startLaunchSequenceIfNeeded()
    }

    // MARK: - Launch Sequence

    /// Starts the launch sequence exactly once.
    /// Idempotent — safe to call from both init and test harnesses.
    func startLaunchSequenceIfNeeded() {
        guard !launchSequenceStarted else {
            logger.debug("Launch sequence already started — skipping duplicate invocation")
            return
        }
        launchSequenceStarted = true
        Task { @MainActor [weak self] in
            await self?.performLaunchSequence()
        }
    }

    /// Executes the ordered launch sequence per TRD-1 §7.3.
    /// Fails closed: any error transitions to .failed phase.
    private func performLaunchSequence() async {
        logger.info("Launch sequence started")

        // Phase 1: Validate runtime environment
        guard validateRuntimeEnvironment() else {
            transitionToFailed("Runtime environment validation failed. macOS 14.0+ required.")
            return
        }

        // All checks passed — transition to ready.
        lifecyclePhase = .ready
        logger.info("Launch sequence completed — lifecycle phase: ready")
    }

    /// Validates that the runtime environment meets minimum requirements.
    /// Returns false if the environment is unsupported — fail closed.
    private func validateRuntimeEnvironment() -> Bool {
        // Verify we are running on macOS 14.0+
        // This is a defense-in-depth check; deployment target already enforces this.
        if #available(macOS 14.0, *) {
            logger.debug("Runtime environment validation passed: macOS 14.0+ confirmed")
            return true
        } else {
            logger.error("Runtime environment check failed: macOS version below 14.0")
            return false
        }
    }

    /// Transitions the app to the failed state with a contextual error message.
    /// All failures surface with explicit context — no silent failure paths.
    private func transitionToFailed(_ message: String) {
        launchErrorMessage = message
        lifecyclePhase = .failed
        // Privacy: error message is public-level — no secrets included.
        logger.error("Launch sequence failed: \(message, privacy: .public)")
    }
}

// App/Views/LaunchView.swift
// Minimal launch view displaying application identity and lifecycle status.
// Security: No external input rendered. Bundle values are validated before display.
// Allocation: Two computed string properties derived from Bundle — no stored buffers.

import SwiftUI
import os

/// OS logger for view-level lifecycle and rendering events.
private let viewLogger = Logger(
    subsystem: "com.forge.MacConsensusDevAgent",
    category: "LaunchView"
)

/// The initial view displayed at application launch.
/// Shows application name, bundle version, and current lifecycle status.
/// Transitions to the main interface once AppState reaches .ready phase.
struct LaunchView: View {
    /// Shared application state injected from the composition root.
    @EnvironmentObject private var appState: AppState

    /// Bundle display name, validated with a fallback.
    /// Allocation: Computed on access — no stored cache.
    private var appDisplayName: String {
        // Validate bundle value — never trust raw external input.
        guard let name = Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String,
              !name.isEmpty else {
            return "Mac Consensus Dev Agent"
        }
        return name
    }

    /// Bundle version string, validated with a fallback.
    /// Allocation: Computed on access — no stored cache.
    private var appVersionString: String {
        guard let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String,
              !version.isEmpty else {
            return "0.0.0"
        }
        guard let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String,
              !build.isEmpty else {
            return "v\(version)"
        }
        return "v\(version) (\(build))"
    }

    var body: some View {
        Group {
            switch appState.lifecyclePhase {
            case .launching:
                launchingContent
            case .ready:
                readyContent
                    .onAppear {
                        viewLogger.info("LaunchView presenting ready state")
                    }
            case .failed:
                failedContent
                    .onAppear {
                        viewLogger.error("LaunchView presenting failed state")
                    }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.windowBackgroundColor))
    }

    // MARK: - Phase Content Views

    /// Content displayed during the launching phase.
    private var launchingContent: some View {
        VStack(spacing: 16) {
            ProgressView()
                .controlSize(.large)
                .accessibilityLabel(LocalizedStringKey("launch.progress.label"))
                .accessibilityIdentifier("launch_progress_indicator")

            Text(LocalizedStringKey("launch.status.initializing"))
                .font(.headline)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("launch_status_text")
        }
    }

    /// Content displayed when the application is ready.
    private var readyContent: some View {
        VStack(spacing: 12) {
            Image(systemName: "checkmark.shield.fill")
                .font(.system(size: 48))
                .foregroundStyle(.green)
                .accessibilityLabel(LocalizedStringKey("launch.ready.icon.label"))
                .accessibilityIdentifier("launch_ready_icon")

            Text(appDisplayName)
                .font(.largeTitle)
                .fontWeight(.semibold)
                .accessibilityIdentifier("app_display_name")

            Text(appVersionString)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("app_version_label")

            Text(LocalizedStringKey("launch.status.ready"))
                .font(.body)
                .foregroundStyle(.secondary)
                .padding(.top, 4)
                .accessibilityIdentifier("launch_ready_status_text")
        }
    }

    /// Content displayed when the launch sequence has failed.
    /// Fail closed: shows explicit error context, no retry without user action.
    private var failedContent: some View {
        VStack(spacing: 16) {
            Image(systemName: "xmark.octagon.fill")
                .font(.system(size: 48))
                .foregroundStyle(.red)
                .accessibilityLabel(LocalizedStringKey("launch.failed.icon.label"))
                .accessibilityIdentifier("launch_failed_icon")

            Text(LocalizedStringKey("launch.status.failed"))
                .font(.headline)
                .foregroundStyle(.primary)
                .accessibilityIdentifier("launch_failed_title")

            if let errorMessage = appState.launchErrorMessage {
                Text(errorMessage)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
                    .accessibilityIdentifier("launch_error_message")
            }
        }
    }
}

// App/Views/LaunchView+Previews.swift
// SwiftUI preview provider for LaunchView across all lifecycle phases.
// Allocation: Preview-only — stripped from release builds.

#if DEBUG
import SwiftUI

#Preview("Launching") {
    LaunchView()
        .environmentObject(AppState())
        .frame(width: 800, height: 600)
}
#endif

// App/Resources/Localizable.xcstrings
// Note: In a real Xcode project this would be a .xcstrings catalog file.
// Providing the content as a reference for the localization keys used in views.
// All user-visible strings are localized — no hardcoded strings per Forge standards.
//
// Keys:
//   "launch.progress.label" = "Application is loading"
//   "launch.status.initializing" = "Initializing…"
//   "launch.status.ready" = "Application ready"
//   "launch.status.failed" = "Launch Failed"
//   "launch.ready.icon.label" = "Application ready checkmark"
//   "launch.failed.icon.label" = "Application launch failed"

// App/Errors/ForgeError.swift
// Base error type for Forge application errors.
// Security: Error descriptions never contain secrets, tokens, or PII.
// All errors conform to LocalizedError with explicit context per Forge standards.
// Allocation: Enum with associated String values — minimal heap allocation.

import Foundation

/// Base error type for all Forge application domain errors.
/// Conforms to LocalizedError to surface meaningful diagnostics.
/// Security invariant: No error description may contain secrets, keys, or PII.
enum ForgeError: LocalizedError, Sendable {
    /// A required runtime precondition was not met.
    case runtimePreconditionFailed(context: String)

    /// A subsystem failed to initialize.
    case subsystemInitializationFailed(subsystem: String, reason: String)

    /// An operation was attempted in an invalid lifecycle phase.
    case invalidLifecyclePhase(expected: String, actual: String)

    /// Human-readable error description. No secrets — safe for logging and UI.
    var errorDescription: String? {
        switch self {
        case .runtimePreconditionFailed(let context):
            return "Runtime precondition failed: \(context)"
        case .subsystemInitialization