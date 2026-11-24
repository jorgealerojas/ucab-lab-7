#!/usr/bin/env python3
"""Comprobaciones estaticas sin credenciales ni acceso de red."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class CfnLoader(yaml.SafeLoader):
    pass


def unknown_tag(loader: CfnLoader, tag_suffix: str, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


CfnLoader.add_multi_constructor("!", unknown_tag)


def validate_cloudformation(errors: list[str]) -> None:
    path = ROOT / "infra/lab-stack.yaml"
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=CfnLoader)
    except Exception as exc:
        errors.append(f"CloudFormation no es YAML valido: {exc}")
        return
    resources = document.get("Resources", {})
    required_types = {
        "AWS::S3::Bucket",
        "AWS::IoT::TopicRule",
        "AWS::IoT::Policy",
        "AWS::IoT::Thing",
        "AWS::Glue::Database",
        "AWS::Glue::Table",
        "AWS::Athena::WorkGroup",
    }
    actual_types = {resource.get("Type") for resource in resources.values()}
    for missing in sorted(required_types - actual_types):
        errors.append(f"falta recurso {missing}")
    content = path.read_text(encoding="utf-8")
    for expected in (
        "us-east-2",
        "BlockPublicAcls: true",
        "BytesScannedCutoffPerQuery",
        "EnforceWorkGroupConfiguration: false",
    ):
        if expected not in content:
            errors.append(f"CloudFormation no contiene {expected}")
    if re.search(r"Action:\s*['\"]?\*", content):
        errors.append("se encontro Action: *")
    if re.search(r"Resource:\s*['\"]?\*", content):
        errors.append("se encontro Resource: *")
    if "AWS::KinesisFirehose::DeliveryStream" in content or "firehose:" in content.lower():
        errors.append("la plantilla usa Firehose, bloqueado por la politica de las cuentas estudiantiles")


def validate_repository(errors: list[str]) -> None:
    required = [
        "README.md",
        "LAB_GUIDE.md",
        "TROUBLESHOOTING.md",
        "infra/lab-stack.yaml",
        "evidence/evidence-template.md",
        "scripts/deploy-lab.sh",
        "scripts/cleanup-lab.sh",
        "scripts/verify-lab.sh",
        "queries/02-silver-ctas-template.sql",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"falta {relative}")
    for path in (ROOT / "scripts").glob("*.sh"):
        if not path.stat().st_mode & 0o111:
            errors.append(f"script no ejecutable: {path.relative_to(ROOT)}")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for secret_path in (".lab/", "config/pipeline.json"):
        if secret_path not in gitignore:
            errors.append(f".gitignore no protege {secret_path}")
    for markdown in ROOT.glob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        if "AKIA" in text or "BEGIN PRIVATE KEY" in text:
            errors.append(f"posible credencial en {markdown.name}")
        references = re.findall(
            r"(?:\./)?((?:scripts|queries|config)/[A-Za-z0-9_.-]+\.(?:sh|py|sql|json))",
            text,
        )
        runtime_files = {"config/pipeline.json"}
        for reference in references:
            if reference not in runtime_files and not (ROOT / reference).is_file():
                errors.append(f"{markdown.name} referencia un archivo ausente: {reference}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloudformation-only", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    validate_cloudformation(errors)
    if not args.cloudformation_only:
        validate_repository(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("VALIDACION ESTATICA APROBADA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
