"""AI Editor service — evaluates materials for projects.

Uses Gemini 3.1 Pro via KIE.ai to generate hype and relevance scores
based on project-specific topic guidelines and target audience.
"""

import json
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

KIE_API_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"
KIE_API_KEY = settings.kie_api_key

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


class AIServiceTemporarilyUnavailable(Exception):
    """Raised when the AI API is temporarily unavailable (maintenance, rate limit)."""
    pass


async def evaluate_material_for_project(
    material_data: dict[str, Any], topic_guidelines: str, target_audience: str
) -> dict[str, Any] | None:
    """Evaluate a single material against a project's guidelines using Gemini 3.1 Pro."""
    if not KIE_API_KEY:
        logger.error("ai.evaluate.no_api_key")
        return None

    user_message = f"""Evaluate this material for the content project.
    
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

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(KIE_API_URL, headers=headers, json=payload)
    except httpx.RequestError as e:
        logger.error("ai.evaluate.request_error", error=str(e))
        return None

    if resp.status_code in [429, 500, 503, 504]:
        logger.warning("ai.evaluate.temporarily_unavailable", status=resp.status_code)
        raise AIServiceTemporarilyUnavailable(f"Status {resp.status_code}")

    if resp.status_code != 200:
        logger.error("ai.evaluate.http_error", status=resp.status_code, text=resp.text)
        return None

    try:
        data = resp.json()

        # Parse OpenAI-format tool call
        message = data.get("choices", [])[0].get("message", {})
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            logger.error("ai.evaluate.no_tool_calls", message=message)
            return None

        function_call = tool_calls[0].get("function", {})
        if function_call.get("name") != "evaluate_material":
            logger.error("ai.evaluate.wrong_tool", tool_name=function_call.get("name"))
            return None

        args_str = function_call.get("arguments", "{}")
        args = json.loads(args_str)

        return args
    except Exception as e:
        logger.error("ai.evaluate.parse_error", error=str(e), text=resp.text)
        return None
