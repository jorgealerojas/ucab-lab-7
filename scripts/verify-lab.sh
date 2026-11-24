#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_region
require_state

metrics="$REPO_ROOT/generated/$(lab_id)/metrics.json"
[[ -f "$metrics" ]] || die "no existen metricas; ejecute primero el experimento"
extra=()
if [[ "${1:-}" == "--require-silver" ]]; then
  extra+=("--require-silver")
elif [[ $# -ne 0 ]]; then
  die "uso: ./scripts/verify-lab.sh [--require-silver]"
fi
run_python "$REPO_ROOT/scripts/verify_cloud.py" \
  --outputs "$STATE_DIR/outputs.json" \
  --metrics "$metrics" \
  --region "$LAB_REGION" \
  "${extra[@]}"
