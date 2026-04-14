# ContenZavod

AI-управляемая платформа полного цикла контент-менеджмента: парсинг → AI-классификация → адаптация → мультиканальная публикация.

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Celery, Redis
- **Database:** PostgreSQL 16 (RLS multi-tenancy)
- **AI:** Gemini 2.5 Flash, Kling 3.0 (pluggable provider system)
- **Frontend:** Next.js 15, shadcn/ui, Tailwind CSS v4 *(coming soon)*
- **Storage:** MinIO (S3-compatible)

## Требования

- Docker & Docker Compose
- Make (опционально)

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd ContenZavod

# 2. Создать .env файл
cp .env.example .env
# Отредактировать .env — заполнить API-ключи

# 3. Запустить сервисы
make up-build
# или: docker compose up -d --build

# 4. Применить миграции БД
make db-upgrade
# или: docker compose exec backend alembic upgrade head

# 5. Проверить
curl http://localhost:8000/api/v1/health
# → {"status":"ok","components":{"api":"ok","database":"ok"}}
```

## Структура проекта

```
ContenZavod/
├── backend/              # Python (FastAPI + Celery)
│   ├── app/              # FastAPI application
│   │   ├── api/          # Endpoints
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── services/     # Business logic
│   │   ├── core/         # Auth, exceptions
│   │   ├── config.py     # Settings
│   │   └── database.py   # DB engine
│   ├── ai/               # AI Provider System
│   │   ├── providers/    # Конкретные провайдеры (Gemini, Kling)
│   │   ├── registry.py   # Provider Registry
│   │   └── capabilities.py
│   ├── workers/          # Celery tasks
│   ├── migrations/       # Alembic
│   └── tests/
├── docs/                 # Документация
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── AI_PROVIDERS.md
│   └── adr/              # Architecture Decision Records
├── infra/                # Docker, nginx
├── docker-compose.yml
├── CLAUDE.md             # Правила проекта
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
make lint          # Линтинг
make format        # Форматирование
```

## Документация

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Архитектура системы
- [DATABASE.md](docs/DATABASE.md) — Схема базы данных
- [AI_PROVIDERS.md](docs/AI_PROVIDERS.md) — AI-провайдеры
- [ADR](docs/adr/) — Архитектурные решения

## Лицензия

Private / Proprietary
