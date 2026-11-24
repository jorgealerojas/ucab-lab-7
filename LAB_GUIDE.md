# Guía del laboratorio: cadena de frío, del Edge al Data Lake

- **Unidad:** VII - Datos en la nube
- **Duración:** 1 h 45 min
- **Modalidad:** individual
- **Región obligatoria:** US East (Ohio), `us-east-2`

## Reto

Una empresa transporta productos farmacéuticos que deben permanecer entre 2 °C y 8 °C. Cada camión puede reaccionar localmente, un gateway de depósito puede resumir varios flujos y la nube debe conservar trazabilidad histórica.

Comparará un recorrido Edge directo con un recorrido Edge + Fog. Después convertirá los eventos crudos en datos confiables y calculará indicadores por viaje.

## Reglas de operación

- Use únicamente `us-east-2`.
- Trabaje solo con el identificador generado por su despliegue.
- No muestre claves privadas, certificados completos, ARN de identidad ni el número completo de cuenta.
- No aumente dispositivos, muestras o tamaño de lote fuera de los límites del validador.
- No edite la plantilla CloudFormation durante la sesión.
- Elimine el stack con el script de limpieza.

## Informe y evidencias

Entregue un documento de formato libre que incluya:

- las capturas necesarias de cada paso numerado de la práctica;
- una explicación breve de qué hizo, qué resultado obtuvo y qué demuestra cada captura;
- las métricas y comparaciones solicitadas;
- las respuestas a todas las preguntas de la sección **Preguntas del informe**;
- la evidencia de verificación y limpieza final.

Las capturas deben mostrar el comando y la parte relevante de su salida. No incluya claves privadas, certificados completos, credenciales, ARN de identidad ni el número completo de cuenta.

Evidencias mínimas:

1. Hipótesis Edge/Fog/cloud.
2. Diagnóstico y stack `CREATE_COMPLETE`.
3. Endpoint y topic descubiertos, sin credenciales.
4. Dos identidades y política de mínimo privilegio.
5. Métricas locales Edge/Fog y buffer pendiente.
6. Buffer vacío después del reenvío.
7. Objetos en Bronze y resultado de la consulta inicial.
8. Tabla Silver y comparación JSON/Parquet.
9. Vista Gold e indicadores por viaje.
10. Verificación aprobada y eliminación del stack.

## Cómo leer los comandos de esta guía

No ejecute un comando sin poder explicar su propósito. En cada paso se indica qué hace, por qué se necesita y qué resultado debe observar. Estas convenciones aparecerán varias veces:

- Una orden que comienza con `./scripts/` ejecuta un script versionado en este repositorio. Puede abrirlo para inspeccionarlo; no es un comando opaco del sistema.
- Una ruta como `generated/...` representa evidencia local producida por su ejecución. Una ruta como `.lab/...` contiene estado técnico y material sensible que no debe incluir en el informe.
- Las comillas dobles conservan una ruta como un solo argumento y permiten sustituir variables como `$LAB_ID`.
- `$(comando)` ejecuta el comando interno y asigna o inserta su salida; no es texto literal.
- `|` conecta la salida del comando izquierdo con la entrada del derecho. En esta práctica se usa para presentar un único objeto JSON, no para modificarlo.
- Los helpers de Athena sustituyen `{{DATABASE}}` y `{{BUCKET}}` por recursos de su stack. Así se evita copiar nombres físicos o consultar accidentalmente datos de otro despliegue.

Cuando un comando no produce salida, compruebe el cambio esperado en el paso siguiente. Ausencia de salida no significa por sí sola que el comando haya fallado; los errores sí aparecen en la terminal y devuelven un estado distinto de cero.

## 0-8 min - Hipótesis de arquitectura

Antes de abrir AWS, complete esta tabla en su informe:

| Decisión | Hipótesis inicial | Evidencia que necesitaría |
|---|---|---|
| Lectura fuera de 2-8 °C | ¿Edge, Fog o cloud? | |
| Duplicado exacto del sensor | ¿Edge, Fog o cloud? | |
| Promedio de una ventana | ¿Edge, Fog o cloud? | |
| Comparación de todos los viajes | ¿Edge, Fog o cloud? | |
| Operación durante una caída de Internet | ¿Qué capa continúa? | |

Defina también qué información espera perder al agregar muestras en una ventana Fog.

## 8-22 min - Preparar y desplegar

