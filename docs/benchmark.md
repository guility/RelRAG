# Бенчмарки RelRAG

Измерение пропускной способности загрузки документов, задержек поиска и (опционально) отклика интерфейса.

## Подготовка

1. Поднять стек с профилем bench и переменными из `.env.example`:

   ```bash
   docker compose -f docker-compose.bench.yml --env-file .env.example up -d
   ```

   Сервисы: postgres, keycloak, relrag-api, relrag-app. Для бенчмарков образ `bench-runner` не поднимается по умолчанию (профиль `bench`).

2. Дождаться готовности API (healthcheck). При необходимости задать `EMBEDDING_API_KEY` в `.env.example` для реальной эмбеддинг-модели.

## Запуск бенчмарков

Все команды ниже можно выполнять **на хосте** (тогда `API_URL=http://localhost:8000`, `KEYCLOAK_URL=http://localhost:8080`) или **в контейнере bench-runner** (тогда переменные уже заданы в compose).

### Загрузка документов (throughput, latency)

- **На хосте** (нужен `httpx`: `pip install httpx` или `uv add httpx`):

  ```bash
  export API_URL=http://localhost:8000 KEYCLOAK_URL=http://localhost:8080
  export KEYCLOAK_REALM=relrag KEYCLOAK_CLIENT_ID=relrag-api KEYCLOAK_CLIENT_SECRET=relrag-api-secret
  export BENCH_USER=testuser BENCH_PASSWORD=testpass
  python scripts/bench_upload.py --num-docs 100 --content-size 500 --output ./bench-results/bench_upload.txt
  ```

- **В контейнере** (результаты в `./bench-results/` на хосте):

  ```bash
  docker compose -f docker-compose.bench.yml --profile bench run --rm bench-runner \
    python scripts/bench_upload.py --num-docs 100 --output /results/bench_upload.txt
  ```

Метрики: документов в секунду (docs/s), приблизительно МБ/с текста, задержки p50/p95/p99 (мс).

### Поиск (QPS, latency)

- **На хосте:**

  ```bash
  python scripts/bench_search.py --num-docs 500 --num-queries 100 --output ./bench-results/bench_search.txt
  ```

- **В контейнере:**

  ```bash
  docker compose -f docker-compose.bench.yml --profile bench run --rm bench-runner \
    python scripts/bench_search.py --num-docs 500 --num-queries 100 --output /results/bench_search.txt
  ```

Метрики: запросов в секунду (QPS), задержки p50/p95/p99 (мс). Объём данных задаётся `--num-docs` (сколько документов в коллекции перед прогоном запросов).

## Результаты

- При запуске из контейнера с volume `./bench-results:/results` файлы пишутся в `./bench-results/` на хосте.
- В выводе в консоль и в файл попадает сводка: throughput, latencies, общее время.

## Интерпретация

- **Загрузка:** рост задержки при увеличении размера документа или количества параллельных запросов; пропускная способность ограничена эмбеддинг-API и БД.
- **Поиск:** p95/p99 растут с увеличением размера коллекции (объём данных); QPS зависит от нагрузки и лимитов API/БД.
- Для сравнения сценариев повторяйте прогоны с одинаковыми параметрами (`--num-docs`, `--content-size`, `--num-queries`).

## Остановка

```bash
docker compose -f docker-compose.bench.yml down
```
