#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_command python3
require_region
require_state

[[ $# -eq 1 ]] || die "uso: ./scripts/run-query.sh <archivo.sql>"
query_file="$1"
[[ -f "$query_file" ]] || die "no existe la consulta: $query_file"
run_python "$REPO_ROOT/scripts/run_athena_query.py" \
  --file "$query_file" \
  --outputs "$STATE_DIR/outputs.json" \
  --region "$LAB_REGION"