### 1. Seleccionar Ohio y definir la región principal

Abra AWS CloudShell en **US East (Ohio)**. `export` crea una variable de entorno para la terminal actual. `AWS_REGION` es la región que consultan el SDK de Python y buena parte de AWS CLI; fijarla evita desplegar recursos accidentalmente en otra región. El comando no crea recursos.

```bash
export AWS_REGION=us-east-2
```

El comando no muestra salida. El prompt debe aparecer nuevamente sin errores.

### 2. Definir la región predeterminada

Algunas herramientas consultan `AWS_DEFAULT_REGION` en lugar de `AWS_REGION`. Se define también porque no todos los componentes de AWS resuelven la región con la misma prioridad. Ambas variables deben coincidir para que CloudFormation, IoT, S3, Glue y Athena trabajen sobre Ohio.

```bash
export AWS_DEFAULT_REGION=us-east-2
```

Este comando tampoco muestra salida. El prompt debe aparecer inmediatamente.

### 3. Descargar el repositorio

`git clone` descarga una copia versionada del repositorio en el almacenamiento de CloudShell. Esto permite inspeccionar y ejecutar localmente la aplicación, la infraestructura, las consultas, las pruebas y esta guía. Todavía no crea recursos AWS ni modifica la cuenta.

```bash
git clone https://github.com/jorgealerojas/ucab-lab-7.git
```

La salida debe comenzar con `Cloning into 'ucab-lab-7'` y terminar sin mensajes de error.

### 4. Entrar en el directorio

`cd` cambia el directorio de trabajo de la terminal. Es necesario porque los scripts usan rutas relativas al repositorio y protecciones como `.gitignore`; ejecutarlos desde otra carpeta haría que no encontraran la plantilla, las pruebas o el estado local.

```bash
cd ucab-lab-7
```

El comando no muestra salida. El nombre `ucab-lab-7` debe aparecer en la ruta del prompt.

### 5. Diagnosticar el entorno

El diagnóstico es una compuerta antes de generar costos o estado remoto. Comprueba que existen AWS CLI, Python, `curl` y OpenSSL; valida credenciales y región; ejecuta las pruebas unitarias; y pide a AWS validar la sintaxis de CloudFormation. Las comprobaciones son locales o de lectura y no despliegan la arquitectura. En la primera ejecución crea `.venv/` e instala allí dependencias aisladas, por lo que no modifica Python global de CloudShell.

```bash
./scripts/doctor.sh
```

La salida debe mostrar `Preparando dependencias Python` la primera vez, varias líneas `OK`, las pruebas deben aprobar y la última línea debe ser:

```text
DIAGNOSTICO APROBADO: entorno listo en us-east-2
```

No continúe si aparece `ERROR` o si una prueba falla.

### 6. Desplegar la arquitectura

El script genera un identificador aleatorio de 64 bits para aislar recursos aunque varias personas compartan la cuenta. Luego entrega la plantilla a CloudFormation, espera a que IoT, S3, Glue, Athena e IAM queden consistentes y guarda sus outputs bajo `.lab/`. Finalmente crea dos identidades X.509 diferentes para comprobar que Edge y Fog se autentican como publicadores separados.

```bash
./scripts/deploy-lab.sh
```

La operación puede tardar varios minutos. Debe mostrar `Identificador generado`, después `Creando IoT Core...` y finalmente:

```text
LABORATORIO LISTO: ucab-lab-7-<16 dígitos hexadecimales>
```

Anote el identificador. Las claves quedan bajo `.lab/` y nunca deben copiarse al informe.

Si CloudFormation no puede crear un recurso, el script muestra una tabla bajo `CAUSA REPORTADA POR CLOUDFORMATION` antes de limpiar el stack. Conserve esa salida para diagnosticar el permiso, cuota o recurso que produjo el error.

## 22-38 min - Misión autónoma: conectar el publicador

En esta sección debe investigar parte del procedimiento. Puede usar la consola, `aws help` y la documentación oficial de AWS IoT Core.

Debe descubrir:

1. el **endpoint de datos ATS** de AWS IoT para la cuenta y región actuales;
2. el output `TopicPrefix` del stack propio;
3. la regla IoT que escucha ese topic;
4. la acción que sigue a la regla;
5. los dos Things y sus certificados activos;
6. el único ARN de topic donde la política permite `iot:Publish`.

