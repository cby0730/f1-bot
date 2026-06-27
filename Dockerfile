# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only into a virtual env
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src/ ./src/
RUN uv sync --frozen --no-dev


FROM python:3.13-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN adduser --disabled-password --gecos "" botuser

# Copy the virtual env from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER botuser

CMD ["python", "-m", "f1_bot"]
