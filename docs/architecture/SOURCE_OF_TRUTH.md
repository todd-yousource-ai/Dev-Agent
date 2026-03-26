# Source of Truth

Canonical rules for document discovery, load order, and conflict resolution in the Crafted Dev Agent system.

> **Status**: Normative -- v1.0
> **Normative language**: Uses MUST, SHOULD, MAY per [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).
> **Cross-references**: [ARCHITECTURE.md](./ARCHITECTURE.md) · [INTERFACES.md](./INTERFACES.md) · [CONVENTIONS.md](./CONVENTIONS.md) · [VERSIONING.md](./VERSIONING.md)

---

## Document Hierarchy

The Crafted Dev Agent operates from a layered document hierarchy. When documents at different levels provide conflicting guidance, the higher-priority level wins.

The priority order from highest to lowest is:

| Priority | Document Type | Location | Authority Scope |
|