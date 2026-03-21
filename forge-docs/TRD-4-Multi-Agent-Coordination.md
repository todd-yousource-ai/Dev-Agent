# TRD-4-Multi-Agent-Coordination

_Source: `TRD-4-Multi-Agent-Coordination.docx` — extracted 2026-03-21 18:58 UTC_

---

TRD-4

Multi-Agent Coordination Protocol

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-4: Multi-Agent Coordination Protocol
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-1 (App Shell — XPC, Keychain, engineer identity), TRD-3 (Pipeline — Stage 2/4/7 write to ledger), TRD-5 (GitHub — storage and write protocol)
Required by | TRD-8 (UI/UX Design System — engineer status badges, claim/release buttons)
Language | Python 3.12 (BuildLedger), Swift (XPC integration in TRD-1)
Storage | GitHub repository: forge-docs/BUILD_LEDGER.json on default branch

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Multi-Agent Coordination Protocol — the system that enables multiple engineers running separate instances of the app to build against the same repository without collision.

The Protocol owns:

The Build Ledger — a GitHub-stored JSON file that is the single source of truth for build state across all engineers

Engineer registry — who is active, what they are building, their last heartbeat

Claim protocol — how an engineer atomically claims a PR using optimistic locking

Heartbeat protocol — how active work is signalled and dead agents are detected

Conflict detection — file overlap warnings before and after PR execution

Live sync — ledger refresh via GitHub webhook or polling

Knowledge notes — free-text engineer observations shared across the team

Journal entries — per-PR build journals stored as GitHub files

SCOPE | TRD-4 specifies the coordination protocol and BuildLedger Python API. UI rendering of engineer status is specified in TRD-8. GitHub write mechanics (SHA-based optimistic locking) are implemented by TRD-5 GitHubTool. The engineer identity binding (engineer_id in Keychain) is specified in TRD-1.

# 2. Design Decisions

Decision | Choice | Rationale
Storage location | GitHub repository file | All engineers already have GitHub access. No additional infrastructure. The ledger is version-controlled and auditable. Immutable write history via git.
Consistency model | Eventual consistency with optimistic locking | Strong consistency would require a central server. Optimistic locking on GitHub file SHA is sufficient — ledger writes are infrequent (every 60s heartbeat, per-PR status changes).
Lock mechanism | GitHub file SHA — write fails if SHA changed | GitHub commit API requires the current file SHA. A stale SHA means a concurrent write occurred. Re-read and retry.
Single ledger vs per-PRD | Single ledger file per repository | Simpler — one place to look for build state. Multiple ledger files would require coordination between the files.
Dead agent detection | Passive — detected on ledger read by any engineer | No central watchdog process needed. Any engineer reading the ledger checks heartbeat timestamps and releases stale claims.
Conflict strategy | Warn, do not block | Blocking on conflict requires coordination that is harder than the conflict itself. Engineers are professional — a warning is sufficient.
Journal storage | Separate per-PR markdown files | The ledger file would grow unbounded if journals were inline. Separate files keep the ledger small and fast to read.

# 3. Build Ledger v2 Schema

## 3.1 Top-Level Structure

// forge-docs/BUILD_LEDGER.json
{
    "schema_version":   2,
    "agent_version":    "38.45.0",     // Version of agent that last wrote
    "build_id":         "payments-a1b2c3d4",  // subsystem-slug + random hex
    "subsystem":        "Payment Processing Engine",
    "intent":           "Build the core transaction processing pipeline",
    "scope_statement":  "Implement payment validation, idempotency...",
    "created_at":       1710000000.0,
    "updated_at":       1710003600.0,
    "updated_by":       "todd-gould",

    "engineer_registry": { ... },   // Section 3.2
    "prd_plan":          [ ... ],   // Section 3.3
    "pr_entries":        { ... },   // Section 3.4
    "conflict_log":      [ ... ],   // Section 3.5
    "knowledge_notes":   [ ... ],   // Section 3.6
    "pr_plans_by_prd":   { ... },   // Section 3.7
}

## 3.2 engineer_registry

"engineer_registry": {
    "todd-gould": {
        "display_name":   "Todd Gould",
        "github_username": "todd-yousource-ai",
        "status":         "active",     // "active" | "idle" | "offline"
        "last_heartbeat": 1710003540.0, // Unix epoch seconds
        "active_prd":     "PRD-003",    // null if idle
        "active_pr":      7,            // null if idle
        "agent_version":  "38.45.0",
        "registered_at":  1710000000.0,
    },
    "sara-chen": {
        "display_name":   "Sara Chen",
        "github_username": "sara-yousource-ai",
        "status":         "idle",
        "last_heartbeat": 1710003480.0,
        "active_prd":     null,
        "active_pr":      null,
        "agent_version":  "38.45.0",
        "registered_at":  1710001000.0,
    }
}

## 3.3 prd_plan

"prd_plan": [
    {
        "id":                   "PRD-001",
        "title":                "Transaction Validation Layer",
        "summary":              "Core validation pipeline...",
        "dependencies":         [],
        "estimated_complexity": "high",
        "status":               "complete",  // "pending" | "in_progress" | "complete"
        "completed_by":         "todd-gould",
        "completed_at":         1710001800.0,
    },
    {
        "id":                   "PRD-002",
        "title":                "Idempotency Store",
        "dependencies":         ["PRD-001"],
        "estimated_complexity": "medium",
        "status":               "in_progress",
        "claimed_by":           "sara-chen",
        "claimed_at":           1710003000.0,
    }
]

## 3.4 pr_entries

