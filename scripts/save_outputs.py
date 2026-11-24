#!/usr/bin/env python3
"""Convierte Outputs de CloudFormation en un objeto clave/valor local."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def output_map(stack: dict) -> dict[str, str]:
    return {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.source.read_text(encoding="utf-8"))
    stacks = payload.get("Stacks", [])
    if len(stacks) != 1:
        raise SystemExit("se esperaba exactamente un stack")
    outputs = output_map(stacks[0])
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
