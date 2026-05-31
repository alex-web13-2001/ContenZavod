"""AI Classification service — uses Claude 3.5 Sonnet via KIE.ai.

Classifies raw materials:
  new → classifying → classified

Extracts:
- category (politics, economy, society, culture, sport, tech, opinion, lifestyle)
- tags (up to 5 keywords)
- summary_ru (краткое описание на русском, 1-2 предложения)
- summary_en (short description in English, 1-2 sentences)
- relevance_score (0-100, relevance to Cyprus audience)
- sentiment (positive, negative, neutral, mixed)
"""

import json
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Claude 3.5 Sonnet via KIE.ai — Anthropic-compatible endpoint
KIE_API_URL = "https://api.kie.ai/claude/v1/messages"
KIE_API_KEY = settings.kie_api_key
MODEL = "claude-3-5-sonnet-20241022"

# Classification schema — OpenAI function calling format
CLASSIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_article",
        "description": "Classify a news article and extract structured metadata",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "politics", "economy", "society", "culture",
                        "sport", "tech", "opinion", "lifestyle",
                        "crime", "environment", "health", "world",
                    ],
                    "description": "Primary category of the article",
                },
                "subcategory": {
                    "type": "string",
                    "description": "More specific subcategory (e.g. 'Cyprus politics', 'EU economy', 'Middle East conflict')",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-5 keyword tags for the article",
                },
                "summary_ru": {
                    "type": "string",
                    "description": "Краткое описание статьи на русском языке, 1-2 предложения. Должно быть информативным и точным.",
                },
                "summary_en": {
                    "type": "string",
                    "description": "Short summary of the article in English, 1-2 sentences.",
                },
                "relevance_score": {
                    "type": "integer",
                    "description": "Relevance score 0-100 for Cyprus-based Russian-speaking audience. 100 = directly about Cyprus, 80+ = about Cyprus region, 50+ = about EU/Middle East, <50 = world news",
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral", "mixed"],
                    "description": "Overall sentiment of the article",
                },
                "is_breaking": {
                    "type": "boolean",
                    "description": "True if this is breaking/urgent news that should be published immediately",
                },
                "key_entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "10-15 key factual entities from this article for deduplication. Include: specific person names, organization names, place names, exact numbers/amounts, specific dates, law/bill names, event names. Must be normalized (e.g. 'European Union' not 'EU', 'Nikos Christodoulides' not 'president'). Lowercase.",
                },
                "suggested_format": {
                    "type": "string",
                    "enum": ["flash", "short_post", "longread"],
                    "description": (
                        "Recommended content format for publishing this article. Default to flash unless the article truly demands more.\n"
                        "flash (DEFAULT, use liberally — target ~40-50% of articles): A factual news item whose essence fits in 1-3 sentences: incidents, prices, appointments, awards, accidents, breakdowns, weather, announcements, statistics, single quotes, court rulings, sports results, brief Q&A. If you can summarise the core fact in two sentences, this is flash.\n"
                        "short_post (target ~40-50%): Choose this only when the story has 2-3 distinct connected facts that need a short paragraph of context — not just a single development with quoted reactions. Reactions, background, or 'why this matters' need to add genuine information beyond restating the lead.\n"
                        "longread (rare, target ~5-10%): Reserved for substantial analysis, investigations, multi-source explainers, or complex topics with 4+ data points, expert opinions, and a clear narrative arc. If in doubt, prefer short_post over longread."
                    ),
                },
            },
            "required": [
                "category", "subcategory", "tags",
                "summary_ru", "summary_en",
                "relevance_score", "sentiment", "is_breaking",
                "key_entities", "suggested_format",
            ],
        },
    },
}

SYSTEM_PROMPT = """You are a news classifier for ContenZavod, a content platform targeting Russian-speaking expats living in Cyprus.

Your job is to analyze news articles from Cyprus media — in any source language (commonly English or Greek) — and classify them.

Rules:
- The input article may be in English, Greek, or any other language. Read it directly, do not refuse if it is not in English.
- summary_ru must be in Russian, natural and informative (not machine-translated gibberish). Translate from the source language as needed.
- summary_en must be concise English. If the source is not English, translate; if it is English, summarize.
- Tags should be specific and useful for search (e.g. "IMF", "oil prices", "Strait of Hormuz", not generic like "news"). Tags themselves should be in English regardless of source language, so deduplication and search work cross-lingually.
- relevance_score: 90-100 for Cyprus-specific news, 70-89 for regional (Middle East, EU), 50-69 for world news affecting Cyprus, <50 for distant world news
- is_breaking: only for truly urgent events (wars, earthquakes, major political changes)
- key_entities: Extract 10-15 specific factual entities for deduplication. Focus on proper nouns, exact figures, dates, and named events. **Always normalize to English/Latin script** (e.g. "Nikos Christodoulides" not "Νίκος Χριστοδουλίδης", "European Union" not "Ευρωπαϊκή Ένωση"). All lowercase. This lets the dedup engine match the same event across language editions.

Always call the classify_article tool with your analysis."""


