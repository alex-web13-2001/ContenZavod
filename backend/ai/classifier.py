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
                        "Recommended content format for publishing this article. "
                        "flash: Single fact, price change, appointment, award — anything expressed in 1-2 sentences. No analysis needed. "
                        "short_post: Regular news needing 2-3 paragraphs of context to explain properly. Most articles fall here. "
                        "longread: Complex topic requiring analysis, multiple data points, expert opinions — rare, only for truly substantial stories."
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

Your job is to analyze English-language news articles from Cyprus media and classify them.

Rules:
- summary_ru must be in Russian, natural and informative (not machine-translated gibberish)
- summary_en must be concise English
- Tags should be specific and useful for search (e.g. "IMF", "oil prices", "Strait of Hormuz", not generic like "news")
- relevance_score: 90-100 for Cyprus-specific news, 70-89 for regional (Middle East, EU), 50-69 for world news affecting Cyprus, <50 for distant world news
- is_breaking: only for truly urgent events (wars, earthquakes, major political changes)
- key_entities: Extract 10-15 specific factual entities for deduplication. Focus on proper nouns, exact figures, dates, and named events. Normalize names (full names, not abbreviations). All lowercase.

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
                if isinstance(input_data, str):
                    result = json.loads(input_data)
                else:
                    result = input_data

                logger.info(
                    "ai.classify.success",
                    provider="gemini",
                    title=title[:60],
                    category=result.get("category"),
                    relevance=result.get("relevance_score"),
                )
                return result
            except json.JSONDecodeError as e:
                logger.error("ai.classify.json_parse_error", error=str(e), title=title[:60])
                return None

    # Fallback to pure text parsing
    text_content = message.get("content", "")
    if text_content:
        try:
            return json.loads(text_content)
        except json.JSONDecodeError:
            pass

    logger.warning("ai.classify.no_tool_result", title=title[:60], response=data)
    return None


def _parse_claude_response(data: dict, title: str) -> dict[str, Any] | None:
    """Parse Anthropic Messages response (Claude via KIE)."""
    content_blocks = data.get("content", [])

    for block in content_blocks:
        if block.get("type") == "tool_use" and block.get("name") == "classify_article":
            result = block.get("input", {})
            if result:
                logger.info(
                    "ai.classify.success",
                    provider="claude",
                    title=title[:60],
                    category=result.get("category"),
                    relevance=result.get("relevance_score"),
                )
                return result

    # Fallback: try to parse text blocks as JSON
    for block in content_blocks:
        if block.get("type") == "text":
            try:
                return json.loads(block["text"])
            except (json.JSONDecodeError, KeyError):
                pass

    logger.warning("ai.classify.claude_no_tool_result", title=title[:60])
    return None


async def classify_article(title: str, content: str, url: str = "") -> dict[str, Any] | None:
    """Classify a single article — tries Gemini first, falls back to Claude Haiku.

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

    # Try Gemini first
    try:
        result = await _classify_via_gemini(user_message, title)
        if result:
            return result
    except AIServiceTemporarilyUnavailable as e:
        logger.warning(
            "ai.classify.gemini_down_trying_claude",
            error=str(e)[:100],
            title=title[:60],
        )

    # Fallback to Claude Haiku 4.5
    try:
        result = await _classify_via_claude(user_message, title)
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