"pr_entries": {
    "1": {
        "pr_num":       1,
        "title":        "PR001 Add transaction request validator",
        "branch":       "forge-agent/build/todd/payments-pr001-add-transaction-validator",
        "prd_id":       "PRD-001",
        "impl_files":   ["src/payments/validator.py"],
        "language":     "python",
        "security_critical": false,
        "depends_on_prs": [],
        "estimated_complexity": "high",

        // Status lifecycle
        "status":       "done",   // "available"|"blocked"|"in_progress"|"done"|"failed"|"skipped"
        "claimed_by":   "todd-gould",
        "claimed_at":   1710000100.0,
        "heartbeat":    1710001700.0,   // Last active heartbeat while in_progress
        "completed_by": "todd-gould",
        "completed_at": 1710001800.0,
        "pr_url":       "https://github.com/org/repo/pull/42",

        // Journal reference
        "journal_path": "forge-docs/journals/PR-001.md",

        // Consensus summary
        "consensus_winner":   "claude",
        "consensus_scores":   {"claude": 8, "openai": 6},
        "consensus_cost_usd": 0.043,
    },
    "7": {
        "pr_num":    7,
        "status":    "in_progress",
        "claimed_by": "todd-gould",
        "heartbeat":  1710003540.0,
        // ... other fields
    },
    "8": {
        "pr_num":    8,
        "status":    "available",
        "claimed_by":  null,
        "heartbeat":   null,
        // ... other fields
    }
}

## 3.5 conflict_log

"conflict_log": [
    {
        "detected_at":   1710003000.0,
        "detected_by":   "sara-chen",
        "pr_num":        8,
        "conflicting_pr": 7,
        "overlapping_files": ["src/payments/validator.py"],
        "resolution":    "warned",   // "warned" | "deferred" | "resolved"
    }
]

## 3.6 knowledge_notes

"knowledge_notes": [
    {
        "added_at":   1710001000.0,
        "added_by":   "todd-gould",
        "context":    "PR-001",   // PR or PRD context, or "general"
        "note":       "The validation schema in TRD section 3.2 requires
                       all amounts to be in minor currency units (cents).
                       GPT-4o got this wrong in first generation — watch for it.",
    }
]

## 3.7 pr_plans_by_prd

"pr_plans_by_prd": {
    "PRD-001": [
        {"pr_num": 1, "title": "PR001 Add transaction request validator", ...},
        {"pr_num": 2, "title": "PR002 Add amount normalisation", ...},
    ],
    "PRD-002": [
        {"pr_num": 6, "title": "PR006 Add idempotency key store", ...},
    ]
}
// Used by new engineers to see the full PR list without reading each pr_entry.
// Populated by Stage 4 (PRPlanStage) for each PRD.

# 4. GitHub Storage Protocol

## 4.1 File Locations

File | GitHub Path | When Created | Updated By
Build Ledger | forge-docs/BUILD_LEDGER.json | Stage 2 — initialise() | Any engineer: register, claim, heartbeat, mark_done, add_note
PR Journal | forge-docs/journals/PR-{NNN:03d}.md | Stages 7–8 — mark_pr_done() | Only the engineer who completed the PR
PRD Markdown | prds/{subsystem_slug}/{prd_id}.md | Stage 3 — after PRD approval | Only the engineer who generated the PRD
PR Plan | prds/{subsystem_slug}/{prd_id}-pr-plan.md | Stage 4 — after PR plan | Only the engineer who generated the plan

## 4.2 SHA-Based Optimistic Locking

# Every ledger write follows this protocol:
#
# 1. Read current file from GitHub → get content + SHA
# 2. Modify content in memory
# 3. Write to GitHub with SHA from step 1
#    → GitHub rejects with 422 if SHA has changed (concurrent write)
# 4. On 422: sleep(random 0.5–2.0s) + go to step 1
# 5. After 3 failures: raise LedgerConflictError
#
# The SHA is GitHub's built-in optimistic lock.
# No separate lock file needed.

MAX_WRITE_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # seconds

def _write_ledger(self, data: dict) -> None:
    import random, time
    for attempt in range(MAX_WRITE_RETRIES):
        try:
            content = json.dumps(data, indent=2)
            self._github.commit_file(
                branch=self._github.default_branch,
                path=LEDGER_PATH,
                content=content,
                message=f"forge-ledger[{self._engineer_id}]: {data.get('updated_by','?')}",
                sha=self._cached_sha,   # Pass SHA for optimistic lock
            )
            # Update cached SHA from response
            self._cached_sha = self._github.get_file_sha(LEDGER_PATH)
            return
        except GitHubToolError as e:
            if "422" in str(e) or "SHA" in str(e).upper():
                # Concurrent write — re-read and retry
                sleep_sec = RETRY_BACKOFF_BASE * (2 ** attempt) + random.random()
                logger.warning(f"Ledger write conflict (attempt {attempt+1}) — retrying in {sleep_sec:.1f}s")
                time.sleep(sleep_sec)
                raw = self._read_raw()   # Re-read fresh
                if raw is None:
                    raise LedgerError("Ledger disappeared during retry")
            else:
                raise
    raise LedgerConflictError(f"Ledger write failed after {MAX_WRITE_RETRIES} attempts")

## 4.3 Read Protocol

LEDGER_PATH   = "forge-docs/BUILD_LEDGER.json"
JOURNALS_PATH = "forge-docs/journals"

def _read_raw(self) -> Optional[dict]:
    """Read ledger from GitHub. Returns None if file does not exist."""
    try:
        content, sha = self._github.get_file_with_sha(LEDGER_PATH)
        self._cached_sha = sha
        return json.loads(content)
    except GitHubToolError as e:
        if "404" in str(e) or "not found" in str(e).lower():
            return None
        raise

# Cache: ledger is cached in memory for up to CACHE_TTL_SEC.
# Stale cache is acceptable — worst case: an engineer misses a
# recently completed PR for up to CACHE_TTL_SEC before refresh.
CACHE_TTL_SEC = 60

# 5. Ledger Initialisation

## 5.1 When Initialised

The Build Ledger is initialised by Stage 2 (PRDPlanStage) after the operator approves the PRD plan. If a ledger already exists for this repository, the existing data is preserved and the new build is merged in.

## 5.2 initialise() Method

