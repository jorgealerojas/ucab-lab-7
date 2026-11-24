#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_state
config_file="$REPO_ROOT/config/pipeline.json"
[[ -f "$config_file" ]] || die "falta config/pipeline.json; complete la mision de descubrimiento"
output_dir="$REPO_ROOT/generated/$(lab_id)"
run_python "$REPO_ROOT/scripts/prepare_experiment.py" \
  --config "$config_file" \
  --outputs "$STATE_DIR/outputs.json" \
  --output "$output_dir"
