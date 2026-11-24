# Solución de problemas

Trabaje siempre sobre el stack registrado en `.lab/stack-name`. No elimine recursos manualmente salvo que esta guía lo indique.

## `doctor.sh` rechaza la región

Defina primero la región principal. El comando no produce salida:

```bash
export AWS_REGION=us-east-2
```

Defina después la región predeterminada. Tampoco produce salida:

```bash
export AWS_DEFAULT_REGION=us-east-2
```

Compruebe la configuración efectiva. La fila `region` debe mostrar `us-east-2`:

```bash
aws configure list
```

## Python informa `No module named pytest`

Actualice su copia del repositorio y vuelva a ejecutar el diagnóstico. La versión actual crea un entorno aislado `.venv/` e instala automáticamente `pytest`, `boto3` y `PyYAML`:

```bash
git pull
```

Cuando termine la descarga, ejecute el diagnóstico nuevamente:

```bash
./scripts/doctor.sh
```

La primera ejecución necesita conexión a Internet y puede tardar alrededor de un minuto. Debe aparecer `OK: dependencias Python instaladas en .venv` o `OK: dependencias Python disponibles en .venv`.

## CloudFormation falla

Lea la tabla que el script imprime bajo `CAUSA REPORTADA POR CLOUDFORMATION`. Cada fila identifica el recurso, su tipo y la razón de `CREATE_FAILED`. Causas habituales:

- permisos ausentes para IoT, S3, Glue, Athena o IAM;
- política institucional que impide crear roles;
- nombre global de bucket ocupado por una inconsistencia excepcional;
- cuota de reglas IoT o recursos Glue.

El script conserva el stack fallido únicamente mientras consulta esos eventos y luego lo elimina junto con el estado local. Si la tabla no puede consultarse, abra **CloudFormation → Stacks → Events** de inmediato y busque el primer evento `CREATE_FAILED` antes de realizar cambios manuales.

## Falló la creación del certificado

El trap del despliegue intenta desactivar y eliminar cualquier certificado parcial y luego solicita borrar el stack. Revise que la identidad IAM permita:

- crear, activar, adjuntar, separar y eliminar certificados IoT;
- adjuntar políticas y Things;
- descargar la CA raíz pública de Amazon Trust Services.

Nunca cree una clave privada manualmente para “arreglar” el estado.

## `CONFIGURACION APROBADA` no aparece

- El endpoint debe ser ATS, pertenecer a `us-east-2` y terminar en `.iot.us-east-2.amazonaws.com`.
- `topic_prefix` debe coincidir exactamente con el output del stack registrado.
- La ventana debe estar entre 5 y 25.
- No agregue comentarios dentro del JSON.

## AWS IoT responde 403

Compruebe que:

1. no intercambió las carpetas `.lab` entre sesiones;
2. el certificado sigue `ACTIVE`;
3. la política está adjunta al certificado;
4. el topic contiene su LabId y termina en `/edge` o `/fog`;
5. el reloj de CloudShell es correcto.

Consulte el inventario seguro. El comando muestra el stack, los recursos principales y los identificadores abreviados de los certificados, pero no imprime claves privadas:

```bash
./scripts/status.sh
```

## La publicación se interrumpe

Repita únicamente el publicador. El checkpoint permite continuar desde la etapa incompleta:

```bash
./scripts/publish-experiment.sh
```

El checkpoint evita repetir Edge si esa etapa ya terminó. Fog conserva el spool hasta que todos los lotes se publican. No vuelva a ejecutar `prepare-experiment.sh`, pues reemplazaría la evidencia local.

## S3 todavía no contiene Bronze

La regla IoT escribe cada lote directamente en S3. Espere unos segundos y después revise:

- regla IoT habilitada;
- acción S3 configurada sobre el bucket propio;
- rol de la regla con `s3:PutObject` limitado a `bronze/` y `errors/iot/`;
- prefijo `errors/iot/`.

Si existe un archivo de error, registre el mensaje sin copiar ARN de cuenta ni contenido sensible.

## Athena devuelve cero filas

Confirme primero que S3 contiene objetos bajo `bronze/year=...`. La tabla usa proyección de particiones entre 2025 y 2030. Si el reloj del servicio queda fuera de ese rango, deténgase y documente la inconsistencia.

No ejecute `MSCK REPAIR TABLE`; la tabla usa partition projection.

## CTAS informa que la ubicación ya tiene datos

Athena no sobrescribe `silver/`. La consulta ya se ejecutó antes. No borre objetos manualmente durante la práctica. Use la tabla Silver existente si aparece en Glue. Si la tabla no existe pero el prefijo contiene datos, deténgase y documente la inconsistencia antes de cambiar recursos.

## La plantilla SQL conserva `TODO`

`run-query.sh` rechaza consultas incompletas antes de enviarlas a Athena. Busque los marcadores:

```bash
grep -n TODO generated/*.sql
```

La salida indica archivo, número de línea y marcador pendiente. Investigue la expresión requerida; no elimine el texto sin sustituirlo por SQL válido.

## La limpieza falla

Vuelva a ejecutar la limpieza. El proceso es idempotente para certificados ausentes y tablas opcionales:

```bash
./scripts/cleanup-lab.sh
```

La salida debe terminar en `LIMPIEZA COMPLETA`. Si CloudFormation indica que el bucket no está vacío, el script debe vaciar todas las versiones antes de reintentar.

No elimine certificados de otros estudiantes. El script valida nombre de stack, LabId, bucket y base Glue antes de modificar recursos.
