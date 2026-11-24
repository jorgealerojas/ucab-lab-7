"""Carga y validacion de decisiones configurables por el estudiante."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ENDPOINT_RE = re.compile(r"^[a-z0-9-]+\.iot\.us-east-2\.amazonaws\.com$")
TOPIC_RE = re.compile(r"^ucab/lab7/[0-9a-f]{16}/telemetry$")


class ConfigError(ValueError):
    """Configuracion incompleta o fuera de los limites del laboratorio."""


@dataclass(frozen=True)
class PipelineConfig:
    region: str
    iot_endpoint: str
    topic_prefix: str
    window_size: int
    min_temperature_c: float
    max_temperature_c: float
    devices: int
    samples_per_device: int
    publish_batch_size: int

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, allow_placeholder: bool = False) -> "PipelineConfig":
        required = {
            "region",
            "iot_endpoint",
            "topic_prefix",
            "window_size",
            "min_temperature_c",
            "max_temperature_c",
            "devices",
            "samples_per_device",
            "publish_batch_size",
        }
        missing = required - set(data)
        if missing:
            raise ConfigError(f"faltan opciones: {', '.join(sorted(missing))}")
        config = cls(**{key: data[key] for key in required})
        config.validate(allow_placeholder=allow_placeholder)
        return config

    def validate(self, *, allow_placeholder: bool = False) -> None:
        if self.region != "us-east-2":
            raise ConfigError("la region obligatoria es us-east-2")
        placeholders = {"REEMPLAZAR_ENDPOINT", "REEMPLAZAR_TOPIC_PREFIX"}
        if self.iot_endpoint in placeholders or self.topic_prefix in placeholders:
            if not allow_placeholder:
                raise ConfigError("debe investigar y reemplazar endpoint y topic_prefix")
        else:
            if not ENDPOINT_RE.fullmatch(self.iot_endpoint):
                raise ConfigError("iot_endpoint no corresponde a AWS IoT en us-east-2")
            if not TOPIC_RE.fullmatch(self.topic_prefix):
                raise ConfigError("topic_prefix no cumple el formato aislado del laboratorio")
        if not isinstance(self.window_size, int) or not 5 <= self.window_size <= 25:
            raise ConfigError("window_size debe estar entre 5 y 25")
        if self.min_temperature_c >= self.max_temperature_c:
            raise ConfigError("el limite minimo debe ser menor que el maximo")
        if not (1 <= self.devices <= 20):
            raise ConfigError("devices debe estar entre 1 y 20")
        if not (20 <= self.samples_per_device <= 500):
            raise ConfigError("samples_per_device debe estar entre 20 y 500")
        if not (1 <= self.publish_batch_size <= 400):
            raise ConfigError("publish_batch_size debe estar entre 1 y 400")


def load_config(path: Path | str, *, allow_placeholder: bool = False) -> PipelineConfig:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"no existe la configuracion: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON invalido en {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("la configuracion debe ser un objeto JSON")
    return PipelineConfig.from_mapping(data, allow_placeholder=allow_placeholder)
