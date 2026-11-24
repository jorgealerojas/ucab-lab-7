from pathlib import Path

from scripts import empty_versioned_bucket, manage_identities


def test_empty_bucket_deletes_versions_and_markers(monkeypatch):
    deleted = []

    class Paginator:
        def paginate(self, **kwargs):
            assert kwargs == {"Bucket": "ucab-lab-7-account-us-east-2-id"}
            yield {
                "Versions": [{"Key": "a", "VersionId": "1"}],
                "DeleteMarkers": [{"Key": "b", "VersionId": "2"}],
            }

    class Client:
        def get_paginator(self, name):
            assert name == "list_object_versions"
            return Paginator()

        def delete_objects(self, **kwargs):
            deleted.extend(kwargs["Delete"]["Objects"])
            return {}

    monkeypatch.setattr(empty_versioned_bucket.boto3, "client", lambda *_args, **_kwargs: Client())
    assert empty_versioned_bucket.empty_bucket(
        "ucab-lab-7-account-us-east-2-id", "us-east-2"
    ) == 2
    assert deleted == [{"Key": "a", "VersionId": "1"}, {"Key": "b", "VersionId": "2"}]


def test_cleanup_identity_detaches_before_removing_files(tmp_path):
    calls = []

    class Client:
        def __getattr__(self, name):
            def method(**kwargs):
                calls.append((name, kwargs))

            return method

    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    cert.write_text("cert")
    key.write_text("key")
    identity = {
        "certificate_arn": "arn:cert",
        "certificate_id": "cert-id",
        "thing_name": "thing",
        "policy_name": "policy",
        "certificate_path": str(cert),
        "private_key_path": str(key),
    }
    manage_identities.cleanup_identity(Client(), identity)
    assert [name for name, _ in calls] == [
        "detach_thing_principal",
        "detach_policy",
        "update_certificate",
        "delete_certificate",
    ]
    assert not cert.exists()
    assert not key.exists()
