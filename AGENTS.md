# AGENTS.md — Consensus Dev Agent

Instructions for AI agents working in this repository. Read this before making any change.

---

## Repository Identity

**Product:** Consensus Dev Agent — a native macOS AI coding agent.
**Architecture:** Two-process. Swift shell (UI, auth, Keychain, XPC) + Python backend (consensus, pipeline, GitHub).
**Specification:** 12 TRDs in `forge-docs/`. They are the source of truth. Code must match them.
**Security model:** TRD-11 governs all components. Read it before touching security-relevant code.

---

## Before You Write Any Code

1. **Find the TRD that owns the component you are modifying.** Check the TRD Index in `README.md`.
2. **Read the relevant TRD sections** — especially: interfaces, error contracts, security, testing requirements.
3. **Check TRD-11** if your change touches credentials, external content, generated code, or CI.
4. **Run the existing tests** before making changes: `cd src && pytest ../tests/ -v --tb=short`

---

## Repository Structure

```
forge-docs/                      ← ALL TRDs and PRDs live here. Read before building.
  TRD-1-v1.1-macOS-App-Shell.docx
  TRD-2-Consensus-Engine.docx
  TRD-3-Build-Pipeline.docx
  TRD-4-Multi-Agent-Coordination.docx
  TRD-5-GitHub-Integration.docx
  TRD-6-Holistic-Code-Review.docx
  TRD-7-TRD-Development-Workflow.docx
  TRD-8-UIUX-Design-System.docx
  TRD-9-Mac-CI-Runner.docx
  TRD-10-Document-Store.docx
  TRD-11-Security-Threat-Model.docx
  TRD-12-Backend-Runtime-Startup.docx

forge-standards/                 ← Coding standards, interface contracts, decisions
  ARCHITECTURE.md
  INTERFACES.md
  DECISIONS.md
  CONVENTIONS.md

src/                             ← Python backend
  agent.py                       ← Entry point, REPL, version
  build_director.py              ← Pipeline orchestration (calls consensus.run())
  consensus.py                   ← ConsensusEngine — parallel generation + arbitration
  providers.py                   ← ClaudeProvider, OpenAIProvider, GitHubProvider
  build_ledger.py                ← BuildLedger — multi-engineer coordination
  github_tools.py                ← GitHubTool — all GitHub API calls
  document_store.py              ← DocumentStore — embeddings, FAISS, retrieval
  ci_workflow.py                 ← forge-ci.yml and forge-ci-macos.yml generation
  config.py                      ← AgentConfig — all configuration
  api_errors.py                  ← classify_api_error(), is_transient_error()
  path_security.py               ← validate_write_path() — must be called before every write

ForgeAgent/                      ← Swift/SwiftUI application shell (TRD-1)
ForgeAgentTests/                 ← XCTest suites (TRD-9)
tests/                           ← Python test suite
.github/workflows/
  forge-ci.yml                   ← Ubuntu CI (Python, Go, TypeScript, Rust)
  forge-ci-macos.yml             ← Mac CI (Swift, xcodebuild) — requires self-hosted runner
```

---

## The Core Loop

When `/prd start <intent>` is called:

```
ScopeStage → PRDPlanStage → PRDGenStage → PRPlanStage
    → for each PR:
        CodeGenStage → ThreePassReview → CIGateStage → OperatorGateStage
```

Each stage is a separate class. Max cyclomatic complexity 15 per function. State checkpointed after every stage via `ThreadStateStore`. Never modify the stage sequence — it is in TRD-3.

---

## Consensus Engine Usage

Always pass language:

```python
result = await self._consensus.run(
    task=f"Implement: {spec.title}",
    context=context_string,
    language=spec.language,   # "python" | "swift" | "go" | "typescript" | "rust"
)
code = result.final_code
```

`language="swift"` selects `SWIFT_GENERATION_SYSTEM` — 14 Swift-specific rules.
`language="python"` selects `GENERATION_SYSTEM` — security-focused Python rules.

Never call providers directly from pipeline code. Always go through `ConsensusEngine.run()`.

---

## Document Store Usage

```python
# Context for generation (primary use case)
ctx = self._doc_store.auto_context(
    query=f"{thread.subsystem} {spec.title}",
    project_id=project_id,
    doc_filter=thread.relevant_docs or None,   # restrict to relevant TRDs
    max_chars=24_000,
)

# Load a specific document (e.g. PRODUCT_CONTEXT.md)
content = self._doc_store.get_document_content("PRODUCT_CONTEXT.md", project_id)
```

`auto_context()` returns text already wrapped in injection-defense delimiters. Append it to the user prompt — never the system prompt.

---

## GitHub Operations

```python
# ALL GitHub ops go through GitHubTool. Never use the GitHub API directly.
self._github.commit_file(branch, path, content, message)
self._github.create_pr(branch, title, body)
self._github.get_file(path)

# Validate paths before ANY write
from path_security import validate_write_path
safe_path = validate_write_path(user_supplied_path)  # raises on traversal
```

Branch naming convention (mandatory):
`forge-agent/build/{engineer_id}/{subsystem_slug}/pr-{N:03d}-{title_slug}`

---

