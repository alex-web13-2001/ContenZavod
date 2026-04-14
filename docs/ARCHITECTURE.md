# ContenZavod — Архитектура

> Последнее обновление: 2026-04-15

## Обзор

ContenZavod — мультитенантная SaaS-платформа полного цикла контент-менеджмента:
парсинг → AI-классификация → адаптация → мультиканальная публикация → аналитика → AI-оптимизация.

## Стек технологий

### Backend
| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Runtime | Python | 3.12+ |
| Package Manager | uv | latest |
| API | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | latest |
| Task Queue | Celery | 5.4+ |
| Broker/Cache | Redis | 7+ |
| Database | PostgreSQL | 16+ |
| Scraper | Playwright | latest |
| Telegram | aiogram | 3.x |

### Frontend
| Компонент | Технология |
|-----------|-----------|
| Framework | Next.js 15 (App Router) |
| Styling | Tailwind CSS v4 |
| UI Kit | shadcn/ui |
| State | Zustand |
| Charts | Recharts |

### AI Providers (pluggable)
| Задача | Провайдер | Модель |
|--------|----------|--------|
| Текст | Google | Gemini 2.5 Flash |
| Изображения | Google | Nano Banana 2 (Gemini 3.1 Flash Image) |
| Видео | Kling | Kling 3.0 |

## Высокоуровневая архитектура

```
┌──────────────────────────────────────────────────────────┐
│                    Admin Panel (Next.js 15)               │
│              Tenant Switcher / Dashboard / CRUD           │
└──────────────────────┬───────────────────────────────────┘
                       │ REST API
┌──────────────────────▼───────────────────────────────────┐
│                  FastAPI (Backend)                         │
│     ┌─────────┬──────────┬──────────┬──────────────┐     │
│     │ Auth    │ Materials │ Publish  │ Analytics    │     │
│     │ (JWT)   │ CRUD     │ Queue    │ Stats        │     │
│     └─────────┴──────────┴──────────┴──────────────┘     │
│                       │                                    │
│     ┌─────────────────▼─────────────────────────────┐    │
│     │          Service Layer                         │    │
│     │  MaterialService / ClassifyService / etc.      │    │
│     └─────────────────┬─────────────────────────────┘    │
└───────────────────────┼──────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ Redis      │ │ MinIO / S3   │
│ (RLS)        │ │ (Queue +   │ │ (Media)      │
│              │ │  Cache)    │ │              │
└──────────────┘ └─────┬──────┘ └──────────────┘
                       │
                ┌──────▼───────┐
                │ Celery       │
                │ Workers      │
                │ ┌──────────┐ │
                │ │ scrape   │ │
                │ │ ai       │ │
                │ │ publish  │ │
                │ │ media    │ │
                │ │ analytics│ │
                │ └──────────┘ │
                └──────────────┘
```

## Мультитенантность

- **Модель:** Shared Database + Row Level Security
- **Ключ:** `tenant_id UUID` в каждой таблице
- **Изоляция:** PostgreSQL RLS policies
- **Context:** `set_config('app.current_tenant', ...)` через middleware

## Потоки данных

### 1. Парсинг → Классификация → Адаптация
```
Celery Beat (cron) → scrape_task → БД (raw_material, status=new)
                                         ↓
                   classify_task ← Celery (ai_queue)
                   Gemini Flash → БД (ai_result + material.status=classified)
                                         ↓
                   adapt_task ← Celery (ai_queue)
                   Gemini Flash → БД (adapted_content, status=draft)
```

### 2. Публикация
```
Модератор одобряет → adapted_content.status=approved
                              ↓
                   publish_task ← Celery (publish_queue)
                   ├── Telegram (aiogram)
                   ├── Website (CMS API)  
                   └── YouTube (Data API v3)
                              ↓
                   БД (publish_job.status=published)
```

## Подробная документация

- [DATABASE.md](./DATABASE.md) — Схема БД
- [AI_PROVIDERS.md](./AI_PROVIDERS.md) — AI-провайдеры
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Деплой
- [adr/](./adr/) — Архитектурные решения
