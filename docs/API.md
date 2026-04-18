# ContenZavod — API Reference

> Последнее обновление: 2026-04-18
> Base URL: `http://localhost:8000/api/v1`

## Аутентификация

Все эндпоинты (кроме auth и health) требуют JWT-токен:
```
Authorization: Bearer <access_token>
```

Токеновая пара (access + refresh) получается через `POST /auth/login`.

---

## Auth

### `POST /auth/register`
Регистрация нового пользователя.

| Поле | Тип | Обязательно |
|------|-----|-------------|
| email | string | ✅ |
| password | string | ✅ |
| tenant_name | string | ✅ |

**Response:** `201` → `{ access_token, refresh_token, token_type }`

### `POST /auth/login`
Вход в систему.

| Поле | Тип | Обязательно |
|------|-----|-------------|
| email | string | ✅ |
| password | string | ✅ |

**Response:** `200` → `{ access_token, refresh_token, token_type }`

### `GET /auth/me`
Текущий пользователь.

**Response:** `200` → `{ id, email, tenant_id, role, created_at }`

---

## Materials

### `GET /materials`
Список материалов с пагинацией.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| page | int | 1 | Страница |
| per_page | int | 20 | Элементов на странице (max 100) |
| status | string | — | Фильтр по статусу |
| source_id | UUID | — | Фильтр по источнику |

**Response:** `200` → `{ items: Material[], total, page, per_page, pages }`

### `GET /materials/{material_id}`
Один материал по ID.

**Response:** `200` → `Material`

### `PATCH /materials/{material_id}/status`
Обновить статус материала.

| Поле | Тип | Значения |
|------|-----|----------|
| status | string | new, classifying, classified, adapting, adapted, rejected, archived |

### `POST /materials/{material_id}/classify`
Запустить AI-классификацию для одного материала.

**Response:** `202` → `{ message, task_id }`

### `POST /materials/classify-all`
Запустить AI-классификацию для всех непроверенных.

**Response:** `202` → `{ message, count }`

---

## Sources

### `GET /sources`
Список источников.

### `GET /sources/{source_id}`
Один источник.

### `POST /sources`
Создать источник.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| name | string | ✅ | Название |
| url | string | ✅ | URL источника |
| source_type | string | ✅ | rss / website / api / social |
| schedule | string | — | Cron-выражение |
| is_active | bool | — | default: true |

### `PATCH /sources/{source_id}`
Обновить источник (частичное обновление).

### `DELETE /sources/{source_id}`
Удалить источник.

**Response:** `204 No Content`

### `POST /sources/{source_id}/scrape`
Ручной запуск парсинга источника.

**Response:** `202` → `{ message, task_id }`

---

## Projects

### `GET /projects`
Список проектов.

### `GET /projects/{project_id}`
Один проект.

### `POST /projects`
Создать проект.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| name | string | ✅ | Название проекта |
| description | string | — | Описание |
| topic_guidelines | string | — | Темы для AI-скоринга |
| target_audience | string | — | Целевая аудитория |
| is_active | bool | — | default: true |

### `PATCH /projects/{project_id}`
Обновить проект.

### `DELETE /projects/{project_id}`
Удалить проект и все связанные данные.

**Response:** `204 No Content`

### `GET /projects/{project_id}/recommendations`
Рекомендации материалов для проекта (отсортированы по AI-скорингу).

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| page | int | 1 | |
| per_page | int | 20 | |
| category | string | — | Фильтр по рубрике (из metadata) |

**Response:** `200` → `{ items: Recommendation[], total, page, per_page, pages }`

Каждая рекомендация включает:
```json
{
  "score_id": "uuid",
  "material_id": "uuid",
  "material_title": "...",
  "material_url": "...",
  "relevance_score": 8,
  "hype_score": 6,
  "explanation": "...",
  "is_recommended": true,
  "material_status": "classified",
  "source_name": "CyprusMail",
  "category": "Экономика",
  "material_summary": "...",
  "material_created_at": "..."
}
```

### `GET /projects/{project_id}/categories`
Уникальные рубрики материалов в проекте (для фильтра).

**Response:** `200` → `{ categories: string[] }`

---

## Channels

### `GET /channels`
Список каналов.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| project_id | UUID | — | Фильтр по проекту |

### `GET /channels/{channel_id}`
Один канал.

### `POST /channels`
Создать канал.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| project_id | UUID | — | Привязка к проекту |
| name | string | ✅ | Название (@ecocyprus_ru) |
| channel_type | string | ✅ | telegram / youtube / website |
| content_formats | string[] | — | ["short_post", "longread", ...] |
| tone_of_voice | string | — | Инструкции по тону |
| languages | string[] | — | ["ru"] |
| config | object | — | `{ bot_token, chat_id }` для Telegram |
| is_active | bool | — | default: true |

### `PATCH /channels/{channel_id}`
Обновить канал.

### `DELETE /channels/{channel_id}`
Удалить канал.

---

## Adaptations

### `GET /adaptations`
Список адаптаций с фильтрацией.

| Параметр | Тип | Описание |
|----------|-----|----------|
| material_id | UUID | По материалу |
| channel_id | UUID | По каналу |

### `PATCH /adaptations/{adaptation_id}`
Обновить адаптацию (статус, текст).

| Поле | Тип | Описание |
|------|-----|----------|
| status | string | draft / approved / rejected / published |
| headline | string | Заголовок |
| body | string | Текст |

> **⚡ Важно:** При `status = "approved"` автоматически создаётся `PublishJob`
> и ставится Celery-задача на публикацию в Telegram.

### `POST /adaptations/generate`
Сгенерировать адаптацию через AI.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| material_id | UUID | ✅ | Исходный материал |
| channel_id | UUID | ✅ | Целевой канал |
| content_format | string | ✅ | short_post / longread / video_script / digest |

**Response:** `202` → `{ message, task_id }`

---

## Dashboard

### `GET /dashboard/stats`
Статистика для дашборда.

**Response:** `200` →
```json
{
  "materials_total": 150,
  "materials_today": 12,
  "adaptations_total": 45,
  "published_total": 20,
  "sources_active": 5
}
```

---

## Health

### `GET /health`
Проверка состояния сервисов. Не требует аутентификации.

**Response:** `200` →
```json
{
  "status": "ok",
  "components": {
    "api": "ok",
    "database": "ok"
  }
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Невалидные данные (Pydantic validation) |
| 401 | Не аутентифицирован / невалидный токен |
| 403 | Нет доступа (tenant isolation) |
| 404 | Ресурс не найден |
| 409 | Конфликт (дубликат) |
| 422 | Ошибка валидации запроса |
| 500 | Внутренняя ошибка сервера |

Формат ошибки:
```json
{
  "detail": "Описание ошибки"
}
```
