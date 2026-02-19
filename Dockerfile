# RelRAG API - uv + Python 3.14
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

WORKDIR /app

ENV UV_NO_DEV=1
ENV UV_LINK_MODE=copy

# Install dependencies first (better layer caching)
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

# Copy project and install
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uvicorn", "relrag.main:create_relrag_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
