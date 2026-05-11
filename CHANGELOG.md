# Changelog

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Версионирование следует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added
- Мульти-форматный автопилот: формат `flash` (молния, 80–200 символов, без заголовка и обложки) рядом с `short_post` и `longread`
- `suggested_format` в схеме классификатора — AI рекомендует формат при классификации (flash / short_post / longread)
- Балансировка форматов в очереди автопилота через `format_ratios` (по умолчанию 40/40/20) с допуском перебора 1.5×
- Жёсткий дневной лимит лонгридов (`longread_max_per_day`, default 2)
- API: `format_ratios`, `longread_max_per_day` в `GET/PATCH /autopilot/config`; `format_counts` в `GET /autopilot/stats`
- UI: слайдеры формат-микса в настройках канала, бейджи ⚡📝📊 в карточках очереди, мини-статистика формат-микса в шапке автопилота
- Data-migration script `backend/scripts/add_flash_format.py` — добавляет `flash` в `content_formats` существующих Telegram-каналов
- ADR-006: переход от primary-format-only к ratio-balanced multi-format очереди
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
- Проекты: CRUD, привязка каналов к проектам
- Рекомендации: AI-скоринг материалов для проектов (relevance + hype)
- Адаптации: AI-генерация контента под формат канала (short_post, longread, video_script, digest)
- On-demand генерация: API `POST /adaptations/generate` + UI-кнопки «+ ещё формат»
- Умный выбор основного формата: short_post для Telegram, longread для Website, video_script для YouTube
- Фильтр по рубрикам: UI-чипы с эмодзи, `GET /projects/{id}/categories`, query-параметр `category`
- Telegram-публикация: полный пайплайн Одобрить → PublishJob → Bot API → Опубликовано
- `TelegramClient` — HTTP-клиент для Telegram Bot API (markdown → HTML, отправка сообщений)
- `PublishService` — сервис публикации контента с lifecycle менеджментом
- UI настроек бота: поля Bot Token и Chat ID в формах создания/редактирования каналов
- Статус-индикаторы: «✅ Опубликовано в Telegram» / «⏳ Одобрено — публикация в очереди»

### Changed
- Промпт `short_post`: длина с 300–700 на **250–500** символов, ужесточена краткость
- Промпт `longread`: длина с 1000–3000 на **1000–2500**, акцент на «аналитик, не блогер»
- `adapt_material_for_channels`: использует AI-рекомендованный формат, если он в `channel.content_formats`; платформенный дефолт — fallback
- `autopilot_rank_and_queue`: отбирает черновики ВСЕХ разрешённых форматов канала, а не только primary
- `TelegramClient.format_post`: `flash` отправляется без заголовка
- `TelegramClient.send_message`: добавлен `disable_web_page_preview` (включается для flash)
- `PublishService`: flash пропускает загрузку обложки и отключает превью ссылок
- `content_formats` канала Telegram: порядок изменён на `[short_post, longread, ...]` (был longread первым)
- `PublishJob.content_id` FK: перенаправлен с `adapted_contents` на `channel_adaptations`
- `publish_tasks.py`: вынесена бизнес-логика в `PublishService` + `TelegramClient` (было 200 строк → 55)

### Fixed
- Исправлен дефолтный формат для Telegram: теперь генерируется short_post вместо longread
- Исправлен ORM-атрибут `metadata` → `metadata_` в запросах категорий
