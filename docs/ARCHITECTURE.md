# ContenZavod — Архитектура

> Последнее обновление: 2026-05-06

## Обзор

ContenZavod — мультитенантная SaaS-платформа полного цикла контент-менеджмента:
**парсинг → AI-классификация → AI-скоринг → адаптация → модерация → публикация.**

Дополнительно платформа поддерживает:
- **Автопилот** — полностью автономная публикация по расписанию с AI-ранжированием
- **Видео-дайджесты** — генерация AI-видео из новостей через ReVid API v3

## Стек технологий

### Backend
| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Runtime | Python | 3.12+ |
| Package Manager | uv | latest |
| API | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| Migrations | Alembic | latest (async) |
| Task Queue | Celery | 5.4+ |
| Broker/Cache | Redis | 7+ |
| Database | PostgreSQL | 16+ (RLS) |
| Scraper | Playwright | latest |
| HTTP Client | httpx | latest |

### Frontend
| Компонент | Технология |
|-----------|-----------|
| Framework | Next.js 16 (App Router) |
| Runtime | Node.js 22+ |
| Styling | CSS Variables (custom design system) |
| State | React useState/useEffect + localStorage |
| Icons | Lucide React |

### AI Providers (pluggable)
| Задача | Провайдер | Модель | Файл |
|--------|----------|--------|------|
| Классификация | Google | Gemini 2.5 Flash | `ai/classifier.py` |
| Адаптация контента | Google / KIE | Gemini 2.5 Flash / Claude Haiku 4.5 | `ai/editor.py` |
| Скоринг для проектов | Google | Gemini 2.5 Flash | `ai/classifier.py` |
| Дедупликация | Google | Gemini 2.5 Flash | `ai/deduplicator.py` |
| Генерация скриптов | Google | Gemini 2.5 Flash | `ai/digest_script.py` |
| Генерация обложек | KIE | Claude Haiku 4.5 → Kling | `ai/image_generator.py` |

### Внешние интеграции
| Сервис | Назначение | Файл |
|--------|-----------|------|
| ReVid API v3 | Рендер AI-видео (avatar-to-video) | `integrations/revid.py` |
| Telegram Bot API | Публикация постов в каналы | `app/services/telegram_client.py` |

### Инфраструктура (Docker)
| Сервис | Docker Container | Порт (host:container) |
|--------|-----------------|----------------------|
| Backend API | `contenzavod-backend` | 8010:8000 |
| Frontend | dev server (npm) | 3000 |
| Celery Worker | `contenzavod-celery-worker` | — |
| Celery Beat | `contenzavod-celery-beat` | — |
| PostgreSQL | `contenzavod-postgres` | 5435:5432 |
| Redis | `contenzavod-redis` | 6381:6379 |
| MinIO | `contenzavod-minio` | 9002:9000, 9003:9001 |

---

## Высокоуровневая архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│               Admin Panel (Next.js 16, порт 3000)                │
│  Login → Dashboard → Projects → Recommendations →                │
│  Channels → Adaptations → Approve → Published! ✅                 │
│  🎬 Видео-Дайджесты → Script → Render → Ready! ▶️                │
│  🤖 Автопилот → Config → Queue → Auto-Publish! 🚀                │
└──────────────────────┬───────────────────────────────────────────┘
                       │ REST API (JWT auth)
┌──────────────────────▼───────────────────────────────────────────┐
│                FastAPI Backend (порт 8000)                        │
│  ┌──────────┬──────────┬───────────┬──────────────────────────┐  │
│  │ Auth     │ Projects │ Channels  │ Adaptations              │  │
│  │ (JWT)    │ + Scores │ CRUD      │ Generate/Approve         │  │
│  ├──────────┼──────────┼───────────┼──────────────────────────┤  │
│  │ Materials│ Sources  │ Dashboard │ Health                   │  │
│  │ CRUD     │ CRUD     │ Stats     │ Check                    │  │
│  ├──────────┼──────────┼───────────┼──────────────────────────┤  │
│  │ Digests  │ Autopilot│ Files     │                          │  │
│  │ Video Gen│ Queue API│ Upload    │                          │  │
│  └──────────┴──────────┴───────────┴──────────────────────────┘  │
│                        │                                          │
│  ┌─────────────────────▼──────────────────────────────────────┐  │
│  │                Service Layer                                │  │
│  │  AuthService · ChannelService · MaterialService             │  │
│  │  ProjectService · SourceService · PublishService             │  │
│  │  TelegramClient · StorageService                            │  │
│  └─────────────────────┬──────────────────────────────────────┘  │
└────────────────────────┼─────────────────────────────────────────┘
                         │
           ┌─────────────┼──────────────┐
           ▼             ▼              ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ Redis       │ │ MinIO / S3   │
