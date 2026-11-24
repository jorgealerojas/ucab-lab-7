"""Gateway Fog: ventanas por dispositivo, buffer local y reenvio."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

from .io import append_jsonl, read_jsonl, write_jsonl
from .schema import stable_event_id, validate_cloud_event


def aggregate_window(events: Sequence[dict], *, replayed: bool = False) -> dict:
    if not events:
        raise ValueError("no se puede agregar una ventana vacia")
    first = events[0]
    identity = (first["device_id"], first["trip_id"], first["lot_id"])
    if any((item["device_id"], item["trip_id"], item["lot_id"]) != identity for item in events):
        raise ValueError("una ventana Fog no puede mezclar dispositivos o viajes")
    source_ids = [item["source_event_ids"][0] for item in events]
    temperatures = [float(item["avg_temperature_c"]) for item in events]
    humidities = [float(item["avg_humidity_pct"]) for item in events]
    event = {
        "event_id": stable_event_id(["fog", first["device_id"], source_ids]),
        "pipeline": "fog",
        "device_id": first["device_id"],
        "gateway_id": first["gateway_id"],
        "trip_id": first["trip_id"],
        "lot_id": first["lot_id"],
        "event_time": events[-1]["event_time"],
        "sample_count": len(events),
        "avg_temperature_c": round(sum(temperatures) / len(events), 3),
        "min_temperature_c": round(min(temperatures), 3),
        "max_temperature_c": round(max(temperatures), 3),
        "avg_humidity_pct": round(sum(humidities) / len(events), 3),
        "max_vibration_g": round(max(float(item["max_vibration_g"]) for item in events), 4),
        "anomaly_count": sum(int(item["anomaly_count"]) for item in events),
        "local_alarm": any(bool(item["local_alarm"]) for item in events),
        "replayed": replayed,
        "source_event_ids": source_ids,
    }
    validate_cloud_event(event)
    return event


def aggregate_events(events: Iterable[dict], *, window_size: int, replayed: bool = False) -> list[dict]:
    if window_size < 1:
        raise ValueError("window_size debe ser positivo")
    windows: dict[str, list[dict]] = defaultdict(list)
    aggregated: list[dict] = []
    for event in events:
        if event["pipeline"] != "edge":
            raise ValueError("Fog recibe eventos normalizados por Edge")
        bucket = windows[event["device_id"]]
        bucket.append(event)
        if len(bucket) == window_size:
            aggregated.append(aggregate_window(bucket, replayed=replayed))
            windows[event["device_id"]] = []
    for device_id in sorted(windows):
        if windows[device_id]:
            aggregated.append(aggregate_window(windows[device_id], replayed=replayed))
    return sorted(aggregated, key=lambda item: (item["event_time"], item["device_id"]))


def spool_events(path: Path | str, events: Iterable[dict]) -> int:
    """Conserva eventos localmente cuando el enlace cloud no esta disponible."""

    count = 0
    for event in events:
        item = dict(event)
        item["replayed"] = True
        validate_cloud_event(item)
        append_jsonl(path, item)
        count += 1
    return count


def replay_spool(
    path: Path | str,
    publish: Callable[[list[dict]], None],
    *,
    batch_size: int,
) -> int:
    """Publica el buffer y lo vacia solo despues de confirmar todos los lotes."""

    spool_path = Path(path)
    if not spool_path.exists():
        return 0
    events = list(read_jsonl(spool_path))
    for batch in chunked(events, batch_size):
        publish(batch)
    write_jsonl(spool_path, [])
    return len(events)


def chunked(events: Sequence[dict], size: int) -> Iterator[list[dict]]:
    if size < 1:
        raise ValueError("size debe ser positivo")
    for index in range(0, len(events), size):
        yield list(events[index : index + size])
