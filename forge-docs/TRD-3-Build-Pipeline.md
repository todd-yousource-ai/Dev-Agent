# TRD-3-Build-Pipeline

_Source: `TRD-3-Build-Pipeline.docx` — extracted 2026-03-20 00:25 UTC_

---

TRD-3

Build Pipeline and 3-Pass Review

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-3: Build Pipeline and 3-Pass Review
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-1 (App Shell), TRD-2 (Consensus Engine), TRD-5 (GitHub)
Required by | TRD-4 (Multi-Agent Coordination references BuildThread and ledger)
Language | Python 3.12
Replaces | build_director._stage_interleaved() (complexity 88) + agent.main() (complexity 84)

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Build Pipeline — the directed, human-in-the-loop system that takes a plain-language build intent and produces merged pull requests in a GitHub repository.

The Pipeline owns:

All 8 pipeline stages — from scope confirmation through CI gate

The 3-pass iterative review cycle (Stage 6) that calls the Consensus Engine

The BuildThread state object and its persistence across restarts

All operator gate interactions — displaying options, reading responses, routing decisions

The resume protocol — restarting a build session from the last checkpoint

The REPL command router — dispatching /prd, /patch, /ledger, /clear, etc.

Error escalation — routing failures to FailureHandler, surfacing errors to UI

SCOPE | TRD-3 specifies the pipeline logic and stage contracts. It does NOT specify: consensus generation internals (TRD-2), GitHub API operations (TRD-5), multi-agent coordination (TRD-4), or UI rendering (TRD-8).

# 2. Pipeline Overview

## 2.1 Stage Sequence

BUILD PIPELINE — STAGE SEQUENCE

/prd start
    │
    ▼
Stage 1: ScopeStage
    Operator confirms intent → BuildThread created
    Checkpoint: BuildThread saved to ThreadStateStore
    │
    ▼
Stage 2: PRDPlanStage
    Consensus decomposes intent into ordered PRD list
    Operator approves plan (or corrects once)
    Checkpoint: prd_plan saved, PRD_PLAN.md committed to GitHub
    │
    ▼  ─────────────── FOR EACH PRD ──────────────────────────────
    │
Stage 3: PRDGenerationStage
    Consensus generates PRD document
    .docx exported locally for operator review
    Operator: yes / skip / stop / [correction → regenerate]
    Checkpoint: approved PRD committed to GitHub
    │
Stage 4: PRPlanStage
    Consensus generates full ordered PR list for this PRD
    Auto-committed to GitHub (no gate)
    Checkpoint: pr_plan saved to BuildThread
    │
    ▼  ─────────────── FOR EACH PR ───────────────────────────────
    │
Stage 5: CodeGenerationStage
    Consensus generates implementation + test files
    path_security validates all file paths
    OI-13 gate checked before generation
    │
Stage 6: ThreePassReviewStage  ← NEW
    Pass 1: Correctness + Spec Compliance
    Pass 2: Performance + Edge Cases
    Pass 3: Security + Optimization
    Each pass: Claude reviews, GPT reviews, Claude synthesizes
    Confidence gate: skip Pass 3 if Passes 1+2 produce no changes
    Major-change gate: flag for operator if structural rewrite detected
    │
Stage 7: TestStage
    Tests run locally via TestRunner
    Retry loop: up to MAX_TEST_RETRIES fix cycles
    Syntax error fast-path: skip fix loop, regenerate directly
    Failure escalation: FailureHandler after MAX_RETRIES
    Checkpoint: completed PR saved to BuildThread
    │
Stage 8: CIGate
    PR pushed as draft, CI triggered
    Poll or webhook for GitHub Actions result
    CI pass → PR marked ready for review
    CI fail → error card, operator decides retry/skip/stop
    │
    ▼  ─────────────── END FOR EACH PR ───────────────────────────
    │
    ▼  ─────────────── END FOR EACH PRD ──────────────────────────
    │
BUILD COMPLETE
    Summary card: PRDs done, PRs merged, total cost, GitHub URL

## 2.2 Complexity Budget

The original _stage_interleaved() had McCabe complexity 88. This TRD mandates the following maximums for all pipeline classes:

Class | Max Complexity | Current (pre-refactor) | Note
ScopeStage.run() | 12 | ~12 (part of _stage_interleaved) | Already acceptable
PRDPlanStage.run() | 15 | ~15 | Already acceptable
PRDGenerationStage.run() | 15 | ~20 (part of monolith) | Needs cleanup
PRPlanStage.run() | 10 | ~10 | Already acceptable
CodeGenerationStage.run() | 15 | ~20 | Needs cleanup
ThreePassReviewStage.run() | 15 | New — specify correctly from start | 
TestStage.run() | 15 | ~15 (test_runner.run) | Already acceptable
CIGate.run() | 10 | ~8 | Already acceptable
CommandRouter.handle() | 12 | 84 (entire main() REPL) | Major refactor
Per-command handler | 10 | Varies — most acceptable | 
BuildDirector._orchestrate() | 20 | 88 (entire _stage_interleaved) | Replaced by stage classes

# 3. BuildThread v2 Schema

## 3.1 Core Dataclass

from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class BuildThread:
    """
    Shared state object passed between all pipeline stages.
    One BuildThread per build session. Persisted after every stage checkpoint.
    
    Ownership rules:
    - Stage 1 (ScopeStage) creates the BuildThread and owns: intent,
      subsystem, scope_statement, branch_prefix, relevant_docs
    - Stage 2 (PRDPlanStage) owns: prd_plan, ledger_build_id
    - Stage 3 (PRDGenerationStage) appends to: prd_results, completed_prd_ids
    - Stage 4 (PRPlanStage) writes to: pr_plans_by_prd
    - Stage 5–8 append to: pr_executions, completed_prs,
      completed_pr_nums_by_prd
    - No stage may modify fields owned by a prior stage
    """

    # ── Identity (owned by Stage 1) ──────────────────────────────
    intent:           str                    # Raw operator intent
    subsystem:        str                    # Derived from docs: "DTL", "Payments", etc
    scope_statement:  str                    # 2-3 sentence scope from docs
    branch_prefix:    str                    # forge-agent/build/{engineer_id}/{subsystem}
    relevant_docs:    list[str]              # Doc names from scope — used for doc_filter

    # ── PRD Plan (owned by Stage 2) ──────────────────────────────
    prd_plan:         list                   # list[PRDItem] — full ordered plan
    ledger_build_id:  str      = ""          # Build ID in shared ledger (TRD-4)

    # ── PRD Results (appended by Stage 3) ────────────────────────
    prd_results:      list     = field(default_factory=list)   # list[PRDResult]
    completed_prd_ids: list[str] = field(default_factory=list) # PRD IDs fully done

    # ── PR Plans (written by Stage 4, per PRD) ───────────────────
    pr_plans_by_prd:  dict     = field(default_factory=dict)   # prd_id → list[PRSpec]

    # ── PR Executions (appended by Stages 5–8) ───────────────────
    pr_specs:         list     = field(default_factory=list)   # Active batch
    pr_executions:    list     = field(default_factory=list)   # list[PRExecution]
    completed_prs:    list     = field(default_factory=list)   # list[PRSpec] done
    completed_pr_nums_by_prd: dict = field(default_factory=dict) # prd_id → [pr_num]

    # ── Lifecycle ─────────────────────────────────────────────────
    state:            str      = "scoping"   # See Section 20 for valid values
    created_at:       float    = field(default_factory=time.time)
    updated_at:       float    = field(default_factory=time.time)

    # ── Internal tracking (not persisted) ────────────────────────
    _manual_batches_approved: int = 0        # For auto-approve threshold

## 3.2 Supporting Dataclasses

### 3.2.1 PRDItem

@dataclass
class PRDItem:
    id:                   str          # "PRD-001", "PRD-002", etc
    title:                str          # Short descriptive title
    summary:              str          # What this PRD builds
    rationale:            str          # Why this PRD exists, what it enables
    dependencies:         list[str]    # IDs of PRDs that must complete first
    estimated_complexity: str          # "low" | "medium" | "high"

