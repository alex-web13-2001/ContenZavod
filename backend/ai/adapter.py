"""AI Adapter service — generates adapted content for channels.

Takes a raw material + channel config (tone_of_voice, content_formats, language)
and produces a headline + body ready for publishing.
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
4. The headline should be catchy and attention-grabbing
5. Use Telegram-compatible markdown (bold **text**, italic _text_, [links](url))
6. DO NOT invent facts — use only information from the source material
7. DO NOT include meta-text like "Вот пост:" or "Заголовок:", just output the content directly

Always call the adapt_content tool with your result.
"""

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
                    "description": "Full body text ready for publishing, in markdown",
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


class AIServiceTemporarilyUnavailable(Exception):
    """Raised when the AI API is temporarily unavailable."""
    pass


LANGUAGE_NAMES = {
    "ru": "Русский", "en": "English", "de": "Deutsch", "uk": "Українська",
    "es": "Español", "fr": "Français", "zh": "中文", "el": "Ελληνικά",
}


async def adapt_material_for_channel(
    material_data: dict[str, Any],
    channel_name: str,
    channel_type: str,
    content_format: str,
    tone_of_voice: str,
    language: str,
) -> dict[str, Any] | None:
    """Generate adapted content for a specific channel × format × language."""
    if not KIE_API_KEY:
        logger.error("ai.adapt.no_api_key")
        return None

    format_instruction = FORMAT_INSTRUCTIONS.get(content_format, FORMAT_INSTRUCTIONS["short_post"])
    lang_name = LANGUAGE_NAMES.get(language, language)

    user_message = f"""Adapt this material for the channel.

--- CHANNEL ---
Name: {channel_name}
Platform: {channel_type}
Language: {lang_name} ({language})
Tone of Voice: {tone_of_voice or "Информативный, нейтральный"}

--- FORMAT ---
{format_instruction}

--- SOURCE MATERIAL ---
Title: {material_data.get('original_title', '')}
Summary (RU): {material_data.get('summary_ru', '')}
Summary (EN): {material_data.get('summary_en', '')}
Full text excerpt: {(material_data.get('content_text', '') or '')[:2000]}
Source URL: {material_data.get('original_url', '')}
"""

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

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(KIE_API_URL, headers=headers, json=payload)
    except httpx.RequestError as e:
        logger.error("ai.adapt.request_error", error=str(e))
        return None

    if resp.status_code in [429, 500, 503, 504]:
        logger.warning("ai.adapt.temporarily_unavailable", status=resp.status_code)
        raise AIServiceTemporarilyUnavailable(f"Status {resp.status_code}")

    if resp.status_code != 200:
        logger.error("ai.adapt.http_error", status=resp.status_code, text=resp.text)
        return None

    try:
        data = resp.json()
        message = data.get("choices", [])[0].get("message", {})
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

        args_str = function_call.get("arguments", "{}")
        args = json.loads(args_str)
        return args
    except Exception as e:
        logger.error("ai.adapt.parse_error", error=str(e), text=resp.text)
        return None
