# ContenZavod — AI Providers

> Последнее обновление: 2026-05-06

## Обзор системы

AI-провайдеры подключаются через **Adapter Pattern + Provider Registry**.
Каждый провайдер реализует один или несколько интерфейсов: `TextAIProvider`, `ImageAIProvider`, `VideoAIProvider`.

## Активные провайдеры

### Gemini 2.5 Flash (основной)
- **Capabilities:** TEXT_CLASSIFY, TEXT_ADAPT, TEXT_ANALYZE, TEXT_SCORE, TEXT_DEDUPLICATE, SCRIPT_GENERATE
- **API:** Google Generative AI SDK (`google-generativeai`)
- **Модель:** `gemini-2.5-flash`
- **Env:** `GEMINI_API_KEY`
- **Используется для:**
  - Классификация материалов (рубрика, теги, саммари)
  - AI-скоринг (relevance + hype для проектов)
  - Адаптация контента (short_post, longread, video_script, digest)
  - Дедупликация контента
  - Генерация видеосценариев для дайджестов

### Claude Haiku 4.5 через KIE (fallback)
- **Capabilities:** TEXT_CLASSIFY, TEXT_ADAPT, IMAGE_GENERATE
- **API:** KIE.ai REST API
- **Модель:** `claude-haiku-4.5`
- **Env:** `KIE_API_KEY`
- **Используется для:**
  - Fallback для классификации (когда Gemini недоступен)
  - Fallback для адаптации контента
  - Генерация обложек (текст → prompt → Kling)
- **Особенности:** `thinkingFlag: false`, температура 0.7-0.75

### ReVid API v3 (видео)
- **Capabilities:** VIDEO_RENDER
- **API:** ReVid REST API (`https://api.revid.ai/v3`)
- **Env:** `REVID_API_KEY`
- **Используется для:**
  - Рендер AI-видео с аватаром (workflow: `avatar-to-video`)
  - Проверка статуса рендера
  - Получение баланса кредитов
- **Файл:** `integrations/revid.py`
- **Особенности:**
  - Media type normalization: `"provided"` → `"custom"`, `"stock-image"` → `"moving-image"`
  - Detailed error capture (HTTP 400 body logging)
  - Auto-polling on GET endpoint

## Модули AI

```
ai/
├── capabilities.py      # Enum: TEXT_CLASSIFY, TEXT_ADAPT, IMAGE_GENERATE...
├── registry.py          # Provider Registry с fallback
├── adapter.py           # Адаптация контента (Gemini + Claude Haiku fallback)
├── classifier.py        # Классификация + скоринг (Gemini Flash, Claude fallback)
├── deduplicator.py      # Дедупликация контента (Gemini Flash)
├── digest_script.py     # Генерация видеосценариев (Gemini Flash)
├── editor.py            # Редактирование/тонкая правка текстов
├── image_generator.py   # Генерация обложек (Claude → Kling)
└── providers/
    ├── base.py          # Abstract base classes
    └── __init__.py

integrations/
└── revid.py             # ReVid API v3 client
```

## Промпты

Промпты хранятся **inline** в модулях AI:

### Классификация (`ai/classifier.py`)
- Извлекает: рубрику, теги, краткое описание
- Оценивает: relevance_score (0-10), hype_score (0-10)
- Решает: is_recommended (оба >= 6)
- **Fallback:** При ошибке Gemini → Claude Haiku 4.5

### Адаптация (`ai/adapter.py`)
Генерирует контент в одном из форматов:

| Формат | Описание | Длина |
|--------|----------|-------|
| `short_post` | Telegram-пост с emoji, хуками | 800-1500 символов |
| `longread` | Развёрнутая статья с подзаголовками | 3000-5000 символов |
| `video_script` | Сценарий для короткого видео | 200-400 слов |
| `digest` | Дайджест-формат (краткие факты) | 500-1000 символов |

- **Пост-обработка:** Валидация языка output (не допускает cross-language leaks)
- **Fallback:** При ошибке Gemini → Claude Haiku 4.5

### Дедупликация (`ai/deduplicator.py`)
- Анализирует семантическое сходство между материалами
- Предотвращает дублирование контента в автопилоте

### Сценарии видео (`ai/digest_script.py`)
- Генерирует сценарий из массива материалов
- Формат: `[описание сцены]\nТекст озвучки.\n<break time="1.0s" />`
- Включает сцены, паузы, transition hints для ReVid

### Генерация обложек (`ai/image_generator.py`)
- **Prompt generation:** Claude Haiku 4.5 → текстовый prompt
- **Image generation:** Kling API (async: submit → poll → download)
- Retry с exponential backoff (до 5 попыток)

## Провайдеры (planned / suspended)

### Kling 3.0 Video (standalone)
- **Статус:** 🔧 Частично интегрирован (через image_generator для обложек)
- **Capabilities:** VIDEO_GENERATE
- **API:** KIE API (async: submit → poll → download)
- **Для:** Генерация multi-shot видео (до 15 секунд)

## Как добавить нового провайдера

1. Создать `ai/providers/my_provider.py`
2. Реализовать нужный интерфейс (`TextAIProvider` / `ImageAIProvider` / `VideoAIProvider`)
3. Зарегистрировать в `ai/registry.py`
4. Добавить env-переменные в `.env.example` и `app/config.py`
5. Обновить этот файл
6. Создать ADR (если принципиально новый провайдер)
