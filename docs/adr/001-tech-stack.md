# 001. Выбор технологического стека

**Статус:** accepted
**Дата:** 2026-04-15

## Контекст

Проект ContenZavod — мультитенантная SaaS-платформа для автоматизации контент-менеджмента. Требуется стек, который:
- Поддерживает высокую нагрузку (500+ публикаций/день)
- Позволяет быстро подключать новые AI-провайдеры
- Масштабируется горизонтально
- Использует один язык для всего бэкенда (парсер, AI, API, workers)

## Решение

### Backend: Python 3.12+ (FastAPI + Celery)
- **FastAPI** — async API, автодокументация, Pydantic v2
- **Celery + Redis** — распределённая очередь задач
- **SQLAlchemy 2.0** — async ORM
- **uv** — менеджер пакетов (10-100x быстрее pip)
- **Playwright** — браузерный парсинг

### Frontend: Next.js 15 (React)
- **App Router** — modern React patterns
- **shadcn/ui + Tailwind v4** — кастомизируемые компоненты
- **Zustand** — лёгкий state management

### Database: PostgreSQL 16
- RLS для мультитенантности
- JSONB для динамических данных
- Mature ecosystem, расширения

### Infrastructure: Docker Compose → VPS
- Простой старт
- Миграция на Kubernetes при необходимости

## Альтернативы

| Вариант | Причина отказа |
|---------|---------------|
| Node.js для бэкенда | Два языка (Python всё равно нужен для Playwright + AI SDK) |
| Django | Монолитный, FastAPI быстрее и гибче для API-first |
| MongoDB | Нет RLS, слабые транзакции, PostgreSQL JSONB покрывает потребности |
| RabbitMQ | Redis уже нужен для кэша, проще один инструмент |
| pip/poetry | uv кратно быстрее, нативный lockfile |

## Последствия

**Плюсы:**
- Один язык (Python) для всего бэкенда — проще поддержка
- FastAPI + Pydantic — строгая типизация, автодокументация
- Celery — проверенное решение для task queues, горизонтальное масштабирование

**Минусы:**
- Python не самый быстрый runtime (но bottleneck в I/O, а не CPU)
- Next.js + FastAPI — два отдельных деплоя (но это стандарт для SPA + API)
