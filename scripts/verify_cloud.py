#!/usr/bin/env python3
"""Verificacion integral de recursos y resultados sin modificar datos."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3


class VerificationError(AssertionError):
    pass


def ok(message: str) -> None:
    print(f"OK: {message}")


def verify(args: argparse.Namespace) -> None:
    outputs = json.loads(args.outputs.read_text(encoding="utf-8"))
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    session = boto3.session.Session(region_name=args.region)
    s3 = session.client("s3")
    iot = session.client("iot")
    glue = session.client("glue")
    athena = session.client("athena")

    rule = iot.get_topic_rule(ruleName=outputs["TopicRuleName"])["rule"]
    if rule.get("ruleDisabled"):
        raise VerificationError("la regla IoT esta deshabilitada")
    ok("regla IoT habilitada")

    actions = rule.get("actions", [])
    if not any("s3" in action for action in actions):
        raise VerificationError("la regla IoT no contiene la accion S3 esperada")
    ok("regla IoT conectada directamente con S3 Bronze")

    deadline = time.monotonic() + args.wait_seconds
    objects = []
    while time.monotonic() < deadline:
        response = s3.list_objects_v2(Bucket=outputs["DataLakeBucketName"], Prefix="bronze/")
        objects = response.get("Contents", [])
        if objects:
            break
        time.sleep(5)
    if not objects:
        raise VerificationError("la regla IoT aun no entrego objetos en bronze/")
    ok(f"zona bronze contiene {len(objects)} objeto(s) visibles")

    database = outputs["DatabaseName"]
    tables = {
        item["Name"]
        for item in glue.get_tables(DatabaseName=database)["TableList"]
    }
    if "bronze_telemetry" not in tables:
        raise VerificationError("falta bronze_telemetry")
    if args.require_silver and "silver_telemetry" not in tables:
        raise VerificationError("falta silver_telemetry; complete la mision CTAS")
    ok("catalogo Glue contiene las tablas requeridas")

    workgroup = athena.get_work_group(WorkGroup=outputs["AthenaWorkGroupName"])["WorkGroup"]
    if workgroup["State"] != "ENABLED":
        raise VerificationError("workgroup Athena deshabilitado")
    ok("workgroup Athena habilitado")

    edge_count = metrics["edge"]["accepted"]
    fog_count = metrics["fog"]["unique_events"]
    if edge_count <= fog_count:
        raise VerificationError("Fog no redujo la cantidad de eventos")
    if metrics["fog"]["represented_samples"] != edge_count:
        raise VerificationError("Fog perdio muestras aceptadas")
    ok(f"Fog redujo {edge_count} eventos Edge a {fog_count} resumenes sin perder muestras")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--wait-seconds", type=int, default=90)
    parser.add_argument("--require-silver", action="store_true")
    args = parser.parse_args()
    try:
        verify(args)
    except (VerificationError, KeyError, IndexError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("VERIFICACION APROBADA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
