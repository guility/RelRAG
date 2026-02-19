# RelRAG API — примеры curl

Базовый URL: `http://localhost:8000`

## 1. Health

```bash
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/health/ready
```

## 2. Создать конфигурацию

```bash
curl -X POST http://localhost:8000/v1/configurations \
  -H "Content-Type: application/json" \
  -d '{"chunking_strategy":"recursive","embedding_model":"text-embedding-3-small","embedding_dimensions":1536,"chunk_size":512,"chunk_overlap":50}'
```

Сохраните `id` из ответа как `CONFIG_ID`.

## 3. Создать коллекцию

```bash
curl -X POST http://localhost:8000/v1/collections \
  -H "Content-Type: application/json" \
  -d '{"configuration_id":"CONFIG_ID"}'
```

Сохраните `id` как `COLLECTION_ID`.

## 4. Загрузить документ

```bash
curl -X POST http://localhost:8000/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"collection_id":"COLLECTION_ID","content":"RelRAG is a RAG framework for PostgreSQL and pgvector.","properties":{}}'
```

Требуется `EMBEDDING_API_KEY` (OpenAI или совместимый API).

## 5. Получить документ

```bash
curl "http://localhost:8000/v1/documents/DOCUMENT_ID?collection_id=COLLECTION_ID"
```

## 6. Гибридный поиск

```bash
curl -X POST "http://localhost:8000/v1/collections/COLLECTION_ID/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"PostgreSQL vector","vector_weight":0.7,"fts_weight":0.3,"limit":5}'
```
