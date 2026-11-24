#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_command aws
require_region
require_state

current_stack="$(stack_name)"
aws cloudformation describe-stacks \
  --stack-name "$current_stack" \
  --region "$LAB_REGION" \
  --query 'Stacks[0].{Stack:StackName,Estado:StackStatus}' \
  --output table

printf '\nRecursos que debe localizar durante la mision:\n'
# shellcheck disable=SC2016
aws cloudformation describe-stack-resources \
  --stack-name "$current_stack" \
  --region "$LAB_REGION" \
  --query 'StackResources[?ResourceType==`AWS::IoT::TopicRule` || ResourceType==`AWS::S3::Bucket` || ResourceType==`AWS::Glue::Database` || ResourceType==`AWS::Athena::WorkGroup`].[ResourceType,PhysicalResourceId,ResourceStatus]' \
  --output table

printf '\nIdentidades X.509 activas del laboratorio:\n'
run_python - "$STATE_DIR/identities.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    state = json.load(stream)
for item in state["identities"]:
    print(f"- {item['layer']}: {item['thing_name']} / certificado {item['certificate_id'][:12]}...")
PY