def initialise(
    self,
    build_id:        str,
    subsystem:       str,
    intent:          str,
    scope_statement: str,
    prd_plan:        list,      # list[PRDItem]
    pr_plans_by_prd: dict,      # prd_id → list[PRSpec]  (empty at init)
) -> None:
    """
    Initialise or update the Build Ledger.
    If ledger does not exist: create with full schema.
    If ledger exists: update subsystem/intent/prd_plan, preserve existing data.
    """
    import time
    existing = self._read_raw()

    if existing is None:
        # First build on this repo — create fresh ledger
        data = {
            "schema_version":   2,
            "agent_version":    _read_agent_version(),
            "build_id":         build_id,
            "subsystem":        subsystem,
            "intent":           intent,
            "scope_statement":  scope_statement,
            "created_at":       time.time(),
            "updated_at":       time.time(),
            "updated_by":       self._engineer_id,
            "engineer_registry": {},
            "prd_plan":         [_prd_item_to_dict(p) for p in prd_plan],
            "pr_entries":       {},
            "conflict_log":     [],
            "knowledge_notes":  [],
            "pr_plans_by_prd":  {},
        }
    else:
        # Existing ledger — update build fields, preserve engineers and PRs
        data = existing
        data["build_id"]        = build_id
        data["subsystem"]       = subsystem
        data["intent"]          = intent
        data["scope_statement"] = scope_statement
        data["prd_plan"]        = [_prd_item_to_dict(p) for p in prd_plan]
        data["updated_at"]      = time.time()
        data["updated_by"]      = self._engineer_id
        data["agent_version"]   = _read_agent_version()

    # Register this engineer if not already in registry
    self._ensure_registered(data)

    # Write to GitHub
    self._write_ledger(data)
    logger.info(f"Ledger initialised: {build_id}")

## 5.3 PR Entry Population

def add_pr_plan(self, prd_id: str, pr_specs: list) -> None:
    """
    Called by Stage 4 (PRPlanStage) after PR plan is generated.
    Populates pr_entries for all PRs in this PRD.
    PRs with unmet dependencies get status="blocked".
    PRs with no dependencies get status="available".
    """
    data = self._read_raw()
    if data is None:
        raise LedgerError("Ledger not initialised — call initialise() first")

    completed_prs = {
        int(k) for k, v in data["pr_entries"].items()
        if v.get("status") == "done"
    }

    for spec in pr_specs:
        deps_met = all(d in completed_prs for d in spec.depends_on_prs)
        status   = "available" if deps_met else "blocked"

        data["pr_entries"][str(spec.pr_num)] = {
            "pr_num":               spec.pr_num,
            "title":                f"PR{spec.pr_num:03d} {spec.title}",
            "branch":               spec.branch,
            "prd_id":               prd_id,
            "impl_files":           spec.impl_files,
            "language":             spec.language,
            "security_critical":    spec.security_critical,
            "depends_on_prs":       spec.depends_on_prs,
            "estimated_complexity": spec.estimated_complexity,
            "status":               status,
            "claimed_by":           None,
            "claimed_at":           None,
            "heartbeat":            None,
            "completed_by":         None,
            "completed_at":         None,
            "pr_url":               None,
            "journal_path":         None,
        }

    data["pr_plans_by_prd"][prd_id] = [vars(s) if hasattr(s,"__dict__") else s
                                        for s in pr_specs]
    data["updated_at"]  = time.time()
    data["updated_by"]  = self._engineer_id
    self._write_ledger(data)

# 6. Engineer Registry

## 6.1 Registration

def _ensure_registered(self, data: dict) -> None:
    """
    Register this engineer in the ledger if not already present.
    Called on every ledger write — idempotent.
    """
    import time
    registry = data.setdefault("engineer_registry", {})
    if self._engineer_id not in registry:
        registry[self._engineer_id] = {
            "display_name":    self._display_name,
            "github_username": self._github_username,
            "status":          "idle",
            "last_heartbeat":  time.time(),
            "active_prd":      None,
            "active_pr":       None,
            "agent_version":   _read_agent_version(),
            "registered_at":   time.time(),
        }
    else:
        # Update mutable fields on every write
        entry = registry[self._engineer_id]
        entry["last_heartbeat"] = time.time()
        entry["agent_version"]  = _read_agent_version()

## 6.2 Status Transitions

From | Event | To | Fields Updated
idle | claim_next_pr() succeeds | active | status="active", active_pr=N, active_prd=PRD-X, last_heartbeat=now
active | mark_pr_done() called | idle | status="idle", active_pr=null, active_prd=null, last_heartbeat=now
active | heartbeat > 10 minutes old (detected on read) | offline | status="offline" — set by the detecting engineer
offline | Engineer makes any ledger write | idle | status="idle", last_heartbeat=now — engineer is back
idle | No ledger write for > 30 minutes | offline | Set by any other engineer on ledger read

## 6.3 Identity Sources

# Engineer identity comes from Keychain (TRD-1) via XPC credential delivery:
# - engineer_id:    stored as SecretKey.engineerId in Keychain
# - display_name:   stored in UserDefaults "display_name"
# - github_username: fetched from GitHub /user endpoint on first auth

# The BuildLedger receives identity at construction time:
class BuildLedger:
    def __init__(
        self,
        github:          GitHubTool,
        engineer_id:     str,     # From XPC credential delivery
        display_name:    str,     # From UserDefaults
        github_username: str,     # From GitHub /user API
    ) -> None:
        self._github          = github
        self._engineer_id     = engineer_id
        self._display_name    = display_name
        self._github_username = github_username
        self._cached_sha:     Optional[str] = None
        self._cached_data:    Optional[dict] = None
        self._cache_time:     float = 0.0

# 7. Claim Protocol

## 7.1 claim_next_pr()

