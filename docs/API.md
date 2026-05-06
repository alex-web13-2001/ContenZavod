# ContenZavod — API Reference

> Последнее обновление: 2026-05-06
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

### `POST /auth/refresh`
Обновление JWT-токена.

| Поле | Тип | Обязательно |
|------|-----|-------------|
| refresh_token | string | ✅ |

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

## Video Digests 🎬

AI-видеодайджесты через ReVid API v3. Полный цикл: создание → генерация скрипта → рендер видео.

### `GET /digests?project_id={uuid}`
Список дайджестов проекта.

**Response:** `200` → `VideoDigest[]`

### `GET /digests/{digest_id}`
Один дайджест. **Автоматически проверяет статус** ReVid при `revid_status == "rendering"`.

**Response:** `200` → `VideoDigest`

> **⚡ Auto-polling:** Если дайджест в статусе `rendering`, GET-запрос
> автоматически опрашивает ReVid API, обновляет `video_url` и `revid_status`
> в БД, и возвращает актуальные данные.

### `POST /digests`
Создать дайджест.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| project_id | UUID | ✅ | Проект |
| title | string | ✅ | «Дайджест — 5 мая 2026 г.» |
| material_ids | UUID[] | ✅ | Массив ID материалов |
| language | string | — | "ru" (default) |
| config | object | — | render_config (см. ниже) |

### `PATCH /digests/{digest_id}`
Обновить дайджест (скрипт, заголовок).

| Поле | Тип | Описание |
|------|-----|----------|
| title | string | Заголовок |
| script_text | string | Текст сценария |
| config | object | render_config |

### `DELETE /digests/{digest_id}`
Удалить дайджест.

**Response:** `204 No Content`

### `POST /digests/{digest_id}/generate-script`
Запустить AI-генерацию сценария из выбранных материалов.

**Response:** `202` → `{ message, task_id }`

Статус переходит: `draft` → `script_generating` → `script_ready`

### `POST /digests/{digest_id}/render`
Запустить рендер видео через ReVid API.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| render_config | object | — | Настройки рендера |

**render_config structure:**
```json
{
  "mediaType": "custom",          // custom | stock-video | ai-image | ai-video | moving-image | video
  "mediaDensity": "medium",       // low | medium | high
  "mediaImageModel": "good",      // good | best
  "videoModel": "base",           // base | pro
  "removeBackground": true,
  "avatarUrl": "https://cdn.revid.ai/uploads/xxx.png",
  "voiceId": "Qvbf0AoA7UZSgJUp8Ba5",
  "voiceSpeed": 1,
  "captionsEnabled": true,
  "captionsAnimation": "word",    // word | sentence | line
  "aspectRatio": "9:16",          // 9:16 | 16:9 | 1:1
  "quality": "pro",               // base | pro
  "providedMedia": [
    {"url": "https://...", "title": "описание сцены", "type": "image"}
  ]
}
```

**Response:** `202` → `{ message, task_id }`

Статус переходит: `script_ready` → `rendering` → `ready`

> **Нормализация media type:** Бэкенд автоматически маппит невалидные значения:
> `"provided"` → `"custom"`, `"stock-image"` → `"moving-image"`

### `GET /digests/{digest_id}/credits`
Проверить баланс кредитов ReVid.

**Response:** `200` → `{ total_credits, used_credits, remaining }`

---

## Autopilot 🤖

Автоматическая AI-ранжированная публикация контента.

### `GET /autopilot/queue?project_id={uuid}`
Очередь автопилота для проекта.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| project_id | UUID | ✅ | Проект |
| status | string | — | Фильтр: queued / published / skipped / expired |
| page | int | 1 | |
| per_page | int | 50 | |

**Response:** `200` → `{ items: AutopilotQueueItem[], total }`

### `PATCH /autopilot/queue/{item_id}`
Обновить элемент очереди (одобрить/отклонить в shadow mode).

| Поле | Тип | Описание |
|------|-----|----------|
| status | string | approved / rejected / skipped |

### `DELETE /autopilot/queue/{item_id}`
Удалить элемент из очереди.

### `GET /autopilot/config?project_id={uuid}`
Конфигурация автопилота для проекта.

### `PATCH /autopilot/config`
Обновить конфигурацию автопилота.

| Поле | Тип | Описание |
|------|-----|----------|
| project_id | UUID | ✅ |
| enabled | bool | Включить/выключить |
| shadow_mode | bool | Требовать одобрения |
| max_posts_per_day | int | Лимит публикаций |
| language_limits | object | `{ "ru": 3, "en": 2 }` |

### `POST /autopilot/trigger`
Принудительный запуск цикла ранжирования.

| Поле | Тип | Описание |
|------|-----|----------|
| project_id | UUID | ✅ |

**Response:** `202` → `{ message }`

---

## Files

### `POST /files/upload`
Загрузка файлов в MinIO.

**Content-Type:** `multipart/form-data`

**Response:** `200` → `{ url, filename, size }`

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
