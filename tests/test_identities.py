from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import manage_identities


def test_download_root_ca_uses_verified_curl(monkeypatch, tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout="-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n",
            stderr="",
        )

    monkeypatch.setattr(manage_identities.subprocess, "run", run)
    destination = tmp_path / "ca.pem"
    manage_identities.download_root_ca(destination)
    assert destination.read_text().startswith("-----BEGIN CERTIFICATE-----")
    assert "--proto" in calls[0][0]
    assert destination.stat().st_mode & 0o777 == 0o600


def test_download_root_ca_rejects_bad_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(
        manage_identities.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="html", stderr=""),
    )
    with pytest.raises(RuntimeError, match="certificado PEM"):
        manage_identities.download_root_ca(tmp_path / "ca.pem")
