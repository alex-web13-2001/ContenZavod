"""AI Editor service — evaluates materials for projects.

Uses Gemini 3.1 Pro via KIE.ai with Claude Haiku 4.5 fallback.
Generates hype and relevance scores based on project-specific
topic guidelines and target audience.
"""

import json
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

KIE_API_KEY = settings.kie_api_key
GEMINI_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"
CLAUDE_URL = "https://api.kie.ai/claude/v1/messages"

SYSTEM_PROMPT = """You are an expert Chief Editor for a news/content project.
Your job is to evaluate incoming raw materials and determine how perfectly they
fit the project's target audience and editorial guidelines.

You MUST be ruthlessly honest. If a material is garbage or irrelevant to the
audience, penalize it heavily. If it's a perfect match — give high scores.

You must assign two scores (0 to 10):
- relevance_score: How closely the topic aligns with the project's guidelines and audience.
- hype_score: How exciting, viral, dramatic, or engaging this specific story is, assuming it is relevant.

A material is recommended if relevance >= 7 AND hype >= 5.
You MUST provide a short 1-2 sentence explanation in the SAME LANGUAGE as the material summary.

Always call the evaluate_material tool with your analysis.
"""

# OpenAI-compatible tool schema (for Gemini via KIE)
EVALUATE_TOOL = {
    "type": "function",
    "function": {
        "name": "evaluate_material",
        "description": "Evaluate a material's fitness for a specific project",
        "parameters": {
            "type": "object",
            "properties": {
                "relevance_score": {
                    "type": "integer",
                    "description": "Relevance to the project's audience (0-10)",
                },
                "hype_score": {
                    "type": "integer",
                    "description": "Hype, virality, or engagement potential (0-10)",
                },
                "is_recommended": {
                    "type": "boolean",
                    "description": "True if relevance >= 7 and hype >= 5",
                },
                "explanation": {
                    "type": "string",
                    "description": "Short 1-2 sentence explanation of the reasoning",
                },
            },
            "required": ["relevance_score", "hype_score", "is_recommended", "explanation"],
        },
    },
}

# Anthropic tool schema (for Claude via KIE)
EVALUATE_TOOL_CLAUDE = {
    "name": "evaluate_material",
    "description": "Evaluate a material's fitness for a specific project",
    "input_schema": EVALUATE_TOOL["function"]["parameters"],
}


class AIServiceTemporarilyUnavailable(Exception):
    """Raised when the AI API is temporarily unavailable (maintenance, rate limit)."""
    pass


def _build_user_message(
    material_data: dict[str, Any], topic_guidelines: str, target_audience: str
) -> str:
    """Build the user prompt for material evaluation."""
    return f"""Evaluate this material for the content project.
    
--- PROJECT PROFILE ---
Topic Guidelines: {topic_guidelines}
Target Audience: {target_audience}

--- MATERIAL ---
Original Title: {material_data.get('original_title')}
Summary (RU): {material_data.get('summary_ru')}
Summary (EN): {material_data.get('summary_en')}
Category: {material_data.get('category')}
Tags: {', '.join(material_data.get('tags', []))}
Sentiment: {material_data.get('sentiment')}
Relevance (General): {material_data.get('relevance_score')}
"""


async def _evaluate_via_gemini(user_message: str) -> dict[str, Any] | None:
    """Evaluate using Gemini 3.1 Pro via KIE (OpenAI-compatible format).

    Returns evaluation dict, None on parse failure.
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
        "tools": [EVALUATE_TOOL],
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
            logger.error("ai.evaluate.gemini_failed", error=str(e))
            return None

    # Parse OpenAI-format tool call
    choices = data.get("choices", [])
    if not choices:
        logger.warning("ai.evaluate.gemini_no_choices")
        return None

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        logger.error("ai.evaluate.no_tool_calls", message=message)
        return None

    function_call = tool_calls[0].get("function", {})
    if function_call.get("name") != "evaluate_material":
        logger.error("ai.evaluate.wrong_tool", tool_name=function_call.get("name"))
        return None

    args_raw = function_call.get("arguments", "{}")
    if isinstance(args_raw, str):
        return json.loads(args_raw)
    return args_raw


async def _evaluate_via_claude(user_message: str) -> dict[str, Any] | None:
    """Evaluate using Claude Haiku 4.5 via KIE (Anthropic Messages format).

    Returns evaluation dict, None on parse failure.
    Raises AIServiceTemporarilyUnavailable if API is down.
    """
    import random
    import asyncio

    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 2048,
        "stream": False,
        "messages": [
            {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{user_message}"},
        ],
        "tools": [EVALUATE_TOOL_CLAUDE],
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
                    if data.get("code") in (500, 503, 429, 455):
                        msg = data.get("msg", "API error")
                        if "frequency is too high" in msg and attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(2, 6))
                            continue
                        raise AIServiceTemporarilyUnavailable(msg)
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
            logger.error("ai.evaluate.claude_failed", error=str(e))
            return None

    # Parse Anthropic tool_use response
    content_blocks = data.get("content", [])

    for block in content_blocks:
        if block.get("type") == "tool_use" and block.get("name") == "evaluate_material":
            result = block.get("input", {})
            if result:
                return result

    # Fallback: try text blocks as JSON
    for block in content_blocks:
        if block.get("type") == "text":
            try:
                return json.loads(block["text"])
            except (json.JSONDecodeError, KeyError):
                pass

    logger.warning("ai.evaluate.claude_no_tool_result")
    return None


async def evaluate_material_for_project(
    material_data: dict[str, Any], topic_guidelines: str, target_audience: str
) -> dict[str, Any] | None:
    """Evaluate a material against project guidelines — Gemini first, Claude fallback.

    Returns evaluation dict with relevance_score, hype_score, is_recommended, explanation.
    Raises AIServiceTemporarilyUnavailable only if ALL providers are down.
    """
    if not KIE_API_KEY:
        logger.error("ai.evaluate.no_api_key")
        return None

    user_message = _build_user_message(material_data, topic_guidelines, target_audience)

    # Try Gemini first
    try:
        result = await _evaluate_via_gemini(user_message)
        if result:
            logger.info("ai.evaluate.success", provider="gemini")
            return result
    except AIServiceTemporarilyUnavailable as e:
        logger.warning("ai.evaluate.gemini_down_trying_claude", error=str(e)[:100])

    # Fallback to Claude Haiku 4.5
    try:
        result = await _evaluate_via_claude(user_message)
        if result:
            logger.info("ai.evaluate.success", provider="claude")
            return result
    except AIServiceTemporarilyUnavailable:
        raise  # Both down — propagate for Celery retry

    logger.error("ai.evaluate.all_providers_failed")
    return None

