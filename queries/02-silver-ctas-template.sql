-- Copie este archivo a generated/silver-ctas.sql y complete los tres TODO.
-- Pistas:
-- 1. El marcador de formato representa el formato columnar solicitado para Silver.
-- 2. El marcador de idempotencia debe ser la columna que identifica establemente
--    al mismo evento aunque se publique mas de una vez.
-- 3. El marcador de recencia debe ser la columna temporal que permite conservar
--    la observacion mas reciente con ORDER BY ... DESC.
CREATE TABLE "{{DATABASE}}".silver_telemetry
WITH (
  format = 'TODO_FORMAT',
  parquet_compression = 'SNAPPY',
  external_location = 's3://{{BUCKET}}/silver/'
) AS
SELECT
  event_id, pipeline, device_id, gateway_id, trip_id, lot_id, event_time,
  sample_count, avg_temperature_c, min_temperature_c, max_temperature_c,
  avg_humidity_pct, max_vibration_g, anomaly_count, local_alarm, replayed,
  source_event_ids
FROM (
  SELECT
    expanded.*,
    row_number() OVER (
      PARTITION BY TODO_IDEMPOTENCY_KEY
      ORDER BY TODO_RECENCY_FIELD DESC
    ) AS row_rank
  FROM (
    SELECT
      event.event_id AS event_id,
      event.pipeline AS pipeline,
      event.device_id AS device_id,
      event.gateway_id AS gateway_id,
      event.trip_id AS trip_id,
      event.lot_id AS lot_id,
      event.event_time AS event_time,
      event.sample_count AS sample_count,
      event.avg_temperature_c AS avg_temperature_c,
      event.min_temperature_c AS min_temperature_c,
      event.max_temperature_c AS max_temperature_c,
      event.avg_humidity_pct AS avg_humidity_pct,
      event.max_vibration_g AS max_vibration_g,
      event.anomaly_count AS anomaly_count,
      event.local_alarm AS local_alarm,
      event.replayed AS replayed,
      event.source_event_ids AS source_event_ids
    FROM "{{DATABASE}}".bronze_telemetry
    CROSS JOIN UNNEST(events) AS batch(event)
    WHERE event.event_id IS NOT NULL
      AND year = date_format(current_timestamp, '%Y')
      AND month = date_format(current_timestamp, '%m')
      AND day = date_format(current_timestamp, '%d')
  ) AS expanded
)
WHERE row_rank = 1;
