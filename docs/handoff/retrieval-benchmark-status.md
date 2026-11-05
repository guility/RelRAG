# PostgreSQL retrieval research handoff

**Status snapshot:** 2026-11-05  
**Research state:** in progress; no production backend or production SLO has been selected.  
**Purpose:** let the Linux handoff continue the PostgreSQL retrieval comparison without treating a partial or synthetic result as a final choice.

This is the consolidated plan/status/results/decision record for the three open research issues: [Linux profile and reproducibility (#1)](https://github.com/guility/RelRAG/issues/1), [retrieval quality (#2)](https://github.com/guility/RelRAG/issues/2), and [index build, load, and resources (#3)](https://github.com/guility/RelRAG/issues/3). The issues are all **open** as of this snapshot. The generic [docs/benchmark.md](../benchmark.md) describes the RelRAG API smoke benchmark; it is not the PostgreSQL backend research plan.

## Plan and current status

| Workstream | Status | What is established | Remaining work |
|---|---|---|---|
| Linux benchmark profile and reproducibility | **Open; Linux cohort not run** | Handoff defines host/resource profile, phase separation, seeds, manifests, CSV/JSON, and Linux-vs-WSL2 separation. | Implement and run Linux-native preflight, PostgreSQL/extension smoke, host profile capture, GPU smoke, and repeatability checks. |
| Shared GigaEmbeddings service | **Runbook present; Linux runtime validation pending** | Standalone Compose, launcher, pinned model manifest, LiteLLM gateway and synthetic batch examples are in [the GigaEmbeddings handoff](giga-embeddings/README.md). | Run GPU smoke on Linux; preserve exact model/runtime provenance. Historical bit-for-bit cache reconstruction is not currently proven; see below. |
| Public retrieval quality | **Partial** | Full SberQUAD and RuBQ results exist for selected routes; MIRACL has completed and incomplete candidates. | Complete comparable candidate × dataset matrix, verify application-role/RLS query plans, repeat where required, and retain failures/incomplete runs. |
| Index build and resource comparison | **Partial** | Successful pgvector Binary HNSW and halfvec HNSW builds; float32 HNSW and pgvectorscale DiskANN have incomplete/failure evidence. | Repeat successful builds on Linux and test a viable alternative under the agreed build envelope. |
| Load/capacity comparison | **Partial** | Synthetic high-RPS capacity evidence exists; public-corpus load evidence is short/diagnostic and incomplete for several candidates. | Repeat load ladders with variable RPS, three runs per point where feasible, and record latency separately from load-generator scheduling lag. |
| Security quality gate | **Open for affected candidates** | Historical pgvectorscale image scan reported 2 CRITICAL and 88 HIGH findings. | Rebuild/pin the image, rerun the required security gates, and do not treat it as a release candidate until the gate passes or findings are dispositioned. |

## Intermediate results

### Public retrieval quality

| Dataset / candidate | Interim result | Status and interpretation |
|---|---|---|
| SberQUAD — pgvector dense + pg_trgm weighted | Full test split: 23,936 queries / 17,474 documents. nDCG@10 **0.90080**, MAP@10 **0.88251**, Recall@100 **0.98575**, MRR@10 **0.88251**. Dense-only nDCG@10: **0.78122**. | Completed quality run. The planner did not select the dense and lexical indexes, and background CPU activity included MIRACL preparation. Do not use its elapsed time as isolated indexed-search performance. |
| RuBQRetrieval — pgvector / ParadeDB / hybrid | Full split: 1,692 queries / 56,826 documents; 3 warm repeats. Best nDCG@10: pgvector dense **0.731753**. Best Recall@100: one SQL route with dense 75% / BM25 25%, **0.965475**. | Completed for the measured routes. PostgreSQL did not select GIN for the built-in FTS route; this does not validate indexed GIN retrieval. |
| MIRACL Russian — pgvector Binary HNSW | 1,252 queries / about 9.54M documents. nDCG@10 **0.5457**, MAP@10 **0.4624**, Recall@100 **0.6942**, MRR@10 **0.6528**. Three warm latency repeats: p50 **20.07 ms**, p95 **27.22 ms**. | Full qrels result. Latency repeats excluded exact scans and were not a load test. Exact-reference ANN Recall@100 sample: **0.577** on 20 queries. |
| MIRACL Russian — pgvector halfvec HNSW | 1,252 / 1,252 queries. nDCG@10 **0.684117**, MAP@10 **0.590516**, Recall@100 **0.916959**, MRR@10 **0.778055**; ANN Recall@100 **0.913** on exact sample n=20. | One complete quality run; a second run stopped at 550 / 1,252. M and ef_construction differ from Binary HNSW, so this is not an isolated representation comparison. |
| MIRACL Russian — VectorChord | 1,243 / 1,252 queries; 9 statement timeouts; 2,542.52 s. | Incomplete screening only; not a complete quality score or a sustained RPS result. |
| MIRACL Russian — pgvectorscale DiskANN | No ready index after the build cutoff. | Public retrieval quality and RPS were not measured. |

### Build, load, and resource measurements

| Experiment | Interim result | Status and caveat |
|---|---|---|
| MIRACL pgvector Binary HNSW build, 9.54M rows | **698.372 s**, index **3.18 GB**; Docker CPU mean/p95/peak **194.08 / 203.04 / 204.95%**; RAM mean/p95/peak **27,521.66 / 28,989.44 / 29,214.72 MiB**. | One successful build with an expanded build profile; build-time repeatability is not established. |
| MIRACL pgvector halfvec HNSW build, 9.54M rows | **4,016.175 s**, index **26.01 GB**; Docker CPU mean/p95/peak **192.56 / 205.62 / 221.68%**; working-set RAM mean/p95/peak **28,989 / 32,020 / 32,543 MiB**. | One successful build, no OOM. A previous 29/24 GiB profile spilled; successful profile used PostgreSQL 2.5 CPU / 32 GiB, maintenance_work_mem=26GB and /dev/shm=26GiB. |
| MIRACL float32 HNSW | Stopped at **57.05%** after 5,392,328 tuples when the graph exceeded maintenance_work_mem. | No index produced; not a quality result. |
| MIRACL pgvectorscale DiskANN | Stopped at **10,886.53 s** under the agreed 4× screening cutoff; quantizer training had not completed. | No ready index; no quality or retrieval RPS. |
| Synthetic ANN, 50k × 1,024, target 300 RPS | pgvector HNSW **301.129 RPS / p95 2.029 ms**; pgvectorscale DiskANN **301.130 / 3.656 ms**; VectorChord **121.979 / 54.896 ms**. | Synthetic capacity only, not public retrieval quality. |
| pgvector synthetic RPS ladder | At 1,800 target RPS, median achieved **1,792.414 RPS / p95 3.161 ms**; at 2,400 target, about **2,131 RPS / p95 4.63 s**. | Throughput and latency show degradation above the lower target; repeatability applies to the specific synthetic profile only. |
| ParadeDB weighted RRF synthetic load | 25 runs / **1,449,600** completed transactions. At 1,200 target RPS: median achieved **1,198.954 RPS / p95 2.938 ms**; backlog at 1,600; saturation around **1,535–1,557 RPS**, p95 **5.58–6.28 s** at 1,800 target. | Synthetic capacity diagnostic; not public corpus quality or a production SLO. |
| MIRACL short load ladders | Binary HNSW reached **50 RPS** in a short ladder. Halfvec reached **7 RPS** repeatedly; **10 RPS** was unstable. | Diagnostic-duration load points, not long-duration SLO results. |

## Intermediate accepted decisions

These are research-method and operating decisions, not a production architecture decision or an ADR selecting a backend.

1. **Keep the backend choice open.** The goal is to find the best supported retrieval option; no production winner/SLO is declared from the current mixed evidence. (Issues #1–#3.)
2. **Use a bounded, comparable resource envelope.** The benchmark containers share a maximum of **16 vCPU / 32 GiB RAM**. A typical retrieval/load stand is **3 vCPU / 6 GiB**. Large index builds run one builder at a time, up to the established pgvector HNSW build resource profile; search/load runs return to the smaller stand. Record per-container quotas and actual resource samples. (Issue #3.)
3. **Separate phases.** Embedding generation, source download/preparation, ingest, index build, retrieval quality and load are separately timed and reported. A ready embedding cache is used for retrieval/load; GPU inference is not charged to those phases on cache hits. (Issues #1–#3.)
4. **Use a shared local GPU GigaEmbeddings service.** Runners send batches over the documented HTTP/OpenAI-compatible gateway and reuse a content-addressed cache. The model source/revision and launcher details are in [the runbook](giga-embeddings/README.md). (Issue #1.)
5. **Keep the Russian public benchmarks.** Retain SberQUAD; run the full RuBQ test split; use MIRACL Russian as the separate large-corpus profile. (Issue #2.)
6. **Require comparable repeats and preserve degradation.** Fix corpus/split, query set, seed, route, versions and resource profile; target three successful repeats where practical. Save dropped iterations, errors, timeouts, partial progress and degradation class instead of silently omitting them. (Issues #1–#3.)
7. **Apply the 4× early-screen cutoff only to comparable runs.** A candidate may be stopped before full quality evaluation if its measured/projected retrieval duration is at least 4× pgvector HNSW dense on the same benchmark, query count, phase scope and resource profile. This is screening, not a quality score. (Issue #2.)
8. **Keep synthetic capacity separate from public retrieval quality.** Synthetic ANN and RLS fixtures can compare capacity/query paths but cannot replace public qrels evaluation. (Issues #2–#3.)
9. **Keep Linux results as a separate cohort from Windows/WSL2.** Compare across cohorts only after a paired run with the same data, images, seed and quotas. Record CPU model/topology/affinity and GPU/driver/runtime. (Issue #1.)
10. **Do not weaken tenant/RLS authorization for a faster route.** Validate routes under the application role and current tenant policy. (Issues #2–#3.)

## Handoff gaps and next steps

- The three GitHub issues contain the executable scope and summarized outcomes, but detailed source CSV/JSON artifacts and the original ARAG benchmark catalog are **not copied into this repository branch**. The source report paths are under docs/architecture/catalog/data/giga-benchmarks/ and docs/architecture/catalog/data/retrieval-spike-plan.md in the ARAG repository. Transfer or link the required per-run artifacts before claiming a fully self-contained archival handoff.
- Exact historical vector-cache reconstruction is **not yet reproducible from the handoff**. SberQUAD/RuBQ lack a standalone cache-only builder and recorded per-array hashes; MIRACL has a cache builder but its historical cache manifest was not archived. Preserve cache keys, manifest SHA-256 values, exact source tree/image ID and GPU/driver provenance on future runs.
- Linux runtime validation is pending. The Giga Compose/config has a runbook, but that is not evidence of a completed GPU inference run on the target Linux host.
- Next: port and validate the benchmark harness on Linux; attach/import source CSV/JSON and manifests; verify Giga GPU smoke and cache identity; run comparable quality/build/load matrices; close security findings before admitting affected images.

## Source of truth

- [Issue #1 — Linux profile and reproducibility](https://github.com/guility/RelRAG/issues/1)
- [Issue #2 — public retrieval quality](https://github.com/guility/RelRAG/issues/2)
- [Issue #3 — builds, load and resources](https://github.com/guility/RelRAG/issues/3)
- [GigaEmbeddings runbook](giga-embeddings/README.md)
