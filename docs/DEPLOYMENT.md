# ContenZavod — Deployment Guide

> Последнее обновление: 2026-04-18

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
# Заполнить .env: DATABASE_URL, SECRET_KEY, GEMINI_API_KEY

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

| Сервис | Образ | Порт | Persistent Volume |
|--------|-------|------|-------------------|
| backend | Python 3.12 | 8000 | — |
| celery-worker | Python 3.12 | — | — |
| celery-beat | Python 3.12 | — | — |
| postgres | PostgreSQL 16 | 5432 | `cz_postgres_data` |
| redis | Redis 7 | 6379 | `cz_redis_data` |
| minio | MinIO | 9000/9001 | `cz_minio_data` |

### Полезные команды

```bash
# Логи
docker compose logs -f backend
docker compose logs -f celery-worker

# Shell в контейнере
docker compose exec backend bash
docker compose exec postgres psql -U cz_user -d contenzavod

# Перезапуск после изменений кода
docker compose restart backend celery-worker

# Полная пересборка
docker compose down && docker compose up -d --build
```

## Переменные окружения

### Обязательные

| Переменная | Пример | Описание |
|------------|--------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://cz_user:pass@postgres/contenzavod` | |
| `SECRET_KEY` | random 64 chars | JWT signing |
| `GEMINI_API_KEY` | `AIza...` | Google AI API key |

### Опциональные

| Переменная | Default | Описание |
|------------|---------|----------|
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker |
| `MINIO_ENDPOINT` | `minio:9000` | S3 storage |
| `APP_DEBUG` | `false` | SQL echo, verbose logging |
| `POSTGRES_POOL_SIZE` | `10` | Connection pool |

## Настройка Telegram

1. Создать бота через [@BotFather](https://t.me/BotFather)
2. Добавить бота как администратора в целевой канал
3. В UI: Каналы → Редактировать → ввести Bot Token и Chat ID
4. При одобрении адаптации → автоматическая публикация

## Production (TODO)

- `docker-compose.prod.yml` — production конфигурация
- Nginx reverse proxy для backend + frontend
- SSL через Let's Encrypt
- Backup PostgreSQL (pg_dump cron)
- Monitoring: Prometheus + Grafana