### 7. Consultar el inventario del laboratorio

El script combina dos fuentes: consulta a CloudFormation para conocer el estado y los identificadores físicos, y lee el inventario local de certificados. Se ejecuta para relacionar la arquitectura lógica con recursos reales antes de configurar el publicador. Es de solo lectura y abrevia los certificados; no imprime claves privadas.

```bash
./scripts/status.sh
```

Debe ver el stack en `CREATE_COMPLETE`, una tabla de recursos y dos identidades: `edge` y `fog`.

### 8. Crear una configuración de trabajo

`cp` crea una copia editable del contrato de configuración. Se conserva el ejemplo como referencia recuperable y se trabaja sobre `pipeline.json`, que Git ignora porque contiene el endpoint particular de la cuenta. Todavía no se publica telemetría.

```bash
cp config/pipeline.example.json config/pipeline.json
```

El comando no muestra salida si la copia termina correctamente.

### 9. Editar las decisiones investigadas

`nano` abre la copia en un editor de terminal. Aquí debe trasladar al contrato local los datos que investigó en AWS y tomar una decisión propia sobre el tamaño de ventana Fog; por eso el repositorio no completa estos valores automáticamente.

```bash
nano config/pipeline.json
```

Sustituya únicamente:

- `iot_endpoint` con el endpoint ATS descubierto;
- `topic_prefix` con el output exacto de su stack;
- `window_size` con un entero entre 5 y 25.

Justifique la ventana elegida antes de validarla. Una ventana mayor reduce mensajes, pero oculta más detalle temporal y retiene datos durante más tiempo. Guarde el archivo y cierre `nano`; el editor no produce un resumen automático.

### 10. Validar la configuración

El validador analiza el JSON antes de que se utilicen certificados o red. Comprueba tipos, límites, región, forma del endpoint y que el topic pertenezca al stack registrado. Esta separación permite detectar un error de configuración sin publicar telemetría en el topic equivocado.

```bash
./scripts/validate-config.sh
```

Debe mostrar la ventana, la cantidad de dispositivos y las muestras por dispositivo. La primera línea debe indicar `CONFIGURACION APROBADA`.

## 38-53 min - Edge y Fog sin conectividad

### 11. Preparar el experimento sin usar la nube

El script ejecuta el experimento sin usar la red: genera telemetría reproducible, inyecta casos inválidos y duplicados, aplica validación y alarmas Edge, agrega ventanas Fog y deja los resúmenes en un spool local. Separar preparación de publicación permite observar qué capacidades continúan durante una caída de Internet y conservar una base comparable entre ejecuciones.

```bash
./scripts/prepare-experiment.sh
```

La salida presenta un objeto JSON con lecturas recibidas, inválidas, duplicadas, alarmas, eventos Fog y factor de reducción. Debe terminar con `BUFFER FOG PENDIENTE` y la ruta del archivo.

### 12. Recuperar el identificador local

La parte `tr -d '\r\n' < .lab/lab-id` lee el archivo y elimina el salto de línea final. `$(...)` captura ese resultado y la asignación lo guarda en `LAB_ID`. Se evita copiar el identificador manualmente y mezclar evidencia de otro despliegue.

```bash
LAB_ID="$(tr -d '\r\n' < .lab/lab-id)"
```

La asignación no muestra salida. Las instrucciones siguientes utilizarán la variable `LAB_ID`.

### 13. Examinar las métricas

`python3 -m json.tool` valida y presenta el JSON con indentación. La ruta entre comillas sustituye `$LAB_ID` por el identificador actual. Se usa para interpretar las métricas que luego sustentan las comparaciones y respuestas; no modifica el archivo.

```bash
python3 -m json.tool "generated/$LAB_ID/metrics.json"
```

La salida debe contener las secciones `edge` y `fog`. Registre entradas recibidas, inválidas, duplicadas, eventos aceptados, resúmenes Fog y factor de reducción.

### 14. Contar el buffer Fog

`wc -l` cuenta líneas. Como el spool usa JSON Lines —un evento Fog por línea—, el resultado equivale al número de publicaciones pendientes. El objetivo no es solo comprobar que existe un archivo, sino medir cuánto trabajo quedó retenido durante la desconexión.

```bash
wc -l "generated/$LAB_ID/fog-spool.jsonl"
```

La salida muestra un número mayor que cero seguido de la ruta del spool.

