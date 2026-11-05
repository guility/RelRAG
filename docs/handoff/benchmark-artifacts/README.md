# Benchmark summaries and provenance

Selected ARAG benchmark export, snapshot 2026-11-05.

Included:

- 350 summary/aggregate CSV and JSON files (659,765 bytes).
- 10 screening summary CSV/JSON files (25,878 bytes).
- 19 manifest/provenance JSON files (48,539 bytes).
- quality-runs/run-register.csv (10,789 bytes).

The bundle contains 380 CSV/JSON files in total (744,971 bytes, about 0.71 MiB). Paths below giga-benchmarks/ preserve the source catalog layout. manifest.json records each file's class, byte length, SHA-256 and JSON status when available, plus source snapshot provenance. All copied files were SHA-256 checked against their source.

The source data was collected from ARAG branch 0012_shared_gpu_embeddings_service at commit e7bbaf4fffdb1bcfd991c12fa02a65279991f913. Some generated outputs were untracked, so the per-file hashes identify the exact transferred contents; the source commit alone does not.

Warm-up-only summaries, raw resource/transaction/sample telemetry, failure/progress/debug/probe files, and other per-run detail records are excluded. Screening summaries are retained as evidence for the agreed early cutoff. Consult quality-runs/run-register.csv and the matching JSON status before treating a run as complete; completed_with_degradation remains a degraded outcome.

Verify from the repository root:

```bash
jq -r '.files[] | "\(.sha256)  docs/handoff/benchmark-artifacts/\(.path)"' docs/handoff/benchmark-artifacts/manifest.json | sha256sum -c -
```

The consolidated research plan, current status, interim results and accepted intermediate decisions are in [retrieval-benchmark-status.md](../retrieval-benchmark-status.md). No production backend has been selected.
