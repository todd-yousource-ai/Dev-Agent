# TRD-2-Consensus-Engine

_Source: `TRD-2-Consensus-Engine.docx` — extracted 2026-03-20 00:25 UTC_

---

TRD-2

Consensus Engine

Technical Requirements Document  •  v1.0

Field | Value
Product | Consensus Dev Agent
Document | TRD-2: Consensus Engine
Version | 1.0
Status | Draft — Engineering Review
Author | YouSource.ai
Date | 2026-03-19
Depends on | TRD-1 (macOS Application Shell)
Required by | TRD-3 (Build Pipeline — uses ConsensusEngine for code generation)
Language | Python 3.12 (backend), Swift protocol definitions (TRD-1 bridge)
Providers | Claude (Anthropic) + GPT-4o (OpenAI) — Claude arbitrates

# 1. Purpose and Scope

This document specifies the complete technical requirements for the Consensus Engine — the subsystem that takes a task prompt and produces a single best implementation by running two LLM providers in parallel and having Claude arbitrate the result.

The Consensus Engine is called by the Build Pipeline (TRD-3) for:

Code generation — implementation files for each PR

Test generation — test files for each PR

PRD generation — product requirement documents for each PRD item

PRD decomposition — breaking a scope statement into an ordered PRD list

The Engine does not own the 3-pass iterative review cycle. That is Stage 6 of the Build Pipeline (TRD-3), which calls back into the Engine for each review pass. The Engine provides the generation and arbitration primitives; the Pipeline orchestrates the passes.

SCOPE | This TRD specifies: provider protocol, parallel generation, arbitration, fallback state machine, token budget enforcement, context injection, OI-13 gate, result schema, and testing strategy. The 3-pass review protocol is in TRD-3 Section 6.

# 2. Design Decisions

## 2.1 Two-Provider Architecture

The Engine uses exactly two providers in v1: Anthropic Claude and OpenAI GPT-4o. Claude arbitrates. This is a deliberate cost and complexity decision — not a limitation to be overcome in v1.

Decision | Choice | Rationale
Provider count | 2 (Claude + GPT-4o) | 3+ providers add cost proportionally. Two providers capture the most useful diversity (reasoning style, code style) at lowest cost.
Arbitrator | Claude always | Claude has the deepest context about the target codebase from document injection. GPT-4o sees the same docs but Claude reasons about architectural compliance more reliably in practice.
Self-evaluation rule | Claude must NOT score its own output first | Arbitration prompt explicitly instructs: score both implementations on technical merit, not stylistic preference. If GPT output is objectively better, Claude must select it.
Third provider | Deferred to v2 via ProviderProtocol | Interface is pluggable. Adding Gemini or a local model requires only a new ProviderAdapter implementation.
Generation order | Parallel — both providers called simultaneously | Halves generation latency vs sequential. Neither provider sees the other's output during generation.
Arbitration model | Same Claude model used for generation | Consistent reasoning capability. A separate "judge" model adds cost and latency without clear benefit given the objectivity prompt.

## 2.2 What the Engine Does NOT Do

It does not run the 3-pass review cycle — that is TRD-3

It does not manage GitHub operations — that is TRD-5

It does not persist build state — that is the Build Pipeline's ThreadStateStore

It does not make decisions about which PR to build next — that is TRD-3

It does not enforce gate logic — operators interact with TRD-3, not the Engine

# 3. Provider Protocol

## 3.1 ProviderAdapter Interface

Every LLM provider is wrapped in a ProviderAdapter. Adding a new provider means implementing this protocol and registering it in the provider registry — no changes to the ConsensusEngine core.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProviderConfig:
    """Configuration for a single provider instance."""
    provider_id: str          # Unique ID: "claude", "openai", "gemini"
    display_name: str         # "Claude (claude-sonnet-4-5)", "GPT-4o"
    model: str                # Exact model string: "claude-sonnet-4-5"
    api_key: str              # From Keychain via credential delivery
    max_tokens: int           # Per-call output limit
    temperature: float        # 0.0–1.0
    timeout_sec: int          # Per-call timeout
    cost_per_input_mtok: float  # USD per million input tokens
    cost_per_output_mtok: float # USD per million output tokens


@dataclass
class ProviderResult:
    """Output from a single provider generation call."""
    provider_id: str
    content: str              # Generated code or text
    input_tokens: int
    output_tokens: int
    cost_usd: float           # Computed from token counts and rates
    duration_sec: float
    model: str                # Actual model used (may differ from requested)
    error: Optional[str]      # None on success
    success: bool             # False if error is set


class ProviderAdapter(ABC):
    """Abstract base for all LLM provider adapters."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def generate(self,
                       system: str,
                       user: str,
                       max_tokens: Optional[int] = None) -> ProviderResult:
        """
        Call the provider with the given system and user prompts.
        Must return a ProviderResult — never raise. Errors go into result.error.
        """
        ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a string using provider's tokenizer."""
        ...

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

## 3.2 Anthropic Adapter

import anthropic
import time
import asyncio

class AnthropicAdapter(ProviderAdapter):

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client = anthropic.AsyncAnthropic(api_key=config.api_key)

    async def generate(self, system: str, user: str,
                        max_tokens: Optional[int] = None) -> ProviderResult:
        mt = max_tokens or self.config.max_tokens
        start = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self._client.messages.create(
                    model=self.config.model,
                    max_tokens=mt,
                    temperature=self.config.temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                ),
                timeout=self.config.timeout_sec,
            )
            content = resp.content[0].text if resp.content else ""
            input_tok  = resp.usage.input_tokens
            output_tok = resp.usage.output_tokens
            cost = (input_tok  / 1_000_000 * self.config.cost_per_input_mtok +
                    output_tok / 1_000_000 * self.config.cost_per_output_mtok)
            return ProviderResult(
                provider_id=self.provider_id, content=content,
                input_tokens=input_tok, output_tokens=output_tok,
                cost_usd=cost, duration_sec=time.monotonic()-start,
                model=resp.model, error=None, success=True,
            )
        except asyncio.TimeoutError:
            return ProviderResult(
                provider_id=self.provider_id, content="",
                input_tokens=0, output_tokens=0, cost_usd=0.0,
                duration_sec=self.config.timeout_sec,
                model=self.config.model, error="timeout", success=False,
            )
        except Exception as e:
            return ProviderResult(
                provider_id=self.provider_id, content="",
                input_tokens=0, output_tokens=0, cost_usd=0.0,
                duration_sec=time.monotonic()-start,
                model=self.config.model, error=str(e), success=False,
            )

    def estimate_tokens(self, text: str) -> int:
        # Approximation: 1 token ≈ 4 chars for English/code
        # Use tiktoken cl100k_base for OpenAI; Anthropic has no public tokenizer
        return len(text) // 4