### 3.2.2 PRDResult

@dataclass
class PRDResult:
    item:           PRDItem
    claude_prd:     str          # Claude's PRD text
    openai_prd:     str          # GPT's PRD text
    winner:         str          # "claude" | "openai" | "tie"
    rationale:      str          # Why this winner was selected
    final_prd:      str          # The selected PRD text (may be improved)
    duration_sec:   float
    timestamp:      float    = field(default_factory=time.time)
    md_path:        str      = ""  # GitHub path: prds/{subsystem}/{id}.md
                                   # Set after approval, before commit

### 3.2.3 PRSpec

@dataclass
class PRSpec:
    pr_num:               int
    title:                str
    branch:               str          # Full branch name
    summary:              str          # One-line description
    description_md:       str          # Full PR description in markdown
    impl_files:           list[str]    # Files this PR writes (validated by path_security)
    test_files:           list[str]    # Test files this PR writes
    impl_plan:            dict         # Steps for implementation
    test_plan:            dict         # Test strategy
    acceptance_criteria:  list[str]
    language:             str          # "python" | "go" | "typescript" | "rust"
    framework:            str          # "pytest" | "jest" | "go test" | "cargo test"
    security_critical:    bool         # Triggers extra review scrutiny
    depends_on_prs:       list[int]    # PR numbers that must complete first
    estimated_complexity: str          # "low" | "medium" | "high"
    status:               str          # "pending"|"in_progress"|"complete"|"skipped"|"failed"

### 3.2.4 PRExecution

@dataclass
class PRExecution:
    spec:           PRSpec
    pr_number:      Optional[int]  = None  # GitHub PR number after open
    pr_url:         Optional[str]  = None
    impl_code:      str            = ""    # Final implementation after review
    test_code:      str            = ""    # Final test code
    local_passed:   bool           = False
    ci_passed:      bool           = False
    retry_count:    int            = 0
    review_passes_applied: int     = 0     # 0, 1, 2, or 3
    review_changes_made:   bool    = False # True if any review pass modified code
    completed_at:   Optional[float] = None

# 4. ThreadStateStore v2

## 4.1 Persistence Contract

ThreadStateStore is the single persistence mechanism for BuildThread. All pipeline stages save through it — never write thread state directly to disk. Writes are atomic (tmp file + rename).

Checkpoint Event | What is Saved | Stage
Scope confirmed | intent, subsystem, scope_statement, branch_prefix, relevant_docs, state="prd_plan" | Stage 1
PRD plan approved | prd_plan, ledger_build_id, state="prd_gen" | Stage 2
PRD generated | prd_results (appended), state="prd_gen" | Stage 3
PRD approved + committed | completed_prd_ids (appended), md_path set on result | Stage 3
PR plan generated | pr_plans_by_prd (updated for this PRD) | Stage 4
PR implementation complete | pr_executions (appended), completed_pr_nums_by_prd (updated) | Stage 7
PR batch complete | completed_prs (appended), state="pr_pipeline" | Stage 7
Build complete | state="done" | BuildDirector

## 4.2 PersistedThread Schema

@dataclass
class PersistedThread:
    """JSON-serializable representation of BuildThread for disk storage."""
    # Version for future migration
    schema_version:           int   = 2

    # Core identity
    subsystem:                str   = ""
    intent:                   str   = ""
    scope_statement:          str   = ""
    branch_prefix:            str   = ""
    state:                    str   = "scoping"

    # Doc context
    relevant_docs:            list  = field(default_factory=list)

    # PRD plan
    prd_plan:                 list  = field(default_factory=list)  # list[dict]
    completed_prd_ids:        list  = field(default_factory=list)
    ledger_build_id:          str   = ""

    # PR tracking
    pr_plans_by_prd:          dict  = field(default_factory=dict)
    completed_pr_nums_by_prd: dict  = field(default_factory=dict)
    completed_pr_nums:        list  = field(default_factory=list)  # flat list

    # Lifecycle
    prd_count:                int   = 0
    created_at:               float = 0.0
    updated_at:               float = 0.0
    slug:                     str   = ""  # URL-safe subsystem slug

    def __post_init__(self):
        if not self.slug and self.subsystem:
            import re
            self.slug = re.sub(r"[^a-z0-9]+", "-", self.subsystem.lower())[:40]

## 4.3 Atomic Write Protocol

class ThreadStateStore:

    def save(self, thread: BuildThread) -> None:
        import re, time, json
        from dataclasses import asdict
        slug = re.sub(r"[^a-z0-9]+", "-", thread.subsystem.lower())[:40]

        # Serialize — convert dataclass objects to dicts
        persisted = PersistedThread(
            schema_version=2,
            subsystem=thread.subsystem,
            intent=thread.intent,
            scope_statement=thread.scope_statement,
            branch_prefix=thread.branch_prefix,
            state=thread.state,
            relevant_docs=list(thread.relevant_docs),
            prd_plan=[vars(i) if hasattr(i,"__dict__") else i
                      for i in thread.prd_plan],
            completed_prd_ids=list(thread.completed_prd_ids),
            ledger_build_id=thread.ledger_build_id,
            pr_plans_by_prd={k:[vars(s) if hasattr(s,"__dict__") else s
                                for s in v]
                             for k,v in thread.pr_plans_by_prd.items()},
            completed_pr_nums_by_prd=dict(thread.completed_pr_nums_by_prd),
            completed_pr_nums=[p.pr_num for p in thread.completed_prs],
            prd_count=len(thread.prd_results),
            created_at=thread.created_at,
            updated_at=time.time(),
            slug=slug,
        )

        # Atomic write: .tmp → rename
        target = self._state_dir / f"{slug}.json"
        tmp    = self._state_dir / f"{slug}.json.tmp"
        tmp.write_text(
            json.dumps(asdict(persisted), indent=2),
            encoding="utf-8"
        )
        tmp.rename(target)   # Atomic on POSIX
        logger.debug(f"Thread state saved: {slug} (state={thread.state})")

    def load(self, slug: str) -> Optional[dict]:
        path = self._state_dir / f"{slug}.json"
        if not path.exists(): return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Migrate v1 → v2 if needed
            if data.get("schema_version", 1) < 2:
                data = _migrate_thread_v1_to_v2(data)
            return data
        except Exception as e:
            logger.warning(f"Failed to load {slug}: {e}")
            return None

# 5. Stage Interface Contract

from abc import ABC, abstractmethod
from typing import Optional

class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.
    
    Invariants:
    - run() must save to ThreadStateStore at its checkpoint before returning
    - run() must emit at least one card to the UI (via emit_card)
    - run() must not modify fields owned by earlier stages
    - run() must return StageResult — never raise (errors go into StageResult)
    - Max McCabe complexity of run(): 15
    """

    def __init__(
        self,
        thread:       BuildThread,
        consensus:    ConsensusEngine,
        github:       GitHubTool,
        doc_store:    DocumentStore,
        thread_store: ThreadStateStore,
        audit:        AuditLogger,
        emit_card:    Callable[[dict], None],   # XPC card to Swift UI
        emit_gate:    Callable[[dict], Awaitable[str]],  # Gate card, returns response
    ) -> None:
        self.thread       = thread
        self.consensus    = consensus
        self.github       = github
        self.doc_store    = doc_store
        self.thread_store = thread_store
        self.audit        = audit
        self.emit_card    = emit_card
        self.emit_gate    = emit_gate

    @abstractmethod
    async def run(self) -> "StageResult":
        ...


@dataclass
class StageResult:
    success:   bool
    action:    str    # "continue"|"stop"|"skip_prd"|"skip_pr"|"error"
    message:   str    = ""
    error:     Optional[Exception] = None

# 6. Stage 1: ScopeStage

## 6.1 Responsibilities

Parse plain-language intent against loaded TRD documents

Identify subsystem, scope statement, relevant docs, and ambiguities

Resolve ambiguities one at a time — never re-scope (infinite loop risk)

Show operator the scope summary and await confirmation

Create BuildThread on confirmation

Save to ThreadStateStore as first checkpoint

## 6.2 System Prompt

SCOPE_SYSTEM = """You are the build scope analyzer for a software development agent.