│ 16 + RLS     │ │ (Broker +   │ │ (Media)      │
│              │ │  Cache)     │ │              │
└──────────────┘ └──────┬──────┘ └──────────────┘
                        │
                 ┌──────▼──────────────────────────────────────┐
                 │ Celery Workers                               │
                 │ ┌──────────────┐ ┌──────────────────────┐   │
                 │ │ scrape_tasks │ │ ai_tasks             │   │
                 │ │ → Playwright │ │ → classify, score,   │   │
                 │ │   RSS/HTML   │ │   adapt, deduplicate │   │
                 │ ├──────────────┤ ├──────────────────────┤   │
                 │ │ publish_tasks│ │ digest_tasks         │   │
                 │ │ → Telegram   │ │ → script gen + ReVid │   │
                 │ ├──────────────┤ ├──────────────────────┤   │
                 │ │ autopilot_   │ │                      │   │
                 │ │ tasks        │ │ External APIs:       │   │
                 │ │ → rank,      │ │ • Gemini Flash       │   │
                 │ │   publish,   │ │ • Claude Haiku 4.5   │   │
                 │ │   retry,     │ │ • ReVid v3           │   │
                 │ │   expire     │ │ • Telegram Bot       │   │
                 │ └──────────────┘ └──────────────────────┘   │
                 │                                              │
                 │ Celery Beat (cron scheduler)                 │
                 └─────────────────────────────────────────────┘
```

---

## Слои приложения

```
API Routes (app/api/v1/)     ← Тонкие контроллеры: валидация + вызов сервиса
     ↓
Services (app/services/)     ← Бизнес-логика, оркестрация
     ↓
Models (app/models/)         ← ORM, schema definition
     ↓
Database (app/database.py)   ← Connection pool (async + sync)
```

**Правила:**
- ❌ Запрещено обращаться к БД напрямую из API routes
- ❌ Запрещено класть бизнес-логику в Celery tasks (tasks вызывают services)
- ❌ Запрещено хардкодить AI-промпты (через `ai/` модули)

---

## Мультитенантность

- **Модель:** Shared Database + Row Level Security
- **Ключ:** `tenant_id UUID` в каждой таблице (через `TenantMixin`)
- **Изоляция:** PostgreSQL RLS policies
- **Context:** `set_config('app.current_tenant', ...)` через middleware
- **Timestamps:** `TimestampMixin` добавляет `created_at`, `updated_at`

---

## Потоки данных

### 1. Сбор материалов
```
Celery Beat (cron: каждые 2 часа)
     ↓
scrape_tasks.scrape_all_active_sources()
     ↓
rss_parser.py → парсит RSS/HTML → извлекает текст
     ↓
БД: raw_materials (status = new, content_hash для дедупликации)
```

### 2. AI-классификация
```
Celery Beat (cron: каждые 30 мин)
     ↓
ai_tasks.classify_new_materials()
     ↓
ai/classifier.py → Gemini Flash
     ↓
Результат: category, summary, tags → material.metadata_
     ↓
БД: raw_material.status = classified
```

### 3. AI-скоринг для проектов
```
Celery Beat (cron: каждые 15 мин)
     ↓
ai_tasks.evaluate_classified_materials()
     ↓
ai/classifier.py → Gemini Flash
     ↓
Для каждого активного проекта: оценка relevance (0-10) + hype (0-10)
     ↓
БД: material_project_scores (is_recommended = true если оба >= 6)
```

### 4. Адаптация контента
```
Пользователь видит рекомендацию в UI → нажимает «Адаптировать»
     или
Autopilot → автоматическая «ленивая адаптация» (lazy-adapt)
     ↓
API: POST /adaptations/generate {material_id, channel_id, content_format}
     ↓
ai_tasks.generate_adaptation → ai/editor.py → Gemini Flash / Claude Haiku 4.5
     ↓
Формат определяется каналом:
  Telegram → short_post (по умолчанию)
  Website  → longread
  YouTube  → video_script
     ↓
БД: channel_adaptations (status = draft, headline + body)
```

### 5. Модерация → Публикация (ручная)
```
Редактор видит адаптацию → нажимает «Одобрить»
     ↓
API: PATCH /adaptations/{id} {status: "approved"}
     ↓
