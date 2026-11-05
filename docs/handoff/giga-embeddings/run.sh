#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${ARAG_ROOT:?Set ARAG_ROOT to the Linux ARAG source checkout}"
ARAG_ROOT="$(cd -- "$ARAG_ROOT" && pwd)"
export ARAG_ROOT
compose_file="$script_dir/compose.yaml"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'docker CLI is required' >&2
  exit 127
fi
for required in \
  deploy/Dockerfiles/models/Dockerfile.giga \
  deploy/Dockerfiles/models/Dockerfile.giga-gpu \
  deploy/locks/giga-gpu/uv.lock \
  deploy/litellm/giga-embeddings.yaml \
  scripts/v3/giga_embeddings/metadata/model.json; do
  if [[ ! -f "$ARAG_ROOT/$required" ]]; then
    printf 'ARAG_ROOT is missing required source file: %s\n' "$required" >&2
    exit 2
  fi
done

compose() {
  docker compose --project-directory "$ARAG_ROOT" --file "$compose_file" --profile giga-embeddings "$@"
}

case "${1:-up}" in
  download)
    compose run --build --rm giga-download
    ;;
  up)
    compose run --build --rm giga-download
    compose up --build --detach giga-embedding litellm-gateway
    compose ps --all
    ;;
  down)
    compose stop litellm-gateway giga-embedding
    ;;
  status)
    compose ps --all
    ;;
  health)
    compose exec -T litellm-gateway python -c 'import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen("http://giga-embedding:8000/healthz",timeout=5)),indent=2))'
    ;;
  batch)
    if [[ -t 0 ]]; then
      printf '%s\n' 'pipe one JSON embeddings request to stdin' >&2
      exit 2
    fi
    compose exec -T -i litellm-gateway python -c 'import os,sys,urllib.request; body=sys.stdin.buffer.read(); request=urllib.request.Request("http://127.0.0.1:4000/v1/embeddings",data=body,headers={"Authorization":"Bearer "+os.environ["LITELLM_MASTER_KEY"],"Content-Type":"application/json"}); sys.stdout.buffer.write(urllib.request.urlopen(request,timeout=120).read())'
    ;;
  *)
    printf 'usage: %s [download|up|down|status|health|batch]\n' "$0" >&2
    exit 2
    ;;
esac
