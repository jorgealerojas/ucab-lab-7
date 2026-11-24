-- Copie este archivo a generated/gold-view.sql y sustituya TODO con expresiones SQL.
-- Pistas:
-- 1. Los totales por viaje se obtienen agregando, no contando filas.
-- 2. Cada fila Fog indica cuantas muestras representa y cuantas fueron anomalas.
-- 3. Para los extremos termicos, agregue el maximo de los maximos y el minimo
--    de los minimos de cada ventana Fog.
CREATE OR REPLACE VIEW "{{DATABASE}}".gold_trip_metrics AS
SELECT
  trip_id,
  lot_id,
  TODO_TOTAL_SAMPLES AS represented_samples,
  TODO_ANOMALY_SAMPLES AS anomalous_samples,
  TODO_MAX_TEMPERATURE AS peak_temperature_c,
  TODO_MIN_TEMPERATURE AS lowest_temperature_c
FROM "{{DATABASE}}".silver_telemetry
WHERE pipeline = 'fog'
GROUP BY trip_id, lot_id;
