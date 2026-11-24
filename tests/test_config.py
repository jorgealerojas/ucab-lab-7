import json

import pytest

from app.config import ConfigError, PipelineConfig, load_config


def valid_mapping():
    return {
        "region": "us-east-2",
        "iot_endpoint": "a1234567890-ats.iot.us-east-2.amazonaws.com",
        "topic_prefix": "ucab/lab7/0123456789abcdef/telemetry",
        "window_size": 10,
        "min_temperature_c": 2.0,
        "max_temperature_c": 8.0,
        "devices": 12,
        "samples_per_device": 240,
        "publish_batch_size": 200,
    }


def test_valid_config():
    config = PipelineConfig.from_mapping(valid_mapping())
    assert config.window_size == 10


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("region", "us-east-1", "us-east-2"),
        ("window_size", 4, "entre 5 y 25"),
        ("devices", 0, "devices"),
        ("samples_per_device", 501, "samples_per_device"),
        ("publish_batch_size", 401, "publish_batch_size"),
    ],
)
def test_invalid_limits(field, value, message):
    data = valid_mapping()
    data[field] = value
    with pytest.raises(ConfigError, match=message):
        PipelineConfig.from_mapping(data)


def test_placeholder_allowed_only_for_local_demo():
    data = valid_mapping()
    data["iot_endpoint"] = "REEMPLAZAR_ENDPOINT"
    data["topic_prefix"] = "REEMPLAZAR_TOPIC_PREFIX"
    with pytest.raises(ConfigError, match="investigar"):
        PipelineConfig.from_mapping(data)
    assert PipelineConfig.from_mapping(data, allow_placeholder=True).window_size == 10


def test_load_config_rejects_non_object(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ConfigError, match="objeto"):
        load_config(path)