Your job: given a plain-language build intent and TRD/PRD documents,
define the precise engineering scope.

Rules:
- Ground every decision in the provided document excerpts
- Do NOT invent requirements not present in the documents
- Do NOT use prior knowledge about the domain — use the documents only
- Flag genuine ambiguities that cannot be resolved from the documents
- "subsystem" should match terminology used in the documents

Respond in JSON only:
{
  "subsystem": "exact name from documents",
  "scope_statement": "2-3 sentences: what will be built, grounded in TRD sections",
  "relevant_docs": ["exact document names from provided context"],
  "ambiguities": ["only gaps not answerable from the documents — max 3"]
}
"""

## 6.3 Ambiguity Protocol

# Ambiguities are resolved ONE AT A TIME — collected, then appended to scope.
# DO NOT re-scope after collecting answers. Re-scoping causes infinite loops
# as the LLM generates new ambiguities in response to the refined scope.

async def _resolve_ambiguities(
    ambiguities: list[str],
    scope_stmt: str,
) -> str:
    """Collect ambiguity answers and append to scope. Never re-scope."""
    clarifications = {}
    for i, amb in enumerate(ambiguities, 1):
        response = await self.emit_gate({
            "gate_type":  "ambiguity",
            "gate_id":    f"ambiguity-{i}",
            "title":      f"Ambiguity {i} of {len(ambiguities)}",
            "body":       amb,
            "options":    ["proceed with TRD defaults", "type your answer"],
        })
        if response in (None, "stop"):
            return None  # Operator cancelled
        clarifications[amb] = response

    # Append clarifications — do NOT call LLM again
    clarification_text = "\n".join(
        f"- {a}: {r}"
        for a, r in clarifications.items()
        if r != "proceed with TRD defaults"
    )
    if clarification_text:
        scope_stmt += f"\n\nOperator clarifications:\n{clarification_text}"
    return scope_stmt

## 6.4 Scope Confirmation Gate

# After ambiguity resolution, one scope confirmation gate:
gate_response = await self.emit_gate({
    "gate_type": "scope_confirm",
    "gate_id":   "scope-confirm",
    "title":     "Confirm Build Scope",
    "body":      scope_summary,  # Formatted subsystem, docs, scope statement
    "options":   ["yes", "no", "correction"],
})

# Response routing:
# "yes" or "ok" or "approve"  → create BuildThread, checkpoint, return continue
# "no" or "stop"              → return StageResult(success=False, action="stop")
# Any other string            → treat as single correction:
#     scope_stmt += f"\nOperator correction: {gate_response}"
#     Proceed with updated scope — DO NOT re-scope via LLM

# RULE: At most one correction accepted. Second correction → prompt again.
# RULE: No recursive scope refinement loops.

# 7. Stage 2: PRDPlanStage

## 7.1 Responsibilities

Run Consensus Engine to decompose scope into ordered PRD list

Display plan to operator with complexity indicators and dependencies

Show estimated cost before commitment

Accept operator approval or single correction (re-decompose once)

Commit PRD_PLAN.md to GitHub on approval

Initialize build ledger entry (TRD-4)

Save checkpoint to ThreadStateStore

## 7.2 Token Budget

DECOMPOSE_MAX_TOKENS = 16_000   # Sufficient for 35-PRD plans
# 8192 was too small — caused truncated PRD lists in v38.37
# 16000 comfortably covers 35 PRDs with dependency descriptions

## 7.3 Correction Protocol

# If operator provides correction text:
# 1. Append correction to intent: f"{thread.intent}\n\nPlan correction: {correction}"
# 2. Re-run decomposition ONCE with updated intent
# 3. Display revised plan
# 4. Ask for final approval (yes/no only — no second correction)
# 5. If no: StageResult(success=False, action="stop")

# RULE: Maximum ONE re-decomposition per stage run.
# If the revised plan is also rejected: build cancelled.
# Rationale: unlimited corrections → unbounded API cost.

## 7.4 PRD_PLAN.md Commit

# Committed to: {branch_prefix}/prds
# Path: prds/{subsystem_slug}/PRD_PLAN.md
# Format: markdown table

| # | ID | Title | Complexity | Dependencies |
|---|---|---|---|---|
| 1 | PRD-001 | Transaction Validation Layer | high | — |
| 2 | PRD-002 | Idempotency Store | medium | PRD-001 |
...

# Commit message: "forge-agent: PRD plan for {subsystem} — {n} PRDs"
# Branch created by _ensure_branch() before first commit
# If commit fails: error card shown, build continues (non-fatal)
# The local ThreadStateStore is authoritative — GitHub commit is for visibility

# 8. Stage 3: PRDGenerationStage

## 8.1 Responsibilities

For each PRDItem in the plan: generate a full PRD via Consensus Engine

Export as .docx to local temp directory for operator review

Show inline preview (first 18 lines) in build stream

Present per-PRD review gate: yes / skip / stop / [correction → regenerate]

Commit approved PRD markdown to GitHub

Mark PRD complete in ThreadStateStore

Skip PRDs already in completed_prd_ids (resume support)

## 8.2 PRD Generation Call

# The PRDPlanner wraps the ConsensusEngine for PRD-specific generation.
# Two retries on timeout before skipping the PRD.

prd_result = None
for attempt in range(2):
    try:
        prd_result = await self.planner.generate_prd(
            item=prd_item,
            doc_filter=self.thread.relevant_docs or None,
        )
        break
    except RuntimeError as e:
        if "timed out" in str(e).lower() and attempt == 0:
            self.emit_card({"card_type":"warning",
                "body": f"PRD generation timed out — retrying once..."})
            continue
        raise

if prd_result is None:
    self.emit_card({"card_type":"error",
        "body": f"PRD generation failed after 2 attempts. Skipping {prd_item.id}."})
    continue  # Skip to next PRD

## 8.3 Correction Protocol

# Correction uses dataclasses.replace() — NEVER mutate prd_item directly.
# Mutating prd_item corrupts the prd_plan for future iterations.

from dataclasses import replace

if isinstance(gate_response, str) and gate_response not in ("yes","skip","stop"):
    # Correction text: regenerate with feedback appended to summary
    corrected_item = replace(
        prd_item,
        summary=f"{prd_item.summary}\n\nCorrections: {gate_response}"
    )
    # Original prd_item is UNCHANGED — corrected_item is a new object
    prd_result = await self.planner.generate_prd(
        item=corrected_item,
        doc_filter=self.thread.relevant_docs or None,
    )
    # Proceed with corrected prd_result — do NOT offer second correction
    # One correction per PRD maximum.

## 8.4 .docx Export Protocol

# .docx is written to macOS temp directory — not to Application Support
# Path: /tmp/forge-prd-{subsystem_slug}-{prd_id}.docx
# If python-docx unavailable: raise clearly — do NOT write plain text to .docx

try:
    docx_path = os.path.join(
        tempfile.gettempdir(),
        f"forge-prd-{_slug(self.thread.subsystem)}-{prd_item.id.lower()}.docx"
    )
    await self.docx_exporter.export_prd_bundle(
        prd_results=[prd_result],
        subsystem=self.thread.subsystem,
        output_path=docx_path,
    )
    self.emit_card({"card_type":"prd_generated",
        "title": f"{prd_item.id}: {prd_item.title}",
        "body":  prd_result.final_prd[:600],   # Preview in stream
        "docx_path": docx_path,
        "winner": prd_result.winner,
    })
except RuntimeError as e:
    # python-docx missing or export failed — show gate without docx
    logger.warning(f"docx export failed: {e}")
    self.emit_card({"card_type":"warning", "body": f"docx export failed: {e}"})

## 8.5 GitHub Commit

# Committed ONLY after operator approves (yes or correction-then-auto-approve)
# Path: prds/{subsystem_slug}/{prd_id.lower()}.md
# Branch: {branch_prefix}/prds

try:
    _safe_commit(
        github=self.github,
        branch=prd_branch,
        path=md_path,
        content=prd_result.final_prd,
        message=f"forge-agent: {prd_item.id} — {prd_item.title[:55]}",
    )
    self.emit_card({"card_type":"progress",
        "body": f"{prd_item.id} committed to GitHub"})
except Exception as e:
    # Commit failure is surfaced to UI — build continues
    # Local ThreadStateStore is authoritative
    self.emit_card({"card_type":"error",
        "body": f"Commit failed for {prd_item.id}: {e}",
        "recoverable": True})

# 9. Stage 4: PRPlanStage

## 9.1 Responsibilities

For each approved PRD: generate a full ordered PR list via PRPlanner

Display the full plan in the build stream

Show estimated PR build cost before execution

Auto-save to BuildThread (no operator gate — plan is visible for audit)

Commit pr-plan.md to GitHub branch for visibility

Update build ledger with PR plan (TRD-4)

## 9.2 PR Numbering

# PR numbers are global within a build session — not per-PRD.
# PRD-001 might have PRs 1–5, PRD-002 has PRs 6–12, etc.
# This makes the build ledger PR references unambiguous.

# PR title format: "PR{NNN} {title}"
# Example: "PR003 Add transaction idempotency check"

# Branch format: {branch_prefix}-pr{NNN}-{slug}
# Example: forge-agent/build/todd/payments-pr003-add-transaction-idempotency-check

## 9.3 PR Plan Commit

# Committed to: {branch_prefix}/prds
# Path: prds/{subsystem_slug}/{prd_id.lower()}-pr-plan.md
# Format: markdown table

| PR | Title | Complexity | Security | Dependencies |
|---|---|---|---|---|
| PR003 | Add transaction idempotency check | high | 🔒 | PR001, PR002 |

# Commit is non-fatal — build continues if GitHub commit fails

# 10. Stage 5: CodeGenerationStage

## 10.1 Responsibilities

For each approved PRSpec: check OI-13 gate, then generate implementation + tests

Validate ALL model-supplied file paths through path_security before any use

Inject prior-PR dependency code as context for dependent PRs

Route MCP components to MCPGenerator

Pass results to Stage 6 (ThreePassReviewStage)

## 10.2 Path Security Gate

# path_security.validate_write_path() is called on EVERY path before use.
# This is the release blocker fix — null-byte injection prevention.
# See path_security.py for full validation rules.

from path_security import validate_write_path

impl_path = validate_write_path(
    spec.impl_files[0] if spec.impl_files else f"src/{_slug(spec.title)}.py",
    context="CodeGenerationStage",
)
# validate_write_path returns "src/untitled.py" on any violation.
# A returned "src/untitled.py" when spec.impl_files was set is logged as a warning.

## 10.3 Dependency Code Injection

# If spec.depends_on_prs is non-empty:
# Fetch the impl_code from completed PRExecution objects for those PR numbers.
# Inject as additional context — the dependent PR sees the actual interface.

prior_code_ctx = ""
if spec.depends_on_prs:
    prior_parts = []
    for dep_num in spec.depends_on_prs:
        for done_exc in self.thread.pr_executions:
            if done_exc.spec.pr_num == dep_num and done_exc.impl_code:
                prior_parts.append(
                    f"=== Prior PR #{dep_num}: {done_exc.spec.title} ===\n"
                    f"File: {done_exc.spec.impl_files[0] if done_exc.spec.impl_files else \"?\"}"
                    f"\n{done_exc.impl_code[:2000]}"
                )
    if prior_parts:
        prior_code_ctx = ("\nDependency code (reference these interfaces):\n"
                          + "\n".join(prior_parts))

# Injected into the consensus user prompt, not the system prompt.
# Capped at 2000 chars per dependency to control token cost.

## 10.4 Unmet Dependency Warning

# If a dependency PR is in depends_on_prs but not yet in pr_executions:
# Warn — do not block. The code will be generated without that context.

completed_nums = {e.spec.pr_num for e in self.thread.pr_executions}
unmet = [n for n in spec.depends_on_prs if n not in completed_nums]
if unmet:
    self.emit_card({"card_type":"warning",
        "body": f"PR #{spec.pr_num} depends on PR(s) {unmet} not yet complete. "
               "Generating without dependency context."})

# 11. Stage 6: ThreePassReviewStage

## 11.1 Overview

The 3-Pass Review Stage is the primary quality gate for generated code. It runs after code generation and before test execution. Each pass uses a different evaluation lens. Both Claude and GPT-4o review independently per pass. Claude synthesizes the feedback and applies targeted fixes.

DESIGN PRINCIPLE | The three passes target different failure modes. Pass 1 catches missing requirements. Pass 2 catches runtime failures. Pass 3 catches security vulnerabilities. Running all three with independent reviewers is more effective than one comprehensive review because reviewers apply focused attention to a single concern.

## 11.2 Pass Structure

REVIEW_PASS_1 = {
    "name": "Correctness and Spec Compliance",
    "focus": "Does this implementation exactly match the PRD specification?",
    "questions": [
        "Does it implement every requirement stated in the PRD?",
        "Are any specified behaviors missing or incorrectly implemented?",
        "Does it add anything NOT specified (scope creep)?",
        "Are all error cases documented in the PRD handled?",
    ],
}

REVIEW_PASS_2 = {
    "name": "Performance and Edge Cases",
    "focus": "Where does this break under realistic conditions?",
    "questions": [
        "What happens under concurrent load?",
        "What inputs cause failures not handled by the code?",
        "What are the failure modes and do they degrade gracefully?",
        "Are there N+1 query patterns, unnecessary allocations, or blocking calls?",
    ],
}

REVIEW_PASS_3 = {
    "name": "Security and Optimization",
    "focus": "What is dangerous or wasteful?",
    "questions": [
        "What is the attack surface? Can inputs trigger unintended behavior?",
        "Is there path traversal, injection, or credential exposure risk?",
        "What can be removed without losing functionality?",
        "Are there computationally expensive operations that could be eliminated?",
    ],
}

## 11.3 Per-Pass Protocol

async def _run_single_pass(
    self,
    pass_config: dict,
    current_code: str,
    prd_context: str,
    spec: PRSpec,
) -> tuple[str, bool]:
    """
    Run one review pass. Returns (updated_code, changes_made).
    Both providers review independently. Claude synthesizes.
    """

    system = _build_review_system(pass_config)
    user   = _build_review_user(current_code, prd_context, spec)

    # Both providers review the SAME code independently
    # generate_single() bypasses arbitration — we want both opinions
    claude_review = await self.consensus.generate_single(
        provider_id="claude",
        system=system, user=user, max_tokens=4096,
    )
    openai_review = await self.consensus.generate_single(
        provider_id="openai",
        system=system, user=user, max_tokens=4096,
    )

    # Parse review responses
    claude_issues = _parse_review_response(claude_review.content)
    openai_issues = _parse_review_response(openai_review.content)

    # Combine issues from both reviewers
    all_issues = _merge_issues(claude_issues, openai_issues)

    if not all_issues:
        # No issues found — return unchanged code
        return current_code, False

    # Emit review card to UI showing what both reviewers found
    self.emit_card({
        "card_type": "review_pass",
        "title":     f"Review Pass {pass_config['number']}: {pass_config['name']}",
        "claude_feedback": _format_issues(claude_issues),
        "openai_feedback":  _format_issues(openai_issues),
        "fix_count": len(all_issues),
    })

    # Claude synthesizes and applies fixes
    synthesis_prompt = _build_synthesis_prompt(current_code, all_issues)
    synthesis = await self.consensus.generate_single(
        provider_id="claude",
        system=SYNTHESIS_SYSTEM,
        user=synthesis_prompt,
        max_tokens=8192,
    )

    if synthesis.success and len(synthesis.content) > 50:
        return synthesis.content, True
    else:
        logger.warning("Synthesis failed — keeping code from before this pass")
        return current_code, False

## 11.4 Confidence Gate

async def run(self, impl_code: str, spec: PRSpec,
              prd_result: PRDResult) -> tuple[str, int]:
    """
    Run all three review passes with confidence gate.
    Returns (final_code, passes_applied).
    """
    prd_ctx = prd_result.final_prd[:3000]  # Context for reviewers
    current = impl_code
    passes_applied = 0
    any_changes = False

    for i, pass_config in enumerate([REVIEW_PASS_1, REVIEW_PASS_2, REVIEW_PASS_3], 1):
        pass_config = {**pass_config, "number": i}

        # CONFIDENCE GATE:
        # If Passes 1 and 2 made no changes, skip Pass 3.
        # Rationale: two passes found nothing — Pass 3 unlikely to find security issues.
        if i == 3 and not any_changes:
            self.emit_card({"card_type":"progress",
                "body": "Review Pass 3 skipped — Passes 1 and 2 found no issues (high confidence)"})
            break

        updated, changed = await self._run_single_pass(
            pass_config, current, prd_ctx, spec
        )
        current = updated
        passes_applied = i

        if changed:
            any_changes = True

            # MAJOR CHANGE GATE:
            # If Pass 1 produces structural rewrite (> 30% line change):
            # Flag for operator review before continuing.
            if i == 1 and _is_major_rewrite(impl_code, updated):
                response = await self.emit_gate({
                    "gate_type": "review_major_change",
                    "gate_id":   f"review-major-{spec.pr_num}",
                    "title":     f"Major Rewrite Detected — PR #{spec.pr_num}",
                    "body":      ("Review Pass 1 produced significant changes. "
                                 "Inspect the diff before continuing."),
                    "options":   ["continue", "stop"],
                })
                if response in ("stop", None):
                    return current, passes_applied

    return current, passes_applied


def _is_major_rewrite(original: str, revised: str) -> bool:
    """Detect if revision changed > 30% of lines — triggers operator gate."""
    orig_lines = set(original.splitlines())
    rev_lines  = set(revised.splitlines())
    if not orig_lines:
        return False
    unchanged = len(orig_lines & rev_lines)
    change_ratio = 1.0 - (unchanged / len(orig_lines))
    return change_ratio > 0.30

## 11.5 Review System Prompts

def _build_review_system(pass_config: dict) -> str:
    return f"""You are a senior code reviewer. Focus exclusively on:
{pass_config["focus"]}

