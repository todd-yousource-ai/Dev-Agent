# Architecture

Canonical architecture reference for the Crafted Dev Agent system.

> **Status**: Normative -- v1.0
> **Normative language**: Uses MUST, SHOULD, MAY per [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).
> **Cross-references**: [INTERFACES.md](./INTERFACES.md) · [CONVENTIONS.md](./CONVENTIONS.md) · [SOURCE_OF_TRUTH.md](./SOURCE_OF_TRUTH.md) · [VERSIONING.md](./VERSIONING.md)

---

## System Context

The Crafted Dev Agent is a native macOS AI coding system built by YouSource.ai. It accepts a plain-language build intent, decomposes it into an ordered sequence of pull requests, generates implementation and tests for each PR using two LLM providers in parallel (Claude arbitrates), runs self-correction, lint gates, and fix loops, executes CI, and gates on operator approval before merging.

The system is composed of two discrete OS processes that communicate over a local transport channel.

---

## Two-Process Model

Crafted Dev Agent runs as **two separate OS processes** on macOS:

| Process | Technology | Role |
|