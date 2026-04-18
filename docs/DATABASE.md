# ContenZavod — Схема базы данных

> Последнее обновление: 2026-04-18
> Миграции: Alembic (backend/migrations/)

## Общие принципы

- Все таблицы содержат `tenant_id` (кроме `tenants` и `users`)
- PostgreSQL Row Level Security изолирует данные тенантов
- UUID первичные ключи (`gen_random_uuid()`)
- Timestamps: `created_at`, `updated_at` (timestamptz)
- JSONB для динамических/нестабильных полей

## Таблицы

### tenants
Проекты/клиенты. Единица изоляции данных.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| name | VARCHAR(255) | "Тех-новости" |
| slug | VARCHAR(100) UK | "tech-news" |
| owner_id | UUID FK → users | |
| plan | VARCHAR(50) | free / pro / enterprise |
| ai_config | JSONB | Привязка AI-провайдеров по capability |
| settings | JSONB | Общие настройки |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

### users
Пользователи системы.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK → tenants | |
| email | VARCHAR UK | |
| password_hash | VARCHAR | |
| role | VARCHAR(50) | owner / admin / editor / viewer |
| created_at | TIMESTAMPTZ | |

### sources
Источники для парсинга.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| name | VARCHAR(255) | |
| url | TEXT | |
| source_type | VARCHAR(50) | rss / website / api / social |
| scraper_config | JSONB | selectors, auth, proxy |
| schedule | VARCHAR(100) | cron expression |
| is_active | BOOLEAN | |
| last_scraped_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### raw_materials
Собранные сырые материалы.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| source_id | UUID FK → sources | |
| original_url | TEXT UK | |
| title | VARCHAR(500) | |
| content_text | TEXT | plain text |
| content_html | TEXT | original HTML |
| metadata | JSONB | author, date, tags, language |
| content_hash | VARCHAR(64) UK | SHA-256, дедупликация |
| status | VARCHAR(50) | new → classifying → classified → adapting → adapted → rejected → archived |
| word_count | INTEGER | |
| scraped_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### ai_results
Результаты работы AI (классификация, адаптация, анализ).

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| material_id | UUID FK → raw_materials | |
| prompt_config_id | UUID FK → prompt_configs | |
| task_type | VARCHAR(50) | classify / adapt / analyze |
| provider_name | VARCHAR(100) | gemini_flash / ... |
| input_data | JSONB | отправленное в AI |
| output_data | JSONB | полученное от AI |
| tokens_used | INTEGER | |
| cost_usd | NUMERIC(10,6) | |
| latency_ms | INTEGER | |
| created_at | TIMESTAMPTZ | |

### projects
Тематические контент-проекты.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| name | VARCHAR(255) | «EcoCyprus», «TechPulse» |
| description | TEXT | Описание проекта |
| topic_guidelines | TEXT | Темы для AI-скоринга |
| target_audience | TEXT | Целевая аудитория |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

### material_project_scores
AI-скоринг материалов для проектов.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| material_id | UUID FK → raw_materials | |
| project_id | UUID FK → projects | |
| relevance_score | INTEGER | 0-10, релевантность теме |
| hype_score | INTEGER | 0-10, вирусный потенциал |
| is_recommended | BOOLEAN | true если оба >= 6 |
| explanation | TEXT | Обоснование от AI |
| created_at | TIMESTAMPTZ | |
| **UK** | (material_id, project_id) | Один скор на пару |

### material_channel_scores
AI-скоринг материалов для каналов (legacy, заменён на project_scores).

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| material_id | UUID FK → raw_materials | |
| channel_id | UUID FK → channels | |
| relevance_score | INTEGER | 0-10 |
| virality_score | INTEGER | 0-10 |
| is_recommended | BOOLEAN | |
| explanation | TEXT | |
| created_at | TIMESTAMPTZ | |

