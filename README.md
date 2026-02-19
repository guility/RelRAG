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

```bash
docker compose up -d
.\scripts\test_rag_api.ps1   # Windows PowerShell
# or
./scripts/test_rag_api.sh   # Linux/macOS (requires jq)
```

For full E2E (document load, search), set `EMBEDDING_API_KEY` and optionally `EMBEDDING_API_URL` in the environment or docker-compose.

## Documentation

See [docs/TASKS.md](docs/TASKS.md) for development tasks and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
