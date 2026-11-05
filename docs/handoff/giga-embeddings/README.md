# GigaEmbeddings: Linux handoff для benchmark-прогонов

**Статус:** воспроизводимый benchmark-профиль. Production embedder и PostgreSQL backend пока не выбраны: исследование вариантов продолжается.

## Что входит в этот Compose

[compose.yaml](compose.yaml) — полная конфигурация загрузчика, общего GPU embedder-а, LiteLLM gateway, сетей, volumes и ресурсных лимитов. Она **не подключает** `deploy/composes/tests/compose.stage0.yaml` из другого репозитория. `ARAG_ROOT` указывает на checkout исходного ARAG, из которого Compose собирает закреплённые образы и читает конфигурацию LiteLLM.

Топология:

```text
batch client / benchmark runner
        │  OpenAI-compatible HTTP, внутри Docker
        ▼
litellm-gateway:4000  ──►  giga-embedding:8000
        │                       │
        └── сеть arag_test      └── GPU + pinned model volume
```

Порты на хост не публикуются. Скрипт `run.sh batch` запускает клиент внутри gateway-контейнера; runner в том же проекте обращается к `http://litellm-gateway:4000/v1/embeddings`. Имена сетей и project name совместимы с benchmark-проектом ARAG `arag-stage0`.

## Модель и скачивание весов

Используется один snapshot для document и query режимов; отдельные веса для alias-ов не нужны.

- Модель: [ai-sage/Giga-Embeddings-instruct-480M-0826](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826).
- Закреплённая ревизия: [1763d603adac8057bd6482a708001b0ed2e0a903](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826/tree/1763d603adac8057bd6482a708001b0ed2e0a903).
- Прямая ссылка на веса: [model.safetensors](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826/resolve/1763d603adac8057bd6482a708001b0ed2e0a903/model.safetensors).
- ARAG хранит revision и SHA-256 каждого ожидаемого файла в `scripts/v3/giga_embeddings/metadata/model.json`; загрузчик использует только закреплённую ревизию.
- Загрузчик пишет snapshot в `/models/giga` внутри named volume `arag-stage0_giga_model_files_v1`. Основной файл будет доступен как `/models/giga/model.safetensors` внутри контейнера. При старте inference проверяются SHA-256 всех ожидаемых файлов.
- Изображение и vector cache в git не попадают. Остановка Compose сохраняет volume с моделью.

Runtime зафиксирован в исходном ARAG: Python 3.14.10, PyTorch 2.14.0+cu130, CUDA 13.0 runtime image, Sentence Transformers 6.2.0 и `deploy/locks/giga-gpu/uv.lock`.

## Требования

- Linux Docker Engine и Docker Compose v2.
- NVIDIA GPU, корректный NVIDIA Container Toolkit, проверенный доступ GPU к Docker.
- Доступ к Hugging Face на этапе первого скачивания. После загрузки inference работает offline.
- Доступный checkout ARAG с файлами Dockerfile, lock-файлом, manifest модели и LiteLLM config.

Задайте `ARAG_ROOT` на checkout ARAG. Пример из shell-сессии, где есть и checkout ARAG, и этот каталог handoff:

```bash
export ARAG_ROOT=/work/ARAG
bash /work/RelRAG/docs/handoff/giga-embeddings/run.sh download
bash /work/RelRAG/docs/handoff/giga-embeddings/run.sh up
bash /work/RelRAG/docs/handoff/giga-embeddings/run.sh health
bash /work/RelRAG/docs/handoff/giga-embeddings/run.sh status
```

`download` скачивает pinned snapshot и завершает одноразовый контейнер. `up` повторно проверяет volume, собирает GPU runtime/gateway и запускает оба сервиса. Первая компиляция PyTorch может занять несколько минут; readiness probe ждёт CUDA и динамическую компиляцию. `health` выводит только provenance и параметры сервиса, без входных текстов. `down` останавливает два сервиса, но оставляет оба named volume. Для удаления данных используйте явную отдельную команду Docker после проверки имени volume; launcher не выполняет удаление.

Для benchmark-only credentials Compose задаёт одинаковое локальное значение по умолчанию для `LITELLM_MASTER_KEY` и `GIGA_EMBEDDING_API_KEY`. На изолированном тестовом стенде их можно переопределить через окружение. Эти значения синтетические, не предназначены для production или открытой сети.

## Отправка batch-запросов

Каждый пример — один OpenAI-compatible request. Подайте JSON через stdin в launcher; ответ сохраните в файл, потому что embedding vectors большие:

```bash
bash /work/RelRAG/docs/handoff/giga-embeddings/run.sh batch \
  < /work/RelRAG/docs/handoff/giga-embeddings/batch-documents-v1.json \
  > documents-embeddings.json

bash /work/RelRAG/docs/handoff/giga-embeddings/run.sh batch \
  < /work/RelRAG/docs/handoff/giga-embeddings/batch-queries-v1.json \
  > query-embeddings.json
```

Синтетические примеры можно просмотреть в [batch-documents-v1.json](batch-documents-v1.json) и [batch-queries-v1.json](batch-queries-v1.json). Тело запроса:

```json
{
  "model": "giga-document-v1",
  "input": ["Текст первого документа", "Текст второго документа"],
  "encoding_format": "float"
}
```

