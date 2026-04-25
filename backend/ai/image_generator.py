"""AI Image Generator — creates cover images for news articles.

Flow:
    1. Gemini 3.1 Pro generates an optimal prompt for GPT Image-2
    2. KIE.ai GPT Image-2 generates the image (16:9, 1K, photorealistic)
    3. Polls for result and returns the image URL

Uses the same KIE API key as other AI services.
"""

import asyncio
import json
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

KIE_API_KEY = settings.kie_api_key
GEMINI_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"
IMAGE_CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
IMAGE_STATUS_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"

# ── Prompt generation via Gemini ───────────────────────────

PROMPT_SYSTEM = """You are an expert visual prompt engineer for AI image generation.
Your task: create a photorealistic image prompt for a news article cover.

Rules:
1. The image MUST be photorealistic — real-world photography style
2. The image MUST visually match the news topic
3. The image should be dramatic, eye-catching, cinematic
4. Include lighting, composition, and atmosphere details
5. If a headline overlay is requested, integrate the EXACT text naturally into the image
   (as bold modern typography overlaid on the scene, like a magazine cover or news graphic)
6. Text on the image should be in the specified language
7. DO NOT include any watermarks, logos, or stock photo elements
8. Think like a senior art director at a major news outlet

Always call the create_prompt tool with your result."""

PROMPT_TOOL = {
    "type": "function",
    "function": {
        "name": "create_prompt",
        "description": "Return the image generation prompt",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed prompt for GPT Image-2 (photorealistic, 16:9 composition)",
                },
                "overlay_text": {
                    "type": "string",
                    "description": "Short catchy headline text to be rendered ON the image (in the target language). Max 8 words. Should make the reader want to click.",
                },
            },
            "required": ["prompt", "overlay_text"],
        },
    },
}

LANGUAGE_NAMES = {
    "ru": "Русский", "en": "English", "de": "Deutsch", "uk": "Українська",
    "es": "Español", "fr": "Français", "zh": "中文", "el": "Ελληνικά",
}


class ImageGenerationError(Exception):
    """Raised when image generation fails."""
    pass


async def generate_image_prompt(
    headline: str,
    summary: str,
    language: str = "ru",
    content_text: str = "",
) -> dict[str, str]:
    """Use Gemini to create an optimal image prompt based on news context.
    
    Returns: {"prompt": "...", "overlay_text": "..."}
    """
    if not KIE_API_KEY:
        raise ImageGenerationError("No KIE API key configured")

    lang_name = LANGUAGE_NAMES.get(language, language)
    
    user_message = f"""Create a photorealistic cover image prompt for this news article.

--- NEWS CONTEXT ---
Headline: {headline}
Summary: {summary}
Content excerpt: {(content_text or '')[:1500]}

--- REQUIREMENTS ---
Language for text overlay: {lang_name} ({language})
Aspect ratio: 16:9 (wide cinematic)
Style: Photorealistic, dramatic, cinematic lighting
The overlay text should be a SHORT catchy phrase in {lang_name} that makes readers want to read the article.
It should NOT be the full headline — make it punchier and shorter (3-8 words max).
"""

    payload = {
        "model": "gemini-3.1-pro",
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": PROMPT_SYSTEM}]},
            {"role": "user", "content": [{"type": "text", "text": user_message}]},
        ],
        "tools": [PROMPT_TOOL],
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(GEMINI_URL, headers=headers, json=payload)
    except httpx.RequestError as e:
        raise ImageGenerationError(f"Gemini request failed: {e}")

    if resp.status_code != 200:
        raise ImageGenerationError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            args = json.loads(tool_calls[0]["function"]["arguments"])
            return {
                "prompt": args.get("prompt", ""),
                "overlay_text": args.get("overlay_text", ""),
            }

        # Fallback: try content
        content = message.get("content", "")
        if content:
            return {"prompt": content, "overlay_text": ""}

        raise ImageGenerationError("Gemini returned no tool calls or content")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise ImageGenerationError(f"Failed to parse Gemini response: {e}")


# ── GPT Image-2 via KIE.ai ───────────────────────────────