## 3.3 OpenAI Adapter

from openai import AsyncOpenAI

class OpenAIAdapter(ProviderAdapter):

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client = AsyncOpenAI(api_key=config.api_key)

    async def generate(self, system: str, user: str,
                        max_tokens: Optional[int] = None) -> ProviderResult:
        mt = max_tokens or self.config.max_tokens
        start = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self.config.model,
                    max_tokens=mt,
                    temperature=self.config.temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                ),
                timeout=self.config.timeout_sec,
            )
            choice = resp.choices[0]
            content    = choice.message.content or ""
            input_tok  = resp.usage.prompt_tokens
            output_tok = resp.usage.completion_tokens
            cost = (input_tok  / 1_000_000 * self.config.cost_per_input_mtok +
                    output_tok / 1_000_000 * self.config.cost_per_output_mtok)
            return ProviderResult(
                provider_id=self.provider_id, content=content,
                input_tokens=input_tok, output_tokens=output_tok,
                cost_usd=cost, duration_sec=time.monotonic()-start,
                model=resp.model, error=None, success=True,
            )
        except asyncio.TimeoutError:
            return ProviderResult(
                provider_id=self.provider_id, content="",
                input_tokens=0, output_tokens=0, cost_usd=0.0,
                duration_sec=self.config.timeout_sec,
                model=self.config.model, error="timeout", success=False,
            )
        except Exception as e:
            return ProviderResult(
                provider_id=self.provider_id, content="",
                input_tokens=0, output_tokens=0, cost_usd=0.0,
                duration_sec=time.monotonic()-start,
                model=self.config.model, error=str(e), success=False,
            )

    def estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4   # fallback

## 3.4 Provider Registry

class ProviderRegistry:
    """
    Singleton registry of available provider adapters.
    Populated at backend startup after credential delivery from XPC.
    """
    _instance: Optional["ProviderRegistry"] = None

    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    @classmethod
    def instance(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, adapter: ProviderAdapter) -> None:
        self._adapters[adapter.provider_id] = adapter

    def get(self, provider_id: str) -> ProviderAdapter:
        if provider_id not in self._adapters:
            raise KeyError(f"Provider not registered: {provider_id}")
        return self._adapters[provider_id]

    def all(self) -> list[ProviderAdapter]:
        return list(self._adapters.values())

    @classmethod
    def from_credentials(cls, creds: dict) -> "ProviderRegistry":
        """Build registry from XPC credential delivery payload."""
        registry = cls.instance()
        registry.register(AnthropicAdapter(ProviderConfig(
            provider_id="claude",
            display_name="Claude (claude-sonnet-4-5)",
            model="claude-sonnet-4-5",
            api_key=creds["anthropic_api_key"],
            max_tokens=8192,
            temperature=0.2,
            timeout_sec=120,
            cost_per_input_mtok=3.00,
            cost_per_output_mtok=15.00,
        )))
        registry.register(OpenAIAdapter(ProviderConfig(
            provider_id="openai",
            display_name="GPT-4o",
            model="gpt-4o",
            api_key=creds["openai_api_key"],
            max_tokens=8192,
            temperature=0.2,
            timeout_sec=120,
            cost_per_input_mtok=2.50,
            cost_per_output_mtok=10.00,
        )))
        return registry

# 4. Generation Pipeline

## 4.1 ConsensusResult Schema

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ScoringResult:
    """Scores from the arbitration pass."""
    winner: str                  # "claude" | "openai" | "tie"
    claude_score: int            # 1–10
    openai_score: int            # 1–10
    rationale: str               # One concrete sentence: WHY this winner
    claude_weaknesses: list[str] # Up to 3 specific weaknesses
    openai_weaknesses: list[str] # Up to 3 specific weaknesses
    evaluator: str               # "claude" (always in v1)
    evaluation_cost_usd: float
    evaluation_duration_sec: float


@dataclass
class ConsensusResult:
    """Full output from one ConsensusEngine.run() call."""
    # Inputs (stored for audit and replay)
    task: str                    # Task description
    task_type: str               # "code" | "test" | "prd" | "decompose" | "review"

    # Provider outputs
    claude_result: ProviderResult
    openai_result: ProviderResult

    # Arbitration
    scoring: ScoringResult

    # Final output
    winner_content: str          # The winning implementation
    winner_provider: str         # "claude" | "openai" | "fallback"

    # Economics
    total_cost_usd: float        # Sum of all provider + arbitration costs
    total_input_tokens: int
    total_output_tokens: int
    total_duration_sec: float

    # Flags
    single_provider_mode: bool = False   # True if one provider failed
    arbitration_failed: bool   = False   # True if scoring errored
    oi13_blocked: bool         = False   # True if token budget exceeded

    # Optional: improvement pass output
    improved_content: Optional[str] = None
    improvement_applied: bool       = False

## 4.2 Parallel Generation

import asyncio
import logging

logger = logging.getLogger("forge.consensus")

GENERATION_SYSTEM = """You are a senior engineer building production-quality software.
You receive a technical task with full context from the project's technical specifications.

Requirements:
- Implement EXACTLY what the task specifies — no more, no less
- Ground every decision in the provided TRD/PRD document excerpts
- Fail closed: prefer explicit error handling over silent degradation
- Security: validate all inputs, reject dangerous paths, never use shell=True
- No placeholder comments like "# TODO: implement this"
- Complete, runnable code only

Respond with ONLY the implementation — no markdown fences, no explanation.
The output will be written directly to a file and executed.
"""


async def _generate_parallel(
    system: str,
    user: str,
    registry: ProviderRegistry,
    max_tokens: Optional[int] = None,
) -> tuple[ProviderResult, ProviderResult]:
    """
    Call both providers simultaneously.
    Returns (claude_result, openai_result).
    Never raises — errors are captured in ProviderResult.error.
    """
    claude  = registry.get("claude")
    openai_ = registry.get("openai")

    # Fire both calls at the same time — no cross-contamination
    # Neither provider sees the other's prompt or output during generation
    claude_task  = asyncio.create_task(claude.generate(system, user, max_tokens))
    openai_task  = asyncio.create_task(openai_.generate(system, user, max_tokens))

    # Wait for both — do not cancel one if the other finishes first
    claude_result, openai_result = await asyncio.gather(
        claude_task, openai_task,
        return_exceptions=False,  # Errors captured inside ProviderResult
    )
    return claude_result, openai_result

