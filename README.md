# ContenZavod

AI-управляемая платформа полного цикла контент-менеджмента:
**парсинг → AI-классификация → AI-скоринг → адаптация → модерация → публикация в Telegram.**

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Celery, Redis
- **Database:** PostgreSQL 16 (Row Level Security, мультитенантность)
- **AI:** Gemini 2.5 Flash (pluggable provider system)
- **Frontend:** Next.js 16 (App Router), custom CSS design system
- **Storage:** MinIO (S3-compatible)
- **Publishing:** Telegram Bot API (httpx)

## Возможности

- 🔍 **Автосбор** — парсинг RSS/веб-источников по расписанию (Celery Beat + Playwright)
- 🤖 **AI-классификация** — рубрикация, теги, саммари через Gemini Flash
- 📊 **AI-скоринг** — оценка relevance + hype для каждого проекта
- ✍️ **AI-адаптация** — генерация контента в нужном формате (пост / лонгрид / видео-скрипт / дайджест)
- 📋 **Модерация** — просмотр, редактирование, одобрение адаптаций
- 📢 **Автопубликация** — при одобрении → автоматическая отправка в Telegram
- 🏷️ **Фильтры** — по рубрикам, категориям, статусам
- 🔒 **Мультитенантность** — PostgreSQL RLS, полная изоляция данных

## Требования

- Docker & Docker Compose
- Make (опционально)
- Node.js 22+ (для frontend)

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd ContenZavod

# 2. Создать .env файл
cp .env.example .env
# Заполнить: DATABASE_URL, GEMINI_API_KEY, SECRET_KEY

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
├── backend/              # Python (FastAPI + Celery)
│   ├── app/              # FastAPI application
│   │   ├── api/v1/       # REST endpoints (10 модулей)
│   │   ├── models/       # SQLAlchemy ORM models (17 моделей)
│   │   ├── services/     # Business logic (7 сервисов)
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── core/         # Auth, exceptions
│   │   ├── config.py     # Settings (Pydantic)
│   │   └── database.py   # DB engine (async + sync)
│   ├── ai/               # AI Provider System
│   │   ├── classifier.py # Классификация + скоринг
│   │   ├── editor.py     # Адаптация контента
│   │   ├── registry.py   # Provider Registry
│   │   └── providers/    # Абстракции провайдеров
│   ├── workers/          # Celery tasks
│   │   ├── celery_app.py # Config: очереди, beat schedule
│   │   ├── scrape_tasks.py
│   │   ├── ai_tasks.py
│   │   └── publish_tasks.py
│   ├── migrations/       # Alembic
│   └── tests/
├── frontend/             # Next.js 16 Admin Panel
│   └── src/app/          # App Router pages
├── docs/                 # Документация
│   ├── ARCHITECTURE.md   # Архитектура системы
│   ├── DATABASE.md       # Схема БД
│   ├── API.md            # REST API Reference
│   ├── AI_PROVIDERS.md   # AI-провайдеры
│   └── adr/              # Architecture Decision Records
├── docker-compose.yml    # Dev-окружение
├── CLAUDE.md             # Правила проекта (конституция)
├── CHANGELOG.md          # Журнал изменений
└── Makefile              # Удобные команды
```

## Makefile-команды

```bash
make help          # Все доступные команды
make up            # Запустить сервисы
make down          # Остановить
make logs          # Логи всех сервисов
make shell         # Bash в backend
make shell-db      # psql в PostgreSQL
make db-migrate msg="описание"   # Новая миграция
make db-upgrade    # Применить миграции
make test          # Тесты
make lint          # Линтинг (ruff)
make format        # Форматирование (ruff format)
```

## Документация

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура, потоки данных, подсистемы |
| [DATABASE.md](docs/DATABASE.md) | Схема БД, таблицы, индексы |
| [API.md](docs/API.md) | REST API Reference |
| [AI_PROVIDERS.md](docs/AI_PROVIDERS.md) | AI-провайдеры, промпты |
| [ADR](docs/adr/) | Архитектурные решения |
| [CHANGELOG.md](CHANGELOG.md) | Журнал изменений |
| [CLAUDE.md](CLAUDE.md) | Правила проекта |

## Лицензия

Private / Proprietary
