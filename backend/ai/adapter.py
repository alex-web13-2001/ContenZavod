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
    "flash": (
        "Формат: Молния/Flash (80–200 символов). Одно-два предложения с ключевым фактом. "
        "Начинай с эмодзи ⚡. Весь пост — это ТОЛЬКО голый факт. "
        "НЕ добавляй заголовок, комментарии, выводы, вопросы, call-to-action. "
        "НЕ используй жирный текст. Просто факт."
    ),
    "short_post": (
        "Формат: Стандартный пост для Telegram (250–500 символов). Один ключевой факт с кратким контекстом. "
        "2-3 абзаца по 1-2 предложения. Между абзацами ОБЯЗАТЕЛЬНО пустая строка (\\n\\n). "
        "Заключительный вопрос/вывод выделяется жирным и отделяется пустой строкой. "
        "Пиши КРАТКО. Не лей воду. Каждое предложение несёт новую информацию."
    ),
    "longread": (
        "Формат: Аналитика (1000–2500 символов). Развёрнутая статья НА ФАКТАХ: "
        "вводка с главным фактом, 2-3 аргумента с конкретными данными/цифрами, вывод. "
        "4-6 абзацев, между абзацами пустая строка. "
        "Пиши как аналитик, не как блогер. Только факты и обоснованные выводы."
    ),
    "video_script": (
        "Формат: Видеоскрипт (500–1500 символов). Сценарий для озвучки: "
        "хук в первые 5 секунд, основная часть, call-to-action."
    ),
    "digest": (
        "Формат: Дайджест-пункт (100–250 символов). Ультра-краткий саммари "
        "новости в одну фразу для новостного дайджеста."
    ),
}

SYSTEM_PROMPT = """You are a professional content writer and editor.
Your task is to adapt a raw news material into a ready-to-publish post for a specific channel.

Rules:
1. ALWAYS write in the specified language
2. Follow the tone of voice instructions precisely
3. Follow the content format instructions precisely
4. The headline should be catchy and attention-grabbing, with an emoji at the start
   - EXCEPTION: For "flash" format, leave headline EMPTY (empty string ""). The entire post is just the body.
5. Write the body as CLEAN PLAIN TEXT:
   - DO NOT use markdown links like [text](url) — never embed URLs in the body text
   - DO NOT use bold **markers** inside sentences for emphasis on numbers or words
   - Bold **text** is ONLY allowed for the final concluding question or thought (and only if formatting rules require it)
   - Use emoji sparingly — only at the start of the first paragraph for accent
   - CRITICAL: Break text into paragraphs of 2-3 sentences each, separated by BLANK LINES (\\n\\n)
   - NEVER write the entire post as one continuous block of text
   - EXCEPTION: For "flash" format, body is 1-2 sentences MAX, no paragraphs, no bold, no concluding question
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

# Scripts expected for each language (used for post-generation validation)
# Maps language code → set of Unicode script names that are acceptable
_CYRILLIC_LANGS = {"ru", "uk"}
_LATIN_LANGS = {"en", "de", "es", "fr"}
_GREEK_LANGS = {"el"}


def _validate_language(result: dict[str, Any], expected_lang: str) -> bool:
    """Validate that generated content is actually in the expected language.

    Uses a simple heuristic: count Cyrillic vs Latin vs Greek characters
    in headline+body and check if the dominant script matches expectations.
    Returns True if content language looks correct, False otherwise.
    """
    text = (result.get("headline", "") + " " + result.get("body", "")).strip()
    if not text:
        return True  # Empty — nothing to validate

    # Count characters by script
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if ('A' <= c <= 'Z') or ('a' <= c <= 'z'))
    greek = sum(1 for c in text if '\u0370' <= c <= '\u03FF')
    total_alpha = cyrillic + latin + greek

    if total_alpha < 20:
        return True  # Too few chars to judge

    cyrillic_ratio = cyrillic / total_alpha
    latin_ratio = latin / total_alpha
    greek_ratio = greek / total_alpha

    if expected_lang in _CYRILLIC_LANGS:
        # Expect mostly Cyrillic
        return cyrillic_ratio > 0.5
    elif expected_lang in _LATIN_LANGS:
        # Expect mostly Latin — reject if heavy Cyrillic
        return latin_ratio > 0.4 and cyrillic_ratio < 0.2
    elif expected_lang in _GREEK_LANGS:
        # Expect Greek or Latin (Greek posts often have Latin proper nouns)
        return greek_ratio > 0.3 and cyrillic_ratio < 0.2

    return True  # Unknown language — pass through


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
            if _validate_language(result, language):
                logger.info("ai.adapt.success", provider="gemini")
                return result
            else:
                logger.warning(
                    "ai.adapt.wrong_language",
                    provider="gemini",
                    expected=language,
                    headline=result.get("headline", "")[:60],
                )
                # Fall through to Claude — maybe it will respect language
    except AIServiceTemporarilyUnavailable as e:
        logger.warning("ai.adapt.gemini_down_trying_claude", error=str(e)[:100])

    # Fallback to Claude Haiku 4.5
    try:
        result = await _adapt_via_claude(user_message)
        if result:
            if _validate_language(result, language):
                logger.info("ai.adapt.success", provider="claude")
                return result
            else:
                logger.error(
                    "ai.adapt.wrong_language_all_providers",
                    expected=language,
                    headline=result.get("headline", "")[:60],
                )
                return None  # Both providers generated wrong language
    except AIServiceTemporarilyUnavailable:
        raise  # Both down — propagate for Celery retry

    logger.error("ai.adapt.all_providers_failed")
    raise AIServiceTemporarilyUnavailable("All AI providers failed for adaptation")

