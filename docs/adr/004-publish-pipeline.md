# 004. Telegram Publish Pipeline

**Статус:** accepted
**Дата:** 2026-04-17

## Контекст

Пользователи модерируют AI-адаптации в дашборде (одобряют или отклоняют). При одобрении контент должен автоматически публиковаться в целевой канал (Telegram). Нужен надёжный механизм с идемпотентностью и retry.

## Решение

Реализовали трёхуровневую архитектуру публикации:

1. **Trigger:** `PATCH /adaptations/{id}` с `status = "approved"` → создаёт `PublishJob` + ставит Celery task
2. **Service:** `PublishService` (app/services/publish_service.py) — lifecycle менеджмент: load → validate → format → send → update
3. **Client:** `TelegramClient` (app/services/telegram_client.py) — HTTP-клиент для Bot API (markdown → HTML + send)
4. **Task:** `publish_to_telegram` (workers/publish_tasks.py) — тонкий Celery wrapper (retry, session management)

### Идемпотентность

`PublishJob.idempotency_key = f"{adaptation_id}:{channel_id}:{format}"` — предотвращает повторную публикацию при ретраях.

### Хранение credentials

Bot token и chat_id хранятся в `Channel.config` (JSONB):
```json
{"bot_token": "123:ABC...", "chat_id": "@ecocyprus_ru"}
```

## Альтернативы

1. **aiogram** — была в первоначальном плане. Отклонено: aiogram — async framework для ботов с хэндлерами, мы делаем одностороннюю отправку. `httpx` + Bot API проще и не тянет зависимости.
2. **Webhook-based** (через API endpoint вместо Celery task) — отклонено: нет retry, нет rate limiting, блокирует HTTP-ответ.
3. **Scheduled publishing** (отложенные посты) — не реализовано сейчас, но `PublishJob.scheduled_at` уже в схеме для будущего.

## Последствия

**Плюсы:**
- Полная развязка UI и публикации (async через Celery)
- `PublishService` тестируем без Celery
- `TelegramClient` переиспользуем для других задач (уведомления, алерты)
- Retry с exponential backoff (29→ 429, 5xx)

**Минусы:**
- Нет real-time статуса публикации в UI (нужен polling или WebSocket)
- Bot token хранится в plain text в JSONB (нужна encryption at rest)
