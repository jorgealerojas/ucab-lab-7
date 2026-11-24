#!/usr/bin/env python3
"""Publica datos preparados y conserva checkpoints para reintentos seguros."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import ConfigError, load_config
from app.fog import replay_spool
from app.io import read_jsonl
from app.publisher import X509Publisher


def find_identity(state: dict, layer: str) -> dict:
    matches = [item for item in state["identities"] if item["layer"] == layer]
    if len(matches) != 1:
        raise RuntimeError(f"identidad {layer} ausente o duplicada")
    return matches[0]


def make_publisher(config, state: dict, layer: str) -> X509Publisher:
    item = find_identity(state, layer)
    return X509Publisher(
        endpoint=config.iot_endpoint,
        topic=f"{config.topic_prefix}/{layer}",
        certificate=item["certificate_path"],
        private_key=item["private_key_path"],
        root_ca=state["root_ca_path"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    outputs = json.loads((args.state_dir / "outputs.json").read_text(encoding="utf-8"))
    if config.topic_prefix != outputs.get("TopicPrefix"):
        raise ConfigError("topic_prefix no pertenece al stack registrado")
    identities = json.loads((args.state_dir / "identities.json").read_text(encoding="utf-8"))
    checkpoint_path = args.data_dir / "publish-checkpoint.json"
    checkpoint = (
        json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint_path.exists()
        else {"edge": False, "fog": False}
    )

    if not checkpoint["edge"]:
        edge_events = list(read_jsonl(args.data_dir / "edge-events.jsonl"))
        published = make_publisher(config, identities, "edge").publish(
            edge_events, batch_size=config.publish_batch_size
        )
        checkpoint["edge"] = True
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
        print(f"EDGE PUBLICADO: {published} eventos")
    else:
        print("EDGE YA PUBLICADO: se conserva el checkpoint")

    if not checkpoint["fog"]:
        fog_publisher = make_publisher(config, identities, "fog")
        replayed = replay_spool(
            args.data_dir / "fog-spool.jsonl",
            fog_publisher.publish_batch,
            batch_size=config.publish_batch_size,
        )
        checkpoint["fog"] = True
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
        print(f"FOG REENVIADO: {replayed} eventos; buffer local vacio")
    else:
        print("FOG YA PUBLICADO: se conserva el checkpoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
