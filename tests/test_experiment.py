import json

from app.config import PipelineConfig
from app.experiment import run_experiment
from app.io import read_jsonl


def config():
    return PipelineConfig(
        region="us-east-2",
        iot_endpoint="REEMPLAZAR_ENDPOINT",
        topic_prefix="REEMPLAZAR_TOPIC_PREFIX",
        window_size=10,
        min_temperature_c=2.0,
        max_temperature_c=8.0,
        devices=4,
        samples_per_device=140,
        publish_batch_size=100,
    )


def test_experiment_outputs_and_metrics(tmp_path):
    edge_published = []
    fog_published = []
    summary = run_experiment(
        config(),
        tmp_path,
        publish_edge=lambda events: edge_published.extend(events),
        publish_fog=lambda events: fog_published.extend(events),
    )
    assert summary["edge"]["accepted"] == len(edge_published)
    assert summary["fog"]["published_events"] == len(fog_published)
    assert summary["fog"]["duplicate_events_injected"] == 1
    assert summary["expected_bronze_rows"] == len(edge_published) + len(fog_published)
    assert list(read_jsonl(tmp_path / "fog-spool.jsonl")) == []
    assert json.loads((tmp_path / "metrics.json").read_text())["fog"]["reduction_factor"] > 1


def test_experiment_retains_spool_when_publish_fails(tmp_path):
    def fail(_events):
        raise RuntimeError("network")

    try:
        run_experiment(config(), tmp_path, publish_fog=fail)
    except RuntimeError:
        pass
    else:
        raise AssertionError("se esperaba un fallo")
    assert list(read_jsonl(tmp_path / "fog-spool.jsonl"))
