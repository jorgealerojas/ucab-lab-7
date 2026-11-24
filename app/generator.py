"""Generador determinista de telemetria para el caso de cadena de frio."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Iterator


def generate_readings(
    *, devices: int, samples_per_device: int, seed: int = 7028
) -> Iterator[dict]:
    """Genera lecturas intercaladas de varios camiones.

    Incluye datos faltantes, duplicados y excursiones termicas controladas.
    El orden y los valores son reproducibles para que las respuestas puedan
    validarse sin imponer una cifra escrita a mano.
    """

    if devices < 1 or samples_per_device < 1:
        raise ValueError("devices y samples_per_device deben ser positivos")
    rng = random.Random(seed)
    start = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)

    for sequence in range(samples_per_device):
        for device_index in range(devices):
            device_id = f"truck-{device_index + 1:02d}"
            trip_id = f"trip-{device_index + 1:02d}-20261123"
            lot_id = f"lot-{1000 + (device_index // 3)}"
            periodic = math.sin((sequence + device_index * 3) / 17.0) * 0.7
            temperature = 5.0 + periodic + rng.uniform(-0.25, 0.25)

            # Dos excursiones suficientemente largas para que una ventana Fog
            # no esconda por completo el riesgo.
            if 60 <= sequence < 78 and device_index % 4 == 0:
                temperature += 5.8
            if 165 <= sequence < 176 and device_index % 5 == 1:
                temperature -= 5.0

            humidity = 62.0 + math.cos(sequence / 23.0) * 5 + rng.uniform(-1.0, 1.0)
            vibration = abs(rng.gauss(0.18, 0.07))
            if sequence % 79 == 0 and device_index == 2:
                vibration += 1.4

            reading = {
                "device_id": device_id,
                "gateway_id": f"depot-{1 + device_index // 4:02d}",
                "trip_id": trip_id,
                "lot_id": lot_id,
                "sequence": sequence,
                "event_time": (start + timedelta(seconds=sequence * 5 + device_index)).isoformat().replace(
                    "+00:00", "Z"
                ),
                "temperature_c": round(temperature, 3),
                "humidity_pct": round(humidity, 3),
                "vibration_g": round(vibration, 4),
            }

            # Fallas de sensor predecibles que Edge debe rechazar.
            if sequence > 0 and sequence % 97 == 0 and device_index % 3 == 0:
                reading["temperature_c"] = None
            if sequence > 0 and sequence % 131 == 0 and device_index == 1:
                reading["humidity_pct"] = 140.0

            yield reading

            # El sensor retransmite exactamente la misma lectura. Edge conserva
            # una sola copia mediante la identidad dispositivo/secuencia/tiempo.
            if sequence > 0 and sequence % 113 == 0 and device_index == 0:
                yield dict(reading)
