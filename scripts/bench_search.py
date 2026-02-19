#!/usr/bin/env python3
"""Benchmark search: latency (p50, p95, p99) and QPS.

Usage:
  From host:
    export API_URL=http://localhost:8000 KEYCLOAK_URL=... (same as bench_upload.py)
    uv run python scripts/bench_search.py [--num-docs 500] [--num-queries 100]

  From bench-runner container:
    docker compose -f docker-compose.bench.yml --profile bench run --rm bench-runner \\
      python scripts/bench_search.py --num-docs 500 --num-queries 100
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
    parser = argparse.ArgumentParser(description="Benchmark search")
    parser.add_argument("--num-docs", type=int, default=200, help="Documents to add to collection before search")
    parser.add_argument("--num-queries", type=int, default=50, help="Number of search requests")
    parser.add_argument("--output", type=str, default="/results/bench_search.txt", help="Output file path")
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

        print(f"Seeding {args.num_docs} documents...")
        for i in range(args.num_docs):
            client.post(
                f"{api_url}/v1/documents",
                json={
                    "collection_id": collection_id,
                    "content": f"Benchmark document content {i} for search test.",
                    "properties": {},
                },
                headers=headers,
            ).raise_for_status()

    latencies: list[float] = []
    errors = 0
    print(f"Running {args.num_queries} search requests...")
    start_total = time.perf_counter()
    with httpx.Client(timeout=30.0) as client:
        for _ in range(args.num_queries):
            t0 = time.perf_counter()
            r = client.post(
                f"{api_url}/v1/collections/{collection_id}/search",
                json={"query": "benchmark search", "limit": 10},
                headers=headers,
            )
            elapsed = time.perf_counter() - t0
            if r.status_code == 200:
                latencies.append(elapsed)
            else:
                errors += 1
    total_elapsed = time.perf_counter() - start_total

    n = len(latencies)
    if n == 0:
        print("No successful searches.")
        return 1

    qps = n / total_elapsed
    p50 = statistics.median(latencies) * 1000
    p95 = sorted(latencies)[int(n * 0.95) - 1] * 1000 if n >= 20 else p50
    p99 = sorted(latencies)[int(n * 0.99) - 1] * 1000 if n >= 100 else p95

    summary = (
        f"Search benchmark (collection size={args.num_docs}, queries={n}, errors={errors})\n"
        f"  QPS: {qps:.2f}\n"
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
