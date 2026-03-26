# Conventions

Canonical naming and structural conventions for the Crafted Dev Agent repository.

> **Status**: Normative -- v1.0
> **Normative language**: Uses MUST, SHOULD, MAY per [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).
> **Cross-references**: [ARCHITECTURE.md](./ARCHITECTURE.md) · [INTERFACES.md](./INTERFACES.md) · [SOURCE_OF_TRUTH.md](./SOURCE_OF_TRUTH.md) · [VERSIONING.md](./VERSIONING.md)

---

## Branch Naming

All branches MUST follow a structured naming pattern. The canonical pattern for agent-generated build branches is:

```
crafted-agent/build/<slug>
```

Where `<slug>` is a lowercase, hyphen-separated descriptor of the build content (e.g., `foundation-standards`, `python-scaffold`, `swift-shell-bootstrap`).

### Branch Naming Rules

| Branch Pattern | Usage | Example |
|