### 15. Inspeccionar un resumen Fog

`head -n 1` lee únicamente el primer evento del spool. El operador `|` lo entrega a `python3 -m json.tool`, que lo valida y formatea. Se limita a una línea para inspeccionar el contrato Fog sin inundar la terminal ni alterar el buffer.

```bash
head -n 1 "generated/$LAB_ID/fog-spool.jsonl" | python3 -m json.tool
```

La salida debe incluir `sample_count`, `source_event_ids`, `anomaly_count` y `replayed`. El buffer contiene además un duplicado deliberado para representar un reintento cuya confirmación se perdió.

## 53-65 min - Reconexión y Cloud IoT

### 16. Publicar y reenviar

El script abre conexiones HTTPS mutual TLS contra el endpoint de IoT: publica los eventos Edge con su certificado y reenvía el spool con el certificado Fog. Agrupa eventos sin superar el límite de tamaño de AWS IoT y registra checkpoints para tolerar una interrupción. Esto prueba autenticación, autorización por topic y recuperación del gateway, no solo una carga de archivos a S3.

```bash
./scripts/publish-experiment.sh
```

Debe mostrar `EDGE PUBLICADO` y `FOG REENVIADO`. Si se interrumpe, repita solamente este comando: los checkpoints evitan repetir una etapa que ya terminó.

### 17. Confirmar que el buffer se vació

Repita exactamente el conteo del paso 14 para comparar el mismo indicador antes y después de recuperar conectividad. El gateway vacía el spool únicamente cuando AWS IoT acepta todos los lotes; por eso un valor cero representa confirmación de entrega al broker, no la desaparición arbitraria del archivo.

```bash
wc -l "generated/$LAB_ID/fog-spool.jsonl"
```

El resultado esperado comienza por `0`. La regla IoT escribe cada lote aceptado directamente en S3; la aparición en la consola puede tardar algunos segundos.

## 65-77 min - Zona Bronze y consulta inicial

### 18. Inspeccionar la zona Bronze

En la consola de S3, localice el bucket cuyo nombre contiene su identificador. La regla IoT escribe cada lote sin transformarlo en Bronze y construye claves particionadas por hora. Esta zona preserva la evidencia recibida para que las reglas de calidad posteriores sean reproducibles. Debe observar una jerarquía con esta forma:

```text
bronze/year=.../month=.../day=.../hour=.../
```

No descargue ni edite los objetos. Bronze conserva lo recibido, incluido el reintento duplicado. Capture la jerarquía y al menos un objeto, ocultando el número de cuenta si aparece.

### 19. Consultar los datos crudos

El helper primero rechaza consultas con `TODO`, sustituye `{{DATABASE}}` y `{{BUCKET}}` por outputs del stack propio, envía el SQL al workgroup aislado de Athena y espera un estado terminal. La consulta usa `UNNEST` porque cada objeto Bronze contiene un lote `events`; así convierte el arreglo en filas consultables sin reescribir Bronze.

```bash
./scripts/run-query.sh queries/01-bronze-summary.sql
```

La salida debe mostrar `QueryExecutionId`, bytes leídos, tiempo del motor y una fila para `edge` y otra para `fog`. Si todavía no aparecen filas, espere 30 segundos y repita solo este comando.

Registre filas cloud, eventos únicos, muestras representadas y anomalías. Explique por qué `count(*)` y `sum(sample_count)` responden preguntas diferentes. Observe también que el filtro por fecha limita las particiones que Athena explora.

## 77-91 min - Misión autónoma: Silver e idempotencia

La zona Silver debe usar Parquet con compresión Snappy, conservar una fila por `event_id`, preferir la observación más reciente y escribirse bajo `silver/`.

### 20. Copiar la plantilla Silver

`cp` crea una consulta de trabajo dentro de `generated/`. La plantilla original permanece intacta para poder comparar, recuperar o reiniciar el intento. La copia conserva marcadores `TODO_...` deliberados: el helper no permitirá ejecutarla hasta que se conviertan en expresiones SQL.

```bash
cp queries/02-silver-ctas-template.sql generated/silver-ctas.sql
```

El comando no muestra salida. Debe aparecer el archivo `generated/silver-ctas.sql`.

### 21. Completar la transformación Silver

