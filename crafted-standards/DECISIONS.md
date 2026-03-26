# DECISIONS.md

## [Adopt the documented repository structure as a hard contract]
**Status:** Accepted

**Context:** CraftedAgent operates within a repository whose structure is explicitly defined in the TRDs and README. The `forge-docs/` directory is the source of truth for requirements, and `forge-standards/` contains governing engineering documents. The subsystem must behave predictably against this layout rather than infer structure dynamically.

**Decision:** Treat the documented repository layout as mandatory. Read requirements from `forge-docs/` before implementation work, preserve `forge-standards/` as the location for governing standards files, and implement CraftedAgent against the declared top-level structure rather than ad hoc discovery.

**Consequences:** Implementation must not relocate, rename, or reinterpret core repository roots. Features that depend on requirements, standards, or generated artifacts must resolve them from the documented locations. Any code that assumes alternate layouts is out of scope unless the repository contract is formally updated.

**Rejected alternatives:**  
- **Infer repository structure dynamically at runtime:** Rejected because it weakens determinism and risks operating on the wrong files or missing governing documents.  
- **Allow multiple equivalent layouts by convention:** Rejected because it increases complexity and undermines the TRDs as the authoritative contract.  
- **Treat README examples as non-binding guidance:** Rejected because the subsystem depends on these paths for safe and repeatable operation.

## [Require pre-modification review of critical files]
**Status:** Accepted

**Context:** Several files are identified as critical because they define core generation flow, orchestration, GitHub I/O, path security, and CI generation. Changes to these files have outsized impact on system safety and correctness.

**Decision:** Require any change touching `src/consensus.py`, `src/build_director.py`, `src/github_tools.py`, `src/path_security.py`, or `src/ci_workflow.py` to be treated as a high-scrutiny modification. Read and assess the file’s system role before editing, and preserve its documented invariants.

**Consequences:** Implementation work must explicitly account for cross-cutting effects before modifying these files. Reviews and tests for these files must be stricter than for ordinary modules. Refactors that obscure their responsibilities or bypass their safeguards are disallowed.

**Rejected alternatives:**  
- **Treat all files uniformly:** Rejected because these modules define subsystem boundaries and failure here propagates globally.  
- **Rely only on tests to catch mistakes in critical files:** Rejected because tests do not fully substitute for preserving architectural constraints and security boundaries.  
- **Permit convenience edits without prior file review:** Rejected because undocumented assumptions in these files can break orchestration, security, or CI behavior.

## [Centralize GitHub I/O in `src/github_tools.py`]
**Status:** Accepted

**Context:** The TRDs identify `src/github_tools.py` as the location for all GitHub I/O, including path validation, rate limiting, and SHA protocol handling. Distributing GitHub operations across modules would duplicate safety logic and create inconsistent behavior.

**Decision:** Route all GitHub reads and writes through `src/github_tools.py`. Do not implement direct GitHub I/O elsewhere in CraftedAgent.

**Consequences:** Modules needing repository content, commits, branches, PR updates, or related remote operations must call the centralized interface. Path validation, rate limiting, and SHA handling remain consistent. New GitHub capabilities must extend the central module rather than bypass it.

**Rejected alternatives:**  
- **Allow each feature module to call GitHub APIs directly:** Rejected because it fragments security and protocol handling.  
- **Wrap only write operations centrally and leave reads decentralized:** Rejected because correctness also depends on consistent read semantics and rate limiting.  
- **Move GitHub logic into orchestration code:** Rejected because it couples pipeline control flow to transport details and weakens reuse.

## [Enforce path security through `src/path_security.py` for every write]
**Status:** Accepted

**Context:** The TRDs define `src/path_security.py` as the security boundary and state that every write path must pass through it. Path handling is a primary trust boundary because CraftedAgent can generate or modify repository content.

**Decision:** Validate every filesystem and repository write path through `src/path_security.py` before performing the write. Do not permit alternate validation paths or write bypasses.

**Consequences:** All write-capable code must depend on the security boundary. Utility functions that create, update, move, or delete files must integrate the shared validator. Hidden or convenience write paths are prohibited. Security fixes in the boundary propagate system-wide.

**Rejected alternatives:**  
- **Perform local validation in each module:** Rejected because duplicated validation diverges and creates bypass risk.  
- **Validate only external or user-supplied paths:** Rejected because generated paths can also be unsafe or malformed.  
- **Trust repository-relative paths without validation:** Rejected because relative paths can still escape intended roots or violate policy.

## [Use an explicit allowlist of writable root directories]
**Status:** Accepted

**Context:** Lessons learned from GitHub integration show that commits to unexpected root directories fail silently or are rejected by path security guards. Standard project roots must be explicitly allowed, including dot-prefixed roots such as `.github`.

**Decision:** Enforce a root-directory allowlist for writes and commits. At minimum, support the standard allowed roots: `src`, `tests`, `docs`, `scripts`, `.github`, `tools`, `schemas`, `contracts`, and `configs`. Require explicit policy updates to add new writable roots.

**Consequences:** CraftedAgent may write only within approved repository roots. Dot-prefixed roots are not implicitly trusted and must be explicitly listed. New project layouts require deliberate policy extension rather than opportunistic writes. Silent failures caused by unexpected roots are reduced.

**Rejected alternatives:**  
- **Allow writes anywhere under the repository root:** Rejected because it weakens containment and conflicts with path-security expectations.  
- **Blacklist a few dangerous paths instead of allowlisting roots:** Rejected because deny-lists are incomplete and easier to bypass.  
- **Special-case `.github` outside normal validation:** Rejected because it creates inconsistent security behavior for a sensitive directory.

