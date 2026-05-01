"""AI Adapter service — generates adapted content for channels.

Takes a raw material + channel config (tone_of_voice, content_formats, language)
and produces a headline + body ready for publishing.
Uses Gemini 3.1 Pro via KIE.ai with Claude Haiku 4.5 fallback.
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

FORMAT_INSTRUCTIONS = {
    "short_post": "Формат: Короткий пост (300–600 символов). Один ключевой факт, без воды. Можно эмодзи для акцентов. Один абзац.",
    "longread": "Формат: Лонгрид (1000–3000 символов). Развёрнутая статья с вводкой, основной частью и выводом. 3-5 абзацев.",
    "video_script": "Формат: Видеоскрипт (500–1500 символов). Сценарий для озвучки: хук в первые 5 секунд, основная часть, call-to-action.",
    "digest": "Формат: Дайджест-пункт (100–250 символов). Ультра-краткий саммари новости в одну фразу для новостного дайджеста.",
}

SYSTEM_PROMPT = """You are a professional content writer and editor.
Your task is to adapt a raw news material into a ready-to-publish post for a specific channel.

Rules:
1. ALWAYS write in the specified language
2. Follow the tone of voice instructions precisely
3. Follow the content format instructions precisely
4. The headline should be catchy and attention-grabbing, with an emoji at the start
5. Write the body as CLEAN PLAIN TEXT:
   - DO NOT use markdown links like [text](url) — never embed URLs in the body text
   - DO NOT use bold **markers** inside sentences for emphasis on numbers or words
   - Bold **text** is ONLY allowed for the final concluding question or thought (and only if formatting rules require it)
   - Use emoji sparingly for paragraph accents only
   - Paragraphs separated by blank lines
6. DO NOT invent facts — use only information from the source material
7. DO NOT include meta-text like "Вот пост:", "Заголовок:", structural markers like "(Хук)", "(Основная часть)" etc.
8. FORMATTING RULES ARE MANDATORY — if formatting rules are provided, you MUST follow them exactly.
   This includes paragraph structure, line breaks between paragraphs, and any other formatting directives.
   Violations of formatting rules are NOT acceptable.
9. The source URL will be attached automatically — DO NOT include it in the body text.

Always call the adapt_content tool with your result.
"""

# OpenAI-compatible tool schema (for Gemini via KIE)
ADAPT_TOOL = {
    "type": "function",
    "function": {
        "name": "adapt_content",
        "description": "Return the adapted content for publishing",
        "parameters": {
            "type": "object",
            "properties": {
                "headline": {
                    "type": "string",
                    "description": "Catchy headline/title for the post",
                },
                "body": {
                    "type": "string",
                    "description": "Full body text ready for publishing, clean plain text without markdown links or excessive formatting",
                },
                "priority": {
                    "type": "string",
                    "enum": ["urgent", "normal", "filler"],
                    "description": "urgent=breaking news, normal=regular, filler=low priority",
                },
            },
            "required": ["headline", "body", "priority"],
        },
    },
}

# Anthropic tool schema (for Claude via KIE)
ADAPT_TOOL_CLAUDE = {
    "name": "adapt_content",
    "description": "Return the adapted content for publishing",
    "input_schema": ADAPT_TOOL["function"]["parameters"],
}


class AIServiceTemporarilyUnavailable(Exception):
    """Raised when the AI API is temporarily unavailable."""
    pass


LANGUAGE_NAMES = {
    "ru": "Русский", "en": "English", "de": "Deutsch", "uk": "Українська",
    "es": "Español", "fr": "Français", "zh": "中文", "el": "Ελληνικά",
}


def _build_adapt_message(
    material_data: dict[str, Any],
    channel_name: str,
    channel_type: str,
    content_format: str,
    tone_of_voice: str,
    language: str,
    formatting_rules: str = "",
    editorial_rules: str = "",
) -> str:
    """Build the user prompt for content adaptation."""
    format_instruction = FORMAT_INSTRUCTIONS.get(content_format, FORMAT_INSTRUCTIONS["short_post"])
    lang_name = LANGUAGE_NAMES.get(language, language)

    return f"""Adapt this material for the channel.

--- CHANNEL ---
Name: {channel_name}
Platform: {channel_type}
Language: {lang_name} ({language})
Tone of Voice: {tone_of_voice or "Информативный, нейтральный"}