class AIServiceTemporarilyUnavailable(Exception):
    """Raised when the AI API is temporarily unavailable (maintenance, rate limit)."""
    pass


# ── Claude Haiku 4.5 fallback tool schema (Anthropic format) ─────
CLASSIFY_TOOL_CLAUDE = {
    "name": "classify_article",
    "description": "Classify a news article and extract structured metadata",
    "input_schema": CLASSIFY_TOOL["function"]["parameters"],
}

CLAUDE_URL = "https://api.kie.ai/claude/v1/messages"
GEMINI_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"


async def _classify_via_gemini(user_message: str, title: str) -> dict[str, Any] | None:
    """Classify using Gemini 3.1 Pro via KIE (OpenAI-compatible format).

    Returns classification dict, None on parse failure.
    Raises AIServiceTemporarilyUnavailable if API is down.
    """
    import random
    import asyncio

    payload = {
        "model": "gemini-3.1-pro",
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "text", "text": user_message}]},
        ],
        "tools": [CLASSIFY_TOOL],
        # Force the model to CALL classify_article instead of replying in prose.
        # Without this, gemini-3.1-pro frequently returns markdown analysis → no
        # tool result → empty key_entities → semantic dedup silently disabled.
        "tool_choice": {"type": "function", "function": {"name": "classify_article"}},
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(GEMINI_URL, json=payload, headers=headers)
                data = resp.json()

                if isinstance(data, dict):
                    if data.get("code") in (500, 503, 429, 455):
                        msg = data.get("msg", "API error")
                        if "frequency is too high" in msg and attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(2, 6))
                            continue
                        raise AIServiceTemporarilyUnavailable(msg)

                resp.raise_for_status()
                break
        except AIServiceTemporarilyUnavailable:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(2, 6))
                continue
            logger.error("ai.classify.gemini_failed", error=str(e), title=title[:80])
            return None

    return _parse_openai_response(data, title)


async def _classify_via_claude(user_message: str, title: str) -> dict[str, Any] | None:
    """Classify using Claude Haiku 4.5 via KIE (Anthropic Messages format).

    Returns classification dict, None on parse failure.
    Raises AIServiceTemporarilyUnavailable if API is down.
    """
    import random
    import asyncio

    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 4096,
        "stream": False,
        "messages": [
            {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_message}"},
        ],
        "tools": [CLASSIFY_TOOL_CLAUDE],
        # Force tool use (Anthropic format) — same rationale as the Gemini path.
        "tool_choice": {"type": "tool", "name": "classify_article"},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(CLAUDE_URL, json=payload, headers=headers)
                data = resp.json()

                if isinstance(data, dict):
                    # KIE-level errors
                    if data.get("code") in (500, 503, 429, 455):
                        msg = data.get("msg", "API error")
                        if "frequency is too high" in msg and attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(2, 6))
                            continue
                        raise AIServiceTemporarilyUnavailable(msg)
                    # Anthropic-level errors
                    if "error" in data:
                        err = data["error"]
                        msg = err.get("message", str(err))
                        raise AIServiceTemporarilyUnavailable(msg)

                resp.raise_for_status()
                break
        except AIServiceTemporarilyUnavailable:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(2, 6))
                continue
            logger.error("ai.classify.claude_failed", error=str(e), title=title[:80])
            return None

    return _parse_claude_response(data, title)


# Categories the downstream pipeline understands (mirrors CLASSIFY_TOOL enum).
VALID_CATEGORIES = {
    "politics", "economy", "society", "culture", "sport", "tech",
    "opinion", "lifestyle", "crime", "environment", "health", "world",
}


def _validate_classification(result: Any, title: str) -> dict[str, Any] | None:
    """Reject prose-shaped or incomplete classifications.

    A tool result is only usable if it carries the fields the pipeline relies
    on. The critical one is key_entities: an empty list yields an empty
    semantic_fingerprint, which silently turns OFF dedup (uniqueness defaults
    to 10.0 — see ai/deduplicator.py). We'd rather fail and retry/fallback than
    persist undedupable junk. Category is coerced to lowercase; an out-of-enum
    value only downgrades to a warning (it just falls back to default buckets).
    """
    if not isinstance(result, dict):
        return None

    entities = result.get("key_entities")
    if not isinstance(entities, list) or len([e for e in entities if e]) < 3:
        logger.warning("ai.classify.rejected_empty_entities", title=title[:60])
        return None

    if not str(result.get("summary_ru") or "").strip():
        logger.warning("ai.classify.rejected_no_summary", title=title[:60])
        return None

    category = str(result.get("category") or "").strip().lower()
    if category and category not in VALID_CATEGORIES:
        logger.warning(
            "ai.classify.category_out_of_enum",
            title=title[:60],
            category=result.get("category"),
        )
    result["category"] = category or "society"

    return result


