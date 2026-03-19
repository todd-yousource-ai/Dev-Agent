# TRD-12-Backend-Runtime-Startup

_Source: `TRD-12-Backend-Runtime-Startup.docx` — extracted 2026-03-19 19:55 UTC_

---

TRD-12

Backend Runtime Startup and Version Handshake

Technical Requirements Document  •  v1.0

# 1. Purpose and Scope

This document specifies three things and only three things:

Python backend startup sequence — what initializes in what order, why the order matters, and what must succeed before the backend signals ready to the Swift shell.

Swift/Python version compatibility handshake — how the backend communicates its version to the Swift shell, how Swift validates compatibility, and what happens when they are incompatible.

Graceful shutdown — what the Python backend does when it receives a stop signal, how in-flight work is handled, and what state is guaranteed to be persisted before exit.

Why startup order matters: if the document store initializes before the embedding model is loaded, retrieval calls during startup fail. If GitHubTool initializes before credentials are delivered, it has no token and all API calls fail with authentication errors. If the CommandRouter starts accepting commands before the ConsensusEngine is ready, an early command silently fails. Each initialization step has dependencies — this TRD makes them explicit.

# 2. Design Decisions

# 3. Startup Sequence

## 3.1 Ordered Initialization

## 3.2 main() Implementation

# 4. The Ready Message

## 4.1 Schema

## 4.2 Swift Validation Logic

# 5. Version Compatibility Rules

## 5.1 Semver Contract

## 5.2 Compatibility Matrix

The practical effect: when the Swift shell ships a new feature that requires a new XPC message type, it bumps its minor version. The backend must also bump its minor version and add the new message type before operators using the new shell can run. The backend minor version tracks the shell — they move together at each feature release.

## 5.3 Version Constants

# 6. Credential Delivery Gate

## 6.1 What Blocks on Credentials

## 6.2 Credential Timeout Handling

# 7. Startup Failure Modes

## 7.1 Degraded State Operation

# 8. Graceful Shutdown

## 8.1 Three Shutdown Scenarios

## 8.2 Shutdown Implementation

## 8.3 Shutdown Timing Requirements

# 9. Startup Health Check (TRD-9 Integration)

## 9.1 XPC Integration Test Sequence

The XPC integration test in TRD-9 Section 9.2 validates the full startup sequence on the Mac CI runner. This section specifies what the test validates and the timing requirements it must meet.

## 9.2 Startup Timing Budget

# 10. Testing Requirements

## 10.1 Startup Sequence Unit Test

# 11. Out of Scope

# 12. Open Questions

# Appendix A: Startup Sequence Diagram

# Appendix B: Document Change Log