Для документа задайте `giga-document-v1`, для поискового вопроса — `giga-query-v1`. В `input` допустима одна строка или список строк. Query alias сам применяет инструкцию `Instruct: Given a query, retrieve relevant passages\nQuery: {query}`; передавайте обычный вопрос, не добавляйте этот префикс повторно. Для документов дополнительная инструкция не добавляется.

Ограничения одного HTTP запроса: от 1 до 64 текстов, тело не больше 16 MiB, один текст не больше 8 MiB символов. Sequence limit — 8 192 токена после query instruction. Слишком длинный текст обрезается сервисом по токенам; число таких элементов отражается в `arag.truncated_inputs`. Запрос с неподдерживаемыми полями, включая `dimensions`, отклоняется.

Ответ содержит `data[]` с `index` и нормализованным вектором `float32` размерности 1 024, `usage` с числом токенов и `arag.elapsed_ms` / `arag.truncated_inputs` / `arag.max_sequence_tokens`. Порядок элементов совпадает с порядком входа. Endpoint gateway принимает bearer key; launcher подставляет его внутри контейнера и не печатает секрет.

## Соединение benchmark runners с embedder-ом

Стандартный маршрут: runner → `http://litellm-gateway:4000/v1/embeddings` → `http://giga-embedding:8000/v1/embeddings`. LiteLLM предоставляет alias-ы `giga-document-v1` и `giga-query-v1`; кэш ответов LiteLLM и логирование сообщений отключены. Не создавайте отдельную GPU-модель на каждый стенд: один сервис обслуживает все runners, подключённые к внутренней сети `arag_test`.

ARAG retrieval runner ограничивает разрешённые endpoint-ы. Для обычного OpenAI-пути ему задаются:

```text
GIGA_EMBEDDING_API_BASE=http://litellm-gateway:4000/v1
GIGA_EMBEDDING_API_KEY=<тот же ключ, что LITELLM_MASTER_KEY>
```

MIRACL cache precompute может использовать внутренний аутентифицированный endpoint `http://giga-embedding:8000/internal/v1/embeddings`; ответ там бинарный little-endian float32, поэтому клиент не разбирает длинные JSON-массивы. Для этого режима `GIGA_EMBEDDING_API_KEY` совпадает с переменной embedder-а. Оба маршрута доступны только контейнерам внутри compose-сетей; host port mapping отсутствует.

В основном ARAG benchmark Compose embedding cache строится отдельным `miracl-vector-cache` runner-ом с лимитом 1 CPU / 2 GiB RAM; он пишет в named volume `arag-stage0_sberquad_vectors_cache_v1`, смонтированный как `/vector-cache`. Retrieval-прогоны монтируют этот volume read-only и используют `--require-existing-cache`, поэтому cache miss не запускает повторный GPU расчёт. При запуске полного retrieval benchmark используйте основной Compose из ARAG checkout и его manifest/dataset mounts; handoff Compose содержит только downloader, embedder и gateway.

## Кэширование embeddings и повторяемость

Векторный кэш реализован в ARAG runner, а не в LiteLLM. Каталог вычисляется по content-addressed identity. Identity включает digest manifest/input датасета, model id + revision и SHA-256 файлов, dtype/device/precision/execution mode/service version, размерность, query template и размеры коллекций. Внутри каталога находятся `documents.npy`, `queries.npy`, `manifest.json`.

Runner проверяет provenance, размеры массивов и SHA-256, сохраняет NumPy массивы как float32 с атомарной заменой и читает их через memory map. Raw тексты не записываются в отчёт. Если cache валиден, report содержит `cache_hit=true` и `embedding_seconds=0`; подготовка embeddings отделяется от ingest, index build и retrieval. `--require-existing-cache` завершает прогон ошибкой при missing/invalid cache вместо незаметного повторного обращения к GPU.

Отдельные model/cache volumes: `arag-stage0_giga_model_files_v1` для snapshot и `arag-stage0_sberquad_vectors_cache_v1` для массивов benchmark-векторов. Имя cache volume сохранено, чтобы использовать его совместно с существующими ARAG benchmark Compose runners.

## Ограничения, оптимизации и метрики

- Ресурсные квоты: downloader 1 CPU / 2 GiB, GPU embedder 4 CPU / 10 GiB, LiteLLM gateway 1 CPU / 2 GiB. Учтите их вместе с runner и PostgreSQL в пределах согласованного общего лимита 16 vCPU / 32 GiB.
- Root filesystem контейнеров read-only; writable runtime/compiler cache ограничены tmpfs; Linux capabilities сброшены, включён `no-new-privileges`; inference сети внутренние.
- FP16 weights на CUDA дают нормализованные FP32 output-векторы; TF32 выключен. Включён `torch.compile(mode="default", dynamic=True)`. GPU microbatch ограничивается attention-cell budget и максимумом 64 строк; inference serializes одним lock-ом.
- Batch size sweep на коротких synthetic текстах показал 1 479,65 текстов/с при batch 64. Отдельный MIRACL sample с length bucketing показал 706,1 против 293,6 текстов/с и top-10 overlap 99,45%. Length bucketing пока не встроен в HTTP service; это нельзя выдавать за его throughput.
- В Linux фиксируйте host profile и повторяемость отдельно от WSL2. Пишите CSV/JSON метрики, включая время embedding-cache build, hit/miss, CPU/RAM/GPU/VRAM, ошибки и degradation. Не смешивайте с временем ingest, построения индекса и retrieval.
- Security checks остаются quality gate. Benchmark-only defaults не являются production identity/auth configuration.