Бэкенд автоматически:
  1. Создаёт PublishJob (idempotency_key предотвращает дубли)
  2. Ставит Celery task: publish_to_telegram
     ↓
workers/publish_tasks.py → PublishService → TelegramClient
     ↓
TelegramClient:
  1. format_post(headline, body) → markdown → HTML
  2. send_message(chat_id, html) → Bot API
     ↓
БД: publish_job.status = published, adaptation.status = published
     ↓
✅ Пост в Telegram канале
```

### 6. Автопилот (автоматическая публикация)
```
Celery Beat каждые 15 мин → autopilot_rank_and_queue
     ↓
AI-ранжирование: freshness × relevance × hype → queue_score
     ↓
БД: autopilot_queue (status = queued, priority_score)
     ↓
Celery Beat каждые 5 мин → autopilot_publish_next
     ↓
  1. Проверка лимитов (per-language, per-channel)
  2. Ожидание генерации обложки
  3. Публикация через PublishService
     ↓
БД: autopilot_queue.status = published
     ↓
✅ Пост в Telegram (автоматически, без модерации)

Дополнительно:
  • autopilot_retry_covers (каждые 10 мин) — повторная генерация обложек
  • autopilot_expire_stale (каждый час) — очистка устаревших элементов
```

### 7. Видео-дайджесты
```
Пользователь создаёт дайджест → выбирает материалы
     ↓
API: POST /digests/{id}/generate-script
     ↓
digest_tasks.generate_script → ai/digest_script.py → Gemini Flash
     ↓
Скрипт: [scene_description]\nТекст для озвучки.\n<break time="1.0s" />
     ↓
API: POST /digests/{id}/render
     ↓
digest_tasks.render_video → integrations/revid.py → ReVid API v3
     ↓
Payload: workflow=avatar-to-video, render_config (media, voice, captions, avatar)
     ↓
БД: revid_status = rendering, revid_pid = "xxx"
     ↓
GET /digests/{id} → auto-poll ReVid → обновляет БД при готовности
     ↓
БД: revid_status = ready, video_url = https://cdn.revid.ai/...
     ↓
✅ Видео готово к просмотру
```

---

## Ключевые подсистемы

### AI Provider System
```
ai/
├── capabilities.py      # Enum: TEXT_CLASSIFY, TEXT_ADAPT, IMAGE_GENERATE...
├── registry.py          # Provider Registry с fallback
├── adapter.py           # Адаптация контента (Gemini + Claude Haiku fallback)
├── classifier.py        # Классификация + скоринг (Gemini Flash)
├── deduplicator.py      # Дедупликация контента
├── digest_script.py     # Генерация видеосценариев (Gemini Flash)
├── editor.py            # Редактирование/адаптация текстов
├── image_generator.py   # Генерация обложек (Claude → Kling)
└── providers/
    ├── base.py          # Abstract base classes
    └── __init__.py
```

### Service Layer
```
app/services/
├── auth_service.py       # JWT: register, login, verify, refresh
├── channel_service.py    # CRUD каналов с tenant isolation
├── material_service.py   # CRUD материалов + status management
├── project_service.py    # CRUD проектов + channel binding
├── source_service.py     # CRUD источников (RSS)
├── publish_service.py    # Lifecycle публикации (load → validate → send → update)
├── storage.py            # MinIO/S3 файловое хранилище
└── telegram_client.py    # HTTP-клиент Telegram Bot API
```

### Integrations
```
integrations/
└── revid.py              # ReVid API v3: render, check_status, credits
                          # Media type normalization (provided→custom)
                          # Detailed error capture from API responses
