"""E/S JSON Lines atomica y facil de probar."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator


def read_jsonl(path: Path | str) -> Iterator[dict]:
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"linea {line_number}: se esperaba un objeto JSON")
            yield value


def write_jsonl(path: Path | str, values: Iterable[dict]) -> int:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    count = 0
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            for value in values:
                stream.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n")
                count += 1
        os.replace(temporary_name, destination)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return count


def append_jsonl(path: Path | str, value: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n")
