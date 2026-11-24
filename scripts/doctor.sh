#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

for command in aws python3 curl openssl; do
  require_command "$command"
  printf 'OK: %s disponible\n' "$command"
done
require_region
printf 'OK: region %s\n' "$LAB_REGION"

aws sts get-caller-identity --query 'Account' --output text >/dev/null
printf 'OK: credenciales AWS vigentes\n'

"$REPO_ROOT/scripts/bootstrap-python.sh"
run_python -m pytest "$REPO_ROOT/tests" -q
printf 'OK: pruebas unitarias\n'

if command -v cfn-lint >/dev/null 2>&1; then
  cfn-lint "$REPO_ROOT/infra/lab-stack.yaml"
  printf 'OK: CloudFormation validado con cfn-lint\n'
else
  run_python "$REPO_ROOT/scripts/validate_repository.py" --cloudformation-only
  printf 'OK: estructura CloudFormation validada localmente\n'
fi

aws cloudformation validate-template \
  --region "$LAB_REGION" \
  --template-body "file://$REPO_ROOT/infra/lab-stack.yaml" >/dev/null
printf 'OK: AWS acepto la sintaxis de CloudFormation\n'
printf 'DIAGNOSTICO APROBADO: entorno listo en %s\n' "$LAB_REGION"
