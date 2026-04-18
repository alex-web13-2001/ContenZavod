# ContenZavod — Project Rules

> Этот файл — "конституция" проекта. Все разработчики и AI-ассистенты **обязаны** следовать этим правилам.

## 🌍 Язык

- **Код:** английский (переменные, функции, комментарии в коде)
- **Документация:** русский (README, CHANGELOG, ADR, docs/)
- **Коммиты:** английский (Conventional Commits)
- **Общение в чате:** русский

---

## 📁 Структура проекта

```
ContenZavod/
├── CLAUDE.md                 # ← ВЫ ЗДЕСЬ. Правила проекта
├── README.md                 # Описание проекта, запуск, стек
├── CHANGELOG.md              # Все изменения (Keep a Changelog)
├── docker-compose.yml        # Dev-окружение
├── docker-compose.prod.yml   # Production
├── .env.example              # Шаблон переменных окружения
├── Makefile                  # Команды для работы с проектом
│
├── docs/                     # Документация проекта
│   ├── ARCHITECTURE.md       # Высокоуровневая архитектура
│   ├── API.md                # API-эндпоинты (авто-генерация из OpenAPI)
│   ├── DATABASE.md           # Схема БД, отношения, индексы
│   ├── AI_PROVIDERS.md       # Подключённые AI, промпты, конфиги
│   ├── DEPLOYMENT.md         # Гайд по деплою
│   └── adr/                  # Architecture Decision Records
│       ├── README.md         # Индекс решений
│       ├── 001-tech-stack.md
│       └── ...
│
├── backend/                  # Python (FastAPI + Celery)
├── frontend/                 # Next.js 15 Admin Panel
└── infra/                    # Docker, nginx, configs
```

---

## 📝 Документация

### Обязательные документы

| Документ | Где | Когда обновлять |
|----------|-----|----------------|
| `README.md` | Корень | При изменении стека, процесса запуска |
| `CHANGELOG.md` | Корень | **Каждый значимый коммит** |
| `docs/ARCHITECTURE.md` | docs/ | При изменении архитектуры, добавлении подсистем |
| `docs/DATABASE.md` | docs/ | При каждой миграции БД |
| `docs/API.md` | docs/ | При добавлении/изменении API-эндпоинтов |
| `docs/AI_PROVIDERS.md` | docs/ | При добавлении/изменении AI-провайдеров |
| `docs/DEPLOYMENT.md` | docs/ | При изменении инфраструктуры, env-переменных |
| `docs/adr/NNN-*.md` | docs/adr/ | При каждом значимом архитектурном решении |

> **Быстрая проверка:** `make docs-check` — покажет отсутствующие и устаревшие документы.


### CHANGELOG.md — формат Keep a Changelog