## Error Handling Patterns

**Transient API errors (529, 500):**
```python
# In _claude_json: retry after 10s, then fall back to OpenAI
# In consensus.py: retry with the other provider
# Never retry indefinitely — max 3 attempts total
```

**GitHub rate limits:**
```python
# 403 primary: exponential backoff starting at 60s
# 429 secondary: respect Retry-After header exactly
# ETag caching on all polling endpoints
```

**Gate failures:**
```python
# Gates never auto-resolve. They wait.
# If backend restarts mid-gate: gate state is lost, operator must re-approve.
# No undo on gate decisions — document this explicitly.
```

**SECURITY_REFUSAL in LLM output:**
```python
# STOP. Do not retry. Do not rephrase.
# Emit error card. Gate. Log full prompt context.
# Operator must explicitly override.
```

---

## CI Routing

| Language | Runner | Workflow file |
|----------|--------|--------------|
| Python, Go, TypeScript, Rust | `ubuntu-latest` | `forge-ci.yml` |
| Swift | `[self-hosted, macos, xcode, x64]` | `forge-ci-macos.yml` |

If Swift files change and the Mac runner is offline: CI job queues and waits. Never mark Swift CI as passed without the Mac runner result.

If `swiftc` is not available locally: log a warning, return synthetic pass for the type-check step, note that real validation requires the Mac runner. Do not fail the pipeline.

---

## Version Management

VERSION file and `pyproject.toml` must always match. The test `TestVersionConsistency.test_version_matches_pyproject` enforces this.

When bumping version: update BOTH files.
```bash
echo "38.XX.0" > VERSION
sed -i 's/version = "38.YY.0"/version = "38.XX.0"/' pyproject.toml
```

---

## Security Checklist (Run Before Every PR)

- [ ] No hardcoded credentials, keys, or tokens in any string literal
- [ ] No `shell=True` in any subprocess call
- [ ] No `eval()` or `exec()` on any external content
- [ ] No HTTP response bodies in log statements
- [ ] All new file write paths pass through `path_security.validate_write_path()`
- [ ] All new document chunks pass through `_scan_for_injection()` before storage
- [ ] External content only in user prompt — never system prompt
- [ ] New LLM generation calls use `self._gen_system` (language-aware), not hardcoded string
- [ ] New XPC message types: unknown message types are discarded, not raised

---

## What Generates What

| You want | Call this |
|----------|-----------|
| Implementation code for a PR | `ConsensusEngine.run(task, context, language)` |
| Tests for a PR | `PRPlanner.generate_tests(spec, impl_code)` |
| PRD document | `PRDPlanner.generate_prd(item, context)` |
| PR plan for a PRD | `PRPlanner.plan_prs(prd_result, thread)` |
| TRD document | `TRDWorkflow.generate_trd(session)` |
| Holistic review | `ReviewDirector.run(branch, scope, lenses)` |
| Context string for any of the above | `DocumentStore.auto_context(query, project_id)` |

---

## Critical Files — Read Before Modifying

| File | Why It Matters |
|------|---------------|
| `src/consensus.py` | Core generation loop — changes here affect every PR the agent builds |
| `src/build_director.py` | Pipeline orchestration — complexity 15 limit strictly enforced |
| `src/github_tools.py` | All GitHub I/O — path validation, rate limiting, SHA protocol |
| `src/path_security.py` | Security boundary — every write path must pass through here |
| `src/ci_workflow.py` | Generates the YAML that runs in CI — template bugs break every build |
| `ForgeAgent/XPCBridge.swift` | The bridge between Swift and Python — wire protocol is TRD-1 S6 |
| `ForgeAgent/AuthManager.swift` | Touch ID + Keychain — biometric failures must lock session, not degrade |
| `.github/workflows/forge-ci-macos.yml` | Mac runner workflow — YAML errors break all Swift CI |

---

## Forbidden Patterns

These will fail code review. Do not write them.

```python
# FORBIDDEN: shell injection
subprocess.run(cmd, shell=True)

# FORBIDDEN: credential in log
logger.info(f"Using key: {api_key}")

# FORBIDDEN: credential in prompt
system = f"Use this key: {self._config.anthropic_api_key}"

# FORBIDDEN: direct execution of generated code
exec(result.final_code)
eval(result.final_code)

# FORBIDDEN: path traversal
open(f"../{user_input}")  # must use path_security.validate_write_path()

# FORBIDDEN: blind GitHub write (no SHA)
github.create_file(path, content)  # use commit_file() which handles SHA

# FORBIDDEN: context in system prompt
system = f"Context: {doc_store.auto_context(query)}"  # context goes in user prompt

# FORBIDDEN: ignoring SECURITY_REFUSAL
if "SECURITY_REFUSAL" in output:
    output = await self._generate_openai(prompt)  # WRONG — do not retry
```

```swift
// FORBIDDEN: force unwrap
let value = optional!

// FORBIDDEN: LLM API call from Swift
let client = AnthropicClient(apiKey: keychainValue)

// FORBIDDEN: Keychain read for backend
let token = KeychainKit.read("github_token")  // Python reads nothing from Keychain
// Only Swift reads Keychain, only to deliver via XPC
```
