#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_command aws
require_command openssl
require_command python3
require_region

if [[ -f "$STATE_DIR/stack-name" ]]; then
  die "ya existe un laboratorio registrado en .lab; limpielo antes de crear otro"
fi
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

show_stack_failure() {
  local failed_stack="$1"
  printf '\nCAUSA REPORTADA POR CLOUDFORMATION:\n' >&2
  # shellcheck disable=SC2016
  aws cloudformation describe-stack-events \
    --stack-name "$failed_stack" \
    --region "$LAB_REGION" \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceType,ResourceStatusReason]' \
    --output table >&2 || \
    printf 'No fue posible consultar los eventos del stack. Revise CloudFormation > Events.\n' >&2
}

rollback() {
  local exit_code=$?
  if [[ $exit_code -eq 0 ]]; then
    return
  fi
  printf '\nEl despliegue fallo; iniciando limpieza segura.\n' >&2
  run_python "$REPO_ROOT/scripts/manage_identities.py" cleanup --state-dir "$STATE_DIR" || true
  if [[ -f "$STATE_DIR/stack-name" ]]; then
    local failed_stack
    failed_stack="$(tr -d '\r\n' < "$STATE_DIR/stack-name")"
    if aws cloudformation describe-stacks --stack-name "$failed_stack" --region "$LAB_REGION" >/dev/null 2>&1; then
      aws cloudformation delete-stack --stack-name "$failed_stack" --region "$LAB_REGION" || true
      aws cloudformation wait stack-delete-complete --stack-name "$failed_stack" --region "$LAB_REGION" || true
    fi
  fi
  rm -f "$STATE_DIR/stack-name" "$STATE_DIR/lab-id" "$STATE_DIR/stack.json" "$STATE_DIR/outputs.json"
  rmdir "$STATE_DIR/certs" 2>/dev/null || true
  rmdir "$STATE_DIR" 2>/dev/null || true
  exit "$exit_code"
}
trap rollback EXIT

lab_identifier="$(openssl rand -hex 8)"
new_stack_name="$LAB_PREFIX-$lab_identifier"
if aws cloudformation describe-stacks --stack-name "$new_stack_name" --region "$LAB_REGION" >/dev/null 2>&1; then
  die "colision inesperada del identificador; ejecute nuevamente"
fi
printf '%s\n' "$new_stack_name" > "$STATE_DIR/stack-name"
printf '%s\n' "$lab_identifier" > "$STATE_DIR/lab-id"

printf 'Identificador generado: %s\n' "$new_stack_name"
printf 'Creando IoT Core, Data Lake, Glue y Athena...\n'
aws cloudformation create-stack \
  --stack-name "$new_stack_name" \
  --region "$LAB_REGION" \
  --template-body "file://$REPO_ROOT/infra/lab-stack.yaml" \
  --parameters "ParameterKey=LabId,ParameterValue=$lab_identifier" \
  --capabilities CAPABILITY_IAM \
  --tags Key=Course,Value=INFO-02028 Key=Lab,Value=7 Key=LabId,Value="$lab_identifier" >/dev/null

if ! aws cloudformation wait stack-create-complete \
  --stack-name "$new_stack_name" \
  --region "$LAB_REGION"; then
  show_stack_failure "$new_stack_name"
  exit 1
fi
aws cloudformation describe-stacks \
  --stack-name "$new_stack_name" \
  --region "$LAB_REGION" \
  --output json > "$STATE_DIR/stack.json"
run_python "$REPO_ROOT/scripts/save_outputs.py" "$STATE_DIR/stack.json" "$STATE_DIR/outputs.json"

policy_name="$(stack_output DevicePolicyName)"
edge_thing="$(stack_output EdgeThingName)"
fog_thing="$(stack_output FogThingName)"
run_python "$REPO_ROOT/scripts/manage_identities.py" provision \
  --state-dir "$STATE_DIR" \
  --region "$LAB_REGION" \
  --policy "$policy_name" \
  --edge-thing "$edge_thing" \
  --fog-thing "$fog_thing"

trap - EXIT
printf '\nLABORATORIO LISTO: %s\n' "$new_stack_name"
printf 'Anote el identificador y complete config/pipeline.json mediante la mision de descubrimiento.\n'
printf 'Siguiente paso: ./scripts/status.sh\n'