## 4.3 Fallback State Machine

GenerationOutcome:
  BOTH_SUCCESS     → arbitrate → winner_content
  CLAUDE_ONLY      → single_provider_mode=True, winner=claude (no arbitration)
  OPENAI_ONLY      → single_provider_mode=True, winner=openai (no arbitration)
  BOTH_FAILED      → raise ConsensusError (pipeline handles escalation)


async def _resolve_generation(
    claude_r: ProviderResult,
    openai_r: ProviderResult,
    arbitrator: ProviderAdapter,
    task: str,
    task_type: str,
    budget: "TokenBudget",
) -> ConsensusResult:
    """Resolve generation results into a single ConsensusResult."""

    # Both failed
    if not claude_r.success and not openai_r.success:
        raise ConsensusError(
            f"Both providers failed. Claude: {claude_r.error}. OpenAI: {openai_r.error}"
        )

    # Single provider mode — one failed
    if not claude_r.success:
        logger.warning(f"Claude failed ({claude_r.error}), using OpenAI only")
        return _single_provider_result(openai_r, task, task_type, "openai")

    if not openai_r.success:
        logger.warning(f"OpenAI failed ({openai_r.error}), using Claude only")
        return _single_provider_result(claude_r, task, task_type, "claude")

    # Both succeeded — arbitrate
    scoring = await _arbitrate(claude_r, openai_r, arbitrator, task, budget)

    winner_content = (
        claude_r.content if scoring.winner in ("claude", "tie") else openai_r.content
    )

    total_cost = (claude_r.cost_usd + openai_r.cost_usd +
                  scoring.evaluation_cost_usd)

    return ConsensusResult(
        task=task, task_type=task_type,
        claude_result=claude_r, openai_result=openai_r,
        scoring=scoring,
        winner_content=winner_content,
        winner_provider=scoring.winner,
        total_cost_usd=total_cost,
        total_input_tokens=claude_r.input_tokens+openai_r.input_tokens+
                           scoring.evaluation_cost_usd,  # approx
        total_output_tokens=claude_r.output_tokens+openai_r.output_tokens,
        total_duration_sec=max(claude_r.duration_sec, openai_r.duration_sec) +
                           scoring.evaluation_duration_sec,
    )

# 5. Arbitration

## 5.1 Arbitration System Prompt

The arbitration prompt is the most security-sensitive prompt in the system. It must instruct Claude to evaluate both implementations objectively — penalizing self-preference explicitly.

ARBITRATION_SYSTEM = """You are the arbitration judge for a consensus code generation system.

You will evaluate TWO implementations of the same task — one from Claude, one from GPT-4o.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIVITY REQUIREMENT — READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are evaluating the Claude implementation AND your own potential output.
You MUST evaluate both with equal rigor.
Do NOT favor Claude because it shares your architecture or reasoning style.
Do NOT favor GPT-4o out of false modesty.
Stylistic similarity to your own output is NOT a valid reason to prefer Claude.
If GPT-4o's implementation is objectively more correct or more secure, SELECT IT.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVALUATION CRITERIA (in order of weight)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. SPEC COMPLIANCE (weight: 3x)
   Does the implementation do exactly what the task and TRD/PRD specify?
   Missing a required function = major deduction.
   Adding unrequested functionality = minor deduction.

2. SECURITY POSTURE (weight: 2x)
   Does it fail closed? Are inputs validated? Is there injection surface?
   shell=True in subprocess = immediate major deduction.
   Unhandled exception paths that could leak secrets = major deduction.

3. CORRECTNESS (weight: 2x)
   Does it handle edge cases? Are error paths complete?
   Does it compile/parse without errors?

4. CODE QUALITY (weight: 1x)
   Is it readable? Are names meaningful? Is complexity justified?
   Shorter is not always better — clarity matters more than brevity.

5. ENGINEERING STANDARDS (weight: 1x)
   Traceability comments, audit logging where required,
   type hints on public functions, docstrings on classes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — JSON ONLY, NO PREAMBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "winner": "claude" | "openai" | "tie",
  "claude_score": 1-10,
  "openai_score": 1-10,
  "rationale": "One sentence citing the SPECIFIC technical reason for the winner.",
  "claude_weaknesses": ["specific weakness", "..."],  // max 3, be specific
  "openai_weaknesses": ["specific weakness", "..."],  // max 3, be specific
  "evaluator": "claude"
}

Score meanings: 9-10=production-ready, 7-8=good with minor issues,
5-6=functional but needs work, 3-4=major issues, 1-2=broken or dangerous.

Tie rule: Only use "tie" if scores are within 1 point AND both implementations
are production-ready (both >= 7). Do not use "tie" to avoid making a decision.
"""

## 5.2 Arbitration User Prompt

ARBITRATION_USER_TMPL = """Task: {task}

TRD/PRD Context:
{doc_context}

━━━ CLAUDE IMPLEMENTATION ━━━
{claude_content}

━━━ GPT-4O IMPLEMENTATION ━━━
{openai_content}

Evaluate both implementations against the task and context above.
Remember the objectivity requirement: judge on technical merit only.
Respond with JSON only — no preamble."""


# Content truncation for arbitration:
# Show minimum 300 lines of each implementation.
# If implementation > 300 lines, show first 200 + last 100.
# Never truncate to less than 150 lines — scoring on a fragment is invalid.
MAX_PREVIEW_LINES = 300
MIN_PREVIEW_LINES = 150

def _truncate_for_arbitration(content: str, max_lines: int = MAX_PREVIEW_LINES) -> str:
    lines = content.split("\n")
    if len(lines) <= max_lines:
        return content
    # Show first 200 + separator + last 100
    head = lines[:200]
    tail = lines[-100:]
    omitted = len(lines) - 300
    return ("\n".join(head) +
            f"\n\n# ... [{omitted} lines omitted] ...\n\n" +
            "\n".join(tail))

## 5.3 Arbitration Implementation

import json

