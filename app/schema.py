"""Contrato de eventos de cadena de frio usado por todas las capas."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

PIPELINES = {"edge", "fog"}
REQUIRED_EVENT_FIELDS = {
    "event_id",
    "pipeline",
    "device_id",
    "gateway_id",
    "trip_id",
    "lot_id",
    "event_time",
    "sample_count",
    "avg_temperature_c",
    "min_temperature_c",
    "max_temperature_c",
    "avg_humidity_pct",
    "max_vibration_g",
    "anomaly_count",
    "local_alarm",
    "replayed",
    "source_event_ids",
}


class SchemaError(ValueError):
    """Indica que una lectura o un evento no cumple el contrato."""


def utc_iso(value: datetime) -> str:
    """Devuelve un instante UTC estable con sufijo Z."""

    if value.tzinfo is None:
        raise SchemaError("event_time debe incluir zona horaria")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    """Interpreta el formato ISO-8601 UTC usado en el laboratorio."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"timestamp invalido: {value!r}") from exc
    if parsed.tzinfo is None:
        raise SchemaError("timestamp sin zona horaria")
    return parsed.astimezone(timezone.utc)


def stable_event_id(parts: Iterable[Any]) -> str:
    """Crea una identidad idempotente a partir de los campos de origen."""

    canonical = json.dumps(list(parts), ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def validate_cloud_event(event: Mapping[str, Any]) -> None:
    """Valida el contrato comun de eventos Edge y Fog."""

    missing = REQUIRED_EVENT_FIELDS - set(event)
    if missing:
        raise SchemaError(f"faltan campos: {', '.join(sorted(missing))}")
    if event["pipeline"] not in PIPELINES:
        raise SchemaError("pipeline debe ser edge o fog")
    if not isinstance(event["event_id"], str) or len(event["event_id"]) != 32:
        raise SchemaError("event_id debe tener 32 caracteres")
    parse_utc(event["event_time"])
    if not isinstance(event["sample_count"], int) or event["sample_count"] < 1:
        raise SchemaError("sample_count debe ser un entero positivo")
    if not isinstance(event["anomaly_count"], int):
        raise SchemaError("anomaly_count debe ser entero")
    if not 0 <= event["anomaly_count"] <= event["sample_count"]:
        raise SchemaError("anomaly_count fuera de rango")
    if not isinstance(event["source_event_ids"], list):
        raise SchemaError("source_event_ids debe ser una lista")
    if len(event["source_event_ids"]) != event["sample_count"]:
        raise SchemaError("source_event_ids no coincide con sample_count")
    for name in (
        "avg_temperature_c",
        "min_temperature_c",
        "max_temperature_c",
        "avg_humidity_pct",
        "max_vibration_g",
    ):
        if not isinstance(event[name], (int, float)) or isinstance(event[name], bool):
            raise SchemaError(f"{name} debe ser numerico")
    if event["min_temperature_c"] > event["avg_temperature_c"]:
        raise SchemaError("temperatura minima mayor que el promedio")
    if event["avg_temperature_c"] > event["max_temperature_c"]:
        raise SchemaError("temperatura promedio mayor que la maxima")
    for name in ("local_alarm", "replayed"):
        if not isinstance(event[name], bool):
            raise SchemaError(f"{name} debe ser booleano")
