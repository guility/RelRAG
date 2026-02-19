# RelRAG API smoke test
# Usage: .\scripts\test_rag_api.ps1 [-BaseUrl "http://localhost:8000"]
# Requires: docker compose up (API + postgres)
#
# Note: POST /v1/documents and POST /v1/collections/{id}/search require embeddings.
# Set EMBEDDING_API_KEY and EMBEDDING_API_URL (e.g. OpenAI or local) in docker-compose
# for full E2E test. Without it, steps 5-7 may return 500 (expected).

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$headers = @{ "Content-Type" = "application/json" }

function Invoke-Api {
    param([string]$Method, [string]$Path, [object]$Body = $null, [string]$Query = "")
    $uri = "$BaseUrl$Path"
    if ($Query) { $uri += "?$Query" }
    $params = @{
        Method  = $Method
        Uri     = $uri
        Headers = $headers
    }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10) }
    try {
        $r = Invoke-WebRequest @params -UseBasicParsing
        return @{ Status = $r.StatusCode; Content = $r.Content | ConvertFrom-Json }
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd() | ConvertFrom-Json -ErrorAction SilentlyContinue
        return @{ Status = $status; Content = $body; Error = $_.Exception.Message }
    }
}

Write-Host "=== RelRAG API smoke test ===" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl`n"

# 1. Health
Write-Host "1. GET /v1/health" -ForegroundColor Yellow
$r = Invoke-Api -Method GET -Path "/v1/health"
if ($r.Status -eq 200 -and $r.Content.status -eq "ok") {
    Write-Host "   OK (200)" -ForegroundColor Green
} else {
    Write-Host "   FAIL: $($r | ConvertTo-Json -Compress)" -ForegroundColor Red
    exit 1
}

# 2. Health ready
Write-Host "2. GET /v1/health/ready" -ForegroundColor Yellow
$r = Invoke-Api -Method GET -Path "/v1/health/ready"
if ($r.Status -eq 200 -and $r.Content.status -eq "ready") {
    Write-Host "   OK (200)" -ForegroundColor Green
} else {
    Write-Host "   FAIL: $($r | ConvertTo-Json -Compress)" -ForegroundColor Red
    exit 1
}

# 3. Create configuration
Write-Host "3. POST /v1/configurations" -ForegroundColor Yellow
$cfgBody = @{
    chunking_strategy    = "recursive"
    embedding_model      = "text-embedding-3-small"
    embedding_dimensions = 1536
    chunk_size          = 512
    chunk_overlap        = 50
}
$r = Invoke-Api -Method POST -Path "/v1/configurations" -Body $cfgBody
if ($r.Status -eq 201 -and $r.Content.id) {
    $configId = $r.Content.id
    Write-Host "   OK (201) config_id=$configId" -ForegroundColor Green
} else {
    Write-Host "   FAIL: $($r | ConvertTo-Json -Compress)" -ForegroundColor Red
    exit 1
}

# 4. Create collection
Write-Host "4. POST /v1/collections" -ForegroundColor Yellow
$collBody = @{ configuration_id = $configId }
$r = Invoke-Api -Method POST -Path "/v1/collections" -Body $collBody
if ($r.Status -eq 201 -and $r.Content.id) {
    $collectionId = $r.Content.id
    Write-Host "   OK (201) collection_id=$collectionId" -ForegroundColor Green
} else {
    Write-Host "   FAIL: $($r | ConvertTo-Json -Compress)" -ForegroundColor Red
    exit 1
}

# 5. Load document (requires EMBEDDING_API_KEY for real embeddings)
Write-Host "5. POST /v1/documents" -ForegroundColor Yellow
$docBody = @{
    collection_id = $collectionId
    content       = "RelRAG is a RAG framework for PostgreSQL and pgvector. It supports hybrid search."
    properties    = @{}
}
$r = Invoke-Api -Method POST -Path "/v1/documents" -Body $docBody
if ($r.Status -eq 201 -and $r.Content.id) {
    $documentId = $r.Content.id
    Write-Host "   OK (201) document_id=$documentId" -ForegroundColor Green
} else {
    Write-Host "   Response: $($r.Status) - $($r.Content | ConvertTo-Json -Compress)" -ForegroundColor Yellow
    if ($r.Content.error) { Write-Host "   Error: $($r.Content.error)" -ForegroundColor Yellow }
    if ($r.Status -eq 403 -or $r.Status -eq 500) {
        Write-Host "   (Embedding API may require EMBEDDING_API_KEY)" -ForegroundColor Gray
    }
    $documentId = $null
}

# 6. Get document (if we have one)
if ($documentId) {
    Write-Host "6. GET /v1/documents/$documentId?collection_id=$collectionId" -ForegroundColor Yellow
    $r = Invoke-Api -Method GET -Path "/v1/documents/$documentId" -Query "collection_id=$collectionId"
    if ($r.Status -eq 200 -and $r.Content.id -eq $documentId) {
        Write-Host "   OK (200)" -ForegroundColor Green
    } else {
        Write-Host "   FAIL: $($r | ConvertTo-Json -Compress)" -ForegroundColor Red
    }
} else {
    Write-Host "6. GET /v1/documents/{id} - SKIP (no document)" -ForegroundColor Gray
}

# 7. Hybrid search
Write-Host "7. POST /v1/collections/$collectionId/search" -ForegroundColor Yellow
$searchBody = @{
    query         = "PostgreSQL vector search"
    vector_weight = 0.7
    fts_weight    = 0.3
    limit         = 5
}
$r = Invoke-Api -Method POST -Path "/v1/collections/$collectionId/search" -Body $searchBody
if ($r.Status -eq 200 -and $null -ne $r.Content.results) {
    Write-Host "   OK (200) results=$($r.Content.results.Count)" -ForegroundColor Green
} else {
    Write-Host "   Response: $($r.Status) - $($r.Content | ConvertTo-Json -Compress)" -ForegroundColor Yellow
    if ($r.Content.error) { Write-Host "   Error: $($r.Content.error)" -ForegroundColor Yellow }
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
