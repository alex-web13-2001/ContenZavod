# Changelog

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Версионирование следует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added
- Поддержка многоязычных источников: классификатор теперь читает статьи на любом языке (EN/EL и др.), translates `summary_ru/summary_en` напрямую с источника. Tags и `key_entities` всегда нормализуются в латиницу для cross-lingual дедупа.
- Жёсткая политика свежести в автопилоте (ADR-007): новый параметр `autopilot_config.max_material_age_hours` (default 24h) физически отсекает старые материалы от очереди — как в `rank_and_queue`, так и в lazy-adapt
- Периодическая задача `autopilot_archive_stale_drafts` (каждый час в `:30`) — переводит черновики со старыми материалами в `status='archived'`
- API: `POST /projects/{id}/autopilot/enqueue` — ручная постановка материала в очередь автопилота из таба «Рекомендации»
- Celery task `adapt_and_enqueue_autopilot` — sync-адаптация (если черновика ещё нет) + создание `AutopilotQueueItem` со стратегией `express`
- UI: кнопка «⚡ В автопилот» на карточке inbox-материала + модалка с выбором канала и формата (с пометкой «AI рекомендует» при совпадении с `suggested_format`)
- UI: дата материала в карточке очереди автопилота — цвет зависит от свежести (<6h зелёный, <24h серый, иначе жёлтый), с тултипом «когда опубликован источником»
- UI: инпут «Свежесть, часов» в настройках канала автопилота
- ADR-007: переход от soft freshness floor к жёсткому hard cutoff
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
- AI-классификатор: основным провайдером сделан Claude Haiku, Gemini переведён в фоллбэк — `gemini-3.1-pro` на KIE перестал вызывать tool (отвечает прозой), и лидирование Gemini тратило холостой вызов перед каждым фоллбэком на Claude.
- Обложки из источника: одно изображение теперь используется максимум на одном посте. `_fetch_source_image` отклоняет SHA, уже привязанный к другому материалу того же источника (`_load_used_cover_hashes`, заменил порог `DEFAULT_IMAGE_THRESHOLD`). Раньше общее/рубричное/wire-фото попадало обложкой на 3+ разных новостей.
- `autopilot_rank_and_queue` и lazy-adapt: добавлен JOIN с `raw_materials` и фильтр по `scraped_at >= now() - max_material_age_hours`
- Порог семантического дедупа в `autopilot_rank_and_queue` ослаблен с `uniqueness < 2.0` (similarity > 0.8) на `< 4.0` (similarity > 0.6)
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
- **Задвоение обложек закрыто на уровне URL (SHA-дедуп не работал).** Издания (Philenews, Cyprus Mail) отдают одно фото с разными байтами при каждом запросе (CDN-ресайз/перекодирование) — наблюдалось до 22–27 разных SHA на один `source_url`, поэтому дедуп по SHA-256 в принципе не ловил повтор, и одна картинка попадала обложкой на несколько разных новостей. Введён ключ дедупа — **нормализованный `source_url`** (новый модуль `workers/image_dedup.py`: убирает WordPress-суффиксы `-WxH`/`-scaled`, CDN-сегмент `/image/sNNNx/`, query-кэшбастеры). Применён на двух уровнях: (1) при парсинге — `_fetch_source_image` отклоняет уже использованный URL до скачивания (`_load_used_cover_urls`); (2) в автопилоте — все три cover-дедупа (`rank_and_queue` enqueue/in-cycle + `publish_next`) переведены с SHA на нормализованный URL. Проверено: варианты схлопываются в один ключ, 0 ложных слияний на 400 реальных URL.
- **Скоринг (relevance/hype) укреплён — той же причиной, что и классификатор.** `_evaluate_via_gemini` не форсировал вызов tool'а и шёл Gemini-first, из-за чего `gemini-3.1-pro` отвечал прозой (`ai.evaluate.no_tool_calls`), скоринг падал и материалы зависали в статусе `classified` (на момент фикса — 279 шт., старейшие с 14 апреля). Добавлен `tool_choice` на обоих провайдерах + Claude-first.
- **Кросс-источниковый дедуп.** Jaccard по entities не ловил одну историю из разных изданий/языков (наблюдался Jaccard ≈ 0.25 при дублях — теракт в Ларнаке EN/GR, спасение орла и т.п.). Добавлено правило по числу общих *специфичных* сущностей (≥3 и ≥30% меньшего набора, со стоп-листом вездесущих гео/издателей) → форсирует `uniqueness=3.0`. Проверено на 30-дневной выборке: ловит все 12 реальных дублей, 0 ложных срабатываний.
- **Классификатор укреплён (причина дублей постов).** С 25 мая модели KIE (Gemini 3.1 Pro, Claude Haiku) перестали вызывать инструмент `classify_article` и отвечали прозой — `key_entities` приходил пустым, `semantic_fingerprint` не заполнялся, и семантический дедуп молча отключался (`uniqueness` по умолчанию = 10.0), из-за чего одинаковые новости публиковались повторно. Добавлен `tool_choice` (форсированный вызов tool'а) для обоих провайдеров + валидация `_validate_classification`: результат с пустыми `key_entities`/`summary_ru` отклоняется → фоллбэк на Claude → Celery-ретрай. Устраняет ~40% холостых `no_tool_result` и дубли постов.
- Семантический дедуп (`compute_uniqueness_score`) сравнивал кандидата только со статусами `classified/adapting/adapted/published`, пропуская доминирующий `evaluated` — теперь `evaluated` включён в пул сравнения.
- Удалён soft `freshness floor = 5.0` в `_compute_freshness` — из-за него старые материалы с высоким rel/hype прорывались в очередь публикации (см. ADR-007). Теперь просроченные по TTL получают 0 и естественно отсекаются.
- Исправлен дефолтный формат для Telegram: теперь генерируется short_post вместо longread
- Исправлен ORM-атрибут `metadata` → `metadata_` в запросах категорий