Antes de editar, lea la consulta completa. `sed -n '1,140p'` imprime solamente ese rango de líneas y no modifica el archivo. Observe que la subconsulta `expanded` convierte cada arreglo Bronze en filas y asigna nombres simples a los campos.

```bash
sed -n '1,140p' generated/silver-ctas.sql
```

La salida debe mostrar tres marcadores `TODO_...`, la expansión `UNNEST(events)` y la función `row_number`. Ahora abra la copia para editarla:

```bash
nano generated/silver-ctas.sql
```

Sustituya los tres marcadores por SQL válido. No necesita adivinar el esquema; use estas pistas:

- **Formato:** la misión pide el formato columnar que luego se comparará con JSON. El valor se escribe como una cadena SQL.
- **Clave de idempotencia:** busque entre los aliases de `expanded` el campo diseñado como identidad estable del evento. Debe ser igual en un original y en su reintento; `device_id`, posición y timestamp por sí solos no garantizan eso.
- **Recencia:** busque el campo temporal del evento. Con `DESC`, la función de ventana asignará `row_rank = 1` a la observación más reciente de cada identidad.

La lógica completa debe poder explicarse así: agrupar reintentos de la misma identidad, ordenarlos del más reciente al más antiguo y conservar únicamente el rango 1. Guarde con `Ctrl+O`, confirme con `Enter` y salga con `Ctrl+X`. El helper rechazará la consulta si queda algún marcador incompleto.

### 22. Crear la tabla Silver

El helper ejecuta un CTAS (`CREATE TABLE AS SELECT`): Athena lee los lotes JSON de Bronze, aplica la ventana de deduplicación, materializa el resultado en archivos columnares bajo `silver/` y registra la tabla resultante en Glue. Es una transformación de datos y metadatos; no modifica los objetos Bronze.

```bash
./scripts/run-query.sh generated/silver-ctas.sql
```

Debe terminar con un `QueryExecutionId` y estadísticas, sin `FAILED`. La primera ejecución puede tardar más mientras Athena prepara capacidad.

### 23. Medir la consulta sobre JSON

Esta consulta calcula la tasa de anomalías directamente sobre Bronze. Athena debe leer JSON y expandir los arreglos `events`, por lo que esta ejecución sirve como línea base. Registre bytes leídos y tiempo del motor; no use solo el tiempo total de terminal, porque incluye espera del servicio.

```bash
./scripts/run-query.sh queries/04-json-comparison.sql
```

Debe mostrar las filas `edge` y `fog` junto con `represented_samples`, `anomalous_samples` y `anomaly_rate_pct`.

### 24. Medir la consulta sobre Parquet

Ejecute la misma agregación lógica sobre Silver. Como Silver ya está deduplicado y organizado en Parquet, no necesita `UNNEST` y Athena puede leer únicamente las columnas requeridas. La comparación busca relacionar formato, organización y bytes escaneados; no demostrar que toda consulta pequeña será siempre más rápida.

```bash
./scripts/run-query.sh queries/05-parquet-comparison.sql
```

Debe mostrar las mismas muestras representadas para ambos recorridos. Compare sus bytes leídos con el paso anterior. En un dataset pequeño la diferencia puede variar; razone qué ocurriría con más columnas y mayor volumen.

## 91-98 min - Misión autónoma: Gold y decisión

### 25. Copiar la plantilla Gold

La plantilla define la estructura y el nivel de agregación de una vista por `trip_id` y `lot_id`. `cp` crea una versión editable para conservar la referencia original, igual que en Silver.

```bash
cp queries/03-gold-view-template.sql generated/gold-view.sql
```

El comando no muestra salida. Debe aparecer `generated/gold-view.sql`.

### 26. Completar la vista Gold

Inspeccione primero la consulta. `sed` permite ver los aliases esperados, la tabla fuente, el filtro Fog y el `GROUP BY` sin entrar todavía al editor.

```bash
sed -n '1,100p' generated/gold-view.sql
```

Después abra la copia:

```bash
nano generated/gold-view.sql
```

Sustituya las cuatro expresiones `TODO_...`. Aquí tampoco se espera que adivine columnas; debe escoger y aplicar correctamente la función de agregación:

| Resultado Gold | Campo disponible en Silver | Operación que debe razonar |
|---|---|---|
| muestras originales representadas | `sample_count` | sumar todas las ventanas del viaje |
| muestras anómalas | `anomaly_count` | sumar todas las ventanas del viaje |
| pico térmico del viaje | `max_temperature_c` | conservar el mayor máximo observado |
| temperatura más baja | `min_temperature_c` | conservar el menor mínimo observado |

