#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_command python3
require_command curl
require_region
require_state

"$REPO_ROOT/scripts/prepare-experiment.sh"
"$REPO_ROOT/scripts/publish-experiment.sh"
