# TRD-12-Backend-Runtime-Startup-Crafted

_Source: `TRD-12-Backend-Runtime-Startup-Crafted.docx` — extracted 2026-03-26 21:47 UTC_

---

TRD-12

Backend Runtime Startup and Version Handshake

Technical Requirements Document  •  v1.0

Field | Value
Product | Crafted
Document | TRD-12: Backend Runtime Startup and Version Handshake
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-1 (App Shell — XPC channel, credential delivery, process lifecycle), TRD-3 (Build Pipeline — ThreadStateStore flush on shutdown)
Required by | TRD-9 (Mac CI Runner — XPC integration test validates this startup sequence)
Language | Python 3.12 (backend startup), Swift (ready message validation in TRD-1)
Scope | Deliberately narrow: startup sequence, version handshake, and graceful shutdown only

# 1. Purpose and Scope

This document specifies three things and only three things:

Python backend startup sequence — what initializes in what order, why the order matters, and what must succeed before the backend signals ready to the Swift shell.

Swift/Python version compatibility handshake — how the backend communicates its version to the Swift shell, how Swift validates compatibility, and what happens when they are incompatible.

Graceful shutdown — what the Python backend does when it receives a stop signal, how in-flight work is handled, and what state is guaranteed to be persisted before exit.

SCOPE | TRD-12 covers only the startup and shutdown boundary between Swift and Python. The overall app lifecycle is TRD-1. Pipeline state management is TRD-3. XPC wire protocol is TRD-1 Section 6. This document fills the specific gap: the initialization order inside the Python process and the version contract between the two processes.

Why startup order matters: if the document store initializes before the embedding model is loaded, retrieval calls during startup fail. If GitHubTool initializes before credentials are delivered, it has no token and all API calls fail with authentication errors. If the CommandRouter starts accepting commands before the ConsensusEngine is ready, an early command silently fails. Each initialization step has dependencies — this TRD makes them explicit.

# 2. Design Decisions

Decision | Choice | Rationale
Credential delivery timing | Block all initialization that requires credentials until XPC delivery completes | GitHubTool and ConsensusEngine both need credentials at construction time. Initializing them before delivery means they get None as the token — silent failures are worse than explicit blocking.
Doc store loading timing | Async and non-blocking — runs after ready message is sent | Doc store loading takes 5-30 seconds. The backend is usable (for commands that do not require context) while embedding loads. The operator sees immediate response from the app.
Version check timing | Swift validates before delivering credentials — not after | If the backend is incompatible, credentials should not be delivered to it. Version check is the first thing Swift does after receiving the ready message.
Compatibility direction | Backend minor version >= shell minor version (same major) | New backend features (minor bump) are additive — old Swift shells ignore unknown message types. Old backends cannot serve new Swift shells — they lack the new message types the shell expects.
Startup stdout signal | One line to stdout: "CRAFTED_LISTENING:{socket_path}" | Swift needs to know the XPC socket path before it can connect. stdout is available before the XPC connection exists. This is the bootstrap signal — Swift reads it and opens the socket.
Shutdown persistence guarantee | ThreadStateStore.flush() must complete before exit on SIGTERM | A build in progress has a ThreadStateStore checkpoint. On SIGTERM, flush ensures the checkpoint is written. Resume works correctly after an unexpected restart.

# 3. Startup Sequence

## 3.1 Ordered Initialization

Step | Action | Blocks On | Failure Behavior
1 | Initialize logger (file + stderr) | Nothing — always first | Write to raw stderr. exit(1).
2 | Parse startup arguments (socket path, nonce, workspace, log dir) | Logger | Log error. exit(1).
3 | Start XPC server — begin listening on socket path | Arguments | Log error. exit(1).
4 | Write bootstrap signal to stdout: CRAFTED_LISTENING:{socket_path} | XPC server | (Step 3 failure handles this)
5 | Wait for credential delivery via XPC (CREDENTIAL_TIMEOUT = 30s) | XPC connection + handshake | On timeout: send xpc error message, exit(1).
6 | Credentials received. Initialize GitHubTool with token. | Credentials | On bad token: send auth_error XPC card. Continue — operator can fix in Settings.
7 | Initialize ConsensusEngine with API keys. | Credentials | On bad key: send auth_error XPC card. Continue.
8 | Initialize DocumentStore (model load — may take 5-15s). | Nothing — runs concurrently with step 8b | On model load fail: send warning XPC card. Continue without doc context.
8b | Send ready message via XPC (see Section 4). | Steps 6-7 complete | Cannot send ready before ConsensusEngine is initialized.
9 | Enter CommandRouter event loop. | Ready message sent | Normal operation.
(async) | DocumentStore finishes model load and index load. | Background task | Sends doc_store_ready XPC message when complete.

