#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_state
[[ -f "$REPO_ROOT/config/pipeline.json" ]] || die "falta config/pipeline.json"
run_python "$REPO_ROOT/scripts/validate_config.py" \
  --config "$REPO_ROOT/config/pipeline.json" \
  --outputs "$STATE_DIR/outputs.json"
