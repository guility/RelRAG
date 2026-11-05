# GigaEmbeddings: Linux benchmark handoff

**State:** reproducible benchmark profile; no production embedder or PostgreSQL backend has been selected. This folder lives in the RelRAG handoff branch. Its commands use the ARAG source checkout through `ARAG_ROOT`; the source tree remains authoritative for implementation.

## Weights and model lock

- Public model: [ai-sage/Giga-Embeddings-instruct-480M-0826](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826).
- Pinned snapshot: [revision 1763d603adac8057bd6482a708001b0ed2e0a903](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826/tree/1763d603adac8057bd6482a708001b0ed2e0a903); direct [model.safetensors](https://huggingface.co/ai-sage/Giga-Embeddings-instruct-480M-0826/resolve/1763d603adac8057bd6482a708001b0ed2e0a903/model.safetensors).
- `model.json` records the revision and expected SHA-256 for every model artifact. The service checks these hashes before loading the local snapshot.
- The download task writes to the named volume `arag-stage0_giga_model_files_v1`; inference then runs with Hugging Face and Transformers offline. Do not commit weights or vectors.

## Start and stop

Requirements: Linux Docker Engine, Docker Compose v2 with `include` support, NVIDIA Container Toolkit, and a GPU visible to Docker.

```bash
ARAG_ROOT=/path/to/arag bash docs/handoff/giga-embeddings/run.sh up
ARAG_ROOT=/path/to/arag bash docs/handoff/giga-embeddings/run.sh status
ARAG_ROOT=/path/to/arag bash docs/handoff/giga-embeddings/run.sh down
```

`up` downloads the pinned snapshot, then builds and starts the shared GPU embedder and LiteLLM gateway. `down` stops only those two services and preserves named volumes. `compose.yaml` includes the canonical ARAG Compose project rather than copying service definitions. Key source files:

- `deploy/composes/tests/compose.stage0.yaml` — Compose project and includes.
- `deploy/composes/stage0/giga.yaml` — one-time model download, volume, CPU utility benchmark.
- `deploy/composes/stage0/inference/giga-inference.yaml` — shared GPU service and gateway, resource/security/network settings.
- `deploy/Dockerfiles/models/Dockerfile.giga-gpu`, `deploy/locks/giga-gpu/pyproject.toml`, `deploy/locks/giga-gpu/uv.lock` — pinned runtime.
- `deploy/litellm/giga-embeddings.yaml` — model aliases and gateway configuration.
- `scripts/v3/giga_embeddings/{server.py,compiled_inference.py,service.py,service_limits.py}` — verified local inference API.
- `scripts/v3/retrieval_benchmark/embedding/{model.py,gateway.py,cache.py}` — runner connection and content-addressed vector cache.

## Runner path and cache

A single Compose service keeps the model on the GPU. Runners connect over internal Compose DNS: the usual route is runner → `litellm-gateway:4000/v1/embeddings` → `giga-embedding:8000/v1/embeddings`. LiteLLM exposes `giga-document-v1` and `giga-query-v1`; its response cache and message logging are disabled. MIRACL precompute uses the authenticated internal `giga-embedding:8000/internal/v1/embeddings` route, which returns ordered FP32 vectors in a compact binary response. No public ports are published.

Documents are encoded raw. Queries use `Instruct: Given a query, retrieve relevant passages\nQuery: {query}`. API bounds are 64 texts per batch, 16 MiB per request, 8,192 tokens per text, and 1,024 dimensions. The runner passes a bearer credential through environment configuration; the checked-in Compose value is synthetic benchmark-only data, not a production secret.

The model snapshot volume is separate from `arag-stage0_sberquad_vectors_cache_v1`, mounted at `/vector-cache`. Cache path is `<cache-root>/<sha256(identity)>/{documents.npy,queries.npy,manifest.json}`. Identity includes dataset input digest, model id/revision and artifact hashes, dtype/device/precision/execution mode/service version, dimensions, query template, and row counts. Cache validation checks provenance, file digests and array layout; `.npy` is atomically replaced after a durable flush and loaded via `mmap_mode="r"`. With `--require-existing-cache`, a missing or invalid cache fails the benchmark instead of invoking GPU inference. Cache hits record `cache_hit=true` and `embedding_seconds=0`; embedding preparation remains a separate phase. Do not persist raw text in benchmark results.

## Applied optimizations and benchmark evidence

- Python 3.14.10, PyTorch 2.14.0+cu130, pinned CUDA 13.0 base, Sentence Transformers 6.2.0, locked by `deploy/locks/giga-gpu/uv.lock`.
- FP16 CUDA weights with normalized FP32 output; TF32 disabled; `torch.compile(mode="default", dynamic=True)`.
- Adaptive GPU microbatch bounded by the attention-cell budget (64 × 3,000²), maximum 64 rows; inactive CUDA allocator blocks are released when reserved memory exceeds 25 GiB. One service instance serializes inference with a lock.
- Limits: embedder 4 CPU / 10 GiB RAM; LiteLLM 1 CPU / 2 GiB; MIRACL precompute runner 1 CPU / 2 GiB. Root filesystems are read-only, caches use bounded temporary storage, service networks are internal, capabilities are dropped.
- Batch-size sweep `quality-runs/giga-batch-size/1101r2`: batch 64 reached 1,479.65 texts/s over three repeats on short synthetic texts; this is not MIRACL throughput.
- MIRACL sample optimization `quality-runs/giga-optimization/1101r6`: batch 64 plus length bucketing reached 706.1 vs 293.6 texts/s, with 99.45% top-10 overlap. Bucketing was tested in a separate precompute runner; it is not currently part of the HTTP service. Recheck ordering, retrieval quality, and concurrent load before integrating it.
- Snapshot SHA-256 reported by `/healthz`: `60463aff43bceea15fd4f44d84fbe9e89e37b9abc97d3dbc461648d0835414e8`.

Linux runs must have their own host profile and remain separate from WSL2 cohorts without paired runs. Resource admission includes the shared GPU service, gateway, runners, and databases under the 16 vCPU / 32 GiB benchmark ceiling. Security checks stay a quality gate; keep open findings visible and treat this setup as benchmark-only.
