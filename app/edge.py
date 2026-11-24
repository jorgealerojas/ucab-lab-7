"""Procesamiento cercano al sensor: calidad, alarma e idempotencia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import stable_event_id, validate_cloud_event


@dataclass
class EdgeStats:
    received: int = 0
    accepted: int = 0
    invalid: int = 0
    duplicates: int = 0
    local_alarms: int = 0

    def as_dict(self) -> dict:
        return {
            "received": self.received,
            "accepted": self.accepted,
            "invalid": self.invalid,
            "duplicates": self.duplicates,
            "local_alarms": self.local_alarms,
        }


def _numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def reading_identity(reading: dict) -> str:
    return stable_event_id(
        [reading.get("device_id"), reading.get("sequence"), reading.get("event_time")]
    )


def is_valid_reading(reading: dict) -> bool:
    required_strings = ("device_id", "gateway_id", "trip_id", "lot_id", "event_time")
    if any(not isinstance(reading.get(name), str) or not reading[name] for name in required_strings):
        return False
    if not isinstance(reading.get("sequence"), int) or reading["sequence"] < 0:
        return False
    for name in ("temperature_c", "humidity_pct", "vibration_g"):
        if not _numeric(reading.get(name)):
            return False
    return (
        -50.0 <= float(reading["temperature_c"]) <= 80.0
        and 0.0 <= float(reading["humidity_pct"]) <= 100.0
        and 0.0 <= float(reading["vibration_g"]) <= 20.0
    )


def to_edge_event(reading: dict, *, min_temperature_c: float, max_temperature_c: float) -> dict:
    if not is_valid_reading(reading):
        raise ValueError("lectura invalida")
    source_id = reading_identity(reading)
    temperature = float(reading["temperature_c"])
    alarm = temperature < min_temperature_c or temperature > max_temperature_c
    event = {
        "event_id": stable_event_id(["edge", source_id]),
        "pipeline": "edge",
        "device_id": reading["device_id"],
        "gateway_id": reading["gateway_id"],
        "trip_id": reading["trip_id"],
        "lot_id": reading["lot_id"],
        "event_time": reading["event_time"],
        "sample_count": 1,
        "avg_temperature_c": round(temperature, 3),
        "min_temperature_c": round(temperature, 3),
        "max_temperature_c": round(temperature, 3),
        "avg_humidity_pct": round(float(reading["humidity_pct"]), 3),
        "max_vibration_g": round(float(reading["vibration_g"]), 4),
        "anomaly_count": int(alarm),
        "local_alarm": alarm,
        "replayed": False,
        "source_event_ids": [source_id],
    }
    validate_cloud_event(event)
    return event


def process_readings(
    readings: Iterable[dict], *, min_temperature_c: float, max_temperature_c: float
) -> tuple[list[dict], EdgeStats]:
    stats = EdgeStats()
    events: list[dict] = []
    seen: set[str] = set()
    for reading in readings:
        stats.received += 1
        if not is_valid_reading(reading):
            stats.invalid += 1
            continue
        identity = reading_identity(reading)
        if identity in seen:
            stats.duplicates += 1
            continue
        seen.add(identity)
        event = to_edge_event(
            reading,
            min_temperature_c=min_temperature_c,
            max_temperature_c=max_temperature_c,
        )
        events.append(event)
        stats.accepted += 1
        stats.local_alarms += event["anomaly_count"]
    return events, stats
