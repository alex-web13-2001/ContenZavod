FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock* ./

# Install Python dependencies into the project venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv venv /opt/venv && uv sync --frozen --no-dev 2>/dev/null || uv sync

# Make sure venv is used
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
ENV PYTHONPATH="/app"

# Copy application code (overridden by volume mount in dev)
COPY . .

# Default command (overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
