# ContenZavod

AI-управляемая платформа полного цикла контент-менеджмента:
**парсинг → AI-классификация → AI-скоринг → адаптация → модерация → публикация в Telegram.**

Дополнительно: **Автопилот** 🤖 (полностью автономная публикация) и **Видео-дайджесты** 🎬 (AI-аватар зачитывает новости).

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Celery, Redis
- **Database:** PostgreSQL 16 (Row Level Security, мультитенантность)
- **AI:** Gemini 2.5 Flash (основной) + Claude Haiku 4.5 (fallback) — pluggable provider system
- **Video:** ReVid API v3 (avatar-to-video rendering)
- **Frontend:** Next.js 16 (App Router), custom CSS design system
- **Storage:** MinIO (S3-compatible)
- **Publishing:** Telegram Bot API (httpx)

## Возможности

- 🔍 **Автосбор** — парсинг RSS/веб-источников по расписанию (Celery Beat)
- 🤖 **AI-классификация** — рубрикация, теги, саммари через Gemini Flash
- 📊 **AI-скоринг** — оценка relevance + hype для каждого проекта
- ✍️ **AI-адаптация** — генерация контента в нужном формате (пост / лонгрид / видео-скрипт / дайджест)
- 📋 **Модерация** — просмотр, редактирование, одобрение адаптаций
- 📢 **Автопубликация** — при одобрении → автоматическая отправка в Telegram
- 🤖 **Автопилот** — полностью автономный цикл: ранжирование → адаптация → обложка → публикация
- 🎬 **Видео-дайджесты** — AI-генерация сценариев + рендер видео с аватаром через ReVid
- 🖼️ **Обложки** — AI-генерация изображений через Claude Haiku + Kling
- 🔀 **Дедупликация** — семантический анализ предотвращает дублирование
- 🏷️ **Фильтры** — по рубрикам, категориям, статусам, языкам
- 🔒 **Мультитенантность** — PostgreSQL RLS, полная изоляция данных
- 🔄 **Auto-polling** — GET-запрос автоматически проверяет статус видео в ReVid

## Требования

- Docker & Docker Compose v2
- Make (опционально)
- Node.js 22+ (для frontend)

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd ContenZavod

# 2. Создать .env файл
cp .env.example .env
# Заполнить: DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY
# Для видео-дайджестов: REVID_API_KEY, REVID_AVATAR_URL
# Для AI-fallback: KIE_API_KEY

# 3. Запустить бэкенд-сервисы
make up-build
# или: docker compose up -d --build

# 4. Применить миграции БД
make db-upgrade
# или: docker compose exec backend alembic upgrade head

# 5. Запустить фронтенд
cd frontend && npm install && npm run dev

# 6. Проверить
curl http://localhost:8000/api/v1/health
# → {"status":"ok","components":{"api":"ok","database":"ok"}}

# 7. Открыть UI
open http://localhost:3000
```

## Структура проекта

```
ContenZavod/
├── backend/                 # Python (FastAPI + Celery)
│   ├── app/                 # FastAPI application
│   │   ├── api/v1/          # REST endpoints (12 модулей)
│   │   ├── models/          # SQLAlchemy ORM models (18 моделей)
│   │   ├── services/        # Business logic (8 сервисов)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── core/            # Auth, exceptions
│   │   ├── config.py        # Settings (Pydantic)
│   │   └── database.py      # DB engine (async + sync)
│   ├── ai/                  # AI Provider System
│   │   ├── classifier.py    # Классификация + скоринг
│   │   ├── adapter.py       # Адаптация контента
│   │   ├── editor.py        # Редактирование текстов
│   │   ├── deduplicator.py  # Дедупликация
│   │   ├── digest_script.py # Генерация видеосценариев
│   │   ├── image_generator.py # Обложки (Claude + Kling)
│   │   ├── registry.py      # Provider Registry
│   │   └── providers/       # Абстракции провайдеров
│   ├── integrations/        # Внешние API
│   │   └── revid.py         # ReVid v3 (видео-рендер)
│   ├── workers/             # Celery tasks (5 модулей)
│   │   ├── celery_app.py    # Config: 5 очередей, 8 periodic tasks
│   │   ├── scrape_tasks.py  # Парсинг RSS
│   │   ├── ai_tasks.py      # Классификация, скоринг, адаптация
│   │   ├── publish_tasks.py # Публикация в Telegram
│   │   ├── digest_tasks.py  # Сценарии + ReVid рендер
│   │   └── autopilot_tasks.py # Автономная публикация
│   ├── scraper/             # RSS parser
│   ├── migrations/          # Alembic
│   └── tests/
├── frontend/                # Next.js 16 Admin Panel
│   └── src/app/
│       └── (dashboard)/
│           ├── projects/[id]/
│           │   ├── page.tsx            # Проект (4 таба)
│           │   ├── digests/page.tsx    # Видео-дайджесты
│           │   └── _components/
│           │       ├── AutopilotTab.tsx # Автопилот
│           │       ├── RecommendationsTab.tsx
│           │       ├── ChannelsTab.tsx
│           │       └── ...
│           ├── materials/
│           ├── sources/
│           └── channels/
├── docs/                    # Документация
│   ├── ARCHITECTURE.md      # Архитектура системы
│   ├── DATABASE.md          # Схема БД (17 таблиц)
│   ├── API.md               # REST API Reference
│   ├── AI_PROVIDERS.md      # AI-провайдеры
│   ├── DEPLOYMENT.md        # Гайд по деплою
│   └── adr/                 # Architecture Decision Records
├── docker-compose.yml       # Dev-окружение (6 сервисов)
├── CLAUDE.md                # Правила проекта (конституция)
├── CHANGELOG.md             # Журнал изменений
└── Makefile                 # Удобные команды
```

## Makefile-команды

```bash
make help          # Все доступные команды
make up            # Запустить сервисы
make up-build      # Пересобрать и запустить
make down          # Остановить
make logs          # Логи всех сервисов
make logs-backend  # Логи бэкенда
make logs-worker   # Логи Celery worker
make shell         # Bash в backend
make shell-db      # psql в PostgreSQL
make shell-redis   # redis-cli
make db-migrate msg="описание"   # Новая миграция
make db-upgrade    # Применить миграции
make db-downgrade  # Откатить миграцию
make test          # Тесты
make lint          # Линтинг (ruff)
make format        # Форматирование (ruff format)
make docs-check    # Проверка документации
```

## Документация

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура, потоки данных, подсистемы |
| [DATABASE.md](docs/DATABASE.md) | Схема БД, 17 таблиц, индексы |
| [API.md](docs/API.md) | REST API Reference (12 модулей) |
| [AI_PROVIDERS.md](docs/AI_PROVIDERS.md) | AI-провайдеры, промпты, fallback |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Деплой, env vars, Celery config |
| [ADR](docs/adr/) | Архитектурные решения |
| [CHANGELOG.md](CHANGELOG.md) | Журнал изменений |
| [CLAUDE.md](CLAUDE.md) | Правила проекта |

## Лицензия

Private / Proprietary
