# GigaEmbeddings: handoff для Linux-бенчмарков

**Статус:** воспроизводимый benchmark-профиль; production embedder и PostgreSQL backend не выбраны. Эта папка находится в handoff-ветке RelRAG. Для запуска нужен checkout исходного ARAG, указанный через `ARAG_ROOT`; каноническими остаются его код и Compose-конфигурация.

## Веса и фиксация модели

- Публичная модель: [ai-sage/Giga-Embeddings-instruct-480M-0826](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826).
- Зафиксированный snapshot: [revision 1763d603adac8057bd6482a708001b0ed2e0a903](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826/tree/1763d603adac8057bd6482a708001b0ed2e0a903); прямой [model.safetensors](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826/resolve/1763d603adac8057bd6482a708001b0ed2e0a903/model.safetensors).
- `model.json` содержит revision и SHA-256 каждого ожидаемого файла. Сервис проверяет хэши перед загрузкой локального snapshot.
- Загрузчик сохраняет модель в named volume `arag-stage0_giga_model_files_v1`; inference выполняется offline. Не добавлять веса и векторные кэши в git.

## Запуск и остановка

Нужны Linux Docker Engine, Docker Compose v2 с поддержкой `include`, NVIDIA Container Toolkit и GPU, доступная Docker.

```bash
ARAG_ROOT=/path/to/arag bash docs/handoff/giga-embeddings/run.sh up
ARAG_ROOT=/path/to/arag bash docs/handoff/giga-embeddings/run.sh status
ARAG_ROOT=/path/to/arag bash docs/handoff/giga-embeddings/run.sh down
```

`up` скачивает закреплённый snapshot, собирает и запускает общий GPU embedder и LiteLLM gateway. `down` останавливает только эти сервисы и сохраняет volumes. `compose.yaml` подключает канонический Compose-проект ARAG, не копируя определения сервисов. Основные файлы исходного дерева:

- `deploy/composes/tests/compose.stage0.yaml` — Compose проект и его includes.
- `deploy/composes/stage0/giga.yaml` — загрузка модели, volume и CPU utility benchmark.
- `deploy/composes/stage0/inference/giga-inference.yaml` — GPU-сервис, gateway, лимиты ресурсов и сетевые настройки.
- `deploy/Dockerfiles/models/Dockerfile.giga-gpu`, `deploy/locks/giga-gpu/pyproject.toml`, `deploy/locks/giga-gpu/uv.lock` — runtime с закреплёнными зависимостями.
- `deploy/litellm/giga-embeddings.yaml` — псевдонимы моделей и настройки gateway.
- `scripts/v3/giga_embeddings/{server.py,compiled_inference.py,service.py,service_limits.py}` — проверяемый локальный API inference.
- `scripts/v3/retrieval_benchmark/embedding/{model.py,gateway.py,cache.py}` — подключение runners и content-addressed cache векторов.

## Связь runners и кэш

Один Compose-сервис держит модель на GPU. Runners подключаются по внутренним Compose DNS-именам: стандартный маршрут — runner → `litellm-gateway:4000/v1/embeddings` → `giga-embedding:8000/v1/embeddings`. LiteLLM предоставляет `giga-document-v1` и `giga-query-v1`; его response cache и логирование сообщений отключены. MIRACL precompute идёт через аутентифицированный внутренний адрес `giga-embedding:8000/internal/v1/embeddings`, возвращающий упорядоченные FP32-векторы в компактном бинарном ответе. Публичные порты не публикуются.

Документы кодируются без инструкции. Для запросов применяется шаблон `Instruct: Given a query, retrieve relevant passages\nQuery: {query}`. Ограничения API: до 64 текстов и 16 MiB на запрос, до 8 192 токенов на текст и размерность 1 024. Runner передаёт bearer credential через конфигурацию окружения; текущее Compose-значение синтетическое и предназначено только для benchmark.

Volume модели отделён от `arag-stage0_sberquad_vectors_cache_v1`, который подключается к runners как `/vector-cache`. Путь кэша — `<cache-root>/<sha256(identity)>/{documents.npy,queries.npy,manifest.json}`. Identity включает digest входных данных датасета, model id/revision и hashes файлов модели, dtype/device/precision/execution mode/service version, размерность, query template и число строк. Проверяются provenance, хэши и формат массивов; `.npy` заменяются атомарно после durable flush и читаются через `mmap_mode="r"`. С `--require-existing-cache` отсутствующий или невалидный кэш завершает benchmark ошибкой, не вызывая GPU inference. Cache hit фиксируется как `cache_hit=true`, `embedding_seconds=0`; подготовка embeddings учитывается отдельной фазой. Не сохранять сырой текст в результатах.

## Оптимизации и результаты

- Python 3.14.10, PyTorch 2.14.0+cu130, закреплённая CUDA 13.0 base image, Sentence Transformers 6.2.0 и `deploy/locks/giga-gpu/uv.lock`.
- FP16 веса на CUDA и нормализованный FP32 output; TF32 выключен; динамический `torch.compile(mode="default", dynamic=True)`.
- GPU microbatch адаптивно ограничен бюджетом attention cells (64 × 3 000²), максимум 64 строки. При reserved CUDA memory >25 GiB чистятся неактивные allocator blocks. Один instance сериализует inference lock-ом.
- Лимиты: embedder 4 CPU / 10 GiB RAM; LiteLLM 1 CPU / 2 GiB; MIRACL precompute runner 1 CPU / 2 GiB. Root FS read-only, временные кэши ограничены, сеть сервиса внутренняя, capabilities сброшены.
- `quality-runs/giga-batch-size/1101r2/run_batch_size_sweep.py` и `compose.batch-sweep.yaml`: batch 64 дал 1 479,65 текстов/с в трёх повторах на коротких синтетических текстах; это не MIRACL throughput.
- `quality-runs/giga-optimization/1101r6/run_miracl_length_bucketing.py` и `compose.miracl-length-bucketing.yaml`: batch 64 с length bucketing — 706,1 против 293,6 текстов/с, top-10 overlap 99,45%. Bucketing замерялся в отдельном precompute runner и пока не включён в HTTP-сервис. Перед интеграцией повторить проверку порядка, retrieval quality и параллельной нагрузки.
- Snapshot SHA-256 из `/healthz`: `60463aff43bceea15fd4f44d84fbe9e89e37b9abc97d3dbc461648d0835414e8`.

Linux-прогоны получают отдельный host profile и не смешиваются с WSL2 без парных запусков. Resource admission учитывает общий GPU-сервис, gateway, runners и базы в пределах 16 vCPU / 32 GiB. Security checks остаются quality gate; открытые findings должны оставаться видимыми, профиль benchmark-only.
