profiles** on macOS. The CI Runner process SHALL NOT have access to the Host Agent's Keychain items, XPC connections, GitHub tokens, or operator session state.

### Rule 2: Communication Protocol

All communication between the Host Agent and CI Runner SHALL occur through
a defined, validated IPC channel. Permitted IPC mechanisms:

1. **XPC Services** (preferred, per TRD-1 App Shell architecture)
2. **UNIX domain sockets** with authenticated endpoints
3. **File-based exchange** through a designated staging directory with
   mandatory path validation (`path_security.validate_write_path()`)

The following are **prohibited** IPC mechanisms:

- Shared memory without integrity checks
- Environment variable passing of secrets
- Symlink-based file exchange (symlink following is a path traversal vector)
- Any mechanism that allows the CI Runner to invoke Host Agent code directly

### Rule 3: Data Flow Direction and Sanitization

```
Host Agent ──[job manifest]──► CI Runner
Host Agent ◄──[result blob]─── CI Runner
```

**Host → Runner (job manifest):**
- Contains: source file paths, build commands, environment variable names
  (never secret values), timeout parameters.
- MUST NOT contain: Keychain credentials, GitHub tokens, API keys, operator
  session identifiers, or any Tier 1 secret material.
- Validated by the Host Agent before dispatch: all paths resolved to absolute
  form and checked against the allowed workspace root.

**Runner → Host (result blob):**
- Contains: exit code, stdout/stderr (truncated to configurable max),
  artifact paths, test result summary.
- MUST be treated as **untrusted input** by the Host Agent. Specifically:
  - No string from the result blob is passed to `eval`, `exec`, shell
    expansion, or format-string interpolation.
  - Log output from the runner is sanitized before display (strip ANSI
    escape sequences, enforce length limits).
  - Artifact paths in the result blob are re-validated by the Host Agent;
    the Runner's claimed paths are not trusted.

### Rule 4: File System Isolation

The CI Runner process SHALL operate within a **workspace root** that is
disjoint from the Host Agent's configuration, credential, and state
directories.

| Directory                  | Host Agent | CI Runner |
|----------------------------|------------|-----------|
| `~/Library/Application Support/ConsensusDevAgent/` | Read/Write | **No Access** |
| `~/Library/Keychains/`     | Read (via SecItem API) | **No Access** |
| `/var/folders/.../runner-workspace/` | Read-Only (for result collection) | Read/Write |
| Agent binary directory     | Execute    | **No Access** |

Path traversal from the runner workspace to the Host Agent's directories
MUST be prevented by:
1. Sandbox profile enforcement (macOS App Sandbox or custom `sandbox-exec`
   profile).
2. `path_security.validate_write_path()` on every Host Agent file operation
   that touches runner-adjacent paths.
3. Symlink resolution before path comparison (no TOCTOU via symlink races).

### Rule 5: Failure Modes

| Failure Scenario                          | Required Response                        |
|-------------------------------------------|------------------------------------------|
| CI Runner process crashes                 | Host Agent logs error, reports failure to operator gate. Does NOT retry automatically without operator acknowledgment. |
| IPC channel drops unexpectedly            | Host Agent fails closed: marks job as failed, surfaces error with context. |
| Runner result blob fails validation       | Host Agent rejects result entirely. Does NOT attempt partial parsing. |
| Runner attempts to access Host Agent dirs | Blocked by sandbox. Logged as security event. |
| Host Agent cannot verify runner identity  | Job is not dispatched. Fail closed.      |

### Rule 6: Extension Constraint

Future architectural changes that introduce additional processes (e.g.,
a separate LLM proxy process, a UI rendering process) MUST maintain the
invariant that **no process which executes generated code has access to
Tier 1 secret material**. This ADR's two-process model is the minimum
boundary, not the maximum.

## Consequences

### Positive

- Makes it structurally impossible for generated code to access credentials,
  eliminating a class of exfiltration attacks.
- Aligns with macOS platform security model (App Sandbox, XPC isolation).
- Provides a clear audit boundary: any credential access from the runner
  process is definitionally a security violation, with no ambiguous cases.
- CI Runner crashes cannot corrupt Host Agent state.

### Negative

- IPC overhead for job dispatch and result collection. This is acceptable:
  correctness and isolation take precedence over latency optimization
  (per Tier 1 precedence from ADR-0o01).
- Increased operational complexity: two processes to monitor, two sets of
  logs, two crash report streams.
- Sandbox profile authoring for macOS requires platform-specific expertise
  and testing.

### Neutral

- This ADR does not prescribe the specific sandbox profile contents; that
  is deferred to the TRD-9 implementation. This ADR only requires that
  such a profile exist and enforce the boundaries above.
- The two-process model is compatible with TRD-4's multi-agent coordination:
  each agent instance maintains its own Host/Runner pair.

## Compliance Notes

- **Enforcement mechanism**: CI gate that verifies the runner process launches
  under a separate user context or sandbox profile. Integration test that
  attempts credential access from the runner process and asserts it is denied.
  Code review checklist item: "Does this change introduce any code path where
  generated content is processed in the Host Agent without sanitization?"
- **Audit trail**: Security events (runner sandbox violations, IPC validation
  failures) are logged to a dedicated security log channel, separate from
  operational logs, per Forge's "no silent failure paths" invariant.
- **Failure mode**: Any violation of Rules 1-5 is treated as a security
  incident, not a bug. The Host Agent fails closed and surfaces the violation
  to the operator gate.

## References

- Forge Engineering Standards (Tier 1 invariants -- no eval/exec of generated code)
- ADR-0o01: Cross-TRD Precedence Hierarchy (Tier 1/Tier 2 precedence model)
- TRD-1: App Shell (§ XPC boundary, Keychain access patterns)
- TRD-9: Mac CI Runner (§13 -- runner security and isolation)
ADR002_EOF
