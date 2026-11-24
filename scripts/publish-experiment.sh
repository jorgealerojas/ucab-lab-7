#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_state
data_dir="$REPO_ROOT/generated/$(lab_id)"
[[ -f "$data_dir/metrics.json" ]] || die "prepare primero el experimento"
run_python "$REPO_ROOT/scripts/publish_prepared.py" \
  --config "$REPO_ROOT/config/pipeline.json" \
  --state-dir "$STATE_DIR" \
  --data-dir "$data_dir"
printf 'La regla IoT escribe cada lote aceptado directamente en S3 Bronze.\n'
