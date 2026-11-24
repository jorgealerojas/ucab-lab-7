from pathlib import Path
from types import SimpleNamespace

import pytest

from app.publisher import MAX_PAYLOAD_BYTES, PublishError, X509Publisher, build_publish_url
from tests.test_schema_io import valid_event


def test_publish_url_preserves_topic_slashes():
    assert build_publish_url("abc.iot.us-east-2.amazonaws.com", "a/b/c") == (
        "https://abc.iot.us-east-2.amazonaws.com:8443/topics/a/b/c?qos=1"
    )


def test_x509_publisher_builds_safe_curl_command(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        payload_arg = command[command.index("--data-binary") + 1]
        assert payload_arg.startswith("@")
        assert Path(payload_arg[1:]).read_text(encoding="utf-8").startswith('{"events":[')
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    publisher = X509Publisher(
        endpoint="abc.iot.us-east-2.amazonaws.com",
        topic="a/b/edge",
        certificate=tmp_path / "cert.pem",
        private_key=tmp_path / "key.pem",
        root_ca=tmp_path / "ca.pem",
        runner=runner,
    )
    assert publisher.publish([valid_event(), valid_event()], batch_size=1) == 2
    assert len(calls) == 2
    assert calls[0][1]["check"] is False


def test_x509_publisher_reports_curl_failure(tmp_path):
    publisher = X509Publisher(
        endpoint="abc.iot.us-east-2.amazonaws.com",
        topic="a/b/edge",
        certificate=tmp_path / "cert.pem",
        private_key=tmp_path / "key.pem",
        root_ca=tmp_path / "ca.pem",
        runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=22, stderr="403", stdout=""),
    )
    with pytest.raises(PublishError, match="403"):
        publisher.publish_batch([valid_event()])


def test_x509_publisher_splits_batch_by_encoded_bytes(tmp_path):
    calls = []

    def runner(command, **_kwargs):
        payload_path = command[command.index("--data-binary") + 1][1:]
        calls.append(Path(payload_path).read_bytes())
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    publisher = X509Publisher(
        endpoint="abc.iot.us-east-2.amazonaws.com",
        topic="a/b/fog",
        certificate=tmp_path / "cert.pem",
        private_key=tmp_path / "key.pem",
        root_ca=tmp_path / "ca.pem",
        runner=runner,
    )
    event = valid_event()
    event["sample_count"] = 1
    event["source_event_ids"] = ["x" * (MAX_PAYLOAD_BYTES // 2)]
    publisher.publish_batch([event, event])
    assert len(calls) == 2
    assert all(len(payload) <= MAX_PAYLOAD_BYTES for payload in calls)