def claim_next_pr(self) -> Optional[dict]:
    """
    Atomically claim the next available PR.
    Returns the claimed pr_entry dict, or None if nothing available.
    """
    import time

    for _attempt in range(MAX_WRITE_RETRIES):
        data = self._read_raw()
        if data is None:
            return None

        # Scan available PRs in pr_num order
        available = sorted(
            (v for v in data["pr_entries"].values()
             if v.get("status") == "available"),
            key=lambda x: x["pr_num"]
        )
        if not available:
            return None

        target = available[0]
        pr_num_str = str(target["pr_num"])

        # Write claim
        data["pr_entries"][pr_num_str]["status"]      = "in_progress"
        data["pr_entries"][pr_num_str]["claimed_by"]  = self._engineer_id
        data["pr_entries"][pr_num_str]["claimed_at"]  = time.time()
        data["pr_entries"][pr_num_str]["heartbeat"]   = time.time()
        data["engineer_registry"][self._engineer_id]["status"]     = "active"
        data["engineer_registry"][self._engineer_id]["active_pr"]  = target["pr_num"]
        data["engineer_registry"][self._engineer_id]["active_prd"] = target["prd_id"]
        data["updated_at"] = time.time()
        data["updated_by"] = self._engineer_id

        try:
            self._write_ledger(data)
            logger.info(f"Claimed PR #{target['pr_num']}: {target['title']}")
            return target
        except LedgerConflictError:
            # SHA mismatch — another engineer wrote simultaneously.
            # Re-read and try again. _write_ledger already retried internally.
            logger.info("Claim conflict — re-scanning available PRs")
            continue

    logger.warning("Could not claim a PR after max retries")
    return None

## 7.2 claim_specific_pr()

def claim_specific_pr(self, pr_num: int) -> bool:
    """
    Claim a specific PR by number.
    Returns True on success, False if unavailable or already claimed.
    """
    import time
    data = self._read_raw()
    if data is None:
        return False

    entry = data["pr_entries"].get(str(pr_num))
    if entry is None:
        return False
    if entry.get("status") != "available":
        return False

    entry["status"]     = "in_progress"
    entry["claimed_by"] = self._engineer_id
    entry["claimed_at"] = time.time()
    entry["heartbeat"]  = time.time()

    try:
        self._write_ledger(data)
        return True
    except LedgerConflictError:
        return False

## 7.3 release_claim()

def release_claim(self, pr_num: int, reason: str = "released") -> None:
    """
    Release a claimed PR back to the available pool.
    Called when: operator cancels, build stops, or engineer explicitly releases.
    """
    import time
    data = self._read_raw()
    if data is None:
        return

    entry = data["pr_entries"].get(str(pr_num))
    if entry and entry.get("claimed_by") == self._engineer_id:
        entry["status"]      = "available"
        entry["claimed_by"]  = None
        entry["claimed_at"]  = None
        entry["heartbeat"]   = None
        entry["release_reason"] = reason

    reg = data["engineer_registry"].get(self._engineer_id, {})
    reg["status"]     = "idle"
    reg["active_pr"]  = None
    reg["active_prd"] = None
    reg["last_heartbeat"] = time.time()

    data["updated_at"] = time.time()
    data["updated_by"] = self._engineer_id
    self._write_ledger(data)

# 8. Heartbeat Protocol

## 8.1 Active Heartbeat

HEARTBEAT_INTERVAL_SEC = 60    # Update every 60 seconds while PR is active
STALE_THRESHOLD_SEC    = 600   # 10 minutes — claim is dead after this
IDLE_THRESHOLD_SEC     = 1800  # 30 minutes — engineer is offline after this

# Heartbeat is updated by Stage 5–8 (CodeGen through CIGate)
# The Build Pipeline calls update_heartbeat() in a background task
# while any PR is active.

async def _heartbeat_loop(self, pr_num: int) -> None:
    """Run in background while a PR is in_progress."""
    import asyncio, time
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
        try:
            self.update_heartbeat(pr_num)
        except Exception as e:
            logger.warning(f"Heartbeat update failed: {e}")
            # Non-fatal — continue heartbeating

def update_heartbeat(self, pr_num: int) -> None:
    """Update heartbeat for an active PR. Non-blocking — best effort."""
    import time
    data = self._read_raw()
    if data is None:
        return
    entry = data["pr_entries"].get(str(pr_num))
    if entry and entry.get("claimed_by") == self._engineer_id:
        entry["heartbeat"] = time.time()
    reg = data["engineer_registry"].get(self._engineer_id, {})
    reg["last_heartbeat"] = time.time()
    data["updated_at"] = time.time()
    data["updated_by"] = self._engineer_id
    self._write_ledger(data)

## 8.2 Dead Agent Detection

# Dead agent detection runs on every ledger read.
# Any engineer reading the ledger checks all claimed PRs and
# engineer registry entries for stale heartbeats.

def _detect_and_release_dead_agents(self, data: dict) -> bool:
    """
    Check all pr_entries and engineer_registry for stale heartbeats.
    Modifies data in-place. Returns True if any changes were made.
    """
    import time
    now = time.time()
    changed = False

    # Check claimed PRs
    for pr_entry in data["pr_entries"].values():
        if pr_entry.get("status") != "in_progress":
            continue
        heartbeat = pr_entry.get("heartbeat") or pr_entry.get("claimed_at", 0)
        if now - heartbeat > STALE_THRESHOLD_SEC:
            stale_engineer = pr_entry.get("claimed_by", "unknown")
            logger.warning(
                f"PR #{pr_entry['pr_num']} stale — releasing claim for {stale_engineer}"
            )
            pr_entry["status"]         = "available"
            pr_entry["claimed_by"]     = None
            pr_entry["claimed_at"]     = None
            pr_entry["heartbeat"]      = None
            pr_entry["release_reason"] = f"stale_claim:{stale_engineer}"
            # Mark engineer offline
            if stale_engineer in data["engineer_registry"]:
                data["engineer_registry"][stale_engineer]["status"] = "offline"
                data["engineer_registry"][stale_engineer]["active_pr"] = None
                data["engineer_registry"][stale_engineer]["active_prd"] = None
            changed = True

    # Check idle engineers for offline transition
    for eng_id, reg in data["engineer_registry"].items():
        if reg.get("status") == "idle":
            last = reg.get("last_heartbeat", 0)
            if now - last > IDLE_THRESHOLD_SEC:
                reg["status"] = "offline"
                changed = True

    return changed

IMPORTANT | Dead agent detection modifies the data dict in-place but does NOT write to GitHub automatically. The caller must decide whether to write. Typically: if _detect_and_release_dead_agents returns True AND the calling engineer is about to scan for available PRs, they write the cleaned ledger before proceeding.

# 9. PR Entry Lifecycle

## 9.1 Status State Machine

PR Entry Status State Machine

               add_pr_plan()
    ┌─────────────────────────────────────────────────┐
    │                                                  │
    ▼          claim_next_pr()                        │
