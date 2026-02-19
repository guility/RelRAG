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

## Documentation

See [docs/TASKS.md](docs/TASKS.md) for development tasks and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
