# VERSION
```
0.1.0
```

# forge-standards/adrs/ADR-003-version-policy.md
```
# ADR-003: Version Alignment Policy -- Root VERSION File as Canonical Source

| Field        | Value                          |
|--------------|--------------------------------|
| **Status**   | Accepted                       |
| **Date**     | 2025-01-15                     |
| **Authors**  | Forge Platform Engineering     |
| **Replaces** | N/A                            |

## Context

Consensus Dev Agent is a two-process architecture: a Swift shell (macOS native)
and a Python backend, communicating over an authenticated Unix domain socket.
TRD-12 §5 specifies a version handshake as part of IPC connection establishment.

Version mismatches between these two processes can cause:

1. **Silent protocol incompatibilities** -- message schemas diverge without detection.
2. **Data corruption** -- serialization format changes interpreted under old schema.
3. **Security regressions** -- a newer process may expect auth fields the older
   process does not send, creating an unauthenticated path.

Multiple version-bearing artifacts exist today:

- `VERSION` (root)
- `pyproject.toml` (`version = "..."`)
- Swift `Info.plist` / build constants
- IPC handshake payload

Without a single canonical source, drift is inevitable.

### Alternatives Considered

| Alternative                                  | Evaluation                                                                                   |
|----------------------------------------------|----------------------------------------------------------------------------------------------|
| `pyproject.toml` as canonical source         | Python-centric; Swift build cannot trivially read TOML without a parser dependency.           |
| Git tags only                                | Requires a checkout to resolve; not available at build time in all CI configurations.         |
| Per-process independent versions             | Maximum flexibility but requires a compatibility matrix -- exponential test surface.           |
| **Root `VERSION` file (chosen)**             | Language-agnostic plain text; trivially readable by shell, Python, Swift, and CI scripts.     |

## Decision

1. **The file `VERSION` at the repository root is the single source of truth.**
   It contains exactly one line: `MAJOR.MINOR.PATCH` (no trailing newline, no
   prefix, no pre-release suffix in release builds). Pre-release versions use
   the format `MAJOR.MINOR.PATCH-PRERELEASE` per SemVer 2.0.0.

2. **All other version-bearing artifacts derive from `VERSION`.**
   - `pyproject.toml` must match (`TestVersionConsistency` enforces this).
   - Swift shell reads `VERSION` at build time via a Run Script phase or
     embeds it as a generated constant.
   - IPC handshake includes the version string verbatim from `VERSION`.

3. **IPC Version Handshake Contract (per TRD-12 §5.3):**
   - On connection, the Python backend sends its version in the `hello` message.
   - The Swift shell compares the received version against its own compiled version.
   - **MAJOR mismatch → fail closed.** Connection is refused, error surfaced.
   - **MINOR mismatch → warn and continue** only if the newer side is the backend
     (backend is backward-compatible within a MAJOR).
   - **PATCH mismatch → allowed silently** (bug-fix only, no protocol changes).

4. **Bump procedure:** Update `VERSION` first, then run the sync script to
   propagate. CI gate blocks merge if any artifact disagrees.

## Consequences

### Positive

- Single grep/cat gives the repo version -- no parsing required.
- Language-agnostic: works for Swift, Python, shell scripts, CI.
- Handshake enforces alignment at runtime -- fail closed on incompatibility.
- `TestVersionConsistency` catches drift before merge.

### Negative

- Developers must remember to bump `VERSION` (mitigated by CI enforcement).
- Pre-release suffixes require all consumers to parse SemVer (mitigated by
  providing a shared parser module).

## Compatibility Matrix

| Backend MAJOR.MINOR | Shell MAJOR.MINOR | Result               |
|----------------------|--------------------|----------------------|
| X.Y                  | X.Y                | ✅ Full compatibility |
| X.Y+1                | X.Y                | ⚠️ Warn, allow       |
| X.Y                  | X.Y+1              | ❌ Fail closed        |
| X+1.*                | X.*                | ❌ Fail closed        |
| X.*                  | X+1.*              | ❌ Fail closed        |

> **Security note:** The "fail closed" cases MUST NOT be overridable without
> an explicit operator gate approval. No auto-negotiation fallback exists by
> design -- this prevents downgrade attacks.
```

# forge-standards/versioning/SEMVER_POLICY.md
```
# Semantic Versioning Policy -- Consensus Dev Agent

> **Canonical version source:** `/VERSION` (repository root)
> **Governing ADR:** [ADR-003](../adrs/ADR-003-version-policy.md)
> **Specification basis:** [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html)

---

## 1. Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE]
```