--- FORMAT ---
{format_instruction}

--- FORMATTING RULES (ОБЯЗАТЕЛЬНО К ИСПОЛНЕНИЮ!) ---
{formatting_rules or "Используй абзацы для разделения смысловых блоков. Между абзацами — пустая строка."}

{f"--- EDITORIAL RULES ---{chr(10)}{editorial_rules}" if editorial_rules else ""}

--- SOURCE MATERIAL ---
Title: {material_data.get('original_title', '')}
Summary (RU): {material_data.get('summary_ru', '')}
Summary (EN): {material_data.get('summary_en', '')}
Full text excerpt: {(material_data.get('content_text', '') or '')[:2000]}
Source URL: {material_data.get('original_url', '')}
"""


async def _adapt_via_gemini(user_message: str) -> dict[str, Any] | None:
    """Adapt using Gemini 3.1 Pro via KIE (OpenAI-compatible format).

    Returns adaptation dict, None on parse failure.
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
        "tools": [ADAPT_TOOL],
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
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
            logger.error("ai.adapt.gemini_failed", error=str(e))
            return None

    # Parse OpenAI-format tool call
    choices = data.get("choices", [])
    if not choices:
        logger.warning("ai.adapt.gemini_no_choices")
        return None

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        # Fallback: try to parse from content directly
        content = message.get("content", "")
        if content:
            return {"headline": "", "body": content, "priority": "normal"}
        logger.error("ai.adapt.no_tool_calls", message=message)
        return None

    function_call = tool_calls[0].get("function", {})
    if function_call.get("name") != "adapt_content":
        logger.error("ai.adapt.wrong_tool", tool_name=function_call.get("name"))
        return None

    args_raw = function_call.get("arguments", "{}")
    if isinstance(args_raw, str):
        return json.loads(args_raw)
    return args_raw


async def _adapt_via_claude(user_message: str) -> dict[str, Any] | None:
    """Adapt using Claude Haiku 4.5 via KIE (Anthropic Messages format).

    Returns adaptation dict, None on parse failure.
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
        "tools": [ADAPT_TOOL_CLAUDE],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
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
            logger.error("ai.adapt.claude_failed", error=str(e))
            return None

    # Parse Anthropic tool_use response
    content_blocks = data.get("content", [])

    for block in content_blocks:
        if block.get("type") == "tool_use" and block.get("name") == "adapt_content":
            result = block.get("input", {})
            if result:
                return result

    # Fallback: try text blocks as raw content
    for block in content_blocks:
        if block.get("type") == "text" and block.get("text", "").strip():
            text = block["text"].strip()
            # Try JSON first
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            # Use as raw body
            return {"headline": "", "body": text, "priority": "normal"}

    logger.warning("ai.adapt.claude_no_tool_result")
    return None


async def adapt_material_for_channel(
    material_data: dict[str, Any],
    channel_name: str,
    channel_type: str,
    content_format: str,
    tone_of_voice: str,
    language: str,
    formatting_rules: str = "",
    editorial_rules: str = "",
) -> dict[str, Any] | None:
    """Generate adapted content — Gemini first, Claude fallback.

    Returns dict with headline, body, priority.
    Raises AIServiceTemporarilyUnavailable only if ALL providers are down.
    """
    if not KIE_API_KEY:
        logger.error("ai.adapt.no_api_key")
        return None

    user_message = _build_adapt_message(
        material_data, channel_name, channel_type,
        content_format, tone_of_voice, language,
        formatting_rules, editorial_rules,
    )

    # Try Gemini first
    try:
        result = await _adapt_via_gemini(user_message)
        if result:
            logger.info("ai.adapt.success", provider="gemini")
            return result
    except AIServiceTemporarilyUnavailable as e:
        logger.warning("ai.adapt.gemini_down_trying_claude", error=str(e)[:100])

    # Fallback to Claude Haiku 4.5
    try:
        result = await _adapt_via_claude(user_message)
        if result:
            logger.info("ai.adapt.success", provider="claude")
            return result
    except AIServiceTemporarilyUnavailable:
        raise  # Both down — propagate for Celery retry

    logger.error("ai.adapt.all_providers_failed")
    raise AIServiceTemporarilyUnavailable("All AI providers failed for adaptation")