Формат: [keepachangelog.com](https://keepachangelog.com/ru/1.0.0/)

```markdown
## [Unreleased]

### Added
- Описание нового функционала

### Changed
- Описание изменений в существующем функционале

### Fixed
- Описание исправлений

### Removed
- Описание удалённого функционала
```

Правила:
- **Каждый PR / значимое изменение** должен иметь запись в CHANGELOG
- Формулировки от первого лица: "Добавлена поддержка..." (не "Добавил")
- Группировать по категориям: Added, Changed, Fixed, Removed, Security
- При релизе: перенести из `[Unreleased]` в `[X.Y.Z] - YYYY-MM-DD`

### Architecture Decision Records (ADR)

Файл: `docs/adr/NNN-short-title.md`

Формат:

```markdown
# NNN. Название решения

**Статус:** accepted | proposed | deprecated | superseded by NNN
**Дата:** YYYY-MM-DD

## Контекст
Почему возникла необходимость принять это решение?

## Решение
Что мы решили сделать?

## Альтернативы
Какие варианты рассматривались и почему отклонены?

## Последствия
Плюсы и минусы принятого решения.
```

---

## 💻 Стандарты кода

### Python (Backend)

- **Форматтер:** `ruff format` (замена black)
- **Линтер:** `ruff check` (замена flake8 + isort + pyupgrade)
- **Типы:** mypy (strict mode)
- **Python:** 3.12+
- **Пакеты:** uv (НЕ pip)
- **Import Layout:** stdlib → third-party → local (ruff сортирует автоматически)

```python
# ✅ Правильно
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialResponse
```

- **Docstrings:** Google style, обязательны для:
  - Всех публичных функций
  - Всех классов
  - Всех модулей (кратко, в начале файла)

```python
class MaterialService:
    """Сервис для работы с материалами.
    
    Управляет CRUD-операциями над материалами в контексте тенанта.
    Все запросы автоматически фильтруются через PostgreSQL RLS.
    """
    
    async def create_material(self, data: MaterialCreate) -> Material:
        """Создать новый материал.
        
        Args:
            data: Данные нового материала (title, content, source_id).
            
        Returns:
            Созданный объект Material с присвоенным ID.
            
        Raises:
            DuplicateContentError: Если материал с таким content_hash уже существует.
        """
```

### TypeScript (Frontend)

- **Runtime:** Node.js 22+
- **Framework:** Next.js 15 (App Router)
- **Форматтер:** Prettier
- **Линтер:** ESLint (next/recommended)
- **Styling:** Tailwind CSS v4
- **UI:** shadcn/ui
- **State:** Zustand

---

## 🔀 Git & Commits

### Branching Strategy

```
main          ← стабильная версия, только через PR
  └── develop ← основная ветка разработки
       ├── feature/CZ-XX-short-description
       ├── fix/CZ-XX-bug-description
       └── refactor/CZ-XX-what-changed
```

### Conventional Commits

Формат: `type(scope): description`

```
feat(scraper): add generic article source with Playwright
fix(publish): resolve duplicate Telegram messages on retry
refactor(ai): extract provider registry to separate module
docs(adr): add ADR-003 for multi-tenant authentication
chore(deps): upgrade FastAPI to 0.115.x
test(services): add unit tests for material classification
ci(docker): add health checks to docker-compose
perf(db): add composite index for materials tenant+status
```

**Типы:**
| Type | Когда |
|------|-------|
| `feat` | Новый функционал |
| `fix` | Исправление бага |
| `refactor` | Рефакторинг (не меняет поведение) |
| `docs` | Документация |
| `test` | Тесты |
| `chore` | Зависимости, CI, конфиги |
| `perf` | Оптимизация производительности |
| `ci` | CI/CD |

**Правила:**
- Каждый коммит — **одно логическое изменение**
- Коммит-сообщение на **английском**
- Scope указывает подсистему: `scraper`, `ai`, `publish`, `db`, `api`, `ui`
- Body коммита (опционально): объяснение **почему**, а не **что**
- Breaking changes: `feat(api)!: rename /materials to /content`

### Когда коммитить

- **Коммит:** после завершения каждого логически завершённого изменения
- **Не копить:** не более 2-3 файлов в одном коммите (если они логически связаны)
- **Промежуточные:** допускаются `wip:` коммиты в feature-ветках, squash при мерже

---

## 🏗️ Архитектурные правила

### Слои приложения (Backend)

```
API Routes (api/)        ← Тонкие контроллеры, только валидация + вызов сервиса
     ↓
Services (services/)     ← Бизнес-логика, оркестрация
     ↓
Models (models/)         ← ORM, schema definition
     ↓
Database (database.py)   ← Connection pool, session management
```

- **Запрещено:** обращаться к БД напрямую из API routes
- **Запрещено:** класть бизнес-логику в Celery tasks (tasks вызывают services)
- **Запрещено:** хардкодить AI-промпты (только через `prompt_configs` в БД или файлы `ai/prompts/`)

### Добавление нового AI-провайдера

1. Создать файл `ai/providers/new_provider.py`
2. Реализовать интерфейс `BaseAIProvider` (или `TextAIProvider` / `ImageAIProvider` / `VideoAIProvider`)
3. Зарегистрировать в `ai/registry.py`
4. Добавить конфиг в `.env.example`
5. Обновить `docs/AI_PROVIDERS.md`
6. Создать ADR если это принципиально новый провайдер

### Добавление нового источника парсинга

1. Создать файл `scraper/sources/my_source.py`
2. Наследовать `BaseSource`
3. Реализовать `scrape()` → `list[RawMaterial]`
4. Зарегистрировать в конфиге (БД)

### Добавление нового канала публикации

1. Создать файл `publishing/channels/my_channel.py`
2. Наследовать `BaseChannelPublisher`
3. Реализовать `publish()`, `check_status()`
4. Зарегистрировать в `publishing/registry.py`
5. Обновить `docs/ARCHITECTURE.md`

### Миграции БД

- **Alembic autogenerate:** `make db-migrate msg="add field X to materials"`
- **Ревью:** Каждую миграцию проверять перед применением
- **Обновлять:** `docs/DATABASE.md` после каждой миграции
- **JSONB:** Для динамических/нестабильных полей использовать JSONB вместо ALTER TABLE

---

## 🧪 Тестирование

- **Unit tests:** Для сервисов и AI-провайдеров
- **Integration tests:** Для API endpoints
- **Файлы:** `tests/test_<module>/test_<function>.py`
- **Запуск:** `make test`
- **Coverage:** Стремится к 80%+ для services/

---

## 🚀 Makefile-команды

Все часто используемые команды должны быть в `Makefile`:

```makefile
make up            # Поднять все сервисы (docker-compose up)
make down          # Остановить
make logs          # Логи всех сервисов
make shell         # Bash в backend контейнере
make db-migrate    # Создать миграцию
make db-upgrade    # Применить миграции
make test          # Запустить тесты
make lint          # Линтинг (ruff)
make format        # Форматирование (ruff format)
```

---

## ⚠️ Что нельзя делать

1. **Не коммитить секреты:** `.env` в `.gitignore`, используй `.env.example`
2. **Не хардкодить:** URL, ключи, промпты — всё через конфиг
3. **Не менять public API** без обновления `docs/API.md`
4. **Не менять схему БД** без миграции Alembic и обновления `docs/DATABASE.md`
5. **Не добавлять зависимости** без обоснования (предпочтение stdlib)
6. **Не класть бизнес-логику** в API routes или Celery tasks
