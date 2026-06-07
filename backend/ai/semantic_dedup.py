"""LLM-judge semantic deduplication — the final, meaning-level dedup layer.

Why this exists: word/entity/title/event_key heuristics all compare surface
tokens, so they miss the same real-world event reported by different outlets, in
different languages, from different angles (e.g. one paper leads with "no
election connection", another with "pensions and housing" — same DISY/Fidias
deal, near-zero shared words). This layer asks an LLM to compare MEANING: given a
candidate and the recently published items, is the candidate the same event as
any of them?

Cost control: this runs at most once per queue candidate, and only after all the
cheap filters have passed — callers should invoke it only when the cheap dedup
was NOT already confident. On any API failure it returns "not a duplicate" so it
never blocks publishing (the cheap layers remain the safety net).
"""

import json

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

KIE_API_KEY = settings.kie_api_key
CLAUDE_URL = "https://api.kie.ai/claude/v1/messages"
GEMINI_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"

# Only compare against this many most-recent published items (keeps the prompt
# small and the cost bounded). Ordered newest-first by the caller.
MAX_COMPARE = 12

_VERDICT_TOOL_CLAUDE = {
    "name": "dedup_verdict",
    "description": "Decide whether the candidate news item duplicates any already-published item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "duplicate_of_index": {
                "type": "integer",
                "description": "0-based index of the published item the candidate duplicates, or -1 if the candidate is a genuinely new/distinct story.",
            },
            "reason": {"type": "string", "description": "One short sentence."},
        },
        "required": ["duplicate_of_index", "reason"],
    },
}

_SYSTEM = (
    "You are a news-desk editor preventing duplicate posts in a single feed.\n"
    "A DUPLICATE means the SAME real-world event, announcement, incident, or "
    "decision — even if reported by a different outlet, in a different language, "
    "or from a different angle/emphasis.\n"
    "NOT a duplicate: a genuinely new development on a running story (a later "
    "lawsuit, a follow-up ruling, next-day consequences), or a different event "
    "that merely shares topic/people.\n"
    "Be precise: prefer -1 unless you are confident it is the same event."
)


def _build_user_msg(candidate: str, published: list[str]) -> str:
    pub = "\n".join(f"[{i}] {p}" for i, p in enumerate(published))
    return (
        f"CANDIDATE (may be published):\n{candidate}\n\n"
        f"ALREADY PUBLISHED in the last 48h:\n{pub}\n\n"
        "Call dedup_verdict: which published item, if any, does the candidate duplicate?"
    )


async def _judge_via_claude(candidate: str, published: list[str]) -> dict | None:
    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 500,
        "stream": False,
        "messages": [{"role": "user", "content": f"{_SYSTEM}\n\n{_build_user_msg(candidate, published)}"}],
        "tools": [_VERDICT_TOOL_CLAUDE],
        "tool_choice": {"type": "tool", "name": "dedup_verdict"},
    }
    headers = {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post(CLAUDE_URL, json=payload, headers=headers)
        data = r.json()
    if isinstance(data, dict) and data.get("code") in (429, 455, 500, 503):
        raise RuntimeError(f"KIE error {data.get('code')}: {data.get('msg')}")
    for block in data.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "dedup_verdict":
            return block.get("input")
    return None


async def find_duplicate(candidate: str, published: list[str]) -> tuple[int, str] | None:
    """Return (index, reason) of the published item the candidate duplicates, else None.

    candidate / published entries should be compact "headline — summary" strings.
    Fails OPEN: any error → None (not a duplicate) so publishing is never blocked.
    """
    if not KIE_API_KEY or not candidate or not published:
        return None
    published = published[:MAX_COMPARE]
    try:
        verdict = await _judge_via_claude(candidate, published)
    except Exception as e:  # noqa: BLE001 — never block publishing on judge failure
        log.warning("semantic_dedup.judge_failed", error=str(e)[:120])
        return None
    if not verdict:
        return None
    idx = verdict.get("duplicate_of_index", -1)
    if isinstance(idx, int) and 0 <= idx < len(published):
        return idx, str(verdict.get("reason", ""))[:200]
    return None
