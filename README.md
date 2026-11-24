# UCAB Lab 7: cadena de frío, del Edge al Data Lake

Laboratorio de 1 hora y 45 minutos para la Unidad VII de **Computación en la Nube (INFO-02028)**. La práctica sigue telemetría farmacéutica desde sensores simulados hasta un Data Lake consultable con SQL.

El estudiante compara dos recorridos sobre las mismas muestras:

- **Edge directo:** valida cada lectura, elimina duplicados y activa alarmas locales antes de publicar.
- **Fog:** agrupa las lecturas por dispositivo, conserva un buffer durante una desconexión simulada y reenvía resúmenes al recuperar conectividad.

AWS IoT Core recibe lotes autenticados con certificados X.509 diferentes. Una regla IoT escribe cada lote JSON directamente en la zona Bronze de Amazon S3. AWS Glue cataloga los lotes como arreglos de eventos y Athena los expande con `UNNEST`, los transforma en Silver/Parquet y construye Gold.

## Resultados de aprendizaje

Al terminar, el estudiante podrá:

1. separar responsabilidades de Edge, Fog y cloud mediante evidencia;
2. explicar el efecto de una ventana Fog sobre tráfico, detalle e incidentes;
3. autenticar publicadores IoT con identidades distintas y mínimo privilegio;
4. operar un buffer local y reconocer la necesidad de idempotencia;
5. distinguir las zonas Bronze, Silver y Gold de un Data Lake;
6. consultar JSON y Parquet con Athena y comparar bytes leídos;
7. reconocer por qué una simulación pequeña representa problemas de Big Data sin convertirse en Big Data real.

## Arquitectura

```text
Sensores simulados
       |
       +--> Edge: calidad, deduplicación, alarma local --certificado Edge--+
       |                                                                  |
       +--> Fog: ventana, agregación, spool y replay --certificado Fog----+--> AWS IoT Core
                                                                                |
                                                                                v
                                                                  Regla IoT + acción S3
                                                                                |
                                                                                v
                                                        S3 Bronze JSON --> Glue --> Athena
                                                                                |
                                                                  CTAS Parquet Silver
                                                                                |
                                                                   Vista Gold por viaje
```

## Servicios y costo acotado

La infraestructura utiliza AWS IoT Core, S3, Glue Data Catalog, Athena, IAM y CloudFormation en `us-east-2`. No crea instancias, clústeres EMR, NAT Gateways, dashboards ni direcciones IPv4. La ingestión usa la acción S3 nativa de una regla IoT porque la organización de las cuentas estudiantiles bloquea Amazon Data Firehose mediante una Service Control Policy.

El experimento predeterminado genera 2.880 muestras. Las publica en lotes de hasta 200 elementos y divide además por bytes para respetar el límite de mensajes IoT. Athena impone un corte de 1 GiB leído por consulta. El workgroup ofrece una ubicación predeterminada aislada, pero permite que CTAS escriba explícitamente en `silver/`. El consumo es pequeño, pero no se promete costo cero y la limpieza final es obligatoria.

## Aislamiento en cuentas compartidas

`deploy-lab.sh` genera 64 bits aleatorios y crea un stack como:

```text
ucab-lab-7-a1b2c3d4e5f60708
```

El identificador forma parte del bucket, topic MQTT, Things, política IoT, base Glue y workgroup Athena. El script rechaza una colisión y nunca actualiza un stack existente.

Los certificados y claves privadas solo se guardan bajo `.lab/`, con permisos del usuario, y Git los ignora. Cada política permite publicar exclusivamente en el topic del propio laboratorio.

## Organización

| Ruta | Contenido |
|---|---|
| `LAB_GUIDE.md` | Único recorrido estudiantil, tiempos, evidencias y preguntas. |
| `app/` | Generador, Edge, Fog, contrato y publicación X.509. |
| `infra/` | Stack reproducible de AWS. |
| `queries/` | Consulta guiada y plantillas de las misiones Silver/Gold. |
| `scripts/` | Diagnóstico, despliegue, experimento, Athena, verificación y limpieza. |
| `tests/` | Pruebas unitarias, contratos y validaciones de seguridad. |
| `evidence/` | Lista de evidencias del informe. |
| `TROUBLESHOOTING.md` | Diagnóstico de fallas frecuentes. |

## Guía de realización

El procedimiento, los comandos, las salidas esperadas, las evidencias y las preguntas se encuentran exclusivamente en [LAB_GUIDE.md](LAB_GUIDE.md). El README describe el propósito y la estructura del laboratorio, pero no constituye un segundo recorrido operativo.
