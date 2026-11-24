#!/usr/bin/env bash
set -Eeuo pipefail

LAB_REGION="us-east-2"
LAB_PREFIX="ucab-lab-7"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$REPO_ROOT/.lab"
# LAB_PREFIX is consumed by scripts that source this file.
# shellcheck disable=SC2034
readonly LAB_REGION LAB_PREFIX SCRIPT_DIR REPO_ROOT STATE_DIR

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "falta el comando requerido: $1"
}

python_bin() {
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
  else
    command -v python3
  fi
}

run_python() {
  local interpreter
  interpreter="$(python_bin)" || die "falta el comando requerido: python3"
  "$interpreter" "$@"
}

effective_region() {
  if [[ -n "${AWS_REGION:-}" ]]; then
    printf '%s\n' "$AWS_REGION"
  elif [[ -n "${AWS_DEFAULT_REGION:-}" ]]; then
    printf '%s\n' "$AWS_DEFAULT_REGION"
  else
    aws configure get region 2>/dev/null || true
  fi
}

require_region() {
  local current
  current="$(effective_region)"
  [[ "$current" == "$LAB_REGION" ]] || die "seleccione $LAB_REGION; region actual: ${current:-sin configurar}"
  export AWS_REGION="$LAB_REGION"
  export AWS_DEFAULT_REGION="$LAB_REGION"
}

require_state() {
  [[ -f "$STATE_DIR/stack-name" ]] || die "no existe .lab/stack-name; despliegue primero el laboratorio"
}

stack_name() {
  require_state
  tr -d '\r\n' < "$STATE_DIR/stack-name"
}

lab_id() {
  require_state
  tr -d '\r\n' < "$STATE_DIR/lab-id"
}

stack_output() {
  local key="$1"
  run_python - "$STATE_DIR/outputs.json" "$key" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    outputs = json.load(stream)
try:
    print(outputs[sys.argv[2]])
except KeyError as exc:
    raise SystemExit(f"output ausente: {exc.args[0]}")
PY
}
