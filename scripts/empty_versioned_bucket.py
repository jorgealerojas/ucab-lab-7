#!/usr/bin/env python3
"""Elimina solo los objetos y versiones de un bucket nombrado explicitamente."""

from __future__ import annotations

import argparse

import boto3


def chunks(values: list[dict], size: int = 1000):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def empty_bucket(bucket: str, region: str) -> int:
    client = boto3.client("s3", region_name=region)
    paginator = client.get_paginator("list_object_versions")
    deleted = 0
    for page in paginator.paginate(Bucket=bucket):
        identifiers = [
            {"Key": item["Key"], "VersionId": item["VersionId"]}
            for group in (page.get("Versions", []), page.get("DeleteMarkers", []))
            for item in group
        ]
        for batch in chunks(identifiers):
            if batch:
                response = client.delete_objects(
                    Bucket=bucket, Delete={"Objects": batch, "Quiet": True}
                )
                if response.get("Errors"):
                    raise RuntimeError(f"S3 no pudo eliminar objetos: {response['Errors']}")
                deleted += len(batch)
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    if not args.bucket.startswith("ucab-lab-7-"):
        raise SystemExit("se rechazo un bucket fuera del prefijo ucab-lab-7-")
    print(empty_bucket(args.bucket, args.region))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