- **Release builds:** `MAJOR.MINOR.PATCH` (e.g., `0.1.0`)
- **Pre-release builds:** `MAJOR.MINOR.PATCH-PRERELEASE` (e.g., `0.2.0-alpha.1`)
- No `v` prefix. No build metadata suffix in `VERSION`.
- File contains exactly one line, no trailing newline.
- Regex validation: `^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$`

---

## 2. Bump Criteria

### MAJOR Bump (`X.0.0`)

A MAJOR bump is required when **any** of the following occur:

- IPC protocol wire format changes incompatibly (message schema, framing, auth envelope).
- XPC message type IDs are renumbered or removed.
- Security model changes (auth flow, credential format, trust boundary modification).
- Public Python API removes or changes existing function signatures.
- Swift shell command-line interface removes or changes existing flags.
- Any change that would cause a running older process to **silently misbehave**
  when communicating with a newer process.

> **Security invariant:** MAJOR mismatches always fail closed at the IPC handshake.
> No fallback, no negotiation, no auto-approve.

### MINOR Bump (`x.Y.0`)

A MINOR bump is required when **any** of the following occur:

- New IPC message types are added (backward-compatible additions only).
- New Python API surface is added without changing existing surface.
- New CLI flags or subcommands are added without changing existing behavior.
- New configuration keys are added with safe defaults.
- Deprecation notices are introduced (removal requires MAJOR).

> **IPC rule:** A backend at MINOR version N+1 may serve a shell at MINOR
> version N. The reverse (shell newer than backend) fails closed because the
> shell may send message types the backend does not understand.

### PATCH Bump (`x.y.Z`)

A PATCH bump is required when **only** the following occur:

- Bug fixes with no API, CLI, or protocol changes.
- Documentation corrections.
- Dependency updates that do not change public behavior.
- Performance improvements with identical observable behavior.
- Security patches that do not alter the protocol or API surface.

> **IPC rule:** PATCH mismatches are always allowed. No warning emitted.

---

## 3. Pre-Release Conventions

| Suffix           | Meaning                                        | IPC Behavior       |
|------------------|------------------------------------------------|---------------------|
| `-alpha.N`       | Unstable; protocol may change between alphas   | Exact match required |
| `-beta.N`        | Feature-complete; protocol frozen for this beta | MINOR rules apply   |
| `-rc.N`          | Release candidate; identical to release intent  | MINOR rules apply   |

Pre-release versions have **lower precedence** than their release counterpart
per SemVer §11. CI must not publish a release artifact from a pre-release version.

---

## 4. IPC Handshake Version Negotiation Protocol

Reference: TRD-12 §5.3

### 4.1 Handshake Sequence

```
  Shell                          Backend
    |                               |
    |--- connect (Unix socket) ---->|
    |                               |
    |<-- hello {                    |
    |      "protocol": "forge-ipc",|
    |      "version": "<VERSION>", |
    |      "min_compatible": "M.m" |
    |    }                          |
    |                               |
    |--- version_ack / version_reject -->|
    |                               |
```

### 4.2 Hello Message Fields

| Field              | Type   | Description                                                    | Required |
|--------------------|--------|----------------------------------------------------------------|----------|
| `protocol`         | string | Must be `"forge-ipc"`. Any other value → discard and close.   | Yes      |
| `version`          | string | Full SemVer string from backend's `VERSION` file.             | Yes      |
| `min_compatible`   | string | `MAJOR.MINOR` -- oldest shell version this backend supports.   | Yes      |

### 4.3 Shell-Side Validation (Fail-Closed)

```
parse(backend_version) → (B_MAJOR, B_MINOR, B_PATCH, B_PRE)
parse(shell_version)   → (S_MAJOR, S_MINOR, S_PATCH, S_PRE)

IF B_MAJOR ≠ S_MAJOR:
    → REJECT: "MAJOR version mismatch: shell={S}, backend={B}"
    → Close connection. Surface error to operator.

IF B_PRE is alpha AND (B_MAJOR, B_MINOR, B_PATCH, B_PRE) ≠ (S_MAJOR, S_MINOR, S_PATCH, S_PRE):
    → REJECT: "Alpha pre-release requires exact version match"
    → Close connection. Surface error to operator.

IF S_MINOR > B_MINOR:
    → REJECT: "Shell newer than backend (MINOR): shell={S}, backend={B}"
    → Close connection. Surface error to operator.

IF B_MINOR > S_MINOR:
    → WARN to operator log: "Backend MINOR ahead of shell: shell={S}, backend={B}"
    → ACCEPT (backward-compatible)

→ ACCEPT
```

### 4.4 Security Constraints

- **No downgrade negotiation.** The handshake does not offer to "try an older
  protocol." If versions are incompatible, the connection is refused.
- **No version spoofing tolerance.** The version string is validated against
  the `VERSION` file at build time; runtime version injection is not permitted.