## [Generate CI workflows via `src/ci_workflow.py` only]
**Status:** Accepted

**Context:** The TRDs identify `src/ci_workflow.py` as the module that generates CI workflows, and the README specifies required workflows including `crafted-ci.yml` on `ubuntu-latest` and `crafted-ci-macos.yml` for Swift projects. Workflow generation is a governed output, not an ad hoc file write.

**Decision:** Generate CI workflow files exclusively through `src/ci_workflow.py`. Produce the standard workflow set required by the documented pipeline, including Linux and macOS variants where applicable.

**Consequences:** CI behavior remains consistent across generated pull requests. Workflow file shape and naming are controlled centrally. Direct templating or manual file emission from unrelated modules is disallowed. Changes to workflow policy must be implemented in the generator.

**Rejected alternatives:**  
- **Let each language or feature module emit its own workflow YAML:** Rejected because it fragments CI policy and naming conventions.  
- **Store static workflow files and copy them blindly:** Rejected because project-specific generation requirements need controlled adaptation.  
- **Allow orchestration code to write workflows directly:** Rejected because CI policy belongs in the dedicated generator boundary.

## [Implement the build pipeline as staged orchestration with mandatory checkpoints]
**Status:** Accepted

**Context:** The README defines a staged build pipeline and requires that every state transition be checkpointed, including per-PR stages such as `branch_opened → code_generated → tests_passed → committed → ci_passed`. Gate decisions must be recorded.

**Decision:** Model CraftedAgent execution as explicit pipeline stages with persisted checkpoints at every transition. Record per-PR state transitions and gate outcomes as first-class execution data.

**Consequences:** Execution becomes restartable, auditable, and debuggable. Orchestration code must emit checkpoint events rather than hold state only in memory. Features that skip stages, mutate state implicitly, or avoid persistence are disallowed. Recovery logic must resume from checkpoints rather than recompute blindly.

**Rejected alternatives:**  
- **Use a single monolithic run state:** Rejected because it prevents granular recovery and obscures failures.  
- **Checkpoint only major milestones:** Rejected because the documented contract requires every transition to be checkpointed.  
- **Keep transition history only in logs:** Rejected because logs are insufficiently structured for reliable resume and audit behavior.

## [Constrain orchestration complexity to a cyclomatic complexity of 15 per stage]
**Status:** Accepted

**Context:** The README requires every stage to have a maximum cyclomatic complexity of 15, and `src/build_director.py` is explicitly called out as strictly enforcing this limit. The constraint exists to keep orchestration understandable and maintainable.

**Decision:** Keep each pipeline stage implementation at or below cyclomatic complexity 15. Refactor control flow into smaller units when a stage risks exceeding the limit, and preserve this constraint especially within `src/build_director.py`.

**Consequences:** Stage logic must be decomposed into focused functions and helpers. Large conditional chains, mixed concerns, and embedded policy branches are constrained. Complexity budgeting becomes part of implementation and review. Some convenience implementations will be rejected even if functionally correct.

**Rejected alternatives:**  
- **Apply the complexity limit only to the overall pipeline, not individual stages:** Rejected because local stage complexity is the documented constraint and the main maintainability risk.  
- **Treat 15 as an advisory threshold:** Rejected because the requirement is explicit and tied to core orchestration code.  
- **Permit exceptions for “central” modules like `build_director.py`:** Rejected because those modules most need the guardrail.

## [Preserve the documented validation and fix loop sequence]
**Status:** Accepted

**Context:** The build pipeline specifies a validation sequence of `ast.parse → ruff → import check`, followed by a fix loop that runs `pytest` for up to 20 attempts using failure-type-aware strategy. This sequence is part of the expected quality-control behavior of generated changes.

**Decision:** Execute validation in the documented order and implement the fix loop with a hard maximum of 20 pytest-driven attempts. Use failure-type-aware remediation rather than generic repeated retries.

**Consequences:** Validation logic must preserve sequence semantics and stop conditions. Components may not reorder linting and syntax checks arbitrarily. Retry behavior must be bounded and informed by failure type. Infinite or open-ended repair loops are prohibited.

**Rejected alternatives:**  
- **Run all validators in arbitrary or parallel order:** Rejected because the documented pipeline establishes a deterministic sequence with meaningful dependency ordering.  
- **Retry until success with no fixed cap:** Rejected because it can waste resources and mask persistent failures.  
- **Use identical remediation on every failure:** Rejected because the pipeline explicitly calls for failure-type-aware strategy.

## [Require an operator gate before merge]
**Status:** Accepted

**Context:** The README defines Stage 6 as a gate where the operator approves or corrects before merge, and every gate decision must be recorded. CraftedAgent is therefore not authorized to perform an unconditional autonomous merge.

**Decision:** Require explicit operator approval or correction before merge. Record the gate decision as part of checkpointed execution state, and do not bypass this gate.

**Consequences:** Merge automation must remain human-gated. CraftedAgent may prepare changes, tests, commits, and CI status, but final merge progression depends on operator action. Systems that assume full autonomy must integrate an approval step or stop before merge.

**Rejected alternatives:**  
- **Auto-merge once tests and CI pass:** Rejected because it violates the documented Stage 6 gate.  
- **Treat absence of objection as approval:** Rejected because the requirement is for explicit approval or correction.  
- **Record gate decisions only informally:** Rejected because gate outcomes must be checkpointed and auditable.