# RelRAG

RAG and full-text search framework around PostgreSQL 18 and pgvector.

## Features

- ACID-compliant operations
- RAG with embeddings and chunking
- Full-text search (tsvector)
- Keycloak OIDC authorization
- RBAC with configurable permissions

## Quick Start

```bash
uv sync
uv run python -c "import relrag; print('OK')"
```

## Docker + API smoke test

Переменные окружения берутся из `.env.example` (можно скопировать в `.env` и отредактировать).

```bash
docker compose up -d
.\scripts\test_rag_api.ps1   # Windows PowerShell
# or
./scripts/test_rag_api.sh   # Linux/macOS (requires jq)
```

Для полного E2E (загрузка документов, поиск) задайте `EMBEDDING_API_KEY` и при необходимости `EMBEDDING_API_URL` в `.env.example` или `.env`.

## Frontend (SSO)

После `docker compose up -d` фронтенд доступен на http://localhost:8081. Вход через Keycloak (testuser/testpass). Локальная разработка: `python -m http.server 8081` в папке `frontend/` (предварительно задать `RELRAG_CONFIG` в index.html или config.js для API и Keycloak).

## Testing

```bash
# Unit and API tests (no Docker required)
pytest tests/ -m "not e2e" -v --cov=src/relrag

# E2E frontend tests (requires docker compose up + playwright install)
playwright install
pytest tests/e2e/ -v -m e2e
```

## Documentation

See [docs/TASKS.md](docs/TASKS.md) for development tasks and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
