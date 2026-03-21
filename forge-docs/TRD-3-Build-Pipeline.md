# TRD-3-Build-Pipeline

_Source: `TRD-3-Build-Pipeline.docx` — extracted 2026-03-21 21:32 UTC_

---

# TRD-3: Build Pipeline and Iterative Code Quality Engine

Technical Requirements Document — v4.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-3: Build Pipeline and Iterative Code Quality Engine
Version | 4.0
Status | Updated — Native Output Requirement (March 2026)
Author | YouSource.ai
Previous Version | v3.0 (2026-03-20)
Depends on | TRD-1, TRD-2 v2, TRD-5, TRD-13, TRD-14, TRD-15

## What Changed from v3.0

One targeted addition. All sections from v3.0 are unchanged.

Addition in v4.0: - §5d — Native output enforcement gate (new pre-commit check) - §9a — Wrapper detection in the CI fix loop

## 5d. Native Output Enforcement Gate (New in v4.0)

### 5d.1 Why This Exists

In 2026, Apple began rejecting App Store submissions from AI coding platforms that generate wrapper applications rather than native compiled code. The underlying issue is structural: tools that promise “describe it and it appears” in seconds take a shortcut — they generate a runtime that interprets or loads other generated code rather than generating real compiled source. Apple’s review process cannot evaluate such apps deterministically, so they fail review.

This is not an AI policy. It is a basic App Store rule that has always existed. The same rule applies to enterprise deployment, government security requirements, and corporate IT controls. Any software that loads or evaluates code at runtime is not reviewable, not auditable, and not signable as a deterministic artifact.

The Consensus Engine (TRD-2 §4.4) prohibits wrapper output at the generation level. This section specifies the build pipeline enforcement that catches any violation before it reaches a GitHub PR.

### 5d.2 Pre-Commit Native Output Check

The pre-commit gate runs between code generation and the ruff gate. It is non-bypassable.

WRAPPER_PATTERNS = [
    # Dynamic code execution
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'importlib\.import_module\(',
    r'__import__\s*\(',
    r'compile\s*\(.*exec',

    # Runtime code loading
    r'open\([^)]+\)\.read\(\).*exec',
    r'subprocess.*python.*generated',

    # Template placeholder patterns
    r'\{\{[A-Z_]+\}\}',           # {{PLACEHOLDER}} style
    r'###\s*FILL\s*IN',           # ### FILL IN style
    r'#\s*TODO:.*implement',      # # TODO: implement style (hard fail)
]

def check_native_output(code: str, file_path: str) -> list[str]:
    """
    Check generated code for prohibited wrapper patterns.
    Returns list of violation descriptions, empty if clean.
    """
    violations = []

    # Skip test files — eval() is acceptable in test harnesses
    if 'test_' in Path(file_path).name:
        return []

    for pattern in WRAPPER_PATTERNS:
        matches = re.findall(pattern, code, re.MULTILINE | re.IGNORECASE)
        if matches:
            violations.append(
                f"Prohibited wrapper pattern in {file_path}: "
                f"'{matches[0]}' — see TRD-2 §4.4"
            )

    # Thin file check — a file under 10 lines that only imports and dispatches
    # is almost certainly a wrapper, not a real implementation
    lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith('#')]
    if len(lines) < 10:
        non_import_lines = [l for l in lines if not l.startswith('import ')
                           and not l.startswith('from ')]
        if len(non_import_lines) <= 2:
            violations.append(
                f"Generated file {file_path} appears to be a stub or wrapper "
                f"({len(lines)} substantive lines). Must be a complete implementation."
            )

    return violations

### 5d.3 Gate Behavior

If check_native_output() returns violations:

The violations are logged as a pre_commit_native_output_failure audit event

The failure is injected into the fix loop as the first error message:

NATIVE OUTPUT VIOLATION: {violation description}

The generated code contains a prohibited wrapper pattern. This fails
App Store review and enterprise deployment requirements.

Rewrite as a complete native implementation that:
- Implements the functionality directly, not via eval() or exec()
- Contains real classes, functions, and logic — not a dispatcher
- A human engineer could read and own without agent involvement

The fix loop treats this as a test failure — same 20-pass escalation applies

The PR is not committed to GitHub until the check passes

### 5d.4 The Deployment Contract

Every PR merged through this pipeline carries an implicit deployment contract:

The output of this pipeline is production-grade software that: - Compiles or executes directly without agent-managed intermediary layers - Can be submitted to the App Store, deployed to an enterprise environment, or installed on an air-gapped system - Passes security audit because its behavior is deterministic and reviewable - Can be maintained by a human engineering team after the agent completes the build

This is the distinction between a prototype and a product. Every competitor in the market produces prototypes. This pipeline produces products.

## 9a. Wrapper Detection in CI Fix Loop (New in v4.0)

The CI fix loop (§13 in v2.0) fetches GitHub Actions annotations after CI failure. It now also runs check_native_output() on the committed code before attempting CI fixes.

Rationale: a wrapper that passes local tests may still fail App Store review or enterprise deployment. Catching it at the CI stage — before a human reviews the PR — is better than discovering it post-merge.

async def _run_ci_fix_loop(self, exc: PRExecution, thread: BuildThread) -> bool:
    """CI fix loop with native output check."""

    # Native output check before any CI interaction
    violations = check_native_output(exc.impl_code, exc.spec.impl_files[0])
    if violations:
        chat_print(
            f"  ✗ Native output violation detected before CI:\n"
            + "\n".join(f"    {v}" for v in violations)
        )
        # Inject into fix loop as a synthetic CI failure
        exc._ci_failure_annotation = "\n".join(violations)
        # Re-run fix loop with wrapper violation as the error
        return await self._run_local_fix_loop_with_error(
            exc, thread,
            error="\n".join(violations),
            error_type="native_output_violation"
        )

    # Normal CI fix loop follows...

## Appendix: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial specification
2.0 | 2026-03-20 AM | YouSource.ai | Production implementation: 20-pass loop, CI fix loop, sanitization, StateAutosave, GitHub JSON backup, impl_files fix, patch sentinel
3.0 | 2026-03-20 PM | YouSource.ai | Multi-turn fix loop, grounding system prompt, full acceptance criteria in context, OI13 noise fix, docs PR routing, build interface map, 60K context window
4.0 | 2026-03-20 PM | YouSource.ai | Native output enforcement gate (§5d), wrapper detection in CI fix loop (§9a). Driven by Apple App Store rejection pattern for wrapper-based AI apps. Ensures all pipeline output is production-deployable native code.