KEY INSIGHT | Steps 8 and 8b run concurrently: the backend sends the ready message as soon as ConsensusEngine is initialized, while the DocumentStore loads in the background. This means the operator sees the app become responsive quickly. Commands that do not require doc context (like /help or /ledger status) work immediately. Commands that need retrieval wait for the doc_store_ready signal.

## 3.2 main() Implementation

import asyncio, os, sys, signal
from pathlib import Path

CREDENTIAL_TIMEOUT_SEC = 30

async def main() -> int:
    """
    Python backend entry point.
    Returns exit code: 0 = clean, 1 = startup failure.
    """
    # Step 1: Logger
    logger = _init_logger()   # Never fails — falls back to stderr
    logger.info("Crafted backend starting")

    # Step 2: Arguments
    try:
        args = _parse_args()
    except StartupError as e:
        logger.error(f"Argument parse failed: {e}")
        return 1

    # Step 3: XPC server
    try:
        xpc = XPCServer(socket_path=args.socket_path, nonce=args.nonce)
        await xpc.start()
    except OSError as e:
        logger.error(f"XPC server failed to start: {e}")
        return 1

    # Step 4: Bootstrap signal to Swift
    print(f"CRAFTED_LISTENING:{args.socket_path}", flush=True)
    logger.info(f"Listening on {args.socket_path}")

    # Step 5: Wait for credentials
    try:
        creds = await asyncio.wait_for(
            xpc.wait_for_credentials(),
            timeout=CREDENTIAL_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        await xpc.send_error("credential_timeout",
            f"No credentials received within {CREDENTIAL_TIMEOUT_SEC}s")
        logger.error("Credential timeout — exiting")
        return 1

    # Steps 6-7: Initialize tools (errors are non-fatal)
    github  = _init_github_tool(creds, xpc, logger)
    engine  = _init_consensus_engine(creds, xpc, logger)

    # Step 8 (async): Load document store in background
    doc_store = DocumentStore()
    asyncio.create_task(_load_doc_store(doc_store, args.project_id, xpc, logger))

    # Step 8b: Send ready message
    await xpc.send_ready(
        agent_version=_read_version(),
        min_swift_version=MIN_SWIFT_VERSION,
        capabilities=_build_capabilities(github, engine),
    )
    logger.info("Backend ready")

    # Step 9: Enter event loop
    router = CommandRouter(github=github, engine=engine,
                           doc_store=doc_store, xpc=xpc)
    await router.run_until_stop()

    # Clean shutdown
    await _graceful_shutdown(router, xpc, logger)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

# 4. The Ready Message

## 4.1 Schema

# Sent from Python backend to Swift shell via XPC after full initialization.
# This is the version handshake message.

{
    "type":              "ready",
    "id":                "<UUID>",
    "session_id":        "<session UUID>",
    "timestamp":         1710000000000,    // milliseconds epoch

    "agent_version":     "38.45.0",        // semver of this Python backend
    "min_swift_version": "1.0.0",          // minimum Swift shell version required

    "capabilities": [
        "consensus_engine",                // TRD-2 ConsensusEngine available
        "build_pipeline",                  // TRD-3 pipeline available
        "github_integration",              // TRD-5 GitHubTool available
        "multi_agent_ledger",              // TRD-4 BuildLedger available
        "holistic_review",                 // TRD-6 HolisticReview available
        "trd_workflow",                    // TRD-7 TRDWorkflow available
        "doc_store"                        // TRD-10 DocumentStore available (loading)
    ],

    "doc_store_status":  "loading",        // "loading" | "ready" | "unavailable"
    "python_version":    "3.12.8",
    "platform":          "macOS-15.0-arm64"
}

# doc_store_status "loading" means the ready message was sent before
# the embedding model finished loading. A separate doc_store_ready
# XPC message will be sent when loading completes.

## 4.2 Swift Validation Logic

// In TRD-1 BackendManager — runs immediately on receiving the ready message
// BEFORE delivering credentials to the backend.

func validateReadyMessage(_ ready: ReadyMessage) -> VersionCheckResult {
    let agentVersion = SemanticVersion(ready.agentVersion)
    let minSwift     = SemanticVersion(ready.minSwiftVersion)
    let swiftVersion = SemanticVersion(Bundle.main.agentShellVersion)

    // Check 1: Backend requires a newer Swift shell than we are
    if swiftVersion < minSwift {
        return .incompatible(
            reason: "This app version (\(swiftVersion)) is too old. "
                  + "Backend requires \(minSwift)+. Please update the app."
        )
    }

    // Check 2: Backend major version must match shell major version
    if agentVersion.major != swiftVersion.major {
        return .incompatible(
            reason: "Agent version \(agentVersion) is incompatible with "
                  + "app version \(swiftVersion). Major versions must match."
        )
    }

    // Check 3: Backend minor must be >= shell minor (backend is additive)
    if agentVersion.minor < swiftVersion.minor {
        return .incompatible(
            reason: "Agent version \(agentVersion) is older than expected. "
                  + "Update the agent backend to \(swiftVersion.major).\(swiftVersion.minor)+"
        )
    }

    // Warn (non-blocking) if minor versions differ
    if agentVersion.minor > swiftVersion.minor {
        return .compatibleWithWarning(
            warning: "Agent \(agentVersion) is newer than app \(swiftVersion). "
                   + "Some features may not be visible in this app version."
        )
    }

    return .compatible
}

// On .incompatible: show error card, do NOT deliver credentials, offer update.
// On .compatibleWithWarning: deliver credentials, show informational card.
// On .compatible: deliver credentials, no additional message.

# 5. Version Compatibility Rules

## 5.1 Semver Contract

Version Component | Change Trigger | Compatibility Impact
MAJOR (X.0.0) | Breaking change to XPC message schema; removed or renamed message type; changed credential delivery format; incompatible ThreadStateStore schema | Swift and Python MAJOR must match. No cross-major compatibility.
MINOR (0.Y.0) | New XPC message type added; new capability added; new command added to CommandRouter | Backend MINOR >= shell MINOR required. New backend messages that old shells do not understand are silently discarded by Swift (TRD-1 S6.6 — unknown message handling).
PATCH (0.0.Z) | Bug fix; performance improvement; no interface changes | Always compatible within same MAJOR.MINOR.

## 5.2 Compatibility Matrix

Shell Version | Backend 38.44.x | Backend 38.45.x | Backend 38.46.x | Backend 39.0.x
Shell 38.44.x | ✓ Compatible | ✓ Compatible (backend newer minor) | ✗ Incompatible (major mismatch)
Shell 38.45.x | ✗ Incompatible (backend older minor) | ✓ Compatible | ✓ Compatible (backend newer minor) | ✗ Incompatible (major mismatch)
Shell 38.46.x | ✗ Incompatible | ✓ Compatible | ✗ Incompatible (major mismatch)
Shell 39.0.x | ✗ Incompatible | ✓ Compatible

The practical effect: when the Swift shell ships a new feature that requires a new XPC message type, it bumps its minor version. The backend must also bump its minor version and add the new message type before operators using the new shell can run. The backend minor version tracks the shell — they move together at each feature release.

## 5.3 Version Constants

# Python backend — src/version.py
AGENT_VERSION     = "38.45.0"   # Updated on every release
MIN_SWIFT_VERSION = "1.0.0"     # Minimum Swift shell version this backend requires

# Read from VERSION file at runtime (allows version inspection without import):
def _read_version() -> str:
    try:
        return Path(__file__).parent.parent.joinpath("VERSION").read_text().strip()
    except Exception:
        return AGENT_VERSION   # Fallback to hardcoded

# Swift shell — Info.plist / Bundle
# Key: CraftedShellVersion = "1.0.0"   (set at build time)
# Key: CraftedMinBackendVersion = "38.45.0"  (minimum backend this shell requires)

# The ready message validation in Section 4.2 reads both keys.

# 6. Credential Delivery Gate

## 6.1 What Blocks on Credentials

Component | Blocks on Credentials? | Reason
XPC server start | No | Must start before credentials can be delivered. Chicken-and-egg.
Logger | No | Logging works without credentials — file path only.
GitHubTool | YES | Requires GitHub PAT or App token at construction time.
ConsensusEngine | YES | Requires Anthropic and OpenAI API keys at construction time.
BuildLedger | YES (via GitHubTool) | BuildLedger depends on GitHubTool.
DocumentStore | No | Embedding model is local — no credentials required.
CommandRouter | No (partial) | Router starts, but commands requiring GitHub or consensus are unavailable until credentials are delivered. Commands are queued, not rejected.

## 6.2 Credential Timeout Handling

# CREDENTIAL_TIMEOUT_SEC = 30
#
# Swift sends credentials within 1-2 seconds of receiving the
# CRAFTED_LISTENING stdout signal in normal operation.
#
# Timeout causes:
#   - Swift shell crashed before sending credentials
#   - XPC connection failed to establish
#   - Biometric auth took > 30 seconds (unusual)
#   - Deadlock in the credential delivery path
#
# On timeout:
#   1. Send error via XPC if connection is open
#   2. Log the timeout with elapsed time
#   3. exit(1)
#   4. Swift shell detects exit and shows error card (TRD-1 S7.4)
#   5. Swift shell will restart the backend after RESTART_DELAY_SEC

async def wait_for_credentials(self) -> Credentials:
    """Wait for credential delivery. Raises asyncio.TimeoutError on timeout."""
    await self._handshake_complete.wait()  # Set by XPC handshake handler
    creds = await self._credentials_received.get()  # asyncio.Queue
    return creds

# 7. Startup Failure Modes

Step | Failure Mode | Backend Action | Swift Response
Logger init | File system error (permissions, disk full) | Write raw error to stderr. exit(1). | Swift detects exit(1). Retry after RESTART_DELAY. Show error card after MAX_RESTARTS.
Argument parse | Missing required arg (socket path, nonce) | Log to stderr. exit(1). | Same as above.
XPC server start | Socket path already in use; permissions error | Log error with errno. exit(1). | Same as above.
Credential timeout | No credentials within 30 seconds | Send error XPC if channel open. exit(1). | Swift shows error card: "Backend timed out waiting for credentials."
GitHubTool init (bad PAT) | HTTP 401 on token validation call | Send auth_error XPC card: "GitHub token invalid." Continue without GitHub. | Error card in stream. Settings opens to GitHub section.
ConsensusEngine init (bad API key) | HTTP 401 from Anthropic or OpenAI | Send auth_error XPC card per provider. Continue without that provider. | Error card in stream. Settings opens to API Keys section.
DocumentStore model load fail | Model file corrupt, out of memory, download fail | Send warning XPC card: "Document context unavailable." Continue. | Warning card. Doc store shows error state in Navigator.
Ready message send fail | XPC channel disconnected before ready sent | Log error. exit(1). | Swift detects disconnection. Restart backend.

PRINCIPLE | Failures in GitHubTool or ConsensusEngine initialization do NOT abort startup. The backend starts in a degraded state and reports the specific failure via XPC error cards. The operator can fix the credential in Settings and the backend will reinitialize the affected component without a full restart.

## 7.1 Degraded State Operation

# Components that failed initialization report their status via XPC.
# The backend tracks component health in a ComponentStatus registry.

class ComponentStatus(str, Enum):
    OK          = "ok"
    DEGRADED    = "degraded"   # Initialized but with reduced capability
    UNAVAILABLE = "unavailable" # Failed to initialize — commands will fail
    LOADING     = "loading"    # Still initializing (doc store)

@dataclass
class BackendHealth:
    github:        ComponentStatus = ComponentStatus.UNAVAILABLE
    consensus:     ComponentStatus = ComponentStatus.UNAVAILABLE
    doc_store:     ComponentStatus = ComponentStatus.LOADING
    build_ledger:  ComponentStatus = ComponentStatus.UNAVAILABLE

# Commands that require an unavailable component:
# Emit error card: "GitHub integration unavailable. Check Settings → GitHub."
# Do not crash the backend.

# Reinitialization on credential update:
# When operator updates a credential in Settings, Swift sends a new
# credentials XPC message. Backend reinitializes the affected component.
# No restart required.

# 8. Graceful Shutdown

## 8.1 Three Shutdown Scenarios

Scenario | Trigger | Backend Behavior | State Guarantee
Clean shutdown | /stop command from operator or Swift sends stop XPC message | Complete current gate (if any). Flush ThreadStateStore. Send shutdown_ack XPC. exit(0). | All checkpoint state persisted. Build resumes cleanly on next start.
Interrupted shutdown | SIGTERM (e.g. macOS terminating the process) | SIGTERM handler: flush ThreadStateStore immediately. exit(0). | Checkpoint state persisted if flush completes before OS kills. Typical flush < 200ms.
Crash | SIGKILL, unhandled exception, segfault in native code | No handler — process exits immediately. | ThreadStateStore uses atomic writes (tmp → rename). Last complete checkpoint is valid. Partial write is tmp file — ignored on resume.

## 8.2 Shutdown Implementation

import signal

_shutdown_requested = asyncio.Event()

def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Install SIGTERM handler for graceful shutdown."""
    def _sigterm_handler():
        logger.info("SIGTERM received — initiating graceful shutdown")
        _shutdown_requested.set()
    loop.add_signal_handler(signal.SIGTERM, _sigterm_handler)


async def _graceful_shutdown(
    router:    CommandRouter,
    xpc:       XPCServer,
    logger:    logging.Logger,
    reason:    str = "clean",
) -> None:
    """
    Shutdown sequence for clean and SIGTERM scenarios.
    Called by: /stop command handler and SIGTERM signal handler.
    """
    logger.info(f"Graceful shutdown initiated: reason={reason}")

    # 1. Stop accepting new commands
    router.stop_accepting_commands()

    # 2. Wait for active gate to complete (max 5 seconds)
    if router.has_active_gate():
        logger.info("Waiting for active gate to complete...")
        try:
            await asyncio.wait_for(router.gate_complete_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Gate did not complete in 5s — shutting down anyway")

    # 3. Flush ThreadStateStore
    if router.active_thread_store:
        logger.info("Flushing build state...")
        router.active_thread_store.flush()
        logger.info("Build state flushed")

    # 4. Send shutdown acknowledgement to Swift
    try:
        await asyncio.wait_for(
            xpc.send({
                "type": "shutdown_ack",
                "reason": reason,
                "active_build_persisted": router.active_thread_store is not None,
            }),
            timeout=2.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Could not send shutdown_ack — XPC may already be closed")

    # 5. Close XPC server
    await xpc.close()
    logger.info("Shutdown complete")


FLUSH_TIMEOUT_SEC = 10   # Maximum time for ThreadStateStore.flush() on SIGTERM

# SIGTERM handler (synchronous — runs in signal context):
def _fast_sigterm_handler(signum, frame):
    """Fast SIGTERM handler — flush and exit without async overhead."""
    import sys
    # Best-effort flush
    if _active_thread_store is not None:
        try:
            _active_thread_store.flush()  # Atomic write — fast
        except Exception:
            pass  # Exit regardless
    sys.exit(0)

## 8.3 Shutdown Timing Requirements

Operation | Timeout | If Exceeded
Wait for active gate | 5 seconds | Log warning, continue shutdown. Gate state is persisted in ThreadStateStore.
ThreadStateStore.flush() | 200ms (typical), 2s (maximum) | Log error, continue shutdown. Last partial checkpoint is valid due to atomic writes.
XPC shutdown_ack send | 2 seconds | Log warning, continue. Swift detects process exit via process monitoring.
Total clean shutdown time | < 10 seconds | If exceeded: Swift shows "Backend stopped unexpectedly" error card.

# 9. Startup Health Check (TRD-9 Integration)

## 9.1 XPC Integration Test Sequence

The XPC integration test in TRD-9 Section 9.2 validates the full startup sequence on the Mac CI runner. This section specifies what the test validates and the timing requirements it must meet.

# Startup sequence validation in XPCIntegrationTest (TRD-9):

# 1. Start Python backend process with test socket path and nonce
# 2. Read stdout until CRAFTED_LISTENING:{socket_path} received
    assert output received within LISTENING_TIMEOUT_SEC = 10

# 3. Connect XPC client to socket_path
    assert connection established within CONNECT_TIMEOUT_SEC = 5

# 4. Complete handshake (nonce exchange)
    assert handshake_ack received within HANDSHAKE_TIMEOUT_SEC = 5

# 5. Send credentials XPC message
    assert credentials_ack received within CRED_ACK_TIMEOUT_SEC = 5

# 6. Wait for ready message
    assert ready message received within READY_TIMEOUT_SEC = 30
    assert ready.agent_version matches VERSION file
    assert ready.capabilities includes "consensus_engine"
    assert ready.capabilities includes "build_pipeline"

# 7. Send ping
    assert pong received within PING_TIMEOUT_SEC = 5

# 8. Verify startup timing
    total_time = time_from_process_start_to_ready
    assert total_time < STARTUP_TIMEOUT_SEC = 30
    log f"Startup time: {total_time:.1f}s"  # tracked in CI metrics

# 9. Verify version compatibility check
    result = swift_mock.validate_ready_message(ready)
    assert result == VersionCheckResult.compatible

## 9.2 Startup Timing Budget

Phase | Target | Measured From | Alert If Exceeded
Backend process start to LISTENING signal | < 3s | Process launch | 5s — embedding model not needed yet
XPC handshake to credentials_ack | < 1s | LISTENING signal | 3s — pure network/IPC, no I/O
Credentials to ready message | < 5s | credentials_ack | 10s — GitHubTool and ConsensusEngine init
Total startup (launch to ready) | < 8s | Process launch | 15s — alert in CI metrics, not a failure
Doc store ready (background) | < 30s | Process launch | 60s — embedding model load on first run

# 10. Testing Requirements

Test | Coverage Target | Critical Cases
main() startup sequence | 95% | All steps execute in order; GitHubTool init failure does not abort startup; credential timeout exits with code 1; CRAFTED_LISTENING printed before credentials wait
validateReadyMessage() (Swift) | 100% | major mismatch → incompatible; backend older minor → incompatible; backend newer minor → compatibleWithWarning; exact match → compatible; minSwiftVersion check both directions
_graceful_shutdown() | 95% | Gate completes before shutdown in clean scenario; flush called before exit; shutdown_ack sent; SIGTERM triggers flush and exit(0)
Degraded state operation | 90% | GitHubTool unavailable → GitHub commands emit error card, not crash; ConsensusEngine unavailable → generation commands emit error card
Credential reinitialization | 85% | New credentials XPC message triggers GitHubTool reinit; bad credentials leave previous state unchanged
Version compatibility matrix | 100% | All cells in Section 5.2 compatibility matrix tested programmatically
Startup timing | Integration (TRD-9) | Full startup under STARTUP_TIMEOUT_SEC = 30; LISTENING signal under 3s; ready under 8s

## 10.1 Startup Sequence Unit Test

# tests/test_startup.py

async def test_startup_sequence_order():
    """
    Verify components initialize in the correct order.
    Uses a mock XPC server and mock credential delivery.
    """
    init_order = []

    class TrackingGitHubTool:
        def __init__(self, creds, *args, **kwargs):
            init_order.append("github")
            assert "anthropic_api_key" in vars(creds) or hasattr(creds, "anthropic_api_key")

    class TrackingConsensusEngine:
        def __init__(self, creds, *args, **kwargs):
            init_order.append("consensus")

    # Simulate credential delivery after 0.1s
    mock_xpc = MockXPCServer()
    asyncio.create_task(_deliver_creds_after(mock_xpc, delay=0.1))

    await _startup_with_mocks(
        xpc=mock_xpc,
        github_cls=TrackingGitHubTool,
        engine_cls=TrackingConsensusEngine,
    )

    # Verify order: xpc must be first, github before consensus
    assert init_order.index("github") < init_order.index("consensus")
    # Verify both initialized
    assert "github" in init_order
    assert "consensus" in init_order


async def test_credential_timeout_exits_cleanly():
    """Credential timeout results in exit(1), not hang."""
    mock_xpc = MockXPCServer()  # Never delivers credentials

    with pytest.raises(SystemExit) as exc_info:
        await _startup_with_timeout(xpc=mock_xpc, timeout=0.1)

    assert exc_info.value.code == 1

# 11. Out of Scope

Feature | Where Specified
Full app lifecycle (foreground, background, auto-lock) | TRD-1 Section 9
XPC wire protocol (message format, nonce auth, reconnection) | TRD-1 Section 6
Protocol versioning for individual message types | TRD-1 Section 6.6 (extension)
Build pipeline stage execution | TRD-3
ThreadStateStore checkpoint format | TRD-3 Section 4
Credential storage and Keychain mechanics | TRD-1 Section 5
Process health monitoring (ping/pong heartbeat) | TRD-1 Section 7.3
Sparkle auto-update | TRD-1 Section 7.6
Plugin loading model | Not in scope for v1 — no plugin system

# 12. Open Questions

ID | Question | Owner | Needed By
OQ-01 | Credential reinitialization: when an operator updates a GitHub token in Settings, Swift sends a new credentials XPC message. The backend should reinitialize GitHubTool without a full restart. The mechanism is straightforward — replace the GitHubTool instance in the BackendHealth registry. But what happens to in-flight operations that are using the old GitHubTool instance? Recommendation: drain in-flight operations (max 5s wait), then reinitialize. | Engineering | Sprint 1
OQ-02 | Ready message and doc_store_status: the ready message is sent before the doc store finishes loading (status = "loading"). The separate doc_store_ready XPC message signals completion. Should the ready message be delayed until the doc store is ready? Recommendation: no — 5-30 seconds of delay before the operator sees the app respond is too long. The current split approach is correct. | Engineering | Sprint 1
OQ-03 | Startup timing in production: the 8-second startup budget assumes a warm machine. On a cold start (first launch after reboot), the embedding model may need to be loaded from disk for the first time, which can take 15-30 seconds on slower machines. Should the startup timeout in the XPC integration test be different from the production app timeout? Recommendation: yes — CI test uses a strict 8s budget; production app uses a 60s timeout with a progress indicator in the XPC channel. | Engineering | Sprint 1

# Appendix A: Startup Sequence Diagram

TIME →

Swift Shell                     Python Backend
────────────────────────────────────────────────────────────────
Launch Python process ──────────▶ main() starts
                                  Logger initialized
                                  XPC server starts
                                  ◀── stdout: CRAFTED_LISTENING:{path}
Connect XPC socket ─────────────▶
                                  Handshake (nonce exchange)
                      ◀────────── handshake_ack
Touch ID / biometric
Deliver credentials ────────────▶
                                  credentials received
                                  GitHubTool.init()    ─── may emit auth_error
                                  ConsensusEngine.init() ─ may emit auth_error
                                  DocumentStore.load() ─── async background task
                      ◀────────── ready {version, capabilities, doc_store:"loading"}
validateReadyMessage()
if incompatible:
  show error card                 (credentials never delivered)
if compatible:
Deliver credentials ────────────▶ (already delivered above)
                                  ready message IS the handshake — credentials
                                  were delivered in step above, ready confirms
Show app as ready                 receipt and compatibility

    ↕  (async, in background)
                                  DocumentStore finishes loading
                      ◀────────── doc_store_ready
Doc icon in Navigator: Embedded ✓

────────────────────────────────────────────────────────────────
SHUTDOWN (clean):

Operator: /stop
Swift sends stop XPC ───────────▶
                                  Stop accepting commands
                                  Wait for active gate (max 5s)
                                  ThreadStateStore.flush()
                      ◀────────── shutdown_ack
Process exits (exit 0)
Swift shows: "Agent stopped"

SHUTDOWN (SIGTERM):

macOS sends SIGTERM ────────────▶
                                  SIGTERM handler:
                                  ThreadStateStore.flush()
                                  exit(0)
(XPC disconnects automatically)
Swift detects exit, shows card

# Appendix B: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial specification — addresses startup sequence and version handshake gap identified in senior dev review