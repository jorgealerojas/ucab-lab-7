SELECT
  pipeline,
  sum(sample_count) AS represented_samples,
  sum(anomaly_count) AS anomalous_samples,
  round(100.0 * sum(anomaly_count) / sum(sample_count), 2) AS anomaly_rate_pct
FROM "{{DATABASE}}".silver_telemetry
GROUP BY pipeline;
