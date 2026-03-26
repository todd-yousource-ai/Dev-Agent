# Interfaces

Canonical interface contract for inter-process communication in the Crafted Dev Agent system.

> **Status**: Normative -- v1.0
> **Normative language**: Uses MUST, SHOULD, MAY per [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).
> **Cross-references**: [ARCHITECTURE.md](./ARCHITECTURE.md) · [CONVENTIONS.md](./CONVENTIONS.md) · [SOURCE_OF_TRUTH.md](./SOURCE_OF_TRUTH.md) · [VERSIONING.md](./VERSIONING.md)

---

## Transport Assumptions

The Swift shell and Python backend communicate over a local transport channel. The transport layer MUST satisfy the following requirements:

| Property | Requirement |
|