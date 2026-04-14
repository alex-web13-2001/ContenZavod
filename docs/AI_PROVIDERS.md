# ContenZavod — AI Providers

> Последнее обновление: 2026-04-15

## Обзор системы

AI-провайдеры подключаются через **Adapter Pattern + Provider Registry**.
Каждый провайдер реализует один или несколько интерфейсов: `TextAIProvider`, `ImageAIProvider`, `VideoAIProvider`.

## Подключённые провайдеры

### Gemini 2.5 Flash
- **Файл:** `ai/providers/gemini_flash.py`
- **Capabilities:** TEXT_CLASSIFY, TEXT_ADAPT, TEXT_ANALYZE
- **API:** Google Generative AI SDK
- **Модель:** `gemini-2.5-flash`
- **Используется для:** Классификация материалов, адаптация контента под каналы

### Nano Banana 2 (Gemini 3.1 Flash Image)
- **Файл:** `ai/providers/nano_banana.py`
- **Capabilities:** IMAGE_GENERATE
- **API:** Google Generative AI SDK
- **Модель:** `gemini-3.1-flash` (image generation mode)
- **Используется для:** Генерация тематических изображений для постов

### Kling 3.0
- **Файл:** `ai/providers/kling_v3.py`
- **Capabilities:** VIDEO_GENERATE
- **API:** KIE API (async: submit → poll → download)
- **Модель:** `kling-v3`
- **Используется для:** Генерация видео (multi-shot, до 15 секунд)

## Промпты

Промпты хранятся в двух местах:
1. **Файлы:** `ai/prompts/{task_type}/v{N}.txt` — шаблоны по умолчанию
2. **БД:** таблица `prompt_configs` — тенант-специфичные настройки, версионирование

### Задачи

| Задача | Prompt file | Описание |
|--------|------------|----------|
| classify | `ai/prompts/classify/v1.txt` | Классификация: релевантность, тип, каналы |
| adapt_telegram | `ai/prompts/adapt_telegram/v1.txt` | Адаптация под Telegram-пост |
| adapt_website | `ai/prompts/adapt_website/v1.txt` | Адаптация под статью на сайте |
| adapt_video | `ai/prompts/adapt_video/v1.txt` | Генерация сценария для видео |
| strategy | `ai/prompts/strategy/v1.txt` | AI-рекомендации по стратегии |

## Как добавить нового провайдера

1. Создать `ai/providers/my_provider.py`
2. Реализовать нужный интерфейс (`TextAIProvider` / `ImageAIProvider` / `VideoAIProvider`)
3. Зарегистрировать в `ai/registry.py`
4. Добавить env-переменные в `.env.example`
5. Обновить этот файл
6. Создать ADR (если принципиально новый провайдер)
