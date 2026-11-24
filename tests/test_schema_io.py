from datetime import datetime

import pytest

from app.io import read_jsonl, write_jsonl
from app.schema import SchemaError, parse_utc, stable_event_id, utc_iso, validate_cloud_event


def valid_event():
    return {
        "event_id": "a" * 32,
        "pipeline": "edge",
        "device_id": "truck-01",
        "gateway_id": "depot-01",
        "trip_id": "trip-01",
        "lot_id": "lot-01",
        "event_time": "2026-11-23T12:00:00Z",
        "sample_count": 1,
        "avg_temperature_c": 5.0,
        "min_temperature_c": 5.0,
        "max_temperature_c": 5.0,
        "avg_humidity_pct": 60.0,
        "max_vibration_g": 0.2,
        "anomaly_count": 0,
        "local_alarm": False,
        "replayed": False,
        "source_event_ids": ["b" * 32],
    }


def test_schema_accepts_valid_event():
    validate_cloud_event(valid_event())


def test_schema_rejects_bad_counts_and_time():
    event = valid_event()
    event["anomaly_count"] = 2
    with pytest.raises(SchemaError, match="fuera de rango"):
        validate_cloud_event(event)
    with pytest.raises(SchemaError, match="zona horaria"):
        parse_utc("2026-11-23T12:00:00")
    with pytest.raises(SchemaError, match="zona horaria"):
        utc_iso(datetime(2026, 1, 1))


def test_stable_id_and_jsonl_roundtrip(tmp_path):
    assert stable_event_id(["x", 1]) == stable_event_id(["x", 1])
    path = tmp_path / "events.jsonl"
    assert write_jsonl(path, [valid_event(), valid_event()]) == 2
    assert list(read_jsonl(path)) == [valid_event(), valid_event()]


def test_jsonl_rejects_scalar(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="objeto"):
        list(read_jsonl(path))
