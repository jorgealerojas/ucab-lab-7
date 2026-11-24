import json
from pathlib import Path

import pytest

from scripts import run_athena_query
from scripts.run_athena_query import render_sql
from scripts.save_outputs import output_map


ROOT = Path(__file__).resolve().parents[1]


def test_output_map():
    assert output_map({"Outputs": [{"OutputKey": "A", "OutputValue": "B"}]}) == {"A": "B"}


def test_render_sql_replaces_owned_resources():
    sql = render_sql(
        'SELECT * FROM "{{DATABASE}}".x WHERE p = \'s3://{{BUCKET}}/\'',
        {"DatabaseName": "db", "DataLakeBucketName": "bucket"},
    )
    assert '"db".x' in sql
    assert "s3://bucket/" in sql


def test_render_sql_rejects_todo():
    with pytest.raises(ValueError, match="TODO"):
        render_sql("SELECT TODO_FIELD", {"DatabaseName": "db", "DataLakeBucketName": "bucket"})


def test_render_sql_allows_instructional_todo_comment():
    assert render_sql(
        "-- complete el TODO\nSELECT 1",
        {"DatabaseName": "db", "DataLakeBucketName": "bucket"},
    ).endswith("SELECT 1")


def test_silver_template_can_be_completed_without_hidden_markers():
    template = (ROOT / "queries" / "02-silver-ctas-template.sql").read_text(encoding="utf-8")
    completed = (
        template.replace("TODO_FORMAT", "PARQUET")
        .replace("TODO_IDEMPOTENCY_KEY", "event_id")
        .replace("TODO_RECENCY_FIELD", "event_time")
    )

    rendered = render_sql(completed, {"DatabaseName": "db", "DataLakeBucketName": "bucket"})
    assert "PARTITION BY event_id" in rendered
    assert "ORDER BY event_time DESC" in rendered


def test_gold_template_can_be_completed_without_hidden_markers():
    template = (ROOT / "queries" / "03-gold-view-template.sql").read_text(encoding="utf-8")
    replacements = {
        "TODO_TOTAL_SAMPLES": "sum(sample_count)",
        "TODO_ANOMALY_SAMPLES": "sum(anomaly_count)",
        "TODO_MAX_TEMPERATURE": "max(max_temperature_c)",
        "TODO_MIN_TEMPERATURE": "min(min_temperature_c)",
    }
    for marker, expression in replacements.items():
        template = template.replace(marker, expression)

    rendered = render_sql(template, {"DatabaseName": "db", "DataLakeBucketName": "bucket"})
    assert "sum(sample_count) AS represented_samples" in rendered
    assert "max(max_temperature_c) AS peak_temperature_c" in rendered


def test_athena_client_token_is_long_enough(monkeypatch, tmp_path):
    sql = tmp_path / "query.sql"
    sql.write_text("SELECT 1", encoding="utf-8")
    outputs = tmp_path / "outputs.json"
    outputs.write_text(
        json.dumps(
            {
                "DatabaseName": "db",
                "DataLakeBucketName": "bucket",
                "AthenaWorkGroupName": "wg",
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    class Client:
        def start_query_execution(self, **kwargs):
            captured.update(kwargs)
            return {"QueryExecutionId": "query-id"}

    monkeypatch.setattr(run_athena_query.boto3, "client", lambda *_args, **_kwargs: Client())
    monkeypatch.setattr(
        run_athena_query,
        "wait_for_query",
        lambda *_args, **_kwargs: {"Status": {"State": "SUCCEEDED"}, "Statistics": {}},
    )
    monkeypatch.setattr(run_athena_query, "result_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        "sys.argv",
        ["run_athena_query.py", "--file", str(sql), "--outputs", str(outputs)],
    )
    assert run_athena_query.main() == 0
    assert len(captured["ClientRequestToken"]) >= 32
