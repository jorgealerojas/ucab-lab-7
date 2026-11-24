from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deploy_preserves_failure_long_enough_to_report_events():
    deploy = (ROOT / "scripts" / "deploy-lab.sh").read_text(encoding="utf-8")

    assert "--on-failure DELETE" not in deploy
    assert "describe-stack-events" in deploy
    assert "CREATE_FAILED" in deploy
    assert "CAUSA REPORTADA POR CLOUDFORMATION" in deploy


def test_python_bootstrap_has_all_runtime_and_test_dependencies():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    bootstrap = (ROOT / "scripts" / "bootstrap-python.sh").read_text(encoding="utf-8")

    assert "boto3" in requirements
    assert "pyyaml" in requirements
    assert "pytest" in requirements
    assert "pytest-cov" in requirements
    assert "python3 -m venv" in bootstrap
    assert "--requirement" in bootstrap


def test_common_prefers_repository_virtual_environment():
    common = (ROOT / "scripts" / "common.sh").read_text(encoding="utf-8")

    assert '.venv/bin/python' in common
    assert "run_python" in common


def test_cloudformation_uses_iot_s3_action_without_firehose():
    template = (ROOT / "infra" / "lab-stack.yaml").read_text(encoding="utf-8")

    assert "AWS::KinesisFirehose::DeliveryStream" not in template
    assert "firehose:" not in template.lower()
    assert "- S3:" in template
    assert "/bronze/*" in template
    assert "parse_time" in template


def test_bronze_queries_expand_iot_batches():
    for name in (
        "01-bronze-summary.sql",
        "02-silver-ctas-template.sql",
        "04-json-comparison.sql",
    ):
        query = (ROOT / "queries" / name).read_text(encoding="utf-8")
        assert "CROSS JOIN UNNEST(events)" in query


def test_student_sql_markers_appear_only_where_they_must_be_replaced():
    silver = (ROOT / "queries" / "02-silver-ctas-template.sql").read_text(encoding="utf-8")
    gold = (ROOT / "queries" / "03-gold-view-template.sql").read_text(encoding="utf-8")

    for marker in ("TODO_FORMAT", "TODO_IDEMPOTENCY_KEY", "TODO_RECENCY_FIELD"):
        assert silver.count(marker) == 1
    for marker in (
        "TODO_TOTAL_SAMPLES",
        "TODO_ANOMALY_SAMPLES",
        "TODO_MAX_TEMPERATURE",
        "TODO_MIN_TEMPERATURE",
    ):
        assert gold.count(marker) == 1
