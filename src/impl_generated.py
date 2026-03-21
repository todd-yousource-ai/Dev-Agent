VERSION:

0.1.0

docs/VERSIONING.md:

# Versioning Contract Specification

> **Status:** Normative -- all version-sensitive code in this repository MUST comply with this contract.
>
> **Canonical Reference:** `PRD-001` -- Product Foundation, Repository Bootstrap, and Cross-TRD Contract Baseline

---

## 1. Canonical Source

The **single source of truth** for the Consensus Dev Agent version is:

```
VERSION
```

This is a plain-text file at the repository root containing exactly one line: a valid [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) string with **no `v` prefix**, **no trailing whitespace**, and **no blank lines**.

Example contents:

```
0.1.0
```

All other version references in the repository are **derived** from this file. If any derived target disagrees with the `VERSION` file, the build is broken and must not proceed.

---

## 2. Propagation Targets

The canonical version propagates to exactly four targets. Each target has a defined binding location and format:

| # | Target | File | Field / Key | Format | Example |
|---|--------|------|-------------|--------|---------|
| 1 | **Swift shell (macOS app bundle)** | `Forge/Info.plist` | `CFBundleShortVersionString` | Bare SemVer string | `0.1.0` |
| 2 | **Python backend** | `forge_agent/version.py` | `AGENT_VERSION` (module-level constant) | Python string literal | `AGENT_VERSION = "0.1.0"` |
| 3 | **Python packaging** | `pyproject.toml` | `version` field under `[project]` | TOML string | `version = "0.1.0"` |
| 4 | **Git release tag** | Git ref | Tag name | `v`-prefixed SemVer | `v0.1.0` |

### 2.1 Binding Rules

- **Info.plist**: The `CFBundleShortVersionString` value MUST be an exact string match to the contents of `VERSION`. `CFBundleVersion` (build number) is managed separately and is out of scope for this contract.
- **version.py**: The file MUST contain a module-level assignment `AGENT_VERSION = "{version}"` where `{version}` is an exact string match to the contents of `VERSION`. No other logic or imports are permitted in this file.
- **pyproject.toml**: The `version` field under `[project]` MUST be an exact string match to the contents of `VERSION`.
- **Git tag**: Release tags MUST follow the format `v{VERSION}` (e.g., `v0.1.0`). The `v` prefix is used **only** in git tags -- never in the `VERSION` file or any propagation target.

---

## 3. Version Handshake Protocol

Consensus Dev Agent is a two-process architecture: a **Swift shell** (macOS application) and a **Python backend** (consensus engine). These processes communicate over an authenticated Unix domain socket. Version coherence across this boundary is a **correctness requirement**.

### 3.1 Handshake Payload