async def create_image_task(prompt: str) -> str:
    """Submit image generation task to KIE.ai GPT Image-2.
    
    Returns: taskId
    """
    if not KIE_API_KEY:
        raise ImageGenerationError("No KIE API key configured")

    payload = {
        "model": "gpt-image-2-text-to-image",
        "input": {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "resolution": "1K",
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(IMAGE_CREATE_URL, headers=headers, json=payload)
    except httpx.RequestError as e:
        raise ImageGenerationError(f"KIE create task request failed: {e}")

    if resp.status_code != 200:
        raise ImageGenerationError(f"KIE create task HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    if data.get("code") != 200:
        raise ImageGenerationError(f"KIE create task error: {data.get('msg', 'unknown')}")

    task_id = data.get("data", {}).get("taskId")
    if not task_id:
        raise ImageGenerationError("KIE returned no taskId")

    logger.info("image.task_created", task_id=task_id)
    return task_id


async def poll_image_task(task_id: str, max_wait: int = 150) -> str:
    """Poll KIE.ai for task completion. Returns the image URL.
    
    Polls with exponential backoff: 3s, 5s, 8s, 12s, 15s, 15s...
    Max wait: 150 seconds (2.5 minutes).
    """
    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}",
    }

    delays = [3, 5, 8, 12, 15]
    elapsed = 0
    attempt = 0

    while elapsed < max_wait:
        delay = delays[min(attempt, len(delays) - 1)]
        await asyncio.sleep(delay)
        elapsed += delay
        attempt += 1

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    IMAGE_STATUS_URL,
                    params={"taskId": task_id},
                    headers=headers,
                )
        except httpx.RequestError as e:
            logger.warning("image.poll_error", task_id=task_id, error=str(e))
            continue

        if resp.status_code != 200:
            logger.warning("image.poll_http_error", task_id=task_id, status=resp.status_code)
            continue

        data = resp.json()
        task_data = data.get("data", {})
        state = task_data.get("state", "")

        logger.debug("image.poll", task_id=task_id, state=state, attempt=attempt)

        if state == "success":
            # Parse resultJson for image URLs
            result_json_str = task_data.get("resultJson", "{}")
            try:
                result_json = json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
            except json.JSONDecodeError:
                result_json = {}

            urls = result_json.get("resultUrls", [])
            if urls:
                logger.info("image.generated", task_id=task_id, url=urls[0][:80])
                return urls[0]

            # Fallback: check other possible fields
            output = task_data.get("output", {})
            if isinstance(output, dict) and output.get("image_url"):
                return output["image_url"]

            raise ImageGenerationError(f"Task succeeded but no image URL found: {task_data}")

        elif state == "fail":
            fail_msg = task_data.get("failMsg", "unknown error")
            raise ImageGenerationError(f"Image generation failed: {fail_msg}")

        # Still generating — continue polling

    raise ImageGenerationError(f"Image generation timed out after {max_wait}s (task: {task_id})")


async def generate_cover_image(
    headline: str,
    summary: str,
    language: str = "ru",
    content_text: str = "",
) -> dict[str, Any]:
    """Full pipeline: generate prompt → create image → poll → return result.
    
    Returns: {
        "image_url": "https://...",  # temporary KIE URL (download ASAP!)
        "prompt": "...",
        "overlay_text": "...",
    }
    """
    # Step 1: Generate prompt via Gemini
    prompt_data = await generate_image_prompt(
        headline=headline,
        summary=summary,
        language=language,
        content_text=content_text,
    )

    full_prompt = prompt_data["prompt"]
    overlay = prompt_data.get("overlay_text", "")

    # If overlay text exists, ensure it's part of the prompt
    if overlay and overlay.lower() not in full_prompt.lower():
        full_prompt += f'\n\nOverlay bold modern typography text on the image: "{overlay}"'

    logger.info(
        "image.prompt_ready",
        prompt_length=len(full_prompt),
        overlay=overlay[:50] if overlay else "",
    )

    # Step 2: Create image task
    task_id = await create_image_task(full_prompt)

    # Step 3: Poll for result
    image_url = await poll_image_task(task_id)

    return {
        "image_url": image_url,
        "prompt": full_prompt,
        "overlay_text": overlay,
        "task_id": task_id,
    }
