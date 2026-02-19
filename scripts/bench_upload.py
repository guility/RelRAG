#!/usr/bin/env python3
"""Benchmark document upload: throughput (docs/s) and latency.

Usage:
  From host (API on localhost):
    export API_URL=http://localhost:8000 KEYCLOAK_URL=http://localhost:8080
    export KEYCLOAK_REALM=relrag KEYCLOAK_CLIENT_ID=relrag-api KEYCLOAK_CLIENT_SECRET=relrag-api-secret
    export BENCH_USER=testuser BENCH_PASSWORD=testpass
    uv run python scripts/bench_upload.py [--num-docs 100] [--content-size 500]

  From bench-runner container:
    docker compose -f docker-compose.bench.yml --profile bench run --rm bench-runner \\
      python scripts/bench_upload.py --num-docs 100
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time

import httpx


def get_token(
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str:
    url = f"{keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
    r = httpx.post(
        url,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark document upload")
    parser.add_argument("--num-docs", type=int, default=50, help="Number of documents to upload")
    parser.add_argument("--content-size", type=int, default=200, help="Approximate content length per doc")
    parser.add_argument("--output", type=str, default="/results/bench_upload.txt", help="Output file path")
    args = parser.parse_args()

    api_url = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
    keycloak_url = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.environ.get("KEYCLOAK_REALM", "relrag")
    client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "relrag-api")
    client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "relrag-api-secret")
    user = os.environ.get("BENCH_USER", "testuser")
    password = os.environ.get("BENCH_PASSWORD", "testpass")

    print("Getting token...")
    token = get_token(keycloak_url, realm, client_id, client_secret, user, password)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create configuration and collection
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{api_url}/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
            headers=headers,
        )
        r.raise_for_status()
        config_id = r.json()["id"]
        r = client.post(
            f"{api_url}/v1/collections",
            json={"configuration_id": config_id},
            headers=headers,
        )
        r.raise_for_status()
        collection_id = r.json()["id"]

    content = "x" * args.content_size
    latencies: list[float] = []
    errors = 0

    print(f"Uploading {args.num_docs} documents (content size ~{args.content_size} chars)...")
    start_total = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        for i in range(args.num_docs):
            t0 = time.perf_counter()
            r = client.post(
                f"{api_url}/v1/documents",
                json={
                    "collection_id": collection_id,
                    "content": f"{content} doc_{i}",
                    "properties": {},
                },
                headers=headers,
            )
            elapsed = time.perf_counter() - t0
            if r.status_code in (200, 201):
                latencies.append(elapsed)
            else:
                errors += 1
    total_elapsed = time.perf_counter() - start_total

    n = len(latencies)
    if n == 0:
        print("No successful uploads.")
        return 1

    docs_per_sec = n / total_elapsed
    total_chars = n * (args.content_size + 10)
    mb_per_sec = (total_chars / 1_000_000) / total_elapsed if total_elapsed else 0
    p50 = statistics.median(latencies) * 1000
    p95 = sorted(latencies)[int(n * 0.95) - 1] * 1000 if n >= 20 else p50
    p99 = sorted(latencies)[int(n * 0.99) - 1] * 1000 if n >= 100 else p95

    summary = (
        f"Upload benchmark (n={n}, errors={errors})\n"
        f"  Throughput: {docs_per_sec:.2f} docs/s, ~{mb_per_sec:.4f} MB/s (text)\n"
        f"  Latency: p50={p50:.1f} ms, p95={p95:.1f} ms, p99={p99:.1f} ms\n"
        f"  Total time: {total_elapsed:.2f} s\n"
    )
    print(summary)

    try:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"Wrote {args.output}")
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