```

### Celery Workers
```
workers/
├── celery_app.py         # Конфигурация: 5 очередей, beat schedule, task routing
├── scrape_tasks.py       # Парсинг источников (RSS parser)
├── ai_tasks.py           # Классификация, скоринг, адаптация, обложки
├── publish_tasks.py      # Публикация + синхронизация статистики Telegram
├── digest_tasks.py       # Генерация видеосценариев + рендер через ReVid
└── autopilot_tasks.py    # Ранжирование, авто-публикация, retry, expire
```

### Очереди Celery
| Очередь | Задачи | Приоритет |
|---------|--------|-----------|
| `scrape_queue` | Парсинг RSS/HTML | Средний |
| `ai_queue` | Классификация, скоринг, ранжирование, скрипты | Высокий |
| `publish_queue` | Публикация в Telegram, автопилот-publish | Критический |
| `media_queue` | Обложки, retry covers | Низкий |
| `analytics_queue` | Сбор статистики | Самый низкий |

### Периодические задачи (Celery Beat)
| Задача | Расписание | Очередь |
|--------|-----------|---------|
| `scrape_all_active_sources` | Каждые 2 часа | scrape_queue |
| `classify_new_materials` | Каждые 30 мин | ai_queue |
| `evaluate_classified_materials` | Каждые 15 мин | ai_queue |
| `sync_telegram_stats` | Каждые 30 мин | publish_queue |
| `autopilot_rank_and_queue` | Каждые 15 мин | ai_queue |
| `autopilot_publish_next` | Каждые 5 мин | publish_queue |
| `autopilot_retry_covers` | Каждые 10 мин | media_queue |
| `autopilot_expire_stale` | Каждый час | ai_queue |

---

## Структура проекта

```
ContenZavod/
├── docker-compose.yml          # 6 сервисов: pg, redis, minio, backend, worker, beat
├── .env / .env.example         # Конфигурация окружения
├── Makefile                    # Команды: up, logs, db-migrate, test, lint
├── CLAUDE.md                   # Контекст для AI-ассистента
├── README.md                   # Общее описание проекта
├── CHANGELOG.md                # Лог изменений
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml          # Python зависимости (uv)
│   ├── alembic.ini             # Конфигурация миграций
│   │
│   ├── app/                    # FastAPI application
│   │   ├── main.py             # Entrypoint: CORS, middleware, router
│   │   ├── config.py           # Pydantic Settings (env vars)
│   │   ├── database.py         # Async/sync engine + session factory
│   │   ├── core/
│   │   │   └── security.py     # JWT encode/decode
│   │   ├── api/
│   │   │   ├── deps.py         # Dependency injection (get_db, get_user)
│   │   │   └── v1/
│   │   │       ├── router.py   # Агрегатор всех роутеров
│   │   │       ├── auth.py     # Login, register, refresh
│   │   │       ├── projects.py # CRUD + pipeline endpoints
│   │   │       ├── materials.py
│   │   │       ├── sources.py
│   │   │       ├── channels.py
│   │   │       ├── adaptations.py
│   │   │       ├── dashboard.py
│   │   │       ├── digests.py  # Video digest CRUD + ReVid polling
│   │   │       ├── autopilot.py # Autopilot queue management
│   │   │       ├── files.py    # File upload (MinIO)
│   │   │       └── health.py
│   │   ├── models/             # 18 SQLAlchemy моделей
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── services/           # Business logic layer
│   │
│   ├── ai/                     # AI modules (pluggable providers)
│   ├── integrations/           # External API clients (ReVid)
│   ├── workers/                # Celery tasks (5 модулей)
│   ├── scraper/                # RSS parser
│   ├── publishing/             # Publishing utilities
│   ├── migrations/             # Alembic migrations
│   └── tests/
│
├── frontend/                   # Next.js 16 SPA
│   └── src/app/(dashboard)/
│       ├── page.tsx            # Dashboard
│       ├── projects/[id]/
│       │   ├── page.tsx        # Project detail (4 tabs)
│       │   ├── digests/page.tsx # Video digest UI
│       │   └── _components/
│       │       ├── RecommendationsTab.tsx
│       │       ├── ChannelsTab.tsx
│       │       ├── AutopilotTab.tsx
│       │       ├── SettingsTab.tsx
│       │       ├── PipelineCards.tsx
│       │       ├── PipelineNav.tsx
│       │       └── PublishDialog.tsx
│       ├── materials/
│       ├── sources/
│       └── channels/
│
├── docs/                       # Документация проекта
│   ├── ARCHITECTURE.md         # ← Этот файл
│   ├── DATABASE.md             # Схема БД
│   ├── API.md                  # REST API эндпоинты
│   ├── AI_PROVIDERS.md         # AI-провайдеры и промпты
│   ├── DEPLOYMENT.md           # Гайд по деплою
│   └── adr/                    # Architecture Decision Records
│
└── infra/                      # Инфра-скрипты
    └── postgres/init.sql       # Инициализация БД
```

---

## Подробная документация

- [DATABASE.md](./DATABASE.md) — Схема БД, все таблицы и индексы
- [API.md](./API.md) — REST API эндпоинты
- [AI_PROVIDERS.md](./AI_PROVIDERS.md) — AI-провайдеры и промпты
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Гайд по деплою
- [adr/](./adr/) — Архитектурные решения