async def _arbitrate(
    claude_r: ProviderResult,
    openai_r: ProviderResult,
    arbitrator: ProviderAdapter,  # Always the Claude adapter
    task: str,
    budget: "TokenBudget",
) -> ScoringResult:
    """Run the arbitration pass. Returns ScoringResult with neutral fallback on error."""

    claude_preview = _truncate_for_arbitration(claude_r.content)
    openai_preview = _truncate_for_arbitration(openai_r.content)

    user_prompt = ARBITRATION_USER_TMPL.format(
        task=task,
        doc_context="(document context injected by caller)",
        claude_content=claude_preview,
        openai_content=openai_preview,
    )

    start = time.monotonic()
    result = await arbitrator.generate(
        system=ARBITRATION_SYSTEM,
        user=user_prompt,
        max_tokens=512,  # Scoring response is small
    )

    if not result.success:
        logger.error(f"Arbitration failed: {result.error}")
        return _neutral_tiebreak(result.cost_usd, time.monotonic()-start)

    try:
        raw = result.content.strip()
        # Strip markdown fences if model added them despite instructions
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        return ScoringResult(
            winner=data.get("winner", "tie"),
            claude_score=int(data.get("claude_score", 5)),
            openai_score=int(data.get("openai_score", 5)),
            rationale=data.get("rationale", "Evaluation result"),
            claude_weaknesses=data.get("claude_weaknesses", []),
            openai_weaknesses=data.get("openai_weaknesses", []),
            evaluator="claude",
            evaluation_cost_usd=result.cost_usd,
            evaluation_duration_sec=time.monotonic()-start,
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Arbitration parse failed: {e}. Raw: {raw[:200]}")
        return _neutral_tiebreak(result.cost_usd, time.monotonic()-start)


def _neutral_tiebreak(cost: float, duration: float) -> ScoringResult:
    """Used when arbitration fails. Never defaults to either provider."""
    return ScoringResult(
        winner="tie",  # Tiebreak: Claude wins tie (first in priority)
        claude_score=5, openai_score=5,
        rationale="Arbitration unavailable — neutral tiebreak applied",
        claude_weaknesses=[], openai_weaknesses=[],
        evaluator="fallback",
        evaluation_cost_usd=cost,
        evaluation_duration_sec=duration,
    )

## 5.4 Tie Resolution Rule

Condition | Winner | Rationale
Claude score > OpenAI score | Claude | Clear winner
OpenAI score > Claude score | OpenAI | Clear winner — objectivity requirement
"tie" in JSON and both >= 7 | Claude | Tiebreak — Claude has deeper doc context in most builds
"tie" in JSON and either < 7 | Re-run once with same prompts | Tight race on low scores means retry is worth the cost
Arbitration JSON parse error | Neutral tiebreak → Claude | Cannot make a decision without valid scores
Arbitration timeout/failure | Neutral tiebreak → Claude | Same as parse error

AUDIT | Every arbitration result is written to the audit log with full scoring JSON, both provider outputs (truncated to 500 chars each), and the final winner. This enables post-hoc analysis of whether the self-preference bias is occurring.

# 6. Context Injection

## 6.1 Document Context Protocol

Every generation call includes document context extracted from the project's loaded TRD/PRD documents. The context is injected into the user prompt — NOT the system prompt — to preserve the system prompt's instruction authority.

CONTEXT_BUDGET_CHARS = 24_000   # Max chars of doc context per call
CONTEXT_TOP_K        = 8        # Number of document chunks to retrieve

# Context injection position in user prompt:
USER_PROMPT_TEMPLATE = """Task: {task_description}

Technical Specification Context (from loaded TRD/PRD documents):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{doc_context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implementation requirements:
{impl_requirements}

Target file: {target_file}
Language: {language}
Framework: {framework}"""

# RULE: doc_context is retrieved PER CALL from the document store
# It is never shared between the two parallel provider calls
# Both providers get identical context — no asymmetric information

## 6.2 Doc Filter Protocol

The BuildThread carries a relevant_docs list set during scope confirmation. This list restricts which documents are searched for context, preventing cross-subsystem contamination when building a specific component.

# Context retrieval with doc filter
def build_generation_context(
    task: str,
    doc_store: DocumentStore,
    doc_filter: Optional[list[str]] = None,
    max_chars: int = CONTEXT_BUDGET_CHARS,
    top_k: int = CONTEXT_TOP_K,
) -> str:
    """
    Retrieve document context for a generation call.

    doc_filter: list of document names to restrict search to.
    If None: searches all loaded documents (scope-phase behavior).
    If provided: only searches the specified documents.
    If filter docs return < 1000 chars: falls back to unfiltered search.
    """
    ctx = doc_store.auto_context(
        query=task,
        doc_filter=doc_filter,
        top_k=top_k,
    )
    if doc_filter and len(ctx) < 1000:
        # Filter returned too little — fall back to full search
        logger.warning(f"Doc filter returned < 1000 chars, falling back to unfiltered")
        ctx = doc_store.auto_context(query=task, top_k=top_k)
    return ctx[:max_chars]

## 6.3 Forge Context Injection

The current codebase injects a hardcoded Forge architecture summary into every generation prompt. For the new app, this is replaced by a configurable platform context loaded from a file in the project's document store.

# Platform context: loaded from project doc store, not hardcoded
# File: PLATFORM_CONTEXT.md in the project documents
# If absent: no platform context injected (graceful degradation)

PLATFORM_CONTEXT_FILENAME = "PLATFORM_CONTEXT.md"

def get_platform_context(doc_store: DocumentStore) -> str:
    """
    Load platform-level architectural context.
    This is the document that explains what system is being built.
    For Forge builds: Forge architecture summary.
    For other projects: their equivalent context document.
    Returns empty string if no PLATFORM_CONTEXT.md is loaded.
    """
    return doc_store.get_document_content(PLATFORM_CONTEXT_FILENAME) or ""

# Platform context is appended to the system prompt (not user prompt)
# System prompt structure:
# [GENERATION_SYSTEM base] + [PLATFORM_CONTEXT if present]
def build_system_prompt(platform_context: str) -> str:
    if not platform_context:
        return GENERATION_SYSTEM
    return GENERATION_SYSTEM + f"\n\nPLATFORM CONTEXT:\n{platform_context[:4000]}"

# 7. Token Budget and OI-13 Gate

## 7.1 TokenBudget

from dataclasses import dataclass, field
from threading import Lock

@dataclass
class TokenBudgetConfig:
    """Configurable per-project token budget. Replaces hardcoded Forge constants."""
    # Per-PR thresholds
    warn_usd_per_pr: float   = 0.50    # Show warning card in UI
    stop_usd_per_pr: float   = 2.00    # Block generation, require operator override

    # Per-session total
    warn_usd_session: float  = 10.00   # Show session cost warning
    stop_usd_session: float  = 50.00   # Block all generation, require restart

    # Per-provider per-session (OI-13 equivalent)
    max_input_tokens_session:  dict[str, int] = field(
        default_factory=lambda: {"claude": 10_000_000, "openai": 10_000_000}
    )
    max_output_tokens_session: dict[str, int] = field(
        default_factory=lambda: {"claude": 2_000_000, "openai": 2_000_000}
    )


class TokenBudget:
    """Tracks token usage and cost across a build session."""

    def __init__(self, config: TokenBudgetConfig) -> None:
        self.config = config
        self._lock  = Lock()
        self._session_cost_usd   = 0.0
        self._current_pr_cost    = 0.0
        self._input_tokens:  dict[str, int] = {}
        self._output_tokens: dict[str, int] = {}

    def record(self, result: ProviderResult) -> None:
        with self._lock:
            self._session_cost_usd += result.cost_usd
            self._current_pr_cost  += result.cost_usd
            pid = result.provider_id
            self._input_tokens[pid]  = (
                self._input_tokens.get(pid, 0) + result.input_tokens)
            self._output_tokens[pid] = (
                self._output_tokens.get(pid, 0) + result.output_tokens)

    def reset_pr(self) -> None:
        """Call at the start of each new PR."""
        with self._lock:
            self._current_pr_cost = 0.0

    def check_pr_budget(self) -> "BudgetStatus":
        with self._lock:
            if self._current_pr_cost >= self.config.stop_usd_per_pr:
                return BudgetStatus.STOP
            if self._current_pr_cost >= self.config.warn_usd_per_pr:
                return BudgetStatus.WARN
            return BudgetStatus.OK

    def check_session_budget(self) -> "BudgetStatus":
        with self._lock:
            if self._session_cost_usd >= self.config.stop_usd_session:
                return BudgetStatus.STOP
            if self._session_cost_usd >= self.config.warn_usd_session:
                return BudgetStatus.WARN
            return BudgetStatus.OK

    def check_token_limit(self, provider_id: str) -> "BudgetStatus":
        with self._lock:
            in_used  = self._input_tokens.get(provider_id, 0)
            out_used = self._output_tokens.get(provider_id, 0)
            in_max   = self.config.max_input_tokens_session.get(provider_id, 10_000_000)
            out_max  = self.config.max_output_tokens_session.get(provider_id, 2_000_000)
            if in_used >= in_max or out_used >= out_max:
                return BudgetStatus.STOP
            if in_used >= in_max * 0.8 or out_used >= out_max * 0.8:
                return BudgetStatus.WARN
            return BudgetStatus.OK

    @property
    def session_cost_usd(self) -> float:
        return self._session_cost_usd

    @property
    def current_pr_cost_usd(self) -> float:
        return self._current_pr_cost


from enum import Enum
class BudgetStatus(Enum):
    OK   = "ok"
    WARN = "warn"
    STOP = "stop"

## 7.2 Budget Enforcement in the Engine

# In ConsensusEngine.run() — budget checked before each generation call

async def run(self, task: str, task_type: str, ...) -> ConsensusResult:

    # Check token limits for each provider before calling
    for provider_id in ["claude", "openai"]:
        status = self._budget.check_token_limit(provider_id)
        if status == BudgetStatus.STOP:
            raise OI13BlockedError(
                f"Token limit reached for {provider_id}. "
                "Run /oi13 resolve or increase limits in Settings."
            )

    # Check per-PR cost
    pr_status = self._budget.check_pr_budget()
    if pr_status == BudgetStatus.STOP:
        raise CostLimitError(
            f"PR cost exceeded ${self._budget.config.stop_usd_per_pr:.2f}. "
            "Approve override to continue."
        )
    if pr_status == BudgetStatus.WARN:
        # Emit warning card to UI — do NOT block
        self._emit_warning(
            f"PR cost approaching limit: {self._budget.current_pr_cost_usd:.3f} / {self._budget.config.warn_usd_per_pr:.2f}"
        )

    # Generate...
    claude_r, openai_r = await _generate_parallel(...)

    # Record costs after generation
    self._budget.record(claude_r)
    self._budget.record(openai_r)

    # ... arbitrate and return

## 7.3 OI-13 Gate Configuration

The OI-13 gate replaces the hardcoded Forge-specific memory budget constants. Limits are now per-project, configured in Settings, and stored in UserDefaults (non-sensitive values — not secrets).

Setting Key | Default | Description
oi13_claude_input_mtok | 10.0 | Max Claude input tokens per session (millions)
oi13_claude_output_mtok | 2.0 | Max Claude output tokens per session (millions)
oi13_openai_input_mtok | 10.0 | Max OpenAI input tokens per session (millions)
oi13_openai_output_mtok | 2.0 | Max OpenAI output tokens per session (millions)
cost_warn_per_pr_usd | 0.50 | Show UI warning when PR cost exceeds this
cost_stop_per_pr_usd | 2.00 | Block generation when PR cost exceeds this
cost_warn_session_usd | 10.00 | Show session warning when total exceeds this
cost_stop_session_usd | 50.00 | Block all generation when session total exceeds this

# 8. ConsensusEngine Public API

## 8.1 Engine Interface

class ConsensusEngine:
    """
    The single entry point for all generation tasks.
    Called by Build Pipeline (TRD-3) — never called directly by UI.
    """

    def __init__(
        self,
        registry:    ProviderRegistry,
        doc_store:   "DocumentStore",
        budget:      TokenBudget,
        audit:       "AuditLogger",
        emit_card:   Callable[[dict], None],  # XPC card callback
    ) -> None: ...

    async def run(
        self,
        task:         str,
        task_type:    str,             # "code"|"test"|"prd"|"decompose"|"review"
        system:       Optional[str] = None,   # Override default generation system
        doc_filter:   Optional[list[str]] = None,
        max_tokens:   Optional[int] = None,
        context_hint: Optional[str] = None,   # Additional context beyond doc retrieval
    ) -> ConsensusResult:
        """
        Run the full generation + arbitration pipeline.
        Returns ConsensusResult. Never raises — errors are in the result.
        Token budget violations raise OI13BlockedError or CostLimitError.
        """
        ...

    async def generate_single(
        self,
        provider_id: str,
        system:      str,
        user:        str,
        max_tokens:  Optional[int] = None,
    ) -> ProviderResult:
        """
        Call a single provider directly — used by 3-pass review (TRD-3)
        and by arbitration self-call.
        """
        ...

    def reset_pr_budget(self) -> None:
        """Call at the start of each PR in TRD-3."""
        self._budget.reset_pr()

    @property
    def session_cost_usd(self) -> float:
        return self._budget.session_cost_usd

    @property
    def current_pr_cost_usd(self) -> float:
        return self._budget.current_pr_cost_usd

## 8.2 Task Type Configurations

task_type | System Prompt | Max Tokens | Temperature | Arbitration?
code | GENERATION_SYSTEM + platform_context | 8192 | 0.2 | Yes
test | TEST_GENERATION_SYSTEM + platform_context | 4096 | 0.1 | Yes — lower temp for determinism
prd | PRD_GENERATION_SYSTEM | 12000 | 0.3 | Yes — via PRDPlanner
decompose | DECOMPOSE_SYSTEM | 16000 | 0.2 | Yes — via PRDPlanner
review | REVIEW_SYSTEM | 4096 | 0.0 | No — single provider, Claude only

NOTE | Review calls (task_type="review") always use Claude only — they are called by TRD-3's 3-pass review stage which has already selected a winner. There is no point running both providers to review the same code when only one review output is needed.

## 8.3 Generation System Prompts

### 8.3.1 Test Generation System

TEST_GENERATION_SYSTEM = """You are a senior engineer writing production-quality tests.

Test requirements:
- Use pytest for Python, Jest for TypeScript, go test for Go
- Every public function and class must have at least one test
- Test the happy path, one edge case, and one error/failure case minimum
- Use fixtures and parametrize for repetitive cases
- Mock all external I/O (API calls, file system, subprocess)
- Tests must be independent — no shared mutable state between tests
- Test names must describe what they test: test_create_entry_returns_hash_on_success

Security testing requirements:
- If the implementation handles file paths: test path traversal rejection
- If the implementation handles user input: test injection attempt rejection
- If the implementation calls subprocesses: test that shell=True is never used

Respond with ONLY the test file — no markdown fences, no explanation.
"""

### 8.3.2 Review System (used by TRD-3 Stage 6)

REVIEW_SYSTEM_PASS_1 = """You are a senior code reviewer conducting a spec compliance review.

REVIEW FOCUS: Correctness and Spec Compliance
Question to answer: Does this implementation exactly match what the PRD/TRD requires?

- Check every requirement in the provided PRD against the implementation
- Identify any missing functions, classes, or behaviors
- Identify anything implemented that was NOT specified (scope creep)
- Check error handling: are all documented error cases handled?

Respond in JSON:
{
  "issues_found": true | false,
  "issues": [{"location": "function/line", "severity": "critical|major|minor",
               "description": "what is wrong", "fix": "how to fix it"}],
  "improved_code": "complete fixed implementation if issues_found else empty string"
}
"""

REVIEW_SYSTEM_PASS_2 = """... Performance and Edge Cases ..."""

REVIEW_SYSTEM_PASS_3 = """... Security and Optimization ..."""
# Full prompts specified in TRD-3 Section 6

# 9. Result Persistence and Surfacing

## 9.1 Audit Log Entry

# Every ConsensusResult is written to the audit log as a JSONL entry
{
    "event": "consensus_result",
    "timestamp": 1710000000.0,
    "session_id": "uuid",
    "task_type": "code",
    "task_preview": "Implement LedgerEntry dataclass...",  // first 80 chars
    "winner": "claude",
    "claude_score": 8,
    "openai_score": 6,
    "rationale": "Claude handles hash chain validation...",
    "single_provider_mode": false,
    "arbitration_failed": false,
    "total_cost_usd": 0.043,
    "total_input_tokens": 12400,
    "total_output_tokens": 1850,
    "total_duration_sec": 18.4,
    "claude_error": null,
    "openai_error": null
}
// NOTE: winner_content is NOT logged — too large, stored in GitHub PR
// NOTE: claude_weaknesses and openai_weaknesses are NOT logged — use 
//       build_ledger for those if needed for future analysis

## 9.2 PR Body Attribution

# ConsensusResult is surfaced in the GitHub PR description
# Format (appended to PR body by TRD-3):

---
_Generated by Consensus Engine_
_Winner: Claude (8/10) vs GPT-4o (6/10)_
_Rationale: Claude implementation includes complete hash chain verification_
            _which is required by TRD-DTL Section 4.2. GPT-4o omitted this._
_Cost: $0.043 | Tokens: 14,250 | Time: 18.4s_

# Single provider mode attribution:
_Generated by Consensus Engine (single-provider mode — OpenAI unavailable)_
_Winner: Claude (no arbitration)_

# Arbitration failure attribution:
_Generated by Consensus Engine (arbitration unavailable — neutral tiebreak)_
_Winner: Claude (tiebreak)_

## 9.3 Build Ledger Integration

# ConsensusResult summary stored in build ledger journal entry (TRD-4)
# Called by TRD-3 after each completed PR

def consensus_to_journal_entry(result: ConsensusResult) -> dict:
    return {
        "consensus_winner":    result.winner_provider,
        "consensus_scores":    {
            "claude": result.scoring.claude_score,
            "openai": result.scoring.openai_score,
        },
        "consensus_rationale": result.scoring.rationale,
        "consensus_cost_usd":  result.total_cost_usd,
        "single_provider":     result.single_provider_mode,
        "improvement_applied": result.improvement_applied,
    }

# 10. Improvement Pass

## 10.1 When the Improvement Pass Runs

After arbitration, if the winning implementation has identified weaknesses and both scores are below 8, an improvement pass is offered. This takes the winner's content plus the loser's weaknesses and asks Claude to produce a synthesis.

Condition | Action
Both scores >= 8 | No improvement pass — winner is already high quality
Winner score < 8 AND weaknesses listed | Run improvement pass on winner
Score delta >= 3 (clear winner) | No improvement pass — loser had major issues, not useful
task_type == "review" | Never — review calls are already a refinement
single_provider_mode == True | No improvement pass — no losing implementation to learn from

## 10.2 Improvement Prompt

IMPROVEMENT_SYSTEM = """You are improving a code implementation based on peer review feedback.

Rules:
- Apply ONLY the specific improvements listed
- Do not restructure or rewrite sections that are not mentioned
- Do not change working functionality
- Preserve all existing tests and interfaces
- The output must be a complete, drop-in replacement for the original file

Respond with ONLY the improved code — no markdown fences, no explanation.
"""

IMPROVEMENT_USER_TMPL = """Winning implementation ({winner_provider}, {winner_score}/10):
{winner_content}

Specific weaknesses to address (from peer review):
{weaknesses}

Produce an improved version that addresses these weaknesses.
Do not change anything not mentioned above."""


async def _run_improvement_pass(
    result: ConsensusResult,
    arbitrator: ProviderAdapter,
) -> Optional[str]:
    """Returns improved content or None if pass should be skipped."""

    should_improve = (
        not result.single_provider_mode and
        result.task_type != "review" and
        min(result.scoring.claude_score, result.scoring.openai_score) < 8 and
        abs(result.scoring.claude_score - result.scoring.openai_score) < 3
    )
    if not should_improve:
        return None

    loser_weaknesses = (
        result.scoring.openai_weaknesses
        if result.winner_provider == "claude"
        else result.scoring.claude_weaknesses
    )
    if not loser_weaknesses:
        return None

    user = IMPROVEMENT_USER_TMPL.format(
        winner_provider=result.winner_provider,
        winner_score=max(result.scoring.claude_score, result.scoring.openai_score),
        winner_content=result.winner_content,
        weaknesses="\n".join(f"- {w}" for w in loser_weaknesses),
    )
    improved = await arbitrator.generate(
        system=IMPROVEMENT_SYSTEM, user=user, max_tokens=8192
    )
    if improved.success and len(improved.content) > 50:
        return improved.content
    return None

# 11. Error Types

class ConsensusError(Exception):
    """Both providers failed — no output possible."""
    pass

class OI13BlockedError(Exception):
    """Token limit reached for a provider."""
    pass

class CostLimitError(Exception):
    """Per-PR or session cost limit exceeded."""
    pass


# Error handling in Build Pipeline (TRD-3):
#
# ConsensusError:
#   → Show error card in UI
#   → Offer operator retry (up to MAX_RETRIES)
#   → After MAX_RETRIES: escalate to failure_handler
#
# OI13BlockedError:
#   → Show gate card: "Token limit reached for {provider}.
#      Increase limits in Settings > Build Defaults > Token Budgets.
#      Or continue in single-provider mode."
#   → Wait for operator response before continuing
#
# CostLimitError:
#   → Show gate card: "PR cost exceeded ${limit:.2f}.
#      Current: ${current:.2f}. Approve to continue anyway."
#   → Wait for operator override

# 12. Default Provider Configurations

Setting | Claude | GPT-4o | Notes
Model | claude-sonnet-4-5 | gpt-4o | Configurable in ProviderRegistry.from_credentials()
Temperature (code) | 0.2 | Low randomness for deterministic code
Temperature (PRD) | 0.3 | Slightly higher for creative decomposition
Temperature (review) | 0.0 | Deterministic review — same input → same critique
Max output tokens (code) | 8192 | Sufficient for most implementations
Max output tokens (PRD) | 12000 | PRDs are longer documents
Max output tokens (decompose) | 16000 | Large PRD plans need room
Max output tokens (arbitration) | 512 | N/A | Arbitration response is small JSON only
Timeout (generation) | 120s | Long enough for complex files
Timeout (arbitration) | 60s | N/A | Scoring should be fast
Input cost (per M tokens) | $3.00 | $2.50 | Approximate — update when pricing changes
Output cost (per M tokens) | $15.00 | $10.00 | Approximate — update when pricing changes

PRICING NOTE | API pricing changes frequently. The cost figures above are approximate as of 2026-Q1. The ProviderConfig fields cost_per_input_mtok and cost_per_output_mtok must be kept current. A mismatch between configured costs and actual costs affects budget enforcement accuracy but does not block generation.

# 13. Testing Strategy

## 13.1 Unit Tests

The consensus engine is non-deterministic — different runs with the same input produce different outputs. Unit tests focus on the deterministic structural behavior: routing, fallback logic, budget enforcement, schema validation.

Module | Coverage Target | Critical Test Cases
ProviderAdapter (Anthropic) | 85% | Success result schema; timeout returns ProviderResult with error; exception returns ProviderResult with error; never raises
ProviderAdapter (OpenAI) | 85% | Same as Anthropic; tiktoken token estimate vs 4-char approximation
ProviderRegistry | 100% | Register/get round-trip; get missing provider raises KeyError; from_credentials populates both providers
_generate_parallel | 90% | Both succeed; one fails; both fail; timeout respected; neither provider sees other's output during generation
_arbitrate | 100% | Valid JSON parsed correctly; markdown fence stripped; parse error returns neutral tiebreak; timeout returns neutral tiebreak; self-preference instruction present in system prompt
_neutral_tiebreak | 100% | Returns winner="tie" with scores both 5; evaluator="fallback"
TokenBudget | 100% | All four check methods; STOP when at threshold; WARN when at 80%; reset_pr clears PR cost only; session cost accumulates correctly
ConsensusEngine.run | 90% | Both succeed flow; single provider mode; ConsensusError on both fail; OI13BlockedError when limit hit; CostLimitError when cost exceeded
_truncate_for_arbitration | 100% | Content <= max_lines unchanged; content > max_lines shows head+tail+omitted count; minimum 150 lines always shown

## 13.2 Determinism Tests

Tests that verify the structural behavior is deterministic regardless of LLM output.

Winner selection: given mock ProviderResults with known scores, verify winner_provider matches expected logic

Tie resolution: given equal scores, verify Claude always wins tiebreak

Fallback routing: given one failed ProviderResult, verify single_provider_mode=True and no arbitration call

Budget gates: inject mock results with known costs, verify WARN and STOP fire at correct thresholds

Prompt injection check: verify ARBITRATION_SYSTEM contains the objectivity instruction text (regression test against prompt edits removing it)

## 13.3 Prompt Regression Tests

The arbitration prompt is the most important prompt in the system. Any edit that weakens the objectivity requirement must be caught.

# tests/test_consensus.py — prompt regression tests

def test_arbitration_prompt_contains_objectivity_instruction():
    """Guard against edits that remove the objectivity requirement."""
    from consensus import ARBITRATION_SYSTEM
    required_phrases = [
        "Do NOT favor Claude",
        "If GPT-4o",
        "objectively more correct",
        "SELECT IT",
        "Stylistic similarity",
    ]
    for phrase in required_phrases:
        assert phrase in ARBITRATION_SYSTEM, (
            f"Objectivity instruction missing from arbitration prompt: {phrase!r}\n"
            "This is a regression — the self-preference bias fix must be preserved."
        )


def test_arbitration_prompt_contains_all_criteria():
    from consensus import ARBITRATION_SYSTEM
    criteria = ["SPEC COMPLIANCE", "SECURITY POSTURE", "CORRECTNESS",
                "CODE QUALITY", "ENGINEERING STANDARDS"]
    for c in criteria:
        assert c in ARBITRATION_SYSTEM, f"Missing evaluation criterion: {c}"


def test_arbitration_prompt_requires_json_only():
    from consensus import ARBITRATION_SYSTEM
    assert "JSON ONLY" in ARBITRATION_SYSTEM or "JSON only" in ARBITRATION_SYSTEM
    assert "NO PREAMBLE" in ARBITRATION_SYSTEM or "no preamble" in ARBITRATION_SYSTEM.lower()

## 13.4 Mock Provider for Testing

class MockProviderAdapter(ProviderAdapter):
    """
    Deterministic mock for unit tests.
    Configure responses at construction time.
    """

    def __init__(
        self,
        provider_id: str,
        content: str = "mock implementation",
        error: Optional[str] = None,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> None:
        config = ProviderConfig(
            provider_id=provider_id,
            display_name=f"Mock {provider_id}",
            model=f"mock-{provider_id}",
            api_key="mock-key",
            max_tokens=8192,
            temperature=0.2,
            timeout_sec=30,
            cost_per_input_mtok=3.0,
            cost_per_output_mtok=15.0,
        )
        super().__init__(config)
        self._content = content
        self._error   = error
        self._in_tok  = input_tokens
        self._out_tok = output_tokens
        self.call_count = 0
        self.last_system: Optional[str] = None
        self.last_user:   Optional[str] = None

    async def generate(self, system: str, user: str,
                        max_tokens: Optional[int] = None) -> ProviderResult:
        self.call_count += 1
        self.last_system = system
        self.last_user   = user
        cost = (self._in_tok/1e6*3.0 + self._out_tok/1e6*15.0)
        return ProviderResult(
            provider_id=self.provider_id,
            content=self._content,
            input_tokens=self._in_tok,
            output_tokens=self._out_tok,
            cost_usd=cost,
            duration_sec=0.1,
            model=self.config.model,
            error=self._error,
            success=self._error is None,
        )

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

# 14. Performance Requirements

Metric | Target | Notes
Parallel generation latency (p50) | < 30 seconds | Measured: prompt sent → both results received
Parallel generation latency (p95) | < 90 seconds | Timeout is 120s — p95 should be well below
Arbitration latency (p50) | < 8 seconds | Small response (512 tokens max)
Arbitration latency (p95) | < 20 seconds | 
Total consensus run (code, p50) | < 45 seconds | Generation + arbitration combined
Total consensus run (code, p95) | < 110 seconds | 
Cost per code PR (typical) | $0.03–$0.10 | Varies by implementation size
Cost per PRD generation (typical) | $0.05–$0.15 | Larger output tokens
Token budget check overhead | < 1 ms | In-memory atomic operation

# 15. Dependencies

Package | Version | Use
anthropic | >=0.25 | AsyncAnthropic client for Claude
openai | >=1.14 | AsyncOpenAI client for GPT-4o
tiktoken | >=0.6 | Token estimation for OpenAI (cl100k_base encoding)
asyncio | stdlib | Parallel generation via asyncio.gather
dataclasses | stdlib | ProviderConfig, ProviderResult, ConsensusResult, ScoringResult
abc | stdlib | ProviderAdapter abstract base class
threading | stdlib | TokenBudget thread-safe counter (Lock)

# 16. Out of Scope

Feature | Reason Excluded | Target
Third provider (Gemini, Ollama) | ProviderProtocol is designed for this — add in v2 | v2
Streaming generation responses | Requires architectural change to XPC card protocol; deferred | v2
Fine-tuned model support | No fine-tuning infrastructure; deferred | TBD
Local inference (Ollama) | Network-local provider requires different adapter; ProviderProtocol supports it | v2
Cross-provider token sharing | Each provider has independent budget; cross-provider optimization not needed in v1 | v2
Automatic prompt optimization | Would require labeling ground truth; deferred to after v1 data collection | TBD
3-pass review cycle | Specified in TRD-3. Engine provides generate_single() for review calls. | TRD-3

# 17. Open Questions

ID | Question | Owner | Needed By
OQ-01 | Model strings: "claude-sonnet-4-5" and "gpt-4o" are pinned in ProviderRegistry.from_credentials(). Should model selection be a per-project setting? Recommendation: yes — add model_claude and model_openai to Settings in v1.1. | Product | v1.1
OQ-02 | Improvement pass: the threshold (both scores < 8, delta < 3) is a heuristic. Should it be configurable? Recommendation: make it a hidden advanced setting, not surfaced in main UI. | Engineering | Sprint 2
OQ-03 | Arbitration cost: scoring uses Claude with max_tokens=512. At current pricing this adds ~$0.001 per consensus run. Over a 35-PR build that is ~$0.035. Acceptable. No change needed. | Engineering | Resolved — no action
OQ-04 | Retry on ConsensusError: the engine raises, and TRD-3 retries up to MAX_RETRIES. Should the engine have its own internal retry on transient API errors (5xx, rate limit)? Recommendation: yes — add 2-retry internal loop with exponential backoff before raising ConsensusError. | Engineering | Sprint 1

# Appendix A: Cost Model Reference

Approximate costs for common operations. Updated Q1 2026. Verify against provider pricing pages before each release.

Operation | Input Tokens | Output Tokens | Claude Cost | GPT-4o Cost | Total (both + arbitration)
Code generation (500-line impl) | ~8,000 | ~2,500 | $0.061 | $0.045 | ~$0.12
Test generation (200-line test) | ~6,000 | ~1,000 | $0.033 | $0.025 | ~$0.07
PRD generation (full PRD) | ~12,000 | ~3,000 | $0.081 | $0.060 | ~$0.15
PRD decomposition (35 PRDs) | ~15,000 | ~4,000 | $0.105 | $0.075 | ~$0.19
Arbitration only | ~12,000 | ~300 | $0.040 | N/A | ~$0.04
Review pass (single) | ~10,000 | ~800 | $0.042 | N/A | ~$0.04

35-PR BUILD ESTIMATE | A typical 35-PR build using code + test generation with arbitration and no improvement passes costs approximately $5–$12 depending on implementation complexity. With all three review passes (TRD-3 Stage 6) the estimate rises to $12–$20.

# Appendix B: Document Change Log

Version | Date | Author | Changes
1.0 | 2026-03-19 | YouSource.ai | Initial full specification