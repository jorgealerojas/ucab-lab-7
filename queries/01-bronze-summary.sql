SELECT
  event.pipeline,
  count(*) AS cloud_rows,
  count(DISTINCT event.event_id) AS unique_events,
  sum(event.sample_count) AS represented_samples,
  sum(event.anomaly_count) AS anomalous_samples
FROM "{{DATABASE}}".bronze_telemetry
CROSS JOIN UNNEST(events) AS batch(event)
WHERE year = date_format(current_timestamp, '%Y')
  AND month = date_format(current_timestamp, '%m')
  AND day = date_format(current_timestamp, '%d')
GROUP BY event.pipeline
ORDER BY event.pipeline;
