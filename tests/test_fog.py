from pathlib import Path

import pytest

from app.edge import process_readings
from app.fog import aggregate_events, aggregate_window, replay_spool, spool_events
from app.generator import generate_readings
from app.io import read_jsonl


def edge_events(devices=3, samples=23):
    events, _ = process_readings(
        generate_readings(devices=devices, samples_per_device=samples),
        min_temperature_c=2.0,
        max_temperature_c=8.0,
    )
    return events


def test_fog_aggregates_without_losing_samples():
    source = edge_events()
    fog = aggregate_events(source, window_size=10, replayed=True)
    assert sum(item["sample_count"] for item in fog) == len(source)
    assert len(fog) < len(source)
    assert all(item["pipeline"] == "fog" for item in fog)
    assert all(item["replayed"] is True for item in fog)
    assert sum(item["anomaly_count"] for item in fog) == sum(
        item["anomaly_count"] for item in source
    )


def test_window_rejects_mixed_devices():
    source = edge_events(devices=2, samples=1)
    with pytest.raises(ValueError, match="mezclar"):
        aggregate_window(source)


def test_spool_is_cleared_only_after_success(tmp_path):
    fog = aggregate_events(edge_events(devices=1, samples=12), window_size=5)
    spool = tmp_path / "spool.jsonl"
    assert spool_events(spool, fog) == len(fog)
    published = []
    assert replay_spool(spool, lambda batch: published.extend(batch), batch_size=2) == len(fog)
    assert published
    assert list(read_jsonl(spool)) == []


def test_spool_survives_publish_failure(tmp_path):
    fog = aggregate_events(edge_events(devices=1, samples=12), window_size=5)
    spool = tmp_path / "spool.jsonl"
    spool_events(spool, fog)

    def fail(_batch):
        raise RuntimeError("offline")

    with pytest.raises(RuntimeError, match="offline"):
        replay_spool(spool, fail, batch_size=2)
    assert len(list(read_jsonl(spool))) == len(fog)
