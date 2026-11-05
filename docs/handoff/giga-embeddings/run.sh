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
if [[ ! -f "$ARAG_ROOT/deploy/composes/tests/compose.stage0.yaml" ]]; then
  printf '%s\n' 'ARAG_ROOT is not an ARAG source checkout' >&2
  exit 2
fi

compose() {
  docker compose --project-directory "$ARAG_ROOT" --file "$compose_file" "$@"
}

case "${1:-up}" in
  download)
    compose --profile giga-embeddings run --build --rm giga-download
    ;;
  up)
    compose --profile giga-embeddings run --build --rm giga-download
    compose --profile benchmark-miracl-embedding up --build -d giga-embedding litellm-gateway
    compose --profile benchmark-miracl-embedding ps --all
    ;;
  down)
    compose --profile benchmark-miracl-embedding stop litellm-gateway giga-embedding
    ;;
  status)
    compose --profile benchmark-miracl-embedding ps --all
    ;;
  *)
    printf 'usage: %s [download|up|down|status]\n' "$0" >&2
    exit 2
    ;;
esac
