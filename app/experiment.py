"""Orquestacion reproducible del experimento Edge frente a Fog."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

from .config import PipelineConfig
from .edge import process_readings
from .fog import aggregate_events, spool_events
from .generator import generate_readings
from .io import write_jsonl


def run_experiment(
    config: PipelineConfig,
    output_dir: Path | str,
    *,
    publish_edge: Optional[Callable[[list[dict]], None]] = None,
    publish_fog: Optional[Callable[[list[dict]], None]] = None,
    inject_fog_duplicate: bool = True,
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    readings = list(
        generate_readings(devices=config.devices, samples_per_device=config.samples_per_device)
    )
    edge_events, edge_stats = process_readings(
        readings,
        min_temperature_c=config.min_temperature_c,
        max_temperature_c=config.max_temperature_c,
    )
    fog_events = aggregate_events(edge_events, window_size=config.window_size, replayed=True)
    fog_published = list(fog_events)
    if inject_fog_duplicate and fog_published:
        fog_published.append(dict(fog_published[0]))

    write_jsonl(output / "raw-readings.jsonl", readings)
    write_jsonl(output / "edge-events.jsonl", edge_events)
    write_jsonl(output / "fog-events.jsonl", fog_events)
    spool_events(output / "fog-spool.jsonl", fog_published)

    if publish_edge:
        publish_edge(edge_events)
    if publish_fog:
        publish_fog(fog_published)
        # El buffer se elimina solo cuando el callback confirma la publicacion.
        write_jsonl(output / "fog-spool.jsonl", [])

    total_samples = sum(event["sample_count"] for event in fog_events)
    summary = {
        "config": asdict(config),
        "edge": edge_stats.as_dict(),
        "fog": {
            "unique_events": len(fog_events),
            "published_events": len(fog_published),
            "duplicate_events_injected": len(fog_published) - len(fog_events),
            "represented_samples": total_samples,
            "reduction_factor": round(len(edge_events) / len(fog_events), 3),
        },
        "expected_bronze_rows": len(edge_events) + len(fog_published),
        "expected_unique_rows": len(edge_events) + len(fog_events),
    }
    (output / "metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
