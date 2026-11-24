#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_command aws
require_command python3
require_region
require_state

current_stack="$(stack_name)"
current_lab_id="$(lab_id)"
[[ "$current_stack" == "$LAB_PREFIX-$current_lab_id" ]] || die "estado local inconsistente; no se eliminara nada"
[[ "$current_lab_id" =~ ^[0-9a-f]{16}$ ]] || die "LabId invalido; no se eliminara nada"
bucket="$(stack_output DataLakeBucketName)"
database="$(stack_output DatabaseName)"
[[ "$bucket" == "$LAB_PREFIX-"*"-$LAB_REGION-$current_lab_id" ]] || die "bucket fuera del laboratorio registrado"
[[ "$database" == "ucab_lab_7_$current_lab_id" ]] || die "base Glue fuera del laboratorio registrado"

printf 'Laboratorio seleccionado: %s\n' "$current_stack"
run_python "$REPO_ROOT/scripts/manage_identities.py" cleanup --state-dir "$STATE_DIR"

# CTAS y las vistas creadas por el estudiante no pertenecen a CloudFormation.
for table in gold_trip_metrics silver_telemetry; do
  aws glue delete-table --database-name "$database" --name "$table" --region "$LAB_REGION" 2>/dev/null || true
done

deleted="$(run_python "$REPO_ROOT/scripts/empty_versioned_bucket.py" --bucket "$bucket" --region "$LAB_REGION")"
printf 'Versiones y objetos eliminados del bucket propio: %s\n' "$deleted"
aws cloudformation delete-stack --stack-name "$current_stack" --region "$LAB_REGION"
aws cloudformation wait stack-delete-complete --stack-name "$current_stack" --region "$LAB_REGION"

rm -f "$STATE_DIR/stack-name" "$STATE_DIR/lab-id" "$STATE_DIR/stack.json" "$STATE_DIR/outputs.json"
rmdir "$STATE_DIR/certs" 2>/dev/null || true
rmdir "$STATE_DIR" 2>/dev/null || true
printf 'LIMPIEZA COMPLETA: %s\n' "$current_stack"
