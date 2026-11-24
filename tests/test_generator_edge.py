from app.edge import is_valid_reading, process_readings, reading_identity, to_edge_event
from app.generator import generate_readings


def test_generator_is_deterministic_and_injects_quality_cases():
    first = list(generate_readings(devices=4, samples_per_device=140, seed=9))
    second = list(generate_readings(devices=4, samples_per_device=140, seed=9))
    assert first == second
    assert len(first) > 4 * 140
    assert any(item["temperature_c"] is None for item in first)
    assert any(item["humidity_pct"] == 140.0 for item in first)


def test_edge_rejects_invalid_and_deduplicates():
    readings = list(generate_readings(devices=4, samples_per_device=140))
    events, stats = process_readings(readings, min_temperature_c=2.0, max_temperature_c=8.0)
    assert stats.received == len(readings)
    assert stats.invalid > 0
    assert stats.duplicates > 0
    assert stats.accepted == len(events)
    assert stats.local_alarms > 0
    assert len({event["event_id"] for event in events}) == len(events)


def test_edge_alarm_and_identity():
    reading = next(generate_readings(devices=1, samples_per_device=1))
    reading["temperature_c"] = 12.0
    event = to_edge_event(reading, min_temperature_c=2.0, max_temperature_c=8.0)
    assert event["local_alarm"] is True
    assert event["anomaly_count"] == 1
    assert event["source_event_ids"] == [reading_identity(reading)]


def test_edge_validation_rejects_boolean_numeric():
    reading = next(generate_readings(devices=1, samples_per_device=1))
    reading["temperature_c"] = True
    assert is_valid_reading(reading) is False
