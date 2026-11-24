#!/usr/bin/env python3
"""Genera los dos recorridos y deja Fog en buffer, sin usar la red."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import ConfigError, load_config
from app.experiment import run_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    outputs = json.loads(args.outputs.read_text(encoding="utf-8"))
    if config.topic_prefix != outputs.get("TopicPrefix"):
        raise ConfigError("topic_prefix no pertenece al stack registrado")
    summary = run_experiment(config, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"BUFFER FOG PENDIENTE: {args.output / 'fog-spool.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
