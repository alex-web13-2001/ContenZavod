# 005. Channel Adaptations — новая модель адаптаций

**Статус:** accepted
**Дата:** 2026-04-16

## Контекст

Первоначальная модель `adapted_contents` привязывала адаптацию к `target_channel_type` (string: "telegram", "website"). Это не позволяло:
- Генерировать несколько форматов для одного канала (short_post + longread)
- Привязывать адаптацию к конкретному каналу (а не типу)
- Отслеживать статус публикации для конкретной пары (канал + формат)

## Решение

Создана таблица `channel_adaptations` — привязка к конкретному `channel_id` + `content_format`:

```
channel_adaptations
├── channel_id FK → channels     (конкретный канал, а не тип)
├── material_id FK → raw_materials
├── content_format VARCHAR       (short_post / longread / video_script / digest)
├── headline VARCHAR
├── body TEXT
├── metadata JSONB               (hashtags, hooks, структура)
└── status VARCHAR               (draft → approved → published)
```

### On-demand генерация

API `POST /adaptations/generate` позволяет генерировать любой формат для любого канала:
```json
{
  "material_id": "...",
  "channel_id": "...",
  "content_format": "longread"
}
```

### Умный дефолт формата

При первой адаптации формат выбирается по типу канала:
- `telegram` → `short_post`
- `website` → `longread`
- `youtube` → `video_script`

## Альтернативы

1. **Расширить `adapted_contents`** добавив `channel_id` — отклонено: таблица уже используется, ломает существующие FK.
2. **Один формат на адаптацию** — отклонено: пользователи хотят видеть один материал в разных форматах.

## Последствия

**Плюсы:**
- Гибкая генерация: любой формат для любого канала
- Прямая связь адаптация → канал → публикация
- `PublishJob.content_id → channel_adaptations` — clear ownership

**Минусы:**
- `adapted_contents` стала legacy-таблицей (ещё не удалена)
- Два места хранения адаптаций до полной миграции
