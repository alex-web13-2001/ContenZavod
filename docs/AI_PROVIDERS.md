# ContenZavod — AI Providers

> Последнее обновление: 2026-04-18

## Обзор системы

AI-провайдеры подключаются через **Adapter Pattern + Provider Registry**.
Каждый провайдер реализует один или несколько интерфейсов: `TextAIProvider`, `ImageAIProvider`, `VideoAIProvider`.

## Активные провайдеры

### Gemini 2.5 Flash
- **Capabilities:** TEXT_CLASSIFY, TEXT_ADAPT, TEXT_ANALYZE, TEXT_SCORE
- **API:** Google Generative AI SDK (`google-generativeai`)
- **Модель:** `gemini-2.5-flash`
- **Используется для:**
  - Классификация материалов (рубрика, теги, саммари)
  - AI-скоринг (relevance + hype для проектов)
  - Адаптация контента (short_post, longread, video_script, digest)

## Модули AI

```
ai/
├── capabilities.py    # Enum: TEXT_CLASSIFY, TEXT_ADAPT, IMAGE_GENERATE...
├── registry.py        # Provider Registry с fallback
├── adapter.py         # Base adapter interface
├── classifier.py      # Классификация + скоринг для проектов
├── editor.py          # Адаптация контента под формат канала
└── providers/
    ├── base.py        # Abstract base classes
    └── __init__.py
```

## Промпты

Промпты хранятся **inline** в модулях AI:

### Классификация (`ai/classifier.py`)
- Извлекает: рубрику, теги, краткое описание
- Оценивает: relevance_score (0-10), hype_score (0-10)
- Решает: is_recommended (оба >= 6)

### Адаптация (`ai/editor.py`)
Генерирует контент в одном из форматов:

| Формат | Описание | Длина |
|--------|----------|-------|
| `short_post` | Telegram-пост с emoji, хуками | 800-1500 символов |
| `longread` | Развёрнутая статья с подзаголовками | 3000-5000 символов |
| `video_script` | Сценарий для короткого видео | 200-400 слов |
| `digest` | Дайджест-формат (краткие факты) | 500-1000 символов |

### Планируемые задачи

| Задача | Prompt file | Статус |
|--------|------------|--------|
| classify | inline в `classifier.py` | ✅ Работает |
| adapt (все форматы) | inline в `editor.py` | ✅ Работает |
| strategy | `ai/prompts/strategy/v1.txt` | 📋 Planned |

## Провайдеры (planned / suspended)

### Nano Banana 2 (Gemini 3.1 Flash Image)
- **Статус:** 📋 Planned
- **Capabilities:** IMAGE_GENERATE
- **Для:** Генерация тематических изображений для постов

### Kling 3.0
- **Статус:** 📋 Planned
- **Capabilities:** VIDEO_GENERATE
- **API:** KIE API (async: submit → poll → download)
- **Для:** Генерация видео (multi-shot, до 15 секунд)

## Как добавить нового провайдера

1. Создать `ai/providers/my_provider.py`
2. Реализовать нужный интерфейс (`TextAIProvider` / `ImageAIProvider` / `VideoAIProvider`)
3. Зарегистрировать в `ai/registry.py`
4. Добавить env-переменные в `.env.example`
5. Обновить этот файл
6. Создать ADR (если принципиально новый провайдер)
