# ContenZavod — Deployment Guide

> Последнее обновление: 2026-05-06

## Локальная разработка

### Требования
- Docker & Docker Compose v2
- Node.js 22+ (для frontend)
- Make (опционально)

### Запуск

```bash
# 1. Склонировать и настроить
git clone <repo-url> && cd ContenZavod
cp .env.example .env
# Заполнить .env: DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY

# 2. Бэкенд (Docker)
docker compose up -d --build

# 3. Миграции
docker compose exec backend alembic upgrade head

# 4. Фронтенд (локально)
cd frontend && npm install && npm run dev

# 5. Проверить
curl http://localhost:8000/api/v1/health
open http://localhost:3000
```

### Docker Compose сервисы

| Сервис | Образ | Порт (host:container) | Persistent Volume |
|--------|-------|----------------------|-------------------|
| backend | Python 3.12 | 8010:8000 | — |
| celery-worker | Python 3.12 | — | — |
| celery-beat | Python 3.12 | — | — |
| postgres | PostgreSQL 16 | 5435:5432 | `postgres_data` |
| redis | Redis 7 | 6381:6379 | `redis_data` |
| minio | MinIO | 9002:9000, 9003:9001 | `minio_data` |

### Полезные команды

```bash
# Логи
make logs-backend        # или: docker compose logs -f backend
make logs-worker         # или: docker compose logs -f celery-worker

# Shell в контейнере
make shell               # bash в backend
make shell-db            # psql в PostgreSQL
make shell-redis         # redis-cli

# Миграции
make db-migrate msg="add new table"   # Создать
make db-upgrade                        # Применить
make db-downgrade                      # Откатить

# Качество кода
make lint                # ruff check
make format              # ruff format
make test                # pytest

# Перезапуск после изменений кода
docker compose restart backend celery-worker

# Полная пересборка
docker compose down && docker compose up -d --build

# Проверка документации
make docs-check
```

## Переменные окружения

### Обязательные

| Переменная | Пример | Описание |
|------------|--------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://cz_user:pass@postgres:5432/contenzavod` | Подключение к БД |
| `JWT_SECRET_KEY` | random 64 chars | JWT signing key |
| `GEMINI_API_KEY` | `AIza...` | Google Gemini API |

### AI / Video

| Переменная | Default | Описание |
|------------|---------|----------|
| `KIE_API_KEY` | — | KIE.ai (Claude Haiku 4.5 fallback) |
| `KLING_ACCESS_KEY` | — | Kling video/image generation |
| `KLING_SECRET_KEY` | — | Kling secret |
| `REVID_API_KEY` | — | ReVid v3 видео-рендер |
| `REVID_VOICE_ID` | `Qvbf0AoA7UZSgJUp8Ba5` | ID голоса ElevenLabs |
| `REVID_AVATAR_URL` | — | URL аватара для видео |
| `REVID_ASPECT_RATIO` | `9:16` | Соотношение сторон |
| `REVID_QUALITY` | `pro` | Качество видео |

### Инфраструктура

| Переменная | Default | Описание |
|------------|---------|----------|
| `REDIS_URL` | `redis://redis:6379/0` | Cache |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery results |
| `MINIO_ENDPOINT` | `minio:9000` | Object storage |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO login |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO password |

### Приложение

| Переменная | Default | Описание |
|------------|---------|----------|
| `APP_ENV` | `development` | dev / production |
| `APP_DEBUG` | `true` | SQL echo, verbose logs |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `["*"]` | Разрешённые origins |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT TTL (24h) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh TTL |
| `POSTGRES_POOL_SIZE` | `20` | Connection pool |

## Настройка Telegram

1. Создать бота через [@BotFather](https://t.me/BotFather)
2. Добавить бота как администратора в целевой канал
3. В UI: Каналы → Редактировать → ввести Bot Token и Chat ID
4. При одобрении адаптации → автоматическая публикация

## Настройка ReVid (видео-дайджесты)

1. Получить API ключ на [revid.ai](https://revid.ai)
2. Добавить `REVID_API_KEY` в `.env`
3. Загрузить аватар через ReVid CDN или `POST /files/upload`
4. Указать `REVID_AVATAR_URL` или настроить в UI дайджестов
5. Проверить кредиты: `GET /api/v1/digests/{id}/credits`

## Celery Workers

### Очереди
Worker слушает 5 очередей одновременно:
```
scrape_queue, ai_queue, publish_queue, media_queue, analytics_queue
```

### Конкурентность
- Текущая: `--concurrency=8`
- Рекомендации для production: `--concurrency=16` (для I/O-bound AI tasks)

### Beat Schedule
Celery Beat запускает 8 периодических задач:

| Задача | Интервал |
|--------|---------|
| Парсинг источников | Каждые 2 часа |
| Классификация | Каждые 30 мин |
| Скоринг для проектов | Каждые 15 мин |
| Синхронизация статистики TG | Каждые 30 мин |
| Автопилот: ранжирование | Каждые 15 мин |
| Автопилот: публикация | Каждые 5 мин |
| Автопилот: retry обложек | Каждые 10 мин |
| Автопилот: expire stale | Каждый час |

## Production (TODO)

- `docker-compose.prod.yml` — production конфигурация
- Nginx reverse proxy для backend + frontend
- SSL через Let's Encrypt
- Backup PostgreSQL (pg_dump cron)
- Monitoring: Prometheus + Grafana
- Flower для мониторинга Celery workers
