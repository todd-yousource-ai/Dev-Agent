// swift-tools-version: 5.9
// Package.swift -- CraftedAgent Swift shell package manifest
//
// Declares the target graph for the Crafted Dev Agent macOS Swift shell.
// Platform minimum is macOS 14 (Sonoma) per PRD-001 / TRD-1 requirements.
// No external package dependencies are declared (deny-by-default).
//
// Each target directory contains a minimal placeholder .swift file so that
// `swift build` succeeds on this scaffold. Replace placeholders with real
// implementation sources as development proceeds.

import PackageDescription

let package = Package(
    name: "CraftedAgent",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "CraftedAgent", targets: ["CraftedAgent"]),
        .library(name: "XPCContracts", targets: ["XPCContracts"]),
        .library(name: "CraftedAgentFoundation", targets: ["CraftedAgentFoundation"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "CraftedAgent",
            dependencies: [
                "CraftedAgentFoundation",
                "XPCContracts"
            ]
        ),
        .target(
            name: "XPCContracts",
            dependencies: []
        ),
        .target(
            name: "CraftedAgentFoundation",
            dependencies: [
                "XPCContracts"
            ]
        ),
        .testTarget(
            name: "XPCContractsTests",
            dependencies: [
                "XPCContracts"
            ]
        ),
        .testTarget(
            name: "CraftedAgentFoundationTests",
            dependencies: [
                "CraftedAgentFoundation"
            ]
        )
    ]
)