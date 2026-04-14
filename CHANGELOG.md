# Changelog

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Версионирование следует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added
- Инициализация проекта: CLAUDE.md, структура документации, CHANGELOG
- Документация: ARCHITECTURE.md, DATABASE.md, AI_PROVIDERS.md, 3 ADR
- Backend foundation: FastAPI app factory, Pydantic Settings, async DB engine
- 12 ORM-моделей с мультитенантностью (TenantMixin + PostgreSQL RLS)
- JWT-аутентификация (access + refresh tokens, bcrypt)
- AI Provider System: абстрактные интерфейсы + Registry с fallback
- Celery + Redis: 5 очередей (scrape, ai, publish, media, analytics)
- Docker Compose: PostgreSQL 16, Redis 7, MinIO, backend, worker, beat
- Alembic: async миграции для SQLAlchemy 2.0
- Makefile: 20+ команд для управления проектом
- Health check endpoint: /api/v1/health
- API endpoints: auth (register/login/me), CRUD sources/channels, materials listing, dashboard stats
- Pydantic schemas + Service layer с тенантной изоляцией
- Frontend: Next.js 16 + shadcn/ui + Tailwind v4 + Zustand
- Страницы: Login, Dashboard, Sources, Materials, Channels
- Sidebar layout с auth guard и toast-уведомлениями
