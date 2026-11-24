SELECT
  event.pipeline,
  sum(event.sample_count) AS represented_samples,
  sum(event.anomaly_count) AS anomalous_samples,
  round(100.0 * sum(event.anomaly_count) / sum(event.sample_count), 2) AS anomaly_rate_pct
FROM "{{DATABASE}}".bronze_telemetry
CROSS JOIN UNNEST(events) AS batch(event)
WHERE year = date_format(current_timestamp, '%Y')
  AND month = date_format(current_timestamp, '%m')
  AND day = date_format(current_timestamp, '%d')
GROUP BY event.pipeline;
