.PHONY: help up down logs build shell db-migrate db-upgrade db-downgrade db-history test lint format clean docs-check docs-api

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker ────────────────────────────────────────

up: ## Start all services
	docker compose up -d

up-build: ## Build and start all services
	docker compose up -d --build

down: ## Stop all services
	docker compose down

logs: ## Show logs (all services)
	docker compose logs -f

logs-backend: ## Show backend logs
	docker compose logs -f backend

logs-worker: ## Show Celery worker logs
	docker compose logs -f celery-worker

build: ## Build all images
	docker compose build

restart: ## Restart all services
	docker compose restart

# ── Shell Access ──────────────────────────────────

shell: ## Open bash in backend container
	docker compose exec backend bash

shell-db: ## Open psql in PostgreSQL
	docker compose exec postgres psql -U $${POSTGRES_USER:-cz_user} -d $${POSTGRES_DB:-contenzavod}

shell-redis: ## Open redis-cli
	docker compose exec redis redis-cli

# ── Database Migrations ───────────────────────────

db-migrate: ## Create new migration (usage: make db-migrate msg="add users table")
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply all pending migrations
	docker compose exec backend alembic upgrade head

db-downgrade: ## Rollback last migration
	docker compose exec backend alembic downgrade -1

db-history: ## Show migration history
	docker compose exec backend alembic history --verbose

db-current: ## Show current migration
	docker compose exec backend alembic current

# ── Testing ───────────────────────────────────────

test: ## Run tests
	docker compose exec backend python -m pytest tests/ -v

test-cov: ## Run tests with coverage
	docker compose exec backend python -m pytest tests/ -v --cov=app --cov-report=html

# ── Code Quality ──────────────────────────────────

lint: ## Run linter (ruff check)
	docker compose exec backend ruff check .

format: ## Format code (ruff format)
	docker compose exec backend ruff format .

typecheck: ## Run type checking (mypy)
	docker compose exec backend mypy app/

# ── Cleanup ───────────────────────────────────────

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi local
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

# ── Documentation ─────────────────────────────────

docs-check: ## Check documentation health (missing/outdated files)
	@echo "\033[1m📋 Documentation Health Check\033[0m"
	@echo "──────────────────────────────────────"
	@ERRORS=0; \
	for f in CLAUDE.md README.md CHANGELOG.md; do \
		if [ -f "$$f" ]; then \
			echo "\033[32m✅\033[0m $$f"; \
		else \
			echo "\033[31m❌\033[0m $$f — MISSING"; ERRORS=$$((ERRORS+1)); \
		fi; \
	done; \
	for f in docs/ARCHITECTURE.md docs/DATABASE.md docs/API.md docs/AI_PROVIDERS.md docs/DEPLOYMENT.md; do \
		if [ -f "$$f" ]; then \
			echo "\033[32m✅\033[0m $$f"; \
		else \
			echo "\033[31m❌\033[0m $$f — MISSING"; ERRORS=$$((ERRORS+1)); \
		fi; \
	done; \
	echo "──────────────────────────────────────"; \
	ADR_COUNT=$$(ls docs/adr/[0-9]*.md 2>/dev/null | wc -l | tr -d ' '); \
	echo "📝 ADR записей: $$ADR_COUNT"; \
	CHANGELOG_UNRELEASED=$$(grep -c "^- " CHANGELOG.md 2>/dev/null || echo 0); \
	echo "📄 CHANGELOG записей (Unreleased): $$CHANGELOG_UNRELEASED"; \
	echo "──────────────────────────────────────"; \
	STALE=$$(find docs/ -name "*.md" -mtime +14 2>/dev/null | head -5); \
	if [ -n "$$STALE" ]; then \
		echo "\033[33m⚠️  Устаревшие (>14 дней без обновлений):\033[0m"; \
		echo "$$STALE" | while read f; do echo "   $$f (last: $$(stat -f '%Sm' -t '%Y-%m-%d' $$f))"; done; \
	fi; \
	if [ $$ERRORS -gt 0 ]; then \
		echo "\033[31m\n❌ Найдено $$ERRORS отсутствующих документов\033[0m"; \
		exit 1; \
	else \
		echo "\033[32m\n✅ Все обязательные документы на месте\033[0m"; \
	fi

docs-api: ## Regenerate API docs from OpenAPI spec
	@echo "Fetching OpenAPI spec from backend..."
	@curl -s http://localhost:8000/openapi.json | python3 -m json.tool > /tmp/openapi.json 2>/dev/null && \
		echo "\033[32m✅ OpenAPI spec saved to /tmp/openapi.json\033[0m" || \
		echo "\033[31m❌ Backend not running. Start with: make up\033[0m"