During the IPC `ready` handshake, both processes exchange a version payload. The payload is a JSON object with the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product` | `string` | Yes | Product identifier. MUST be `"consensus-dev-agent"`. |
| `version` | `string` | Yes | SemVer version string from the respective process's compiled/embedded version constant. |
| `protocol_version` | `string \| null` | Yes | Reserved for future IPC contract versioning. MUST be `null` until a protocol versioning scheme is adopted. |

Example payload:

```json
{
  "product": "consensus-dev-agent",
  "version": "0.1.0",
  "protocol_version": null
}
```

### 3.2 Handshake Validation Rules

1. Both the Swift shell and the Python backend transmit their version payload immediately after socket connection and authentication.
2. Each process validates the remote payload against its own values.
3. **Product mismatch**: If the `product` fields differ, the connection MUST be refused immediately. This indicates a misconfigured or spoofed endpoint.
4. **Version mismatch**: If the `version` fields differ, the connection MUST be refused immediately. The system MUST NOT fall back to a degraded mode or warn-only behavior.
5. **Protocol version mismatch**: When `protocol_version` is non-null in a future release, mismatched `protocol_version` values MUST also cause connection refusal. While both sides send `null`, this field is ignored during validation.

### 3.3 Failure Behavior (Fail Closed)

On any handshake validation failure:

- The detecting process MUST close the Unix socket immediately.
- The detecting process MUST log a structured error message containing:
  - The local version string
  - The remote version string
  - The specific mismatch field (`product`, `version`, or `protocol_version`)
  - A human-readable remediation hint (e.g., `"Rebuild both targets from the same commit"`)
- The detecting process MUST exit with a non-zero status code or surface the error to the operator via the UI. It MUST NOT silently retry, degrade, or continue operation.
- No data other than the handshake payload may have been exchanged before validation completes. If any application-level message is received before handshake completion, the connection MUST be terminated.

---

## 4. Semantic Versioning Rules

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) with the following project-specific definitions:

### 4.1 Major Version (X.0.0)

A major version increment indicates a **breaking change** to any of:

- **IPC message schema**: Any change to the structure, encoding, or semantics of messages exchanged between the Swift shell and Python backend
- **Handshake protocol**: Any change to the handshake payload fields, validation logic, or authentication mechanism
- **Security boundary**: Any change to the trust model, credential handling, sandbox policy, or entitlements that alters the security contract
- **Operator-facing contract**: Any change that requires operators to modify their configuration, workflow, or integration points

### 4.2 Minor Version (0.X.0)

A minor version increment indicates a **new capability** with no breaking changes:

- New IPC message type added (existing messages unchanged)
- New build pipeline stage supported
- New consensus mode or strategy added
- New operator-facing feature that is backward-compatible
- New configuration option with a safe default

### 4.3 Patch Version (0.0.X)

A patch version increment indicates a **bugfix** with no contract or capability change:

- Correctness fix in existing behavior
- Performance improvement with no API/IPC change
- Documentation correction (when bundled with a code fix)
- Dependency update that does not alter the public contract

### 4.4 Initial Development (0.x.y)

Per SemVer §4, while the major version is `0`, the API is not considered stable. Minor version increments MAY include breaking changes during this phase. However, all handshake validation rules still apply -- version coherence is enforced even during initial development.

---

## 5. Pre-release Tag Format

Pre-release versions follow the format:

```
{major}.{minor}.{patch}-{stage}.{n}
```

Where:

| Component | Description | Valid Values |
|-----------|-------------|--------------|
| `{major}` | Major version | Non-negative integer |
| `{minor}` | Minor version | Non-negative integer |
| `{patch}` | Patch version | Non-negative integer |
| `{stage}` | Pre-release stage identifier | `alpha`, `beta`, `rc` |
| `{n}` | Pre-release sequence number (1-indexed) | Positive integer |

### 5.1 Examples

| Version String | Meaning |
|----------------|---------|
| `0.2.0-alpha.1` | First alpha pre-release of 0.2.0 |
| `0.2.0-alpha.2` | Second alpha pre-release of 0.2.0 |
| `0.2.0-beta.1` | First beta pre-release of 0.2.0 |
| `1.0.0-rc.1` | First release candidate of 1.0.0 |
| `1.0.0-rc.3` | Third release candidate of 1.0.0 |

### 5.2 Ordering

Pre-release versions have lower precedence than the associated release version, following SemVer §11. Stage ordering is: `alpha` < `beta` < `rc` < (release).

### 5.3 Pre-release Handshake Behavior

During IPC handshake, pre-release versions are compared as **exact strings**. A Swift shell at `0.2.0-alpha.1` and a Python backend at `0.2.0-alpha.2` are **not compatible** and the handshake MUST fail. There is no range-based compatibility for pre-release versions.

---

## 6. CI Enforcement Rule

### 6.1 The `version-coherence` Check

A CI check named `version-coherence` (defined in a future PR) MUST run on every pull request and every push to the default branch. This check:

1. Reads the contents of the `VERSION` file and strips any trailing whitespace/newline.
2. Validates that the version string is valid SemVer 2.0.0 (with optional pre-release and build metadata segments).
3. Extracts the version from each propagation target:
   - `CFBundleShortVersionString` from `Forge/Info.plist`
   - `AGENT_VERSION` from `forge_agent/version.py`
   - `version` from `pyproject.toml`
4. Compares each extracted version to the canonical version using **exact string equality** (after whitespace stripping).
5. Reports all mismatches, not just the first one found.

### 6.2 Failure Behavior (Fail Closed)

- **Any mismatch**: The `version-coherence` check MUST exit with a **non-zero exit code**. The build MUST fail. This is never a warning. There is no override flag, no `--force`, no environment variable to skip this check.
- **Missing target file**: If a propagation target file does not yet exist (e.g., during early bootstrap before `version.py` is created), the check SHOULD skip that target with an informational log. Once a target file exists, it MUST contain the correct version from that point forward.
- **Invalid VERSION format**: If the `VERSION` file contains a string that is not valid SemVer 2.0.0, the check MUST exit non-zero with a clear error message identifying the format violation.
- **Missing VERSION file**: If the `VERSION` file does not exist, the check MUST exit non-zero. The `VERSION` file is a mandatory repository artifact.

### 6.3 Git Tag Validation

On release workflows (tag push matching `v*`):

1. The tag name MUST match `v{VERSION}` exactly, where `{VERSION}` is the current contents of the `VERSION` file.
2. If the tag does not match, the release pipeline MUST fail with a non-zero exit code.
3. Annotated tags are preferred but not required by this contract.

---

## 7. Version Bump Procedure

### 7.1 Steps

1. **Edit `VERSION`**: Change the version string in the `VERSION` file to the new target version.
2. **Run sync tooling**: Execute the version synchronization script (defined in a future PR) to propagate the new version to all four targets.
3. **Verify coherence**: Run the `version-coherence` check locally to confirm all targets match.
4. **Commit**: Commit all changed files in a single commit with message format: `chore: bump version to {new_version}`.
5. **Tag (release only)**: After the version bump commit is merged to the default branch, create a git tag `v{new_version}` pointing to the merge commit.

### 7.2 Rules

- The `VERSION` file is **always** changed first. It is the source; all other files are derived.
- All four propagation targets MUST be updated in the **same commit** as the `VERSION` file change. Split-commit version bumps are forbidden -- they create a window where `version-coherence` would fail on intermediate commits.
- Version bumps MUST NOT be combined with feature or bugfix changes in the same commit. The version bump commit is atomic and contains only version-related file changes.
- The version MUST NOT be decremented except during pre-release rollback scenarios, which must be documented in the PR description.

---

## 8. Compatibility Matrix

This matrix defines version compatibility rules for the Swift shell and Python backend inter-process communication:

| Swift Shell Version | Python Backend Version | Compatible? | Rationale |
|---------------------|----------------------|-------------|-----------|
| `X.Y.Z` | `X.Y.Z` | **Yes** | Exact match -- only valid configuration |
| `X.Y.Z` | `X.Y.W` (W ≠ Z) | **No** | Patch mismatch -- handshake fails |
| `X.Y.Z` | `X.W.Z` (W ≠ Y) | **No** | Minor mismatch -- handshake fails |
| `X.Y.Z` | `W.Y.Z` (W ≠ X) | **No** | Major mismatch -- handshake fails |
| `X.Y.Z-alpha.1` | `X.Y.Z-alpha.1` | **Yes** | Exact match including pre-release |
| `X.Y.Z-alpha.1` | `X.Y.Z-alpha.2` | **No** | Pre-release sequence mismatch -- handshake fails |
| `X.Y.Z-alpha.1` | `X.Y.Z` | **No** | Pre-release vs release mismatch -- handshake fails |

**The compatibility rule is exact string equality. There are no version ranges, no "compatible with" semantics, and no negotiation.** This is a deliberate design choice: the two processes are built from the same repository at the same commit, so they must always carry the same version. Any divergence indicates a build or deployment error.

---

## 9. Expected Failure Modes

This section enumerates the failure modes that version enforcement will surface. All failures are **fail closed** -- the system halts and reports the error rather than continuing in an inconsistent state.

| Failure Mode | Detection Point | Behavior |
|-------------|----------------|----------|
| Propagation target version differs from `VERSION` | CI (`version-coherence` check) | Build fails with non-zero exit. All mismatches reported. |
| `VERSION` file missing | CI (`version-coherence` check) | Build fails with non-zero exit. |
| `VERSION` file contains invalid SemVer | CI (`version-coherence` check) | Build fails with non-zero exit. Format violation identified. |
| Swift shell and Python backend version mismatch at startup | IPC handshake | Connection refused. Socket closed. Error logged with both versions. Process exits non-zero or surfaces error to operator. |
| Product identifier mismatch in handshake | IPC handshake | Connection refused. Socket closed. Error logged. |
| Git tag does not match `v{VERSION}` | Release pipeline | Release fails with non-zero exit. |
| Version decremented without documented justification | Code review (human) | PR must not be merged. |

---

## 10. Document History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | Initial | -- | Created versioning contract specification |

---

## 11. References

- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
- PRD-001: Product Foundation, Repository Bootstrap, and Cross-TRD Contract Baseline
- TRD-1: macOS Application Shell (Swift-side version binding)
- TRD-2: Consensus Engine (Python-side version)
- TRD-12: Backend Runtime Startup (Version constants, §5.3)
- AGENTS.md: Repository identity and conventions
