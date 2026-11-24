"""Publicacion HTTPS/MQTT de lotes usando certificados X.509 de AWS IoT."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import quote

from .fog import chunked
from .schema import validate_cloud_event

MAX_PAYLOAD_BYTES = 120 * 1024


class PublishError(RuntimeError):
    """AWS IoT rechazo o no pudo recibir un lote."""


def build_publish_url(endpoint: str, topic: str) -> str:
    encoded_topic = quote(topic, safe="/")
    return f"https://{endpoint}:8443/topics/{encoded_topic}?qos=1"


class X509Publisher:
    def __init__(
        self,
        *,
        endpoint: str,
        topic: str,
        certificate: Path | str,
        private_key: Path | str,
        root_ca: Path | str,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ) -> None:
        self.endpoint = endpoint
        self.topic = topic
        self.certificate = Path(certificate)
        self.private_key = Path(private_key)
        self.root_ca = Path(root_ca)
        self.runner = runner

    def publish_batch(self, events: Sequence[dict]) -> None:
        if not events:
            return
        for event in events:
            validate_cloud_event(event)
        payload = {"events": list(events)}
        encoded_payload = json.dumps(
            payload, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        if len(encoded_payload) > MAX_PAYLOAD_BYTES:
            if len(events) == 1:
                raise PublishError("un solo evento excede el limite seguro de AWS IoT")
            midpoint = len(events) // 2
            self.publish_batch(events[:midpoint])
            self.publish_batch(events[midpoint:])
            return
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as stream:
            stream.write(encoded_payload.decode("utf-8"))
            stream.flush()
            command = [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--retry",
                "3",
                "--retry-all-errors",
                "--connect-timeout",
                "10",
                "--max-time",
                "30",
                "--cert",
                str(self.certificate),
                "--key",
                str(self.private_key),
                "--cacert",
                str(self.root_ca),
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                f"@{stream.name}",
                build_publish_url(self.endpoint, self.topic),
            ]
            result = self.runner(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "sin detalle").strip()
            raise PublishError(f"fallo al publicar en AWS IoT: {detail}")

    def publish(self, events: Sequence[dict], *, batch_size: int) -> int:
        published = 0
        for batch in chunked(events, batch_size):
            self.publish_batch(batch)
            published += len(batch)
        return published