### adapted_contents
Адаптированный контент, готовый к публикации.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| material_id | UUID FK → raw_materials | |
| ai_result_id | UUID FK → ai_results | |
| target_channel_type | VARCHAR(50) | telegram / website / youtube / shorts |
| title | VARCHAR(500) | |
| body | TEXT | |
| extra | JSONB | hashtags, cta, seo_keywords, video_script |
| status | VARCHAR(50) | draft / review / approved / rejected / published |
| approved_by | UUID FK → users | |
| approved_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### media_assets
Сгенерированные медиа-файлы (изображения, видео).

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| content_id | UUID FK → adapted_contents | |
| asset_type | VARCHAR(50) | image / video / thumbnail |
| provider_name | VARCHAR(100) | nano_banana / kling_v3 |
| provider_job_id | VARCHAR(255) | для async jobs |
| prompt | TEXT | |
| status | VARCHAR(50) | pending / generating / ready / failed |
| storage_url | TEXT | |
| mime_type | VARCHAR(100) | |
| file_size_bytes | BIGINT | |
| duration_seconds | INTEGER | для видео |
| created_at | TIMESTAMPTZ | |

### channels
Каналы публикации (Telegram, YouTube, сайты).

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| project_id | UUID FK → projects | nullable |
| name | VARCHAR(255) | |
| channel_type | VARCHAR(50) | telegram / youtube / website |
| content_formats | JSONB | ["short_post", "longread", ...] |
| tone_of_voice | TEXT | Инструкции по тону |
| languages | JSONB | ["ru", "en"] |
| config | JSONB | bot_token, chat_id (Telegram) |
| posting_rules | JSONB | schedule, max per day |
| editorial_rules | TEXT | Редакционные правила |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

### channel_adaptations
Адаптации контента под конкретный канал и формат.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| channel_id | UUID FK → channels | |
| material_id | UUID FK → raw_materials | |
| content_format | VARCHAR(50) | short_post / longread / video_script / digest |
| headline | VARCHAR(500) | Заголовок адаптации |
| body | TEXT | Основной текст |
| metadata | JSONB | hashtags, hooks, структура |
| status | VARCHAR(50) | draft / approved / rejected / published |
| created_at | TIMESTAMPTZ | |

### publish_jobs
Задания на публикацию.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| content_id | UUID FK → channel_adaptations | |
| channel_id | UUID FK → channels | |
| media_asset_id | UUID FK → media_assets | nullable |
| status | VARCHAR(50) | scheduled / queued / publishing / published / failed / cancelled |
| scheduled_at | TIMESTAMPTZ | |
| published_at | TIMESTAMPTZ | |
| platform_post_id | VARCHAR(255) | msg_id, video_id |
| platform_response | JSONB | |
| retry_count | INTEGER | default 0 |
| idempotency_key | VARCHAR(255) UK | |
| created_at | TIMESTAMPTZ | |

### publication_metrics
Метрики опубликованного контента.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| publish_job_id | UUID FK → publish_jobs | |
| metric_name | VARCHAR(100) | views / likes / comments / shares / ctr |
| value | NUMERIC | |
| snapshot_period | VARCHAR(20) | 1h / 6h / 24h / 7d / 30d |
| collected_at | TIMESTAMPTZ | |

### prompt_configs
Конфигурации и версии AI-промптов.

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| task_type | VARCHAR(50) | classify / adapt_telegram / adapt_website / strategy |
| name | VARCHAR(255) | |
| version | INTEGER | |
| system_prompt | TEXT | |
| user_prompt_template | TEXT | с {placeholders} |
| parameters | JSONB | temperature, max_tokens |
| is_active | BOOLEAN | |
| performance_stats | JSONB | |
| created_at | TIMESTAMPTZ | |

## Ключевые индексы

```sql
-- Материалы
CREATE INDEX idx_materials_tenant_status ON raw_materials(tenant_id, status);
CREATE INDEX idx_materials_tenant_created ON raw_materials(tenant_id, created_at DESC);
CREATE INDEX idx_materials_content_hash ON raw_materials(content_hash);

-- Публикации
CREATE INDEX idx_publish_jobs_tenant_status ON publish_jobs(tenant_id, status);
CREATE INDEX idx_publish_jobs_scheduled ON publish_jobs(scheduled_at) WHERE status = 'scheduled';

-- Метрики
CREATE INDEX idx_metrics_pub_period ON publication_metrics(publish_job_id, snapshot_period);
```

## Миграции

Команды:
```bash
make db-migrate msg="описание изменения"   # Создать миграцию
make db-upgrade                             # Применить
make db-downgrade                           # Откатить
```
