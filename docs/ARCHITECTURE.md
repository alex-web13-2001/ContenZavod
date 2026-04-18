# ContenZavod — Архитектура

> Последнее обновление: 2026-04-18

## Обзор

ContenZavod — мультитенантная SaaS-платформа полного цикла контент-менеджмента:
**парсинг → AI-классификация → AI-скоринг → адаптация → модерация → публикация.**

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
| State | React useState/useEffect |
| Icons | Lucide React |

### AI Providers (pluggable)
| Задача | Провайдер | Модель | Файл |
|--------|----------|--------|------|
| Классификация | Google | Gemini 2.5 Flash | `ai/classifier.py` |
| Адаптация контента | Google | Gemini 2.5 Flash | `ai/editor.py` |
| Скоринг для проектов | Google | Gemini 2.5 Flash | `ai/classifier.py` |

### Инфраструктура
| Сервис | Docker | Порт |
|--------|--------|------|
| Backend API | `contenzavod-backend` | 8000 |
| Frontend | dev server (npm) | 3000 |
| Celery Worker | `contenzavod-celery-worker` | — |
| Celery Beat | `contenzavod-celery-beat` | — |
| PostgreSQL | `contenzavod-postgres` | 5432 |
| Redis | `contenzavod-redis` | 6379 |
| MinIO | `contenzavod-minio` | 9000/9001 |

---

## Высокоуровневая архитектура

```
┌──────────────────────────────────────────────────────────┐
│             Admin Panel (Next.js 16, порт 3000)          │
│  Login → Dashboard → Projects → Recommendations →        │
│  Channels → Adaptations → Approve → Published! ✅         │
└──────────────────────┬───────────────────────────────────┘
                       │ REST API (JWT auth)
┌──────────────────────▼───────────────────────────────────┐
│                FastAPI Backend (порт 8000)                │
│  ┌──────────┬──────────┬───────────┬──────────────────┐  │
│  │ Auth     │ Projects │ Channels  │ Adaptations      │  │
│  │ (JWT)    │ + Scores │ CRUD      │ Generate/Approve │  │
│  ├──────────┼──────────┼───────────┼──────────────────┤  │
│  │ Materials│ Sources  │ Dashboard │ Health           │  │
│  │ CRUD     │ CRUD     │ Stats     │ Check            │  │
│  └──────────┴──────────┴───────────┴──────────────────┘  │
│                        │                                  │
│  ┌─────────────────────▼──────────────────────────────┐  │
│  │              Service Layer                          │  │
│  │  AuthService · ChannelService · MaterialService     │  │
│  │  ProjectService · SourceService · PublishService     │  │
│  │  TelegramClient                                     │  │
│  └─────────────────────┬──────────────────────────────┘  │
└────────────────────────┼─────────────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ Redis      │ │ MinIO / S3   │
│ 16 + RLS     │ │ (Broker +  │ │ (Media)      │
│              │ │  Cache)    │ │              │
└──────────────┘ └─────┬──────┘ └──────────────┘
                       │
                ┌──────▼───────┐
                │ Celery       │
                │ Workers      │
                │ ┌──────────┐ │     ┌──────────────┐
                │ │ scrape   │─┼────>│ Playwright   │
                │ │ ai       │─┼────>│ Gemini API   │
                │ │ publish  │─┼────>│ Telegram API │
                │ └──────────┘ │     └──────────────┘
                │              │
                │ Celery Beat  │
                │ (cron)       │
                └──────────────┘
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
Celery Beat (cron: каждые 30 мин)
     ↓
scrape_tasks.scrape_source(source_id)
     ↓
Playwright → парсит RSS/HTML → извлекает текст
     ↓
БД: raw_materials (status = new, content_hash для дедупликации)
```

### 2. AI-классификация
```
scrape_task завершён → ставит classify_task
     ↓
ai/classifier.py → Gemini Flash
     ↓
Входные данные: title, content, source
     ↓
Результат: category, summary, tags → material.metadata_
     ↓
БД: raw_material.status = classified
```

### 3. AI-скоринг для проектов
```
classify_task завершён → ставит score_for_projects_task
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
score_task завершён → автоматически ставит adapt_task
     ↓
API: POST /adaptations/generate {material_id, channel_id, content_format}
     ↓
ai_tasks.generate_adaptation → ai/editor.py → Gemini Flash
     ↓
Формат определяется каналом:
  Telegram → short_post (по умолчанию)
  Website  → longread
  YouTube  → video_script
     ↓
БД: channel_adaptations (status = draft, headline + body)
```

### 5. Модерация → Публикация
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

---

## Ключевые подсистемы

### AI Provider System
```
ai/
├── capabilities.py    # Enum: TEXT_CLASSIFY, TEXT_ADAPT, IMAGE_GENERATE...
├── registry.py        # Provider Registry с fallback
├── adapter.py         # Base adapter interface
├── classifier.py      # Классификация + скоринг (Gemini Flash)
├── editor.py          # Адаптация контента (Gemini Flash)
└── providers/
    ├── base.py        # Abstract base classes
    └── __init__.py
```

### Service Layer
```
app/services/
├── auth_service.py       # JWT: register, login, verify
├── channel_service.py    # CRUD каналов с tenant isolation
├── material_service.py   # CRUD материалов + status management
├── project_service.py    # CRUD проектов + channel binding
├── source_service.py     # CRUD источников
├── publish_service.py    # Lifecycle публикации (load → validate → send → update)
└── telegram_client.py    # HTTP-клиент Telegram Bot API
```

### Celery Workers
```
workers/
├── celery_app.py       # Конфигурация: 5 очередей, beat schedule
├── scrape_tasks.py     # Парсинг источников (Playwright)
├── ai_tasks.py         # Классификация, скоринг, адаптация
└── publish_tasks.py    # Публикация (тонкий wrapper → PublishService)
```

---

## Подробная документация

- [DATABASE.md](./DATABASE.md) — Схема БД, все таблицы и индексы
- [API.md](./API.md) — REST API эндпоинты
- [AI_PROVIDERS.md](./AI_PROVIDERS.md) — AI-провайдеры и промпты
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Гайд по деплою
- [adr/](./adr/) — Архитектурные решения