- **Unknown `protocol` values** → discard message, close socket, log event.
  Per Forge invariant: XPC unknown message types are discarded and logged.
- **Secrets never appear in version mismatch error messages.** Only version
  strings and process identifiers are included.

---

## 5. Version Propagation -- Artifact Alignment

All version-bearing artifacts MUST agree with the root `VERSION` file.

| Artifact                          | Sync Mechanism                                | CI Enforcement                  |
|-----------------------------------|-----------------------------------------------|---------------------------------|
| `VERSION`                         | Canonical source -- manually edited            | N/A (source of truth)           |
| `pyproject.toml` `version`        | Must match `VERSION` exactly                  | `TestVersionConsistency`        |
| Swift `Info.plist` / build const  | Generated from `VERSION` at build time        | Xcode build phase + CI check    |
| IPC `hello` message               | Read from `VERSION` at runtime                | Integration test                |
| Git tag (on release)              | Created from `VERSION` by release automation  | Tag-version match gate          |

### 5.1 Bump Procedure

```bash
# 1. Edit the canonical source -- ALLOCATION: 12 bytes max (e.g., "99.99.99\n")
echo "X.Y.Z" > VERSION

# 2. Sync pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"X.Y.Z\"/" pyproject.toml

# 3. Verify
python -c "
from pathlib import Path
v = Path('VERSION').read_text().strip()
import tomllib
with open('pyproject.toml', 'rb') as f:
    p = tomllib.load(f)['project']['version']
assert v == p, f'Mismatch: VERSION={v}, pyproject={p}'
print(f'✓ Version aligned: {v}')
"
```

---

## 6. Compatibility Guarantees by Release Phase

| Phase          | Version Range | Protocol Stability | API Stability | Config Stability |
|----------------|---------------|--------------------|---------------|------------------|
| `0.x.y`        | Pre-1.0       | No guarantees      | No guarantees | Best-effort      |
| `1.x.y`+       | Post-1.0      | Per bump rules     | Per bump rules| Per bump rules   |

> **Note:** During `0.x.y` development, MINOR bumps MAY include breaking
> changes. The IPC handshake still enforces MAJOR match, providing a safety
> net even in pre-1.0 development.

---

## 7. Version Parsing Reference Implementation

See `src/consensus_dev_agent/version.py` for the Python reference parser.
The parser MUST:

- Validate against the SemVer regex (reject malformed input -- fail closed).
- Return a structured tuple `(major, minor, patch, prerelease)`.
- Never raise an unhandled exception -- all parse failures return a typed error.
- Accept only ASCII input -- no Unicode normalization, no locale sensitivity.
```

# src/consensus_dev_agent/__init__.py
```python
"""
Consensus Dev Agent -- package root.

Security assumptions:
- VERSION file is read from a path relative to this file's location.
  The path is validated to be within the repository tree.
- If VERSION cannot be read or parsed, the module refuses to provide
  a version (fail closed) rather than silently returning a default.
- No secrets are involved in version resolution.

Failure behavior:
- Missing/unreadable VERSION file → raises RuntimeError at import time.
  This is intentional: a missing version indicates a broken installation
  and the agent MUST NOT start without identity.

Memory allocation note (OI-13):
- _VERSION: single string, ≤ 20 bytes (SemVer with pre-release suffix).
  No caching beyond this single module-level binding.
"""
from consensus_dev_agent.version import read_version, parse_version

# ALLOCATION: Single string ≤ 20 bytes -- the canonical runtime version.
__version__: str = read_version()

# Validate at import time -- fail closed if VERSION is malformed.
_parsed = parse_version(__version__)
if _parsed is None:
    raise RuntimeError(
        f"VERSION file contains malformed version string: {__version__!r}. "
        "Expected MAJOR.MINOR.PATCH[-PRERELEASE]. Refusing to start."
    )

__all__ = ["__version__"]
```

# src/consensus_dev_agent/version.py
```python
"""
Version parsing and validation for Consensus Dev Agent.

Security assumptions:
- The VERSION file is trusted (it is committed to the repository and
  read from a known relative path). However, its content is still
  validated against the SemVer regex before use -- defense in depth.
- Path traversal is prevented by using Path resolution and checking
  that the resolved path is within the expected repository tree.
- No secrets are involved. Version strings may appear in logs and
  error messages.

Failure behavior:
- read_version(): raises RuntimeError if VERSION cannot be found or read.
  This is fail-closed -- the agent cannot operate without a known version.
- parse_version(): returns None on invalid input (never raises).
  Callers MUST check the return value.
- compare_versions_for_handshake(): returns a typed result indicating
  accept, warn, or reject -- never raises on valid parsed input.

Memory allocation note (OI-13):