available  ─────────────────────▶  in_progress        │
    ▲                                    │             │
    │  release_claim()                   │             │
    │  (stale heartbeat)                 │ mark_pr_done()
    └────────────────────────────────────┤             │
                                         │             │
                                         ├──▶  done    │
                                         │             │
                                         ├──▶  failed  │
                                         │             │
                                         └──▶  skipped │
                                                       │
blocked  ─────────────────────────────────────────────┘
  (deps unmet)     unblock_pr()                        
                   (called when dep PR goes to "done")

## 9.2 mark_pr_done()

def mark_pr_done(
    self,
    pr_num:         int,
    pr_url:         str,
    journal_summary: str,  # Written to forge-docs/journals/PR-NNN.md
) -> None:
    """
    Mark a PR as done and unblock any PRs that depended on it.
    Writes the journal entry to GitHub.
    """
    import time
    data = self._read_raw()
    if data is None:
        raise LedgerError("Ledger not found")

    entry = data["pr_entries"].get(str(pr_num))
    if entry is None:
        raise LedgerError(f"PR #{pr_num} not in ledger")

    # Mark done
    entry["status"]       = "done"
    entry["completed_by"] = self._engineer_id
    entry["completed_at"] = time.time()
    entry["pr_url"]       = pr_url
    journal_path = f"{JOURNALS_PATH}/PR-{pr_num:03d}.md"
    entry["journal_path"] = journal_path

    # Unblock PRs that depend on this one
    completed_prs = {
        int(k) for k, v in data["pr_entries"].items()
        if v.get("status") == "done"
    }
    for other_entry in data["pr_entries"].values():
        if other_entry.get("status") == "blocked":
            deps = set(other_entry.get("depends_on_prs", []))
            if deps.issubset(completed_prs):
                other_entry["status"] = "available"

    # Update engineer registry
    reg = data["engineer_registry"].get(self._engineer_id, {})
    reg["status"]     = "idle"
    reg["active_pr"]  = None
    reg["active_prd"] = None
    reg["last_heartbeat"] = time.time()

    data["updated_at"] = time.time()
    data["updated_by"] = self._engineer_id
    self._write_ledger(data)

    # Write journal to GitHub (separate file — non-fatal if fails)
    try:
        self._github.commit_file(
            branch=self._github.default_branch,
            path=journal_path,
            content=journal_summary,
            message=f"forge-ledger[{self._engineer_id}]: journal PR-{pr_num:03d}",
        )
    except Exception as e:
        logger.warning(f"Journal write failed for PR #{pr_num}: {e}")

# 10. Conflict Detection

## 10.1 Pre-Start File Overlap Check

# Called by Stage 5 (CodeGenerationStage) before generating implementation.
# Checks if any active engineer is working on files that overlap with this PR.

def check_file_conflicts(self, pr_spec: "PRSpec") -> list[dict]:
    """
    Returns list of conflict dicts. Empty list = no conflicts.
    Does NOT block — caller decides whether to warn or proceed.
    """
    data = self._read_raw()
    if data is None:
        return []

    my_files = set(pr_spec.impl_files + pr_spec.test_files)
    conflicts = []

    for pr_num_str, entry in data["pr_entries"].items():
        if entry.get("status") != "in_progress":
            continue
        if entry.get("claimed_by") == self._engineer_id:
            continue  # My own PR — not a conflict
        their_files = set(entry.get("impl_files", []))
        overlap = my_files & their_files
        if overlap:
            conflicts.append({
                "conflicting_pr":     int(pr_num_str),
                "conflicting_engineer": entry.get("claimed_by"),
                "overlapping_files":  list(overlap),
            })

    return conflicts


