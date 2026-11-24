#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

if [[ -x "$VENV_DIR/bin/python" ]] && \
  "$VENV_DIR/bin/python" -c 'import boto3, pytest, pytest_cov, yaml' >/dev/null 2>&1; then
  printf 'OK: dependencias Python disponibles en .venv\n'
  exit 0
fi

printf 'Preparando dependencias Python en .venv (solo en la primera ejecucion)...\n'
python3 -m venv "$VENV_DIR" || {
  printf 'ERROR: Python no pudo crear .venv. Verifique que el modulo venv este disponible.\n' >&2
  exit 1
}
"$VENV_DIR/bin/python" -m pip install \
  --disable-pip-version-check \
  --quiet \
  --requirement "$REPO_ROOT/requirements.txt" || {
  printf 'ERROR: no fue posible instalar las dependencias Python. Verifique la conexion de CloudShell.\n' >&2
  exit 1
}
"$VENV_DIR/bin/python" -c 'import boto3, pytest, pytest_cov, yaml'
printf 'OK: dependencias Python instaladas en .venv\n'
