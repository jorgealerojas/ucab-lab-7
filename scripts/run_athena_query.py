#!/usr/bin/env python3
"""Ejecuta SQL con el workgroup propio y muestra evidencia de costo/rendimiento."""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from pathlib import Path

import boto3


def render_sql(template: str, outputs: dict[str, str]) -> str:
    replacements = {
        "{{DATABASE}}": outputs["DatabaseName"],
        "{{BUCKET}}": outputs["DataLakeBucketName"],
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    if re.search(r"\bTODO_[A-Z_]+\b", rendered) or "{{" in rendered or "}}" in rendered:
        raise ValueError("la consulta conserva TODO o marcadores sin resolver")
    return rendered


def wait_for_query(client, query_id: str, timeout: int = 180) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get_query_execution(QueryExecutionId=query_id)
        state = response["QueryExecution"]["Status"]["State"]
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return response["QueryExecution"]
        time.sleep(2)
    client.stop_query_execution(QueryExecutionId=query_id)
    raise TimeoutError("Athena excedio el tiempo maximo de espera")


def result_rows(client, query_id: str, limit: int = 20) -> list[list[str]]:
    response = client.get_query_results(QueryExecutionId=query_id, MaxResults=limit)
    return [
        [cell.get("VarCharValue", "NULL") for cell in row.get("Data", [])]
        for row in response.get("ResultSet", {}).get("Rows", [])
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--region", default="us-east-2")
    args = parser.parse_args()
    outputs = json.loads(args.outputs.read_text(encoding="utf-8"))
    sql = render_sql(args.file.read_text(encoding="utf-8"), outputs)
    statements = [part.strip() for part in sql.split(";") if part.strip()]
    if len(statements) != 1:
        raise SystemExit("cada archivo debe contener exactamente una sentencia SQL")
    client = boto3.client("athena", region_name=args.region)
    response = client.start_query_execution(
        QueryString=statements[0],
        QueryExecutionContext={"Database": outputs["DatabaseName"]},
        WorkGroup=outputs["AthenaWorkGroupName"],
        ClientRequestToken=f"ucab-lab-7-{uuid.uuid4().hex}",
    )
    query_id = response["QueryExecutionId"]
    execution = wait_for_query(client, query_id)
    status = execution["Status"]
    if status["State"] != "SUCCEEDED":
        raise SystemExit(f"Athena {status['State']}: {status.get('StateChangeReason', 'sin detalle')}")
    statistics = execution.get("Statistics", {})
    print(f"QueryExecutionId: {query_id}")
    print(f"Bytes leidos: {statistics.get('DataScannedInBytes', 0)}")
    print(f"Tiempo del motor: {statistics.get('EngineExecutionTimeInMillis', 0)} ms")
    for row in result_rows(client, query_id):
        print("\t".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