`count(*)` no sustituye las dos sumas: contaría ventanas Fog, no muestras originales. Escriba las cuatro expresiones como llamadas a funciones SQL, conserve los aliases existentes y cierre el editor cuando no queden marcadores.

### 27. Crear la vista Gold

El helper envía `CREATE OR REPLACE VIEW` a Athena. A diferencia del CTAS, una vista guarda una definición SQL en el catálogo y calcula resultados cuando se consulta; no crea otra copia de los archivos Silver. Esto representa una capa Gold lógica orientada a indicadores de negocio.

```bash
./scripts/run-query.sh generated/gold-view.sql
```

La salida debe mostrar un `QueryExecutionId`, cero o pocos bytes leídos y finalizar sin errores.

Para consultar la vista, cree un archivo separado. No edite la definición Gold ya ejecutada:

```bash
nano generated/gold-analysis.sql
```

Escriba un `SELECT` sobre `"{{DATABASE}}".gold_trip_metrics`. Investigue `ORDER BY ... DESC` y `LIMIT` para ordenar por muestras anómalas y mostrar solo los viajes más relevantes. Guarde el archivo y ejecútelo con el mismo helper:

```bash
./scripts/run-query.sh generated/gold-analysis.sql
```

El helper sustituye la base propia antes de enviar la consulta. Identifique el viaje con más muestras fuera de rango, compruebe que el orden coincide con su criterio y capture el resultado.

## 98-105 min - Verificar y limpiar

### 28. Ejecutar la verificación integral

El verificador realiza comprobaciones de solo lectura en varias capas: regla IoT habilitada y conectada a S3, objetos Bronze visibles, tablas Glue requeridas, workgroup Athena activo y conservación de muestras entre Edge y Fog. `--require-silver` convierte la existencia de Silver en una condición obligatoria, evitando aprobar una ejecución incompleta.

```bash
./scripts/verify-lab.sh --require-silver
```

Cada comprobación debe mostrar `OK`. La última línea debe ser `VERIFICACION APROBADA`.

### 29. Eliminar el laboratorio

El script usa exclusivamente el estado de `.lab/` y valida el patrón del identificador antes de eliminar. Separa y revoca certificados, elimina tablas creadas fuera de CloudFormation, vacía todas las versiones del bucket y finalmente borra el stack. El orden importa: CloudFormation no puede eliminar un bucket versionado que todavía contiene objetos ni certificados aún adjuntos.

```bash
./scripts/cleanup-lab.sh
```

La operación puede tardar varios minutos. Debe terminar con `LIMPIEZA COMPLETA` y el identificador del stack. Conserve esa salida como última captura del informe.

## Preguntas del informe

Responda las cinco preguntas en el documento de formato libre. Use cifras de sus resultados y relacione cada respuesta con una captura o evidencia.

1. Compare Edge y Fog con sus métricas: ¿qué factor de reducción produjo la ventana elegida, qué detalle temporal se perdió y por qué la alarma térmica debe seguir funcionando en Edge?
2. Reconstruya el recorrido de un lote desde el publicador hasta Athena. Distinga las funciones de AWS IoT Core, la regla IoT, S3, Glue, `UNNEST` y Athena.
3. ¿Por qué AWS IoT autentica el certificado X.509 y no confía en el `device_id` declarado dentro del JSON? Relacione su respuesta con la política limitada al topic del laboratorio.
4. ¿Por qué Bronze conserva el duplicado y Silver lo elimina por `event_id`? Use los bytes medidos en Athena para explicar además qué cambió al pasar de JSON a Parquet.
5. Aplique volumen, velocidad, variedad, veracidad y valor al experimento. ¿Qué cambiaría al escalarlo y por qué este dataset no debe presentarse como Big Data real?

## Contenido del informe

Antes de entregar, compruebe que el documento de formato libre contiene:

- identificación del laboratorio y LabId, sin número completo de cuenta;
- hipótesis inicial y corrección final;
- capturas necesarias de los 29 pasos;
- tabla de métricas Edge/Fog;
- comparación Bronze/Silver con bytes y tiempo;
- resultado Gold;
- respuestas numeradas del 1 al 5;
- verificación y limpieza aprobadas.