# In Stage 5:
conflicts = self.ledger.check_file_conflicts(spec)
if conflicts:
    for c in conflicts:
        self.emit_card({"card_type":"warning",
            "body": f"File overlap with PR #{c['conflicting_pr']} 
                    ({c['conflicting_engineer']}): {c['overlapping_files']}"})
    # Log to conflict_log — non-blocking
    self.ledger.log_conflict(spec.pr_num, conflicts)

## 10.2 log_conflict()

def log_conflict(self, my_pr_num: int, conflicts: list[dict]) -> None:
    """Append conflict records to ledger conflict_log."""
    import time
    data = self._read_raw()
    if data is None:
        return
    for c in conflicts:
        data.setdefault("conflict_log", []).append({
            "detected_at":       time.time(),
            "detected_by":       self._engineer_id,
            "pr_num":            my_pr_num,
            "conflicting_pr":    c["conflicting_pr"],
            "overlapping_files": c["overlapping_files"],
            "resolution":        "warned",
        })
    data["updated_at"] = time.time()
    data["updated_by"] = self._engineer_id
    self._write_ledger(data)

# 11. Live Sync

## 11.1 Sync Strategy

Mode | Mechanism | Latency | When Used
Webhook (v2) | GitHub push event → TRD-5 webhook receiver → XPC message to Swift → BuildLedger.refresh() | < 5 seconds | When TRD-5 webhook is active
Polling (fallback) | Background asyncio task polls every POLL_INTERVAL_SEC | 30–90 seconds | When webhook unavailable or on first connect
Manual sync | /ledger sync command | Immediate | Operator-triggered
Read-through | Every ledger API call re-reads if cache is stale (> CACHE_TTL_SEC) | Per CACHE_TTL_SEC | Always active

## 11.2 Polling Loop

POLL_INTERVAL_SEC = 60

async def _poll_loop(self) -> None:
    """Background polling task — runs when webhook is not active."""
    import asyncio
    while True:
        await asyncio.sleep(POLL_INTERVAL_SEC)
        try:
            old_updated = (self._cached_data or {}).get("updated_at", 0)
            fresh = self._read_raw()
            if fresh is None:
                continue
            if fresh.get("updated_at", 0) > old_updated:
                self._cached_data = fresh
                # Notify Swift UI of ledger change
                self._emit_ledger_update(fresh)
        except Exception as e:
            logger.warning(f"Ledger poll failed: {e}")

## 11.3 Webhook Trigger

# TRD-5 webhook receiver handles push events on the default branch.
# When forge-docs/BUILD_LEDGER.json is in the changed files:
# TRD-5 sends an XPC message to the Swift shell (TRD-1):
{
    "type":      "ledger_changed",
    "id":        "<UUID>",
    "session_id": "<session UUID>",
    "timestamp": 1710000000000,
    "payload":   {"path": "forge-docs/BUILD_LEDGER.json"}
}

# Swift shell calls BuildLedger.refresh() on receiving this message.
# refresh() forces a cache-bypassing read and emits ledger_update to UI.

def refresh(self) -> None:
    """Force-read ledger bypassing cache. Called on webhook signal."""
    self._cache_time  = 0.0   # Invalidate cache
    fresh = self._read_raw()
    if fresh:
        self._cached_data = fresh
        self._emit_ledger_update(fresh)

# 12. Knowledge Notes

## 12.1 Adding a Note

# /ledger note <text> — operator command in REPL
# Or: build pipeline adds notes automatically on certain errors

def add_knowledge_note(
    self,
    note: str,
    context: str = "general",   # "general" | "PR-NNN" | "PRD-XXX"
) -> None:
    import time
    data = self._read_raw()
    if data is None:
        logger.warning("Cannot add note — ledger not initialised")
        return
    data.setdefault("knowledge_notes", []).append({
        "added_at":  time.time(),
        "added_by":  self._engineer_id,
        "context":   context,
        "note":      note[:1000],   # Cap note length
    })
    data["updated_at"] = time.time()
    data["updated_by"] = self._engineer_id
    self._write_ledger(data)

## 12.2 Reading Notes for a PR

def read_journal_for_deps(self, dep_pr_nums: list[int]) -> str:
    """
    Load journal entries for dependency PRs.
    Called by Stage 5 to inject prior-PR context into code generation.
    Returns formatted string for insertion into consensus user prompt.
    """
    data = self._read_raw()
    if data is None:
        return ""

    entries = []
    for pr_num in dep_pr_nums:
        entry = data["pr_entries"].get(str(pr_num), {})
        journal_path = entry.get("journal_path")
        if journal_path:
            try:
                content, _ = self._github.get_file_with_sha(journal_path)
                entries.append(f"### PR #{pr_num}: {entry.get('title','?')}\n\n{content}")
            except GitHubToolError:
                pass  # Journal not yet written — non-fatal

    # Also include relevant knowledge notes
    notes = data.get("knowledge_notes", [])
    relevant_notes = [
        n for n in notes
        if n.get("context") in (["general"] +
                                 [f"PR-{num}" for num in dep_pr_nums])
    ]
    if relevant_notes:
        note_text = "\n".join(f"- {n['note']}" for n in relevant_notes[-5:])
        entries.append(f"### Team Knowledge Notes\n\n{note_text}")

    return "\n\n".join(entries) if entries else ""

# 13. Journal Entries

## 13.1 Journal Format

# forge-docs/journals/PR-{NNN:03d}.md
# Written by Stage 7–8 after PR completion.
# Plain markdown — readable by engineers and parseable by the agent.

# Example: forge-docs/journals/PR-007.md
---
PR: 7
Title: PR007 Add idempotency key expiry
Branch: forge-agent/build/todd/payments-pr007-add-idempotency-key-expiry
Engineer: todd-gould
PRD: PRD-002
Completed: 2026-03-19T15:42:00Z
PR URL: https://github.com/org/repo/pull/52

## Consensus
Winner: Claude (8/10) vs GPT-4o (6/10)
Rationale: Claude correctly implemented the sliding window expiry using
a Redis sorted set, matching TRD section 4.3. GPT-4o used a TTL-only
approach that would not handle partial expiry correctly.
Review passes applied: 2
Review changes made: Yes (Pass 1 added missing error handling for Redis timeout)
Total cost: $0.057

## Implementation Notes
The idempotency key format specified in TRD-002 section 3.1 uses
SHA-256({client_id}:{request_id}:{timestamp_day}). GPT-4o interpreted
timestamp_day as Unix day number, but the TRD specifies YYYY-MM-DD format.
Watch for this in dependent PRs.

## Test Results
All 12 tests passed on attempt 1.
Test coverage: 94%

## Dependencies Used
This PR depended on PR-006 (idempotency store). The store interface
is idempotency.IdempotencyStore with methods: check(), store(), expire().
---

## 13.2 build_journal_entry()

def build_journal_entry(
    spec:            "PRSpec",
    execution:       "PRExecution",
    failure_records: list,
    prd_context:     str,
    engineer_id:     str,
    consensus_result: "ConsensusResult",
) -> str:
    """Build the markdown journal entry for a completed PR."""
    import datetime
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "---",
        f"PR: {spec.pr_num}",
        f"Title: PR{spec.pr_num:03d} {spec.title}",
        f"Branch: {spec.branch}",
        f"Engineer: {engineer_id}",
        f"Completed: {ts}",
        f"PR URL: {execution.pr_url or 'not yet merged'}",
        "",
        "## Consensus",
        f"Winner: {_format_winner(consensus_result)}",
        f"Rationale: {consensus_result.scoring.rationale}",
        f"Review passes applied: {execution.review_passes_applied}",
        f"Review changes made: {'Yes' if execution.review_changes_made else 'No'}",
        f"Total cost: ${consensus_result.total_cost_usd:.3f}",
        "",
    ]

    # Add implementation notes if failures occurred
    if failure_records:
        lines += ["## Failure History", ""]
        for rec in failure_records[-3:]:   # Last 3 failures
            lines.append(f"- {rec.get('summary', str(rec))[:200]}")
        lines.append("")

    lines += [
        "## Test Results",
        f"Local tests: {'passed' if execution.local_passed else 'failed'}",
        f"CI: {'passed' if execution.ci_passed else 'failed'}",
        f"Retries: {execution.retry_count}",
        "---",
    ]
    return "\n".join(lines)

# 14. BuildLedger Public API

Method | Called By | Description
initialise(build_id, subsystem, intent, scope_statement, prd_plan, pr_plans_by_prd) | Stage 2 (PRDPlanStage) | Create or update ledger. Register this engineer.
add_pr_plan(prd_id, pr_specs) | Stage 4 (PRPlanStage) | Populate pr_entries for a PRD. Set available/blocked status.
claim_next_pr() | /ledger claim command | Atomically claim next available PR. Returns pr_entry or None.
claim_specific_pr(pr_num) | /ledger claim N command | Claim a specific PR. Returns bool.
release_claim(pr_num, reason) | Stage stop, /ledger release | Release a claimed PR back to available pool.
update_heartbeat(pr_num) | Background task in Stage 5–8 | Update heartbeat for active PR.
mark_pr_done(pr_num, pr_url, journal_summary) | Stages 7–8 | Mark PR complete, unblock deps, write journal.
check_file_conflicts(pr_spec) | Stage 5 (CodeGenerationStage) | Return list of file overlap conflicts.
log_conflict(pr_num, conflicts) | Stage 5 (after conflict detection) | Append to conflict_log.
add_knowledge_note(note, context) | /ledger note command, auto | Add engineer observation to knowledge_notes.
read_journal_for_deps(dep_pr_nums) | Stage 5 (dependency injection) | Load journal entries for dependency PRs.
print_build_overview() | /ledger command, onboarding | Print formatted build status to chat stream.
check_version_compatibility() | App startup | Return (compatible: bool, message: str).
refresh() | Webhook trigger (TRD-5 → TRD-1 → here) | Force-read ledger bypassing cache.

# 15. XPC Integration

## 15.1 ledger_update XPC Message

# Sent from Python backend to Swift UI when ledger changes.
# Swift UI updates the engineer status badges in NavigatorView (TRD-8).

Payload:
{
    "type":    "build_card",
    "payload": {
        "card_type": "ledger_update",
        "engineers": [
            {
                "engineer_id":  "todd-gould",
                "display_name": "Todd Gould",
                "status":       "active",   // "active" | "idle" | "offline"
                "active_pr":    7,
                "active_prd":   "PRD-002",
            },
            {
                "engineer_id":  "sara-chen",
                "display_name": "Sara Chen",
                "status":       "idle",
                "active_pr":    null,
                "active_prd":   null,
            }
        ],
        "available_prs": 4,
        "in_progress_prs": 2,
        "done_prs": 6,
        "total_prs": 12,
    }
}

## 15.2 emit_ledger_update()

def _emit_ledger_update(self, data: dict) -> None:
    """Send ledger summary to Swift UI via XPC emit_card callback."""
    registry = data.get("engineer_registry", {})
    engineers = [
        {
            "engineer_id":  eng_id,
            "display_name": info.get("display_name", eng_id),
            "status":       info.get("status", "offline"),
            "active_pr":    info.get("active_pr"),
            "active_prd":   info.get("active_prd"),
        }
        for eng_id, info in registry.items()
    ]
    pr_entries = data.get("pr_entries", {})
    statuses   = [v.get("status") for v in pr_entries.values()]
    self._emit_card({
        "card_type":      "ledger_update",
        "engineers":      engineers,
        "available_prs":  statuses.count("available"),
        "in_progress_prs": statuses.count("in_progress"),
        "done_prs":       statuses.count("done"),
        "total_prs":      len(statuses),
    })

# 16. Version Compatibility

CURRENT_SCHEMA_VERSION = 2
MIN_COMPATIBLE_SCHEMA   = 1   # Can read v1 ledgers, upgrades on first write

def check_version_compatibility(self) -> tuple[bool, str]:
    """
    Check if this agent version is compatible with the ledger.
    Returns (compatible: bool, message: str).
    Compatible means: can read and write without data loss.
    """
    data = self._read_raw()
    if data is None:
        return True, "No ledger found — will create on first init"

    ledger_schema  = data.get("schema_version", 1)
    ledger_agent   = data.get("agent_version", "unknown")

    if ledger_schema < MIN_COMPATIBLE_SCHEMA:
        return False, (
            f"Ledger schema v{ledger_schema} is too old — this agent requires v{MIN_COMPATIBLE_SCHEMA}+. "
            "A team member with an older agent version wrote this ledger."
        )

    if ledger_schema > CURRENT_SCHEMA_VERSION:
        return False, (
            f"Ledger schema v{ledger_schema} is newer than this agent supports (v{CURRENT_SCHEMA_VERSION}). "
            "Upgrade your agent before continuing."
        )

    # Schema is compatible — warn on agent version mismatch but do not block
    if ledger_agent != _read_agent_version():
        return True, (
            f"Agent version mismatch: ledger was last written by agent {ledger_agent}, "
            f"you are running {_read_agent_version()}. "
            "This is usually fine but verify team is on the same agent version."
        )

    return True, "Compatible"

# 17. Testing Requirements

Module | Coverage Target | Critical Test Cases
initialise() | 95% | Fresh ledger created with all required fields; existing ledger updated without losing engineer data or PR entries; engineer registered on init; schema_version=2
add_pr_plan() | 95% | available status when deps met; blocked status when deps unmet; PR entries include all PRSpec fields; pr_plans_by_prd populated
claim_next_pr() | 100% | Returns lowest available pr_num; returns None when none available; SHA conflict retried up to MAX_WRITE_RETRIES; two concurrent claims: only one succeeds
release_claim() | 100% | PR returns to available; engineer set to idle; no-op if PR not claimed by this engineer
update_heartbeat() | 90% | Heartbeat timestamp updated; engineer last_heartbeat updated; non-fatal on GitHub error
mark_pr_done() | 100% | PR status=done; blocked deps unblocked when all their deps are now done; journal written to GitHub; engineer set to idle
_detect_and_release_dead_agents() | 100% | Stale PR claim released; stale engineer set to offline; non-stale claims untouched; idle→offline after IDLE_THRESHOLD_SEC
check_file_conflicts() | 95% | Own PR not flagged; done PR not flagged; overlapping impl_files detected; non-overlapping files clean
check_version_compatibility() | 100% | Schema too old → incompatible; schema too new → incompatible; schema match → compatible; agent version mismatch → compatible with warning
_write_ledger (SHA lock) | 95% | Success on first attempt; 422 triggers re-read + retry; 3 failures raises LedgerConflictError; non-422 error re-raised immediately

## 17.1 Concurrency Test

# tests/test_build_ledger.py

def test_concurrent_claims_only_one_succeeds():
    """
    Two threads claiming the same PR — exactly one must succeed.
    Uses real SHA-based locking via mock GitHubTool.
    """
    import threading

    results = []
    errors  = []

    def claim_worker(ledger):
        try:
            result = ledger.claim_next_pr()
            results.append(result)
        except Exception as e:
            errors.append(e)

    ledger_a = BuildLedger(mock_github_with_sha_lock, "engineer-a", "Eng A", "github-a")
    ledger_b = BuildLedger(mock_github_with_sha_lock, "engineer-b", "Eng B", "github-b")

    t1 = threading.Thread(target=claim_worker, args=(ledger_a,))
    t2 = threading.Thread(target=claim_worker, args=(ledger_b,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # Exactly one claim should have succeeded
    successful = [r for r in results if r is not None]
    assert len(successful) == 1, f"Expected 1 successful claim, got {len(successful)}"

# 18. Performance Requirements

Metric | Target | Notes
Ledger read (cache miss) | < 2 seconds | GitHub API call + JSON parse
Ledger read (cache hit) | < 5 ms | In-memory dict copy
Ledger write (no conflict) | < 3 seconds | GitHub commit API call
Ledger write (1 conflict) | < 8 seconds | Re-read + retry after backoff
Ledger write (2 conflicts) | < 20 seconds | Two retries with exponential backoff
claim_next_pr() end-to-end | < 5 seconds | Read + claim write
Heartbeat update | < 3 seconds | Read + write cycle
Journal write | < 3 seconds | Separate GitHub commit (non-blocking)
Ledger JSON size | < 500 KB | For 100 PRs with full metadata
print_build_overview() | < 5 seconds | Read + format + emit

# 19. Out of Scope

Feature | Reason | Target
Real-time collaborative editing | Engineers work independently on different PRs | Never
Cross-repository coordination | Single repo per BuildLedger instance | v2 if needed
Automatic PR assignment (push model) | Always engineer-initiated claim pull | Never
Central coordination server | GitHub file is sufficient; server adds infra cost | Never
Distributed lock via Redis/etcd | GitHub SHA lock is sufficient for the write frequency | Never
Ledger encryption | Build state is not sensitive; GitHub access controls are sufficient | Never
Multi-repo builds | Single repo per session | v2
Ledger archiving / pruning | Old ledgers accumulate; pruning policy not defined | v1.1

# 20. Open Questions

ID | Question | Owner | Needed By
OQ-01 | STALE_THRESHOLD_SEC = 600 (10 minutes). If a PR stage takes > 10 minutes (e.g. a slow CI run), the claim will be incorrectly released. Should the threshold be 30 minutes? Recommendation: 30 minutes for PR claims, keep 10 minutes for heartbeat warning. Two separate thresholds. | Engineering | Sprint 1
OQ-02 | Ledger size: at 100 PRs with full consensus metadata, the ledger will be ~200 KB. At 500 PRs it approaches 1 MB. GitHub has no per-file size limit for API reads but large JSON slows parsing. Recommendation: add journal_path reference but keep journal content in separate files (already done). Monitor size in v1. | Engineering | v1.1 monitoring
OQ-03 | PR archiving: completed builds leave the ledger with all done PRs. Should there be a /ledger archive command that moves done PRs to a separate file? Recommendation: yes — add in v1.1 after seeing real ledger growth in production. | Product | v1.1
OQ-04 | forge-docs/ directory naming: current design stores ledger and journals in forge-docs/. This may conflict with TRD documentation also stored in forge-docs/. Recommendation: rename to .forge/ or forge-agent/ to separate agent coordination files from project docs. | Engineering | Sprint 1

# Appendix A: Full JSON Schema Reference

Field | Type | Required | Default | Notes
schema_version | int | Yes | 2 | Increment on breaking schema change
agent_version | str | Yes | — | Semver from VERSION file
build_id | str | Yes | — | "{subsystem_slug}-{random_hex_8}"
subsystem | str | Yes | — | From ScopeStage
intent | str | Yes | — | From operator input
scope_statement | str | Yes | — | 2-3 sentence scope
created_at | float | Yes | — | Unix epoch seconds
updated_at | float | Yes | — | Updated on every write
updated_by | str | Yes | — | engineer_id of last writer
engineer_registry | object | Yes | {} | See Section 3.2
prd_plan | array | Yes | [] | list of PRD objects
pr_entries | object | Yes | {} | pr_num (str) → PR object
conflict_log | array | Yes | [] | list of conflict records
knowledge_notes | array | Yes | [] | list of note objects
pr_plans_by_prd | object | Yes | {} | prd_id → list of PR summary objects

## PR Entry Fields

Field | Type | Required | Notes
pr_num | int | Yes | Global within build session
title | str | Yes | "PR{NNN} {title}"
branch | str | Yes | Full branch name
prd_id | str | Yes | "PRD-001"
impl_files | array[str] | Yes | Validated by path_security
language | str | Yes | "python"|"go"|"typescript"|"rust"
security_critical | bool | Yes | Triggers extra review in Stage 6
depends_on_prs | array[int] | Yes | Empty list if no dependencies
estimated_complexity | str | Yes | "low"|"medium"|"high"
status | str | Yes | "available"|"blocked"|"in_progress"|"done"|"failed"|"skipped"
claimed_by | str|null | Yes | null when not in_progress
claimed_at | float|null | Yes | Unix epoch seconds
heartbeat | float|null | Yes | Last active heartbeat
completed_by | str|null | Yes | null until done
completed_at | float|null | Yes | null until done
pr_url | str|null | Yes | null until GitHub PR created
journal_path | str|null | Yes | "forge-docs/journals/PR-NNN.md"
consensus_winner | str|null | No | "claude"|"openai"|"tie"
consensus_scores | object|null | No | {"claude": N, "openai": N}
consensus_cost_usd | float|null | No | Total cost of generation

# Appendix B: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification