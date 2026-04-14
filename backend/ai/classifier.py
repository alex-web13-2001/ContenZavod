"""AI Classification service — uses Claude Haiku 4.5 via KIE.ai API.

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

KIE_API_URL = "https://api.kie.ai/claude/v1/messages"
KIE_API_KEY = settings.kie_api_key
MODEL = "claude-haiku-4-5"

# Classification schema for structured output via tool_use
CLASSIFY_TOOL = {
    "name": "classify_article",
    "description": "Classify a news article and extract structured metadata",
    "input_schema": {
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
        },
        "required": [
            "category", "subcategory", "tags",
            "summary_ru", "summary_en",
            "relevance_score", "sentiment", "is_breaking",
        ],
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

Always call the classify_article tool with your analysis."""

class AIServiceTemporarilyUnavailable(Exception):
    """Raised when the AI API is temporarily unavailable (maintenance, rate limit)."""
    pass


async def classify_article(title: str, content: str, url: str = "") -> dict[str, Any] | None:
    """Classify a single article using Claude Haiku 4.5 via KIE.ai.

    Returns classification dict or None on failure.
    Raises AIServiceTemporarilyUnavailable for retryable errors.
    """
    if not KIE_API_KEY:
        logger.error("ai.classify.no_api_key")
        return None

    # Truncate content to avoid token limits (Haiku has 200k context but we want speed)
    max_chars = 4000
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")

    user_message = f"""Classify this article:

Title: {title}
URL: {url}
Content: {truncated}"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": user_message},
        ],
        "tools": [CLASSIFY_TOOL],
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
        "anthropic-version": "2023-06-01",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(KIE_API_URL, json=payload, headers=headers)
            data = resp.json()

            # Handle API-level errors (maintenance, rate limits)
            if isinstance(data, dict) and data.get("code") in (500, 503, 429):
                msg = data.get("msg", "API error")
                logger.warning("ai.classify.api_unavailable", msg=msg, title=title[:60])
                raise AIServiceTemporarilyUnavailable(msg)

            resp.raise_for_status()
    except AIServiceTemporarilyUnavailable:
        raise  # Let it propagate for Celery retry
    except Exception as e:
        logger.error("ai.classify.request_failed", error=str(e), title=title[:80])
        return None

    # Extract tool_use result from response
    content_blocks = data.get("content", [])
    for block in content_blocks:
        if block.get("type") == "tool_use" and block.get("name") == "classify_article":
            result = block.get("input", {})
            logger.info(
                "ai.classify.success",
                title=title[:60],
                category=result.get("category"),
                relevance=result.get("relevance_score"),
            )
            return result

    # Fallback: try to parse text response
    for block in content_blocks:
        if block.get("type") == "text":
            text = block.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

    logger.warning("ai.classify.no_tool_result", title=title[:60], response=data)
    return None


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
