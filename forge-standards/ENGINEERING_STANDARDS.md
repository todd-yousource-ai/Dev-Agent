# Forge Engineering Standards

## Core Principles
- All code must be engineered for maximum security.
- All code must be engineered for maximum performance.
- All code must be engineered for simplicity, clarity, maintainability, and traceability.
- Security, correctness, documentation, and operational integrity take priority over development speed.
- Do not introduce complexity unless it is required and justified.

## Security Requirements
- Default to secure-by-design and deny-by-default behavior.
- All trust boundaries must be explicitly identified and enforced.
- All sensitive operations must be authenticated, authorized, and fully auditable.
- All secrets, keys, tokens, and credentials must be protected in memory, at rest, and in transit.
- Never hardcode secrets, tokens, credentials, or cryptographic material.
- All external input must be treated as untrusted and validated strictly.
- All parsing must be bounds-checked and fail safely.
- All failures involving trust, identity, policy, or cryptography must fail closed.
- All administrative or policy-changing actions must generate audit logs.
- Minimize attack surface, dependencies, privileges, and exposed interfaces.

## Performance Requirements
- Performance must be considered a design requirement, not a post-build optimization.
- Favor low-latency, low-overhead architectures.
- Avoid unnecessary allocations, copies, blocking calls, and serialization overhead.
- Measure hot paths, do not guess.
- Design for efficient concurrency and safe parallelism where appropriate.

## Code Quality Requirements
- Code must be production-grade, not demo-grade.
- Code must be readable, deterministic, and easy to review.
- Prefer explicit behavior over magic abstractions.
- Prefer small, composable modules over large multipurpose components.
- Every major component must have clear ownership, interfaces, and failure behavior.
- Remove dead code, unused dependencies, and experimental leftovers.
- No silent failure paths.

## Dependency Requirements
- Every dependency must be justified.
- Prefer mature, actively maintained, minimal dependencies.
- All dependencies must be reviewed for licensing, maintenance health, CVE history.
- Do not add a dependency for convenience if the functionality can be safely implemented internally.

## Observability and Auditability
- All critical actions must be observable through structured logs, metrics, and telemetry.
- Logs must support forensic reconstruction without exposing secrets.
- Security-relevant events must be timestamped, attributable, and tamper-evident where possible.

## Testing Requirements
- All security-critical logic must have unit, integration, and negative-path tests.
- All parsing, policy, trust, and cryptographic logic must be tested against malformed inputs.
- Test for failure behavior, not just success behavior.

## Required Traceability Artifacts
- README.md — purpose, build, test, architecture context
- ARCHITECTURE.md — components, boundaries, flows, dependencies
- SECURITY.md — trust boundaries, sensitive assets, threat assumptions
- DECISIONS.md / ADRs — design and implementation decisions
- TESTING.md — coverage description
- CHANGELOG.md — material behavioral and interface changes

## Forge Architecture Rules
- Trust must never be inferred implicitly when it can be asserted and verified explicitly.
- Identity, policy, telemetry, and enforcement must remain separable but tightly linked.
- All control decisions must be explainable, observable, and reproducible.
- Forge components must default to policy enforcement, not policy suggestion.
- AI-generated code must meet the same review, traceability, and documentation standards as human-written code.
