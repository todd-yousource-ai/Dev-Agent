// Package.swift
// swift-tools-version: 5.9
// SPDX-License-Identifier: Proprietary
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - All modules compile with strict concurrency checking to surface data races at build time.
// - KeychainKit is a leaf module with no internal dependencies — minimizes attack surface for secrets handling.
// - No circular dependencies permitted; the graph is a DAG enforced by SPM resolution.
// - No third-party dependencies — all functionality uses system frameworks only.
// - macOS 13.0 minimum ensures availability of modern Swift concurrency runtime.
//
// Memory budget (OI-13): Package.swift itself is declarative; no runtime allocations.
// Each placeholder source file contains only the minimum required for compilation.

import PackageDescription

/// Platform constraint: macOS 13.0+ required for Swift 5.9 concurrency features,
/// LocalAuthentication API stability, and XPC modern protocol support.
let platformVersion: SupportedPlatform = .macOS(.v13)

/// Strict concurrency checking enabled on every target to catch data races at compile time.
/// This is a Forge security requirement — no silent concurrency bugs in production.
let strictConcurrencySettings: [SwiftSetting] = [
    .enableExperimentalFeature("StrictConcurrency")
]

let package = Package(
    name: "ConsensusDevAgent",
    platforms: [
        platformVersion
    ],
    products: [
        // MARK: - Library Products
        // Each module is exposed as a static library for explicit linking control.
        // No dynamic libraries — reduces attack surface and startup overhead.
        .library(name: "AppShell", targets: ["AppShell"]),
        .library(name: "AuthKit", targets: ["AuthKit"]),
        .library(name: "KeychainKit", targets: ["KeychainKit"]),
        .library(name: "XPCBridge", targets: ["XPCBridge"]),
        .library(name: "ProcessManager", targets: ["ProcessManager"]),
        .library(name: "BuildStream", targets: ["BuildStream"]),
        .library(name: "Settings", targets: ["Settings"]),
        .library(name: "DocImport", targets: ["DocImport"]),
    ],
    dependencies: [
        // No third-party dependencies. All functionality uses Apple system frameworks.
        // Every dependency must be justified per Forge Engineering Standards.
    ],
    targets: [
        // MARK: - KeychainKit (Leaf Node)
        // Leaf module — imports nothing internal. Wraps Security.framework directly.
        // Failure behavior: all Keychain errors fail closed with OSStatus context.
        .target(
            name: "KeychainKit",
            dependencies: [],
            path: "Sources/KeychainKit",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "KeychainKitTests",
            dependencies: ["KeychainKit"],
            path: "Tests/KeychainKitTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - AuthKit
        // Depends on KeychainKit for credential storage.
        // Failure behavior: auth failures fail closed — no session granted on error.
        .target(
            name: "AuthKit",
            dependencies: ["KeychainKit"],
            path: "Sources/AuthKit",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "AuthKitTests",
            dependencies: ["AuthKit"],
            path: "Tests/AuthKitTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - XPCBridge
        // Depends on KeychainKit for credential retrieval when establishing XPC connections.
        // Failure behavior: unknown XPC message types are discarded and logged, never raised.
        .target(
            name: "XPCBridge",
            dependencies: ["KeychainKit"],
            path: "Sources/XPCBridge",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "XPCBridgeTests",
            dependencies: ["XPCBridge"],
            path: "Tests/XPCBridgeTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - ProcessManager
        // Depends on XPCBridge for IPC and KeychainKit for process credential validation.
        // Failure behavior: process launch failures surface with full context, never silently ignored.
        .target(
            name: "ProcessManager",
            dependencies: ["XPCBridge", "KeychainKit"],
            path: "Sources/ProcessManager",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "ProcessManagerTests",
            dependencies: ["ProcessManager"],
            path: "Tests/ProcessManagerTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - BuildStream
        // Depends on XPCBridge for build output streaming over IPC.
        // Failure behavior: stream errors propagate immediately — no buffered silent drops.
        .target(
            name: "BuildStream",
            dependencies: ["XPCBridge"],
            path: "Sources/BuildStream",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "BuildStreamTests",
            dependencies: ["BuildStream"],
            path: "Tests/BuildStreamTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - Settings
        // Depends on KeychainKit for secure preference storage and AuthKit for gated access.
        // Failure behavior: settings read/write errors surface with context, defaults are deny.
        .target(
            name: "Settings",
            dependencies: ["KeychainKit", "AuthKit"],
            path: "Sources/Settings",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "SettingsTests",
            dependencies: ["Settings"],
            path: "Tests/SettingsTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - DocImport
        // No internal dependencies — isolated document ingestion module.
        // All external document input is untrusted and validated before processing.
        .target(
            name: "DocImport",
            dependencies: [],
            path: "Sources/DocImport",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "DocImportTests",
            dependencies: ["DocImport"],
            path: "Tests/DocImportTests",
            swiftSettings: strictConcurrencySettings
        ),

        // MARK: - AppShell (Root)
        // Root application module. Depends on all other modules per TRD-1 §2.3.
        // This is the only module that creates the SwiftUI App entry point.
        .target(
            name: "AppShell",
            dependencies: [
                "AuthKit",
                "KeychainKit",
                "XPCBridge",
                "ProcessManager",
                "BuildStream",
                "Settings",
                "DocImport",
            ],
            path: "Sources/AppShell",
            swiftSettings: strictConcurrencySettings
        ),
        .testTarget(
            name: "AppShellTests",
            dependencies: ["AppShell"],
            path: "Tests/AppShellTests",
            swiftSettings: strictConcurrencySettings
        ),
    ]
)
// ---
// FILE: Sources/KeychainKit/KeychainKit.swift
// ---

// Sources/KeychainKit/KeychainKit.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - This is the leaf module in the dependency graph; it imports no internal modules.
// - All Keychain operations use Security.framework directly — no third-party wrappers.
// - All errors fail closed with OSStatus context — never return partial or stale data.
// - Secrets never appear in logs or error descriptions.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import Security

/// Root namespace for Keychain operations.
///
/// `KeychainKit` provides secure credential storage and retrieval
/// using the macOS Keychain via Security.framework. All operations
/// fail closed — errors surface with OSStatus context but never
/// expose secret material in diagnostics.
public enum KeychainKit {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "KeychainKit"
}
// ---
// FILE: Sources/AuthKit/AuthKit.swift
// ---

// Sources/AuthKit/AuthKit.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - Authentication failures fail closed — no session is ever granted on error.
// - Depends on KeychainKit for credential storage; no direct Security.framework calls here.
// - Session tokens are never logged or included in error descriptions.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import KeychainKit

/// Root namespace for authentication and session management.
///
/// `AuthKit` provides LocalAuthentication gating and session lifecycle
/// management. All authentication failures fail closed — no session
/// is granted when an error occurs.
public enum AuthKit {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "AuthKit"
}
// ---
// FILE: Sources/XPCBridge/XPCBridge.swift
// ---

// Sources/XPCBridge/XPCBridge.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - Unknown XPC message types are discarded and logged — never raised as exceptions.
// - Depends on KeychainKit for credential retrieval during XPC connection establishment.
// - All XPC connections validate peer identity before message exchange.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import KeychainKit

/// Root namespace for XPC inter-process communication.
///
/// `XPCBridge` manages secure XPC connections between the main application
/// and helper processes. Unknown message types are discarded and logged
/// per Forge invariants — they are never raised as exceptions.
public enum XPCBridge {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "XPCBridge"
}
// ---
// FILE: Sources/ProcessManager/ProcessManager.swift
// ---

// Sources/ProcessManager/ProcessManager.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - Process launch failures surface with full context — never silently ignored.
// - Generated code is never executed by the agent — no eval, no exec, no subprocess of generated content.
// - Depends on XPCBridge for IPC and KeychainKit for process credential validation.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import XPCBridge
import KeychainKit

/// Root namespace for child process lifecycle management.
///
/// `ProcessManager` handles spawning, monitoring, and terminating
/// child processes (e.g., xcodebuild, git). All process launch
/// failures surface with explicit context. Generated code is never
/// executed per Forge security invariants.
public enum ProcessManager {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "ProcessManager"
}
// ---
// FILE: Sources/BuildStream/BuildStream.swift
// ---

// Sources/BuildStream/BuildStream.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - Stream errors propagate immediately — no buffered silent drops.
// - Depends on XPCBridge for build output streaming over IPC.
// - Build output is treated as untrusted external input and validated before display.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import XPCBridge

/// Root namespace for build output streaming.
///
/// `BuildStream` provides real-time build output capture and forwarding
/// via XPC. Stream errors propagate immediately — no silent buffered drops.
/// All build output is treated as untrusted external input.
public enum BuildStream {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "BuildStream"
}
// ---
// FILE: Sources/Settings/Settings.swift
// ---

// Sources/Settings/Settings.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - Settings read/write errors surface with context — defaults are deny-by-default.
// - Depends on KeychainKit for secure preference storage and AuthKit for gated access.
// - Sensitive settings (tokens, keys) are stored only in Keychain, never UserDefaults.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import KeychainKit
import AuthKit

/// Root namespace for application settings and preferences.
///
/// `Settings` manages user preferences with a deny-by-default posture.
/// Sensitive values are stored via `KeychainKit`; access is gated
/// through `AuthKit`. Read/write errors always surface with context.
public enum Settings {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "Settings"
}
// ---
// FILE: Sources/DocImport/DocImport.swift
// ---

// Sources/DocImport/DocImport.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - No internal dependencies — isolated document ingestion module.
// - All external document input is untrusted and validated before processing.
// - Document content is never placed in system prompt context — always user prompt only.
// - No eval or exec of document content under any circumstances.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation

/// Root namespace for document import and ingestion.
///
/// `DocImport` handles ingestion of external documents (PRDs, TRDs, etc.)
/// into the agent's context. All document content is treated as untrusted
/// external input and is validated before processing. Document content
/// is never placed in system prompt context per Forge security invariants.
public enum DocImport {
    /// Module version identifier for build verification.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "DocImport"
}
// ---
// FILE: Sources/AppShell/AppShell.swift
// ---

// Sources/AppShell/AppShell.swift
// ConsensusDevAgent — Forge Platform
//
// Security assumptions:
// - Root application module — all other modules are composed here.
// - No direct security operations; delegates to AuthKit/KeychainKit.
// - UI state is MainActor-bound; all SwiftUI views use @MainActor.
// - This is a placeholder; the actual SwiftUI App entry point will be added in subsequent PRs.
//
// Memory budget (OI-13): No caches or buffers allocated. Stateless namespace only.

import Foundation
import AuthKit
import KeychainKit
import XPCBridge
import ProcessManager
import BuildStream
import Settings
import DocImport

/// Root namespace for the application shell.
///
/// `AppShell` is the top-level module that composes all other modules
/// into the running application. The SwiftUI `App` entry point will be
/// defined here in a subsequent PR. This placeholder ensures the module
/// compiles and the full dependency graph resolves correctly.
public enum AppShell {
    /// Module version identifier for build verification.
    /// Validates that all downstream modules are reachable at compile time.
    /// - Note: No runtime allocation — compile-time constant only.
    public static let moduleIdentifier: String = "AppShell"

    /// Validates that all module dependencies are resolvable at compile time.
    /// This function exists solely to exercise the import graph during CI builds.
    /// - Returns: Array of module identifiers for all direct dependencies.
    /// - Note: Allocation is a small fixed-size array — within OI-13 budget.
    public