# Multi-stage build for RelRAG API
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uvicorn", "relrag.main:create_relrag_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
