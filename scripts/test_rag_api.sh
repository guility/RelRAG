#!/usr/bin/env bash
# RelRAG API smoke test
# Usage: ./scripts/test_rag_api.sh [BASE_URL]
# Requires: docker compose up (API + postgres)

set -e
BASE_URL="${1:-http://localhost:8000}"

api() {
    local method="$1" path="$2" body="$3"
    local url="${BASE_URL}${path}"
    if [[ -n "$body" ]]; then
        curl -s -w "\n%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$body" "$url"
    else
        curl -s -w "\n%{http_code}" -X "$method" "$url"
    fi
}

check() {
    local name="$1" expected="$2" body="$3"
    local status
    status=$(echo "$body" | tail -n1)
    if [[ "$status" == "$expected" ]]; then
        echo "   OK ($status)"
    else
        echo "   FAIL: $status"
        echo "$body" | head -n -1
        exit 1
    fi
}

echo "=== RelRAG API smoke test ==="
echo "Base URL: $BASE_URL"
echo ""

# 1. Health
echo "1. GET /v1/health"
r=$(api GET /v1/health)
check "health" "200" "$r"

# 2. Health ready
echo "2. GET /v1/health/ready"
r=$(api GET /v1/health/ready)
check "health/ready" "200" "$r"

# 3. Create configuration
echo "3. POST /v1/configurations"
r=$(api POST /v1/configurations '{"chunking_strategy":"recursive","embedding_model":"text-embedding-3-small","embedding_dimensions":1536,"chunk_size":512,"chunk_overlap":50}')
status=$(echo "$r" | tail -n1)
if [[ "$status" == "201" ]]; then
    config_id=$(echo "$r" | head -n -1 | jq -r '.id')
    echo "   OK (201) config_id=$config_id"
else
    echo "   FAIL: $status"
    echo "$r" | head -n -1
    exit 1
fi

# 4. Create collection
echo "4. POST /v1/collections"
r=$(api POST /v1/collections "{\"configuration_id\":\"$config_id\"}")
status=$(echo "$r" | tail -n1)
if [[ "$status" == "201" ]]; then
    coll_id=$(echo "$r" | head -n -1 | jq -r '.id')
    echo "   OK (201) collection_id=$coll_id"
else
    echo "   FAIL: $status"
    echo "$r" | head -n -1
    exit 1
fi

# 5. Load document
echo "5. POST /v1/documents"
r=$(api POST /v1/documents "{\"collection_id\":\"$coll_id\",\"content\":\"RelRAG is a RAG framework for PostgreSQL and pgvector. It supports hybrid search.\",\"properties\":{}}")
status=$(echo "$r" | tail -n1)
if [[ "$status" == "201" ]]; then
    doc_id=$(echo "$r" | head -n -1 | jq -r '.id')
    echo "   OK (201) document_id=$doc_id"
else
    echo "   Response: $status"
    echo "$r" | head -n -1 | jq -r '.error // .'
    doc_id=""
fi

# 6. Get document
if [[ -n "$doc_id" ]]; then
    echo "6. GET /v1/documents/$doc_id?collection_id=$coll_id"
    r=$(api GET "/v1/documents/$doc_id?collection_id=$coll_id")
    check "get document" "200" "$r"
else
    echo "6. GET /v1/documents/{id} - SKIP (no document)"
fi

# 7. Hybrid search
echo "7. POST /v1/collections/$coll_id/search"
r=$(api POST /v1/collections/$coll_id/search '{"query":"PostgreSQL vector search","vector_weight":0.7,"fts_weight":0.3,"limit":5}')
status=$(echo "$r" | tail -n1)
if [[ "$status" == "200" ]]; then
    count=$(echo "$r" | head -n -1 | jq '.results | length')
    echo "   OK (200) results=$count"
else
    echo "   Response: $status"
    echo "$r" | head -n -1 | jq -r '.error // .'
fi

echo ""
echo "=== Done ==="
