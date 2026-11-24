#!/usr/bin/env python3
"""Comprueba la decision Fog y el aislamiento contra los outputs del stack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import ConfigError, load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    outputs = json.loads(args.outputs.read_text(encoding="utf-8"))
    if config.topic_prefix != outputs.get("TopicPrefix"):
        raise ConfigError("topic_prefix no pertenece al stack registrado")
    print("CONFIGURACION APROBADA")
    print(f"Ventana Fog: {config.window_size} muestras")
    print(f"Dispositivos: {config.devices}")
    print(f"Muestras por dispositivo: {config.samples_per_device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