Review questions to address:
{chr(10).join(f"- {q}" for q in pass_config["questions"])}

Respond in JSON only:
{{
  "issues_found": true | false,
  "issues": [
    {{
      "location": "function name or line description",
      "severity": "critical | major | minor",
      "description": "what is wrong",
      "fix": "concrete fix instruction"
    }}
  ]
}}

If issues_found is false, issues must be an empty list.
Be specific — vague feedback like "could be improved" is not actionable.
"""

SYNTHESIS_SYSTEM = """You are applying targeted code fixes.

Rules:
- Apply ONLY the listed fixes
- Do not restructure code not mentioned in the fix list
- Do not change working logic
- Preserve all existing function signatures and public interfaces
- Output the complete file — no truncation, no placeholders

Respond with ONLY the fixed code — no markdown fences.
"""

## 11.6 Issue Merging

def _merge_issues(claude_issues: list, openai_issues: list) -> list:
    """
    Merge issues from both reviewers.
    De-duplicate by location — if both flag the same function,
    keep the more severe issue.
    Critical issues from either reviewer are always included.
    Minor issues: only include if both reviewers agree.
    """
    by_location: dict[str, dict] = {}

    severity_rank = {"critical": 3, "major": 2, "minor": 1}

    for issue in claude_issues + openai_issues:
        loc = issue.get("location", "unknown")
        existing = by_location.get(loc)
        if existing is None:
            by_location[loc] = {**issue, "_count": 1}
        else:
            # Keep higher severity, increment count
            if severity_rank.get(issue["severity"],0) > severity_rank.get(existing["severity"],0):
                by_location[loc] = {**issue, "_count": existing["_count"]+1}
            else:
                existing["_count"] += 1

    # Filter: critical/major always in, minor only if both agreed
    return [
        issue for issue in by_location.values()
        if issue["severity"] in ("critical","major") or issue["_count"] >= 2
    ]

# 12. Stage 7: TestStage

## 12.1 Responsibilities

Write implementation and test files to workspace directory

Run TestRunner (pytest / go test / jest / cargo test depending on language)

On failure: enter retry loop — generate fixes via Consensus Engine

Syntax error fast-path: skip fix loop, regenerate implementation directly

After MAX_TEST_RETRIES: escalate to FailureHandler

On local pass: mark PR as locally passing, save checkpoint

## 12.2 Retry Loop

MAX_TEST_RETRIES = 3

async def run(self, exc: PRExecution) -> StageResult:
    spec = exc.spec

    for attempt in range(MAX_TEST_RETRIES + 1):
        # Write files to workspace
        impl_path, test_path = self.test_runner.write_files(
            impl_code=exc.impl_code,
            test_code=exc.test_code,
            impl_file=spec.impl_files[0] if spec.impl_files else "src/impl.py",
        )

        # Run tests
        result = self.test_runner.run(
            language=spec.language,
            framework=spec.framework,
            test_path=test_path,
            impl_path=impl_path,
        )

        self.emit_card({
            "card_type": "test_result",
            "passed":    result.passed,
            "total":     result.total_tests,
            "failed":    result.failed_tests,
            "attempt":   attempt + 1,
        })

        if result.passed:
            exc.local_passed = True
            exc.retry_count  = attempt
            self.thread_store.save(self.thread)
            return StageResult(success=True, action="continue")

        if attempt == MAX_TEST_RETRIES:
            # Escalate to FailureHandler
            return await self._escalate(exc, result)

        # SYNTAX ERROR FAST-PATH:
        # Skip fix loop, regenerate implementation from scratch.
        # Fix loop cannot fix a syntax error — just wastes tokens.
        if result.has_syntax_error:
            self.emit_card({"card_type":"warning",
                "body": "Syntax error detected — regenerating implementation directly"})
            exc.impl_code = await self._regenerate_impl(spec, exc)
            exc.retry_count += 1
            continue

        # Fix loop: ask Consensus to fix the failing tests
        exc.impl_code = await self._generate_fix(exc, result)
        exc.retry_count += 1

    return StageResult(success=False, action="error",
                       message=f"Tests failed after {MAX_TEST_RETRIES} retries")

# 13. Stage 8: CIGate

## 13.1 Protocol

CI_POLL_INTERVAL_SEC  = 30    # Check every 30 seconds
CI_TIMEOUT_SEC        = 1800  # 30 minutes max wait

async def run(self, exc: PRExecution) -> StageResult:
    # Open draft PR (or update existing)
    pr_num, pr_url = await self._open_or_update_pr(exc)
    exc.pr_number = pr_num
    exc.pr_url    = pr_url

    self.emit_card({"card_type":"pr_opened",
        "pr_number": pr_num, "url": pr_url})

    # If TRD-5 webhook receiver is active: wait for webhook signal.
    # Otherwise: poll.
    ci_result = await self._wait_for_ci(pr_num)

    if ci_result.passed:
        # Mark PR ready for review (remove draft status)
        await self.github.mark_ready_for_review(pr_num)
        exc.ci_passed = True
        return StageResult(success=True, action="continue")
    else:
        # CI failed — show error card and gate
        return await self._handle_ci_failure(exc, ci_result)


async def _handle_ci_failure(
    self, exc: PRExecution, ci_result
) -> StageResult:
    response = await self.emit_gate({
        "gate_type": "ci_failure",
        "gate_id":   f"ci-failure-{exc.spec.pr_num}",
        "title":     f"CI Failed — PR #{exc.spec.pr_num}",
        "body":      f"GitHub Actions failed. {ci_result.failure_summary}",
        "options":   ["retry", "skip", "stop"],
    })
    if response == "retry":
        return StageResult(success=False, action="continue")  # Caller retries
    if response == "skip":
        return StageResult(success=False, action="skip_pr")
    return StageResult(success=False, action="stop")

# 14. Gate Protocol

## 14.1 Gate Card XPC Schema

# Gate cards are sent via XPC to the Swift UI (TRD-1 Section 7.2).
# They block the build stream until the operator responds.

Gate card payload:
{
    "type":      "gate_card",
    "id":        "<UUID>",
    "session_id": "<session UUID>",
    "timestamp": 1710000000000,
    "payload": {
        "gate_id":   "scope-confirm | prd-plan | prd-003-review | ...",
        "gate_type": "scope_confirm | prd_plan | prd_review | ambiguity |
                      ci_failure | review_major_change | cost_limit | oi13_blocked",
        "title":     "Human-readable gate title",
        "body":      "Context — what the operator needs to review",
        "options":   ["yes", "skip", "stop", "correction"],
        "correction_hint": "Optional: hint for the correction text field"
    }
}

## 14.2 Operator Response Routing

gate_type | Valid Responses | Routing
scope_confirm | "yes"/"ok"/"approve" | "no"/"stop" | any other string | yes→continue; no→stop; string→single correction, proceed
prd_plan | "yes" | "no"/"stop" | any other string | yes→continue; no→stop; string→re-decompose once, then final approval
prd_review | "yes" | "skip" | "stop" | any other string | yes→commit+continue; skip→next PRD; stop→build cancelled; string→regenerate with correction
ambiguity | "proceed with TRD defaults" | any other string | Any response→collect, append to scope, continue
ci_failure | "retry" | "skip" | "stop" | retry→wait for new CI run; skip→skip this PR; stop→build cancelled
review_major_change | "continue" | "stop" | continue→proceed with reviewed code; stop→keep reviewed code, stop pipeline
cost_limit | "approve" | "stop" | approve→continue building; stop→build cancelled
oi13_blocked | "single_provider" | "stop" | "increase_limits" | single→continue with one provider; stop→cancel; increase→open Settings

## 14.3 Gate Timeout

# Gates have no automatic timeout — the operator must respond.
# Rationale: this is a human-in-the-loop system. Timeouts on human decisions
# cause unexpected build behavior that is harder to diagnose than a waiting gate.

# Exception: if the app is backgrounded > 30 minutes while a gate is active:
# - Send a macOS notification: "Gate waiting — Forge Agent needs your input"
# - Gate remains open when app returns to foreground
# - Never auto-answer a gate

# 15. Resume Protocol

## 15.1 Checkpoint Guarantees

On restart, the pipeline resumes from the last saved checkpoint. Each checkpoint represents a point where the operator has already made a decision — the pipeline never re-asks a question the operator already answered.

Checkpoint | What Is Resumed | What Is Replayed
After scope confirmed | Subsystem, scope, branch, docs are restored — ScopeStage skipped | None — scope gate not re-shown
After PRD plan approved | PRD plan restored — PRDPlanStage skipped | None — plan approval not re-shown
After PRD approved | Completed PRD IDs checked — approved PRDs skipped | None
Mid-PRD-list | Resume from first PRD NOT in completed_prd_ids | None
After PR plan generated | pr_plans_by_prd restored for in-progress PRD | None
Mid-PR-list | completed_pr_nums_by_prd checked — completed PRs skipped | None

## 15.2 Resume Entry Point

# At agent startup, ThreadStateStore.check_and_offer_resume() is called.
# If incomplete threads exist, operator is offered a numbered list.
# Selecting one restores the BuildThread and calls BuildDirector.run_resume().

async def run_resume(self, saved: dict) -> None:
    """Resume a saved build session."""
    # Restore BuildThread from saved state
    thread = _restore_thread(saved)

    # Restore Consensus Engine budget
    # (session cost starts at 0 on resume — prior session cost not tracked)
    self.consensus.reset_pr_budget()

    # Route to the appropriate stage based on saved state
    if thread.state in ("scoping",):
        # Scope was not confirmed — restart from scope
        await self.run(thread.intent)

    elif thread.state in ("prd_plan",) and not thread.prd_plan:
        # PRD plan was not generated — restart from PRD plan
        await self._stage_prd_plan(thread)

    else:
        # PRD list or PR pipeline — resume in interleaved loop
        await self._stage_interleaved_resume(thread)

## 15.3 Decomp Variable Re-constitution

# The decomp variable (DecompositionResult) is NOT persisted — it is a transient
# object created during Stage 2. On resume, it is re-constituted from prd_plan.

def _restore_decomp_from_plan(prd_plan: list) -> DecompositionResult:
    """Re-constitute a DecompositionResult from the persisted prd_plan list."""
    prd_list = []
    for item in prd_plan:
        if isinstance(item, dict):
            prd_list.append(PRDItem(**{
                k: item.get(k, "") for k in
                ["id","title","summary","rationale","dependencies","estimated_complexity"]
            }))
        else:
            prd_list.append(item)
    return DecompositionResult(
        prd_list=prd_list,
        claude_list=prd_list,   # Not used on resume
        openai_list=prd_list,   # Not used on resume
        decomposition_notes="(restored from saved state)",
        duration_sec=0.0,
    )

# 16. Error Escalation

## 16.1 Error Type Routing

Error Type | Source | Handling | Operator Involved?
ConsensusError | Both providers failed | Retry up to 2x; after 2x → error card + skip or stop gate | Yes — skip/stop gate
OI13BlockedError | Token limit reached | Gate card: single_provider / stop / increase_limits | Yes — must respond
CostLimitError | PR cost exceeded threshold | Gate card: approve override / stop | Yes — must approve
GitHubToolError (commit) | GitHub write failed | Error card with message; build continues (local state is authoritative) | No — non-fatal
GitHubToolError (PR open) | PR could not be opened | Error card; retry once; after retry fail → skip this PR | Yes — implicitly
RuntimeError (timeout) | Generation timed out | Retry once; after 2nd timeout → skip PRD or PR | No — auto
SyntaxError in generated code | Test runner parse fail | Fast-path regenerate (skip fix loop) | No — auto
Test failure after MAX_RETRIES | Tests never passed | FailureHandler escalation → troubleshooting gate | Yes — manual fix
CI failure | GitHub Actions failed | Gate: retry / skip / stop | Yes — must respond
ThreadStateStore write fail | Disk full or permissions | Log error + emit warning card; continue (data may be lost on restart) | No — non-fatal

## 16.2 _execute_pr Top-Level Guard

# Every PR execution is wrapped in a top-level exception guard.
# This prevents a single unexpected error from crashing the entire pipeline.

async def _execute_pr(self, exc: PRExecution) -> bool:
    """Outer guard — delegates to _execute_pr_inner."""
    try:
        return await self._execute_pr_inner(exc)
    except Exception as top_exc:
        logger.exception(f"Unhandled error in PR #{exc.spec.pr_num}: {top_exc}")
        self.emit_card({"card_type":"error",
            "body": f"PR #{exc.spec.pr_num} failed unexpectedly: {top_exc}",
            "recoverable": True})
        exc.spec.status = "failed"
        return False  # Continue to next PR

## 16.3 _safe_commit

def _safe_commit(
    github: GitHubTool,
    branch: str,
    path: str,
    content: str,
    message: str,
    emit_card: Callable,
) -> None:
    """
    Commit a file to GitHub. On failure: emit error card and raise.
    Callers wrap in try/except and decide whether failure is fatal.
    """
    try:
        github.commit_file(branch=branch, path=path,
                           content=content, message=message)
    except GitHubToolError as exc:
        logger.warning(f"Commit failed [{path}]: {exc}")
        emit_card({"card_type":"error",
            "body": f"Commit failed: {path}\nError: {exc}",
            "recoverable": True})
        raise  # Caller decides if fatal

# 17. REPL Decomposition — CommandRouter

## 17.1 Motivation

The current agent.main() function has McCabe complexity 84. Every command handler is a branch in the REPL loop. This TRD mandates a CommandRouter class that dispatches to per-command handler functions, each with max complexity 10.

## 17.2 CommandRouter

class CommandRouter:
    """
    Dispatches REPL commands to handler functions.
    Complexity of handle() must not exceed 12.
    Each command handler must not exceed 10.
    """

    def __init__(self, context: "AgentContext") -> None:
        self.ctx = context
        self._handlers: dict[str, Callable] = {
            "/prd":          self._handle_prd,
            "/patch":        self._handle_patch,
            "/ledger":       self._handle_ledger,
            "/clear":        self._handle_clear,
            "/save":         self._handle_save,
            "/oi13":         self._handle_oi13,
            "/review":       self._handle_review,
            "/monitor":      self._handle_monitor,
            "/docs":         self._handle_docs,
            "/quit":         self._handle_quit,
            "/help":         self._handle_help,
        }

    async def handle(self, raw: str) -> bool:
        """
        Dispatch a raw input string to the appropriate handler.
        Returns True if the REPL should exit.
        """
        raw = raw.strip()
        if not raw:
            return False

        # Match command prefix
        cmd_key = self._match_command(raw)
        if cmd_key:
            handler = self._handlers[cmd_key]
            return await handler(raw)

        # Build intent pattern — route to BuildDirector
        if _is_build_intent(raw):
            self.ctx.emit_card({"card_type":"guidance",
                "body": "Use /prd start to begin a build. Describe your intent there."})
            return False

        # Single-task pattern: "description → src/path/file.py"
        if "->" in raw or "→" in raw:
            await self.ctx.session.handle_task(raw)
            return False

        # Unknown — guide
        self.ctx.emit_card({"card_type":"guidance",
            "body": "Type /help to see available commands."})
        return False

    def _match_command(self, raw: str) -> Optional[str]:
        for key in self._handlers:
            if raw.lower().startswith(key):
                return key
        return None

## 17.3 Command Handler Specifications

Command | Handler Function | Responsibility | Max Complexity
/prd start, /prd | _handle_prd() | Prompt for intent, call BuildDirector.run() or run_resume() | 8
/patch | _handle_patch() | Apply zip patch, check, rollback | 8
/ledger | _handle_ledger() | Subcommands: sync, claim, note, overview | 10
/clear | _handle_clear() | Show/delete local build state files | 6
/save | _handle_save() | Show persisted thread count | 4
/oi13 | _handle_oi13() | Show or resolve token budget status | 6
/review | _handle_review() | Scan open PRs for review comments, drive fix cycle | 10
/monitor | _handle_monitor() | Show background CI watch queue | 4
/docs | _handle_docs() | List loaded documents, reload, sync from GitHub | 8
/quit, /exit | _handle_quit() | Graceful shutdown | 2
/help | _handle_help() | Print command reference | 3

# 18. Audit Trail

## 18.1 Event Schema

# All events written to: {FORGE_LOG_DIR}/audit-YYYY-MM-DD.jsonl
# One JSON object per line. Never truncated — append only.

Required fields on every event:
{
    "event":      "string — event type (see 18.2)",
    "timestamp":  1710000000.0,
    "session_id": "uuid",
    "engineer_id": "todd-gould",
    "data":       {}  // event-specific payload
}

## 18.2 Required Events

Event | When Emitted | data fields
build_start | BuildDirector.run() called | intent, engineer_id
build_scope_confirmed | Stage 1 complete | subsystem, branch_prefix, relevant_docs[]
build_prd_plan_approved | Stage 2 complete | subsystem, total_prds, prd_ids[]
build_prd_generated | Each PRD generated | prd_id, winner, duration_sec, cost_usd
build_prd_approved | Operator approves PRD | prd_id, had_correction: bool
build_prd_skipped | Operator skips PRD | prd_id
build_pr_plan_generated | Stage 4 complete | prd_id, total_prs
build_pr_started | Stage 5 begins for a PR | pr_num, title, branch
build_review_pass | Each review pass completes | pr_num, pass_num, issues_found, changes_made
build_test_result | Each test run | pr_num, passed, total, failed, attempt
build_pr_complete | Stages 5-8 complete | pr_num, local_passed, ci_passed, retry_count, review_passes
build_pr_skipped | PR skipped | pr_num, reason
build_prd_complete | All PRs for a PRD done | prd_id, pr_count
build_complete | All PRDs done | subsystem, prd_count, pr_count, total_cost_usd
build_cancelled | Operator stops build | stage, reason
gate_response | Operator responds to any gate | gate_id, gate_type, response (not correction text)
consensus_result | ConsensusEngine.run() returns | task_type, winner, claude_score, openai_score, cost_usd
error | Any error in pipeline | error_type, message, recoverable

# 19. Complexity Budget

All pipeline stage classes and the CommandRouter must meet these limits. McCabe complexity is measured by counting branching points (if, while, for, except, with, and/or operators) + 1.

Class / Method | Max Complexity | Enforcement
ScopeStage.run() | 12 | Lint check in CI (ruff --select C901)
PRDPlanStage.run() | 15 | Lint check in CI
PRDGenerationStage.run() | 15 | Lint check in CI
PRPlanStage.run() | 10 | Lint check in CI
CodeGenerationStage.run() | 15 | Lint check in CI
ThreePassReviewStage.run() | 15 | Lint check in CI
ThreePassReviewStage._run_single_pass() | 12 | Lint check in CI
TestStage.run() | 15 | Lint check in CI
CIGate.run() | 10 | Lint check in CI
CommandRouter.handle() | 12 | Lint check in CI
Per-command handler (_handle_*) | 10 | Lint check in CI
BuildDirector._orchestrate() | 20 | Orchestrator only — calls stage.run()
Any other method in pipeline | 15 | Lint check in CI

ENFORCEMENT | Add to CI workflow: ruff check src/ --select C901 --max-complexity 15. The build_director module is exempt from the per-method limit but NOT the per-stage-class limit. This is enforced by splitting the old monolith into stage classes.

# 20. State Machine Transitions

From State | Event | To State | Checkpoint Saved
scoping | ScopeStage complete (operator approved) | prd_plan | Yes
scoping | Operator cancels | done | No
prd_plan | PRDPlanStage complete (plan approved) | prd_gen | Yes
prd_plan | Operator stops | done | No
prd_gen | PRDGenerationStage begins for first PRD | prd_gen | No
prd_gen | Each PRD approved and committed | prd_gen (updated prd_results) | Yes
prd_gen | Each PRD's PR plan generated | pr_pipeline | Yes
pr_pipeline | Each PR execution complete | pr_pipeline (updated completed_prs) | Yes
pr_pipeline | All PRs for current PRD done | prd_gen (next PRD) | Yes
pr_pipeline | Operator stops mid-PR-list | done | Yes
pr_pipeline | All PRDs and all PRs complete | done | Yes
done | — | Yes (final state)

# 21. Testing Requirements

## 21.1 Unit Tests

Module | Coverage Target | Critical Test Cases
ScopeStage | 90% | Ambiguity collection + no re-scope; single correction appended; operator cancel returns stop; BuildThread created with all fields
PRDPlanStage | 90% | Decomposition with mock consensus; single correction triggers one re-decompose; second rejection stops build; PRD_PLAN.md format
PRDGenerationStage | 90% | dataclasses.replace() on correction (original prd_item not mutated); skip response skips PRD; timeout retry; docx export failure is non-fatal
ThreePassReviewStage | 95% | Pass 1+2 no issues → Pass 3 skipped; major rewrite > 30% lines triggers gate; issue merging deduplication; synthesis failure keeps original code; all three prompts contain required keywords
TestStage | 90% | Syntax error fast-path skips fix loop; MAX_TEST_RETRIES exhausted → escalate; successful test → local_passed=True; checkpoint saved on pass
CIGate | 85% | CI pass → PR marked ready; CI fail → gate card; retry response → re-poll; timeout → error card
CommandRouter | 100% | All 11 commands dispatch to correct handler; unknown input shows guidance; build intent pattern → guidance; task pattern → session.handle_task
ThreadStateStore | 100% | Atomic write (no .tmp after save); all BuildThread fields round-trip correctly; v1→v2 migration; corrupt file skipped in list_incomplete
_resolve_ambiguities | 100% | Each ambiguity shown once; answers appended not re-scoped; operator cancel returns None
_merge_issues | 100% | Critical always included; minor only if both agree; higher severity kept on dedup; empty input returns empty
_is_major_rewrite | 100% | 30% threshold correct; empty original returns False; identical code returns False

## 21.2 Review Prompt Regression Tests

# tests/test_pipeline.py — prompt regression tests

def test_review_pass_1_focuses_on_spec():
    from pipeline import REVIEW_PASS_1
    assert "Spec Compliance" in REVIEW_PASS_1["name"]
    assert "PRD" in " ".join(REVIEW_PASS_1["questions"])

def test_review_pass_2_focuses_on_performance():
    from pipeline import REVIEW_PASS_2
    assert "Performance" in REVIEW_PASS_2["name"]
    assert any("concurrent" in q.lower() or "load" in q.lower()
               for q in REVIEW_PASS_2["questions"])

def test_review_pass_3_focuses_on_security():
    from pipeline import REVIEW_PASS_3
    assert "Security" in REVIEW_PASS_3["name"]
    assert any("attack" in q.lower() or "injection" in q.lower()
               for q in REVIEW_PASS_3["questions"])

def test_synthesis_system_prohibits_restructure():
    from pipeline import SYNTHESIS_SYSTEM
    assert "ONLY the listed fixes" in SYNTHESIS_SYSTEM
    assert "restructure" in SYNTHESIS_SYSTEM.lower()

def test_scope_system_prohibits_invention():
    from pipeline import SCOPE_SYSTEM
    assert "Do NOT invent" in SCOPE_SYSTEM
    assert "documents only" in SCOPE_SYSTEM

# 22. Performance Requirements

Metric | Target | Notes
Stage 1 (ScopeStage) end-to-end | < 30s | One LLM call + gate round-trip
Stage 2 (PRDPlanStage) end-to-end | < 90s | Two parallel LLM calls (16k tokens) + gate
Stage 3 per PRD (generation + gate) | < 60s | Two parallel LLM calls + docx export
Stage 5 per PR (code generation) | < 60s | Two parallel LLM calls
Stage 6 Pass 1 (both reviews + synthesis) | < 45s | Three sequential LLM calls
Stage 6 Pass 2 (both reviews + synthesis) | < 45s | Three sequential LLM calls
Stage 6 Pass 3 (if not skipped) | < 45s | Three sequential LLM calls
Stage 7 (test run) | < 120s | Depends on test suite size
Total per PR (code + 3 passes + tests) | < 10 minutes | p50 estimate
ThreadStateStore.save() | < 50ms | In-process JSON + atomic file write
CommandRouter.handle() | < 5ms | Dispatch only — handler timing separate

# 23. Out of Scope

Feature | Reason | Target
Parallel PR execution within a PRD | Sequential ordering ensures dependency code injection works correctly; parallelism would require cross-PR isolation | v2
Automatic merge | Human-in-the-loop is a product principle — operator always merges | Never
LLM provider selection per stage | All stages use ConsensusEngine with the same providers; per-stage routing adds complexity | v2 if needed
Review pass configuration per project | Three passes with fixed lenses in v1; configurable in v2 if evidence suggests different lenses needed | v2
Background builds (while app minimized) | Gates require operator interaction; background builds would time out | Never
Cross-repository builds | Single repo per BuildThread | v2
Multi-PRD parallelism | Two PRDs building simultaneously would interleave gate cards confusingly | v2

# 24. Open Questions

ID | Question | Owner | Needed By
OQ-01 | Review pass issue threshold: currently, minor issues are only included if both reviewers agree. Should the threshold be configurable (e.g., include minor if either reviewer flags)? Recommendation: keep current "both agree" threshold — reduces noise without missing real issues. | Engineering | Sprint 2
OQ-02 | ThreePassReviewStage.run() receives impl_code from Stage 5 and returns final_code. Should it also review and update test_code? Current design only reviews implementation. Tests are assumed valid if they pass. Recommendation: add test review in v2 after validating v1 improvement. | Engineering | v1.1
OQ-03 | _is_major_rewrite threshold: 30% line change. Is this the right threshold? Too low = too many operator gates. Too high = major rewrites go unreviewed. Recommendation: start at 30%, tune after 10 real builds. | Engineering | Sprint 2
OQ-04 | Improvement pass (TRD-2 Section 10): the Consensus Engine offers an improvement pass after arbitration. Should Stage 5 always enable it, or only for high-complexity PRs? Recommendation: enable for all complexity levels — cost is minimal and quality benefit is consistent. | Engineering | Sprint 1

# Appendix A: BuildThread Field Reference

Field | Type | Default | Owner Stage | Persisted?
intent | str | — | Stage 1 | Yes
subsystem | str | — | Stage 1 | Yes
scope_statement | str | — | Stage 1 | Yes
branch_prefix | str | — | Stage 1 | Yes
relevant_docs | list[str] | [] | Stage 1 | Yes
prd_plan | list[PRDItem] | [] | Stage 2 | Yes — as list[dict]
ledger_build_id | str | "" | Stage 2 | Yes
prd_results | list[PRDResult] | [] | Stage 3 (append) | Partial (count only)
completed_prd_ids | list[str] | [] | Stage 3 (append) | Yes
pr_plans_by_prd | dict | {} | Stage 4 | Yes — as dict[str, list[dict]]
pr_specs | list[PRSpec] | [] | Stage 4 (active batch) | No — reconstructed from pr_plans_by_prd
pr_executions | list[PRExecution] | [] | Stages 5–8 (append) | Partial (pr_num, url only)
completed_prs | list[PRSpec] | [] | Stage 7–8 (append) | Yes — as list[pr_num]
completed_pr_nums_by_prd | dict | {} | Stages 7–8 | Yes
state | str | "scoping" | All stages | Yes
created_at | float | time.time() | Stage 1 | Yes
updated_at | float | time.time() | ThreadStateStore | Yes — updated on every save
_manual_batches_approved | int | 0 | Stage 4–5 batch logic | No — resets on resume

# Appendix B: Gate Type Reference

gate_type | When Shown | Options | Can Block Build?
scope_confirm | After scope parsed from documents | yes / no / correction | Yes — no = stop
ambiguity | For each unresolved ambiguity | proceed with TRD defaults / any text | Yes — stop response = stop
prd_plan | After PRD plan generated | yes / no / correction | Yes — no = stop
prd_review | After each PRD generated | yes / skip / stop / correction | Yes — stop = stop
review_major_change | If Pass 1 produces > 30% line change | continue / stop | Yes — stop = halt PR
ci_failure | When GitHub Actions fails | retry / skip / stop | Yes — stop = stop
cost_limit | When PR cost exceeds threshold | approve / stop | Yes — stop = stop
oi13_blocked | When token limit reached | single_provider / stop / increase_limits | Yes
test_escalation | After MAX_TEST_RETRIES exhausted | manual fix / skip / stop | Yes

# Appendix C: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification — replaces build_director._stage_interleaved() and agent.main()