"""AI digest script generator.

Takes a list of news materials and produces a concise anchor-style
script suitable for a 15-30 second avatar video, in Russian.
Uses Claude Sonnet 4.5 via KIE.ai native Anthropic endpoint.
"""

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger()

KIE_API_URL = "https://api.kie.ai/claude/v1/messages"

DIGEST_SYSTEM_PROMPT = """Ты — профессиональный ведущий новостного видео-дайджеста.
Создай скрипт для AI-аватара. Скрипт пойдёт напрямую в ReVid API для генерации видео.

ФОРМАТ (СТРОГО!):

1. Каждый блок начинается с [описание визуала НА АНГЛИЙСКОМ] — подсказка для подбора фонового stock-видео.
   ВАЖНО: ReVid ищет stock-видео ТОЛЬКО по английским ключевым словам!
   Описание: 3-6 английских слов через запятую, конкретных и визуальных.
   ПЛОХО: [экономика], [tourism]
   ХОРОШО: [Limassol city streets people walking], [airport passengers luggage], [Cyprus parliament meeting]
2. Между блоками ОБЯЗАТЕЛЬНО вставляй: <break time="1.0s" />
3. Каждое предложение — НА ОТДЕЛЬНОЙ СТРОКЕ
4. Предложения КОРОТКИЕ: 3-7 слов максимум
5. 2-4 предложения на блок
6. Текст озвучки: ТОЛЬКО РУССКИЙ
7. НЕ используй эмодзи, хештеги, звёздочки, кавычки, markdown
8. Весь скрипт — 6-8 блоков (включая вступление и финал)
9. Первый блок — приветствие с [news studio background]
10. Последний блок — призыв подписаться с [calm outro background subscribe]

ЭТАЛОННЫЙ ПРИМЕР:

[news studio background]
Главные новости Кипра за неделю.
Коротко и по делу.

<break time="1.0s" />

[Limassol city streets people walking]
Экономика показывает рост.
Туристический поток увеличивается.
Бизнес фиксирует рост выручки.

<break time="1.0s" />

[construction site cranes buildings]
Рынок недвижимости под контролем.
Власти обсуждают новые ограничения.
Цель — сдержать рост цен.

<break time="1.0s" />

[airport passengers luggage terminal]
Изменения в миграционной политике.
Упрощают въезд для специалистов.
Кипр привлекает новые кадры.

<break time="1.0s" />

[highway road construction infrastructure]
Развивается инфраструктура.
Строятся дороги.
Обновляются транспортные узлы.

<break time="1.0s" />

[beach resort hotel swimming pool]
Туризм готовится к сезону.
Отели повышают уровень сервиса.
Усиливаются меры безопасности.

<break time="1.0s" />

[calm outro background subscribe]
Это был дайджест новостей Кипра.
За последнюю неделю.
Подписывайтесь, чтобы быть в курсе.
"""


def _get_material_summary(material) -> str:
    """Extract a short summary from material metadata."""
    meta = material.metadata_ or {}
    ai_data = meta.get("ai_classification", {})
    summary = ai_data.get("summary_ru") or ai_data.get("summary_en") or ""
    if summary:
        return summary[:300]
    return (material.content_text or "")[:300]


def generate_digest_script(
    materials: list,
    title: str = "",
) -> str:
    """Generate a digest script from a list of RawMaterial objects."""
    settings = get_settings()
    api_key = settings.kie_api_key
    if not api_key:
        log.error("digest.script.no_api_key")
        return ""

    news_items = []
    for i, m in enumerate(materials, 1):
        summary = _get_material_summary(m)
        news_items.append(f"{i}. {m.title}\n   {summary}")

    user_prompt = f"""{DIGEST_SYSTEM_PROMPT}

Создай скрипт видео-дайджеста из следующих новостей:

{chr(10).join(news_items)}

Количество новостей: {len(materials)}
{"Тема дайджеста: " + title if title else ""}

Верни ТОЛЬКО текст скрипта, без комментариев."""

    log.info("digest.script.generating", materials_count=len(materials), title=title)

    # Claude Sonnet 4.5 via KIE native Anthropic endpoint
    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 2048,
        "stream": False,
        "thinkingFlag": False,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    import time
    import random

    for attempt in range(3):
        try:
            resp = httpx.post(KIE_API_URL, json=payload, headers=headers, timeout=90.0)
            data = resp.json()

            # KIE proxy error
            if isinstance(data, dict) and data.get("code") in (429, 500, 503, 455):
                msg = data.get("msg", "API error")
                log.warning("digest.script.rate_limited", msg=msg, attempt=attempt)
                if attempt < 2:
                    time.sleep(random.uniform(2, 5))
                    continue
                return ""

            resp.raise_for_status()

            # Anthropic native response: {"content": [{"type": "text", "text": "..."}], ...}
            content = data.get("content", [])
            if isinstance(content, list):
                script = "\n".join(
                    b.get("text", "") for b in content if b.get("type") == "text"
                ).strip()
            elif isinstance(content, str):
                script = content.strip()
            else:
                script = ""

            word_count = len(script.split())
            log.info("digest.script.done", word_count=word_count, estimated_seconds=round(word_count / 2.5))

            # Post-process: translate [Russian scene tags] to English
            script = _translate_scene_tags(script, api_key)

            return script

        except Exception as e:
            log.error("digest.script.failed", error=str(e), attempt=attempt)
            if attempt < 2:
                time.sleep(random.uniform(1, 3))
                continue
            return ""

    return ""


def _translate_scene_tags(script: str, api_key: str) -> str:
    """Translate [scene description] tags from Russian to English for ReVid stock video matching."""
    import re

    tags = re.findall(r'\[([^\]]+)\]', script)
    if not tags:
        return script

    # Check if tags are already in English (simple heuristic: ASCII-only = English)
    russian_tags = [t for t in tags if any(ord(c) > 127 for c in t)]
    if not russian_tags:
        log.info("digest.script.tags_already_english", count=len(tags))
        return script

    # Build translation prompt
    tags_list = "\n".join(f"- {t}" for t in russian_tags)
    translate_prompt = f"""Translate these Russian video scene descriptions to English keywords for stock video search.
Return ONLY the translations, one per line, in the same order. No numbering, no dashes, no quotes.
Each translation should be 3-6 concrete visual English words.

{tags_list}"""

    try:
        payload = {
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "stream": False,
            "thinkingFlag": False,
            "messages": [{"role": "user", "content": translate_prompt}],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        resp = httpx.post(KIE_API_URL, json=payload, headers=headers, timeout=30.0)
        data = resp.json()

        # Anthropic native response
        content = data.get("content", [])
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        elif not isinstance(content, str):
            content = str(content) if content else ""

        translations = [line.strip().strip("-").strip() for line in content.strip().split("\n") if line.strip()]

        if len(translations) == len(russian_tags):
            for ru_tag, en_tag in zip(russian_tags, translations):
                script = script.replace(f"[{ru_tag}]", f"[{en_tag}]", 1)
            log.info("digest.script.tags_translated", count=len(translations))
        else:
            log.warning("digest.script.tag_translation_mismatch",
                        expected=len(russian_tags), got=len(translations))

    except Exception as e:
        log.warning("digest.script.tag_translation_failed", error=str(e))

    return script
