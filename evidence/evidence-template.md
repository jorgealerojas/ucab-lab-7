# Evidencias - Laboratorio 7

- **Estudiante:**
- **Identificador del stack:**
- **Ventana Fog elegida:**

Use este archivo solo como lista de control. La entrega consiste en un documento de formato libre con las capturas necesarias de cada paso numerado, una explicación de lo observado y las respuestas solicitadas.

## 1. Hipótesis

Incluya la tabla inicial y su corrección final.

## 2. Infraestructura e identidad

- Diagnóstico aprobado.
- Stack `CREATE_COMPLETE`.
- Endpoint ATS y topic, ocultando cuenta y certificados.
- Dos Things/certificados activos.
- Recurso exacto permitido por `iot:Publish`.

## 3. Edge y Fog

| Métrica | Resultado |
|---|---:|
| Lecturas recibidas | |
| Inválidas | |
| Duplicadas en Edge | |
| Aceptadas | |
| Alarmas locales | |
| Eventos Fog únicos | |
| Factor de reducción | |
| Duplicados de red inyectados | |

Adjunte evidencia del spool antes y después de reconectar.

## 4. Data Lake

- Jerarquía Bronze.
- Resumen Athena por pipeline.
- CTAS Silver aprobado.
- Vista Gold y viaje de mayor riesgo.

| Consulta | Formato | Bytes leídos | Tiempo del motor |
|---|---|---:|---:|
| Comparación Bronze | JSON | | |
| Comparación Silver | Parquet/Snappy | | |

## 5. Respuestas

Responda claramente las cinco preguntas de `LAB_GUIDE.md`, conserve la numeración y relacione cada respuesta con las capturas o métricas correspondientes.

## 6. Cierre

- `VERIFICACION APROBADA`.
- `LIMPIEZA COMPLETA`.

No incluya claves privadas, certificados completos, credenciales, número completo de cuenta ni contenido de `.lab/identities.json`.
