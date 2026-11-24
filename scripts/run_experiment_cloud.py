#!/usr/bin/env python3
"""Ejecuta el experimento y publica los dos recorridos con identidades distintas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import ConfigError, load_config
from app.experiment import run_experiment
from app.publisher import X509Publisher


def identity(state: dict, layer: str) -> dict:
    matches = [item for item in state["identities"] if item["layer"] == layer]
    if len(matches) != 1:
        raise RuntimeError(f"identidad {layer} ausente o duplicada")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    outputs = json.loads((args.state_dir / "outputs.json").read_text(encoding="utf-8"))
    if config.topic_prefix != outputs["TopicPrefix"]:
        raise ConfigError("topic_prefix no coincide con el output del stack propio")
    state = json.loads((args.state_dir / "identities.json").read_text(encoding="utf-8"))
    edge = identity(state, "edge")
    fog = identity(state, "fog")
    edge_publisher = X509Publisher(
        endpoint=config.iot_endpoint,
        topic=f"{config.topic_prefix}/edge",
        certificate=edge["certificate_path"],
        private_key=edge["private_key_path"],
        root_ca=state["root_ca_path"],
    )
    fog_publisher = X509Publisher(
        endpoint=config.iot_endpoint,
        topic=f"{config.topic_prefix}/fog",
        certificate=fog["certificate_path"],
        private_key=fog["private_key_path"],
        root_ca=state["root_ca_path"],
    )
    summary = run_experiment(
        config,
        args.output,
        publish_edge=lambda events: edge_publisher.publish(
            events, batch_size=config.publish_batch_size
        ),
        publish_fog=lambda events: fog_publisher.publish(
            events, batch_size=config.publish_batch_size
        ),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
