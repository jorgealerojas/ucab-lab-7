#!/usr/bin/env python3
"""Aprovisiona y elimina las identidades X.509 que CloudFormation no puede exportar."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

ROOT_CA_URL = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"


def secure_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def download_root_ca(path: Path) -> None:
    """Descarga la CA con el mismo trust store que usa curl en CloudShell."""

    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--proto",
            "=https",
            "--tlsv1.2",
            ROOT_CA_URL,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"no se pudo descargar Amazon Root CA: {result.stderr.strip()}")
    if "BEGIN CERTIFICATE" not in result.stdout:
        raise RuntimeError("Amazon Root CA no contiene un certificado PEM")
    secure_write(path, result.stdout)


def provision_identity(client: Any, directory: Path, layer: str, thing: str, policy: str) -> dict:
    response = client.create_keys_and_certificate(setAsActive=True)
    certificate_id = response["certificateId"]
    certificate_arn = response["certificateArn"]
    certificate_path = directory / f"{layer}-certificate.pem"
    key_path = directory / f"{layer}-private.key"
    secure_write(certificate_path, response["certificatePem"])
    secure_write(key_path, response["keyPair"]["PrivateKey"])
    try:
        client.attach_policy(policyName=policy, target=certificate_arn)
        client.attach_thing_principal(thingName=thing, principal=certificate_arn)
    except BaseException:
        try:
            client.update_certificate(certificateId=certificate_id, newStatus="INACTIVE")
            client.delete_certificate(certificateId=certificate_id, forceDelete=True)
        finally:
            certificate_path.unlink(missing_ok=True)
            key_path.unlink(missing_ok=True)
        raise
    return {
        "layer": layer,
        "thing_name": thing,
        "policy_name": policy,
        "certificate_id": certificate_id,
        "certificate_arn": certificate_arn,
        "certificate_path": str(certificate_path),
        "private_key_path": str(key_path),
    }


def cleanup_identity(client: Any, identity: dict) -> None:
    arn = identity["certificate_arn"]
    certificate_id = identity["certificate_id"]
    calls = (
        lambda: client.detach_thing_principal(thingName=identity["thing_name"], principal=arn),
        lambda: client.detach_policy(policyName=identity["policy_name"], target=arn),
        lambda: client.update_certificate(certificateId=certificate_id, newStatus="INACTIVE"),
        lambda: client.delete_certificate(certificateId=certificate_id, forceDelete=True),
    )
    for call in calls:
        try:
            call()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {
                "ResourceNotFoundException",
                "InvalidRequestException",
            }:
                raise
    for key in ("certificate_path", "private_key_path"):
        Path(identity[key]).unlink(missing_ok=True)


def provision(args: argparse.Namespace) -> None:
    directory = args.state_dir / "certs"
    client = boto3.client("iot", region_name=args.region)
    identities: list[dict] = []
    try:
        identities.append(
            provision_identity(client, directory, "edge", args.edge_thing, args.policy)
        )
        identities.append(provision_identity(client, directory, "fog", args.fog_thing, args.policy))
        root_ca = directory / "AmazonRootCA1.pem"
        download_root_ca(root_ca)
        state = {"region": args.region, "root_ca_path": str(root_ca), "identities": identities}
        secure_write(args.state_dir / "identities.json", json.dumps(state, indent=2) + "\n")
    except BaseException:
        for identity in reversed(identities):
            cleanup_identity(client, identity)
        raise


def cleanup(args: argparse.Namespace) -> None:
    state_path = args.state_dir / "identities.json"
    if not state_path.exists():
        return
    state = json.loads(state_path.read_text(encoding="utf-8"))
    client = boto3.client("iot", region_name=state["region"])
    for identity in reversed(state["identities"]):
        cleanup_identity(client, identity)
    Path(state["root_ca_path"]).unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("provision")
    create.add_argument("--state-dir", type=Path, required=True)
    create.add_argument("--region", required=True)
    create.add_argument("--policy", required=True)
    create.add_argument("--edge-thing", required=True)
    create.add_argument("--fog-thing", required=True)
    create.set_defaults(func=provision)
    remove = subparsers.add_parser("cleanup")
    remove.add_argument("--state-dir", type=Path, required=True)
    remove.set_defaults(func=cleanup)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