def _parse_openai_response(data: dict, title: str) -> dict[str, Any] | None:
    """Parse OpenAI-compatible response (Gemini via KIE)."""
    choices = data.get("choices", [])
    if not choices:
        logger.warning("ai.classify.no_choices", title=title[:60], response=data)
        return None

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    for tc in tool_calls:
        func = tc.get("function", {})
        if func.get("name") == "classify_article":
            try:
                input_data = func.get("arguments", "{}")
                result = json.loads(input_data) if isinstance(input_data, str) else input_data
            except json.JSONDecodeError as e:
                logger.error("ai.classify.json_parse_error", error=str(e), title=title[:60])
                return None

            validated = _validate_classification(result, title)
            if validated is not None:
                logger.info(
                    "ai.classify.success",
                    provider="gemini",
                    title=title[:60],
                    category=validated.get("category"),
                    relevance=validated.get("relevance_score"),
                )
                return validated
            # Tool was called but output is unusable — fall through to None so
            # the caller fails over to Claude, then to a Celery retry.
            return None

    # Fallback to pure text parsing
    text_content = message.get("content", "")
    if text_content:
        try:
            return _validate_classification(json.loads(text_content), title)
        except json.JSONDecodeError:
            pass

    logger.warning("ai.classify.no_tool_result", title=title[:60], response=data)
    return None


def _parse_claude_response(data: dict, title: str) -> dict[str, Any] | None:
    """Parse Anthropic Messages response (Claude via KIE)."""
    content_blocks = data.get("content", [])

    for block in content_blocks:
        if block.get("type") == "tool_use" and block.get("name") == "classify_article":
            validated = _validate_classification(block.get("input", {}), title)
            if validated is not None:
                logger.info(
                    "ai.classify.success",
                    provider="claude",
                    title=title[:60],
                    category=validated.get("category"),
                    relevance=validated.get("relevance_score"),
                )
                return validated
            return None

    # Fallback: try to parse text blocks as JSON
    for block in content_blocks:
        if block.get("type") == "text":
            try:
                return _validate_classification(json.loads(block["text"]), title)
            except (json.JSONDecodeError, KeyError):
                pass

    logger.warning("ai.classify.claude_no_tool_result", title=title[:60])
    return None


async def classify_article(title: str, content: str, url: str = "") -> dict[str, Any] | None:
    """Classify a single article — tries Claude Haiku first, falls back to Gemini.

    Claude leads because gemini-3.1-pro via KIE currently ignores tool_choice and
    answers in prose almost every time (empty key_entities → rejected), so leading
    with Gemini just burned a call + latency before every Claude fallback. Revisit
    the order if/when KIE's Gemini honours tool calls again.

    Returns classification dict or None on failure.
    Raises AIServiceTemporarilyUnavailable only if ALL providers are down.
    """
    if not KIE_API_KEY:
        logger.error("ai.classify.no_api_key")
        return None

    # Truncate content to avoid token limits
    max_chars = 4000
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")

    user_message = f"""Classify this article:

Title: {title}
URL: {url}
Content: {truncated}"""

    # Try Claude first (reliable tool-caller)
    try:
        result = await _classify_via_claude(user_message, title)
        if result:
            return result
    except AIServiceTemporarilyUnavailable as e:
        logger.warning(
            "ai.classify.claude_down_trying_gemini",
            error=str(e)[:100],
            title=title[:60],
        )

    # Fallback to Gemini 3.1 Pro
    try:
        result = await _classify_via_gemini(user_message, title)
        if result:
            return result
    except AIServiceTemporarilyUnavailable:
        raise  # Both are down — propagate up for Celery retry

    logger.error("ai.classify.all_providers_failed", title=title[:60])
    raise AIServiceTemporarilyUnavailable("All AI providers failed for classification")


async def classify_batch(
    articles: list[dict[str, Any]],
    max_concurrent: int = 3,
) -> list[dict[str, Any] | None]:
    """Classify multiple articles with concurrency control.

    Args:
        articles: List of dicts with 'title', 'content', 'url'
        max_concurrent: Max parallel API calls (respect rate limits)

    Returns:
        List of classification results (None for failures)
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[dict[str, Any] | None] = []

    async def _classify_one(article: dict[str, Any]) -> dict[str, Any] | None:
        async with semaphore:
            return await classify_article(
                title=article["title"],
                content=article["content"],
                url=article.get("url", ""),
            )

    tasks = [_classify_one(a) for a in articles]
    results = await asyncio.gather(*tasks)
    return list(results)

