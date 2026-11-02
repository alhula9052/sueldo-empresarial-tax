# Nexo · Análisis empresarial para Chile

Aplicación funcional de asesoría laboral, tributaria y previsional. Django 5.2 LTS, Python 3.12, SQLite, páginas renderizadas en servidor, ReportLab y openpyxl. La arquitectura mantiene autenticación, permisos, transacciones y validación en el servidor; no requiere servicios de pago, claves de IA ni un proceso de frontend separado. SQLite facilita el desarrollo local; PostgreSQL requeriría configurar su driver y probar la migración antes de escalar.

**Estado normativo:** no se pudieron consultar documentos oficiales porque el proxy del entorno respondió `403` a SII, Dirección del Trabajo y BCN. No se incorporaron citas, tasas ni límites jurídicos sin verificar. La biblioteca admite carga manual, extractos, fechas, enlaces y respaldos privados. Las reglas de demostración están **pendientes**, y los resultados definitivos y cálculos sin parámetros verificados se bloquean. Las pruebas matemáticas usan valores sintéticos identificados como tales, nunca normativa chilena.

## Ejecutar

```bash
cd /workspace/sueldo-empresarial-tax
bash scripts/install.sh
DEBUG=1 .venv/bin/python manage.py seed_demo
bash scripts/start.sh
```

El servidor escucha únicamente en `127.0.0.1:8000`. Use el checkout existente: las tareas de nube ya están aisladas; no es necesario crear otro worktree. No se desplegó públicamente.

Usuario de demostración: `demo`. `seed_demo` genera una contraseña aleatoria en `.demo-password`, con permisos `0600`, o utiliza `DEMO_PASSWORD` si usted la proporciona en el entorno. No muestra ni versiona la contraseña. El comando es idempotente y no restablece contraseñas existentes. Ese archivo es exclusivo de la demostración local, no un secreto de producción.

Para un cliente real, sin datos de demostración:

```bash
DEBUG=1 .venv/bin/python manage.py create_client --name "Mi consultora" --username asesor
```

La contraseña se solicita mediante entrada oculta; alternativamente, se acepta `CLIENT_ADMIN_PASSWORD` desde el entorno. Cada usuario pertenece a un cliente. Solo un administrador de ese cliente puede crear usuarios y modificar sus roles o desactivarlos. Para restablecer una contraseña: `manage.py changepassword USUARIO` con el entorno Django configurado.

`.env.example` documenta las variables y no contiene secretos. Django lee variables del proceso: no carga `.env` automáticamente. Para producción, `DEBUG=0` exige `DJANGO_SECRET_KEY`; las cookies son seguras con HTTPS. No use el servidor de desarrollo para publicar.

## Flujo de trabajo

1. **Empresas:** RUT, tipo jurídico, régimen, determinación de renta y sociedad de profesionales.
2. **Personas y entidades:** titulares naturales o jurídicos; RUT normalizado y único dentro del cliente.
3. **Composición:** capital, utilidades, votos, clases, derechos especiales, vigencias e intermediario para participaciones indirectas. Se muestran tabla y mapa; no se infiere control jurídico por propiedad económica.
4. **Administración:** representación y administración separadas, ejercicio individual/conjunto/indistinto, contratación, remuneración, disciplina, directorio, designación y dirección efectiva.
5. **Documentos privados:** escrituras, poderes y respaldos, con persona, página y observaciones. Descarga autenticada como adjunto; no existe ruta pública de medios.
6. **Trabajo efectivo:** una ficha por persona/empresa/mes. Respuestas Sí/No/No determinado, observaciones y evidencia por respuesta, funciones, dedicación, remuneración, aporte societario, otras rentas y discrepancias.
7. **Evaluación:** abra el caso y guarde una versión. Conserva antecedentes, reglas completas, parámetros, fuentes, identidad del autor, fecha, motor y SHA-256. Las actualizaciones no reescriben evaluaciones previas. El hash detecta cambios accidentales, no sustituye firma digital ni protege contra un administrador de base de datos.
8. **APV B:** registre aportes e ingrese renta y cotizaciones de la simulación. La calidad para APV se verifica por separado de la conclusión laboral. Si no existen parámetros verificados aplicables, se muestra una simulación parcial sin beneficio tributario calculado.
9. **Exportación:** elija versiones, empresa, persona y período. Descargue PDF ejecutivo/completo o XLSX; puede seleccionar varias personas y consolidar varias empresas (hasta 50 versiones por archivo).

La demostración incluye una Ltda. **ficticia**, socia de 90% sin administración ni representación y socio administrador de 10%. Dos períodos permiten comparar subordinación declarada y autonomía declarada. Los RUT son sintéticos de formato válido, sin afirmar identidades reales. La comparación describe supuestos y pendientes; no fabrica un dictamen.

## Importación societaria

Desde Composición, descargue la plantilla `.xlsx`. También se admite CSV UTF-8, con coma, punto y coma o tabulación. El flujo es **carga → mapeo → previsualización validada → confirmación**. La previsualización ejecuta las mismas validaciones que la confirmación y revierte sus cambios. La confirmación vuelve a validar y guarda todo en una transacción.

Columnas obligatorias: `nombre`, `rut`, `tipo` (`natural`/`legal`), `capital`, `utilidades`, `votos`, `desde` (ISO `AAAA-MM-DD`). Opcionales: `clase`, `derechos`, `hasta`, `via_rut`. Los porcentajes admiten punto decimal y hasta cuatro decimales. Registre primero al intermediario para usar `via_rut`.

Valida RUT, nombres/tipos de titulares existentes, duplicados y superposiciones, porcentajes, fechas y totales directos por sus fechas de vigencia. Un total inferior al 100% se conserva como **composición incompleta** y aparece como pendiente al evaluar; un total superior se rechaza. Las participaciones indirectas no se suman a la composición directa. No se calcula control jurídico transitivo.

Máximos: 2 MB, 1.000 filas, 40 columnas, 20 MB de XML descomprimido para XLSX. Se rechazan fórmulas en archivos Excel importados. Los textos CSV se tratan como datos. La exportación fuerza celdas de texto OOXML y solo crea fórmulas programadas por la aplicación.

## Reglas y fuentes

Las conclusiones son deterministas y no usan puntajes ni IA. Cada regla contiene código, versión, ámbito, vigencias, condiciones, excepciones, resultado, fundamento, fuentes y estado. Solo administradores y revisores pueden modificar normativa, reglas y parámetros. Esas modificaciones quedan auditadas.

Condición de ejemplo **estructural, no validada jurídicamente**:

```json
{"all":[{"field":"effective_work","eq":"yes"},{"field":"instructions","eq":"yes"},{"field":"supervision","eq":"yes"},{"field":"discipline","eq":"yes"}]}
```

Se admite `all` / `any`, hasta ocho niveles, y comparaciones `eq: yes/no`. Los campos están enumerados en `core.engine.FIELDS`. Una respuesta desconocida conserva el valor lógico desconocido; nunca se vuelve `no`. Excepciones desconocidas bloquean la aplicación definitiva. Las reglas laborales no pueden basarse solamente en porcentaje o representación. `direct_majority` describe mayoría de capital directo declarada; no es control jurídico. `tax_support` y `reasonableness` identifican texto registrado, no acreditan por sí mismos suficiencia del respaldo.

Para concluir se requiere regla verificada, fuentes oficiales verificadas con extracto y fecha, vigencia aplicable y ausencia de excepciones. Versiones del mismo código superpuestas se bloquean. Varias reglas concurrentes requieren revisión, sin elegir una arbitrariamente. Antecedentes laborales contradictorios se muestran expresamente. Una dimensión nunca determina automáticamente las otras.

La biblioteca separa fuentes oficiales de artículos complementarios, incluidos los que se incorporen de Círculo Verde. Las fuentes complementarias no habilitan reglas verificadas. El directorio institucional solo ofrece enlaces de consulta, sin presentarlos como normas. Adjunte el documento oficial de respaldo cuando sea posible. Cada revisión normativa necesita criterio profesional; escribir una URL no verifica su contenido.

## Parámetros, cotizaciones y APV

[Esquema y procedimiento de validación](docs/parametros.md). No hay tasas ni límites legales precargados.

Los importes usan `Decimal`; CLP se redondea al entero con `ROUND_HALF_UP`. Porcentajes societarios: cuatro decimales. Los parámetros monetarios y tasas se ingresan como cadenas decimales exactas, evitando `float`. Los números Excel se exportan como números, los textos como cadenas explícitas.

Se requiere un único conjunto de parámetros aplicable al período y con fuentes verificadas; una superposición bloquea el cálculo. UF, UTM, tramos, topes, tasas y límites se conservan con la versión. Se admiten topes APV por cada mes: no se traslada automáticamente el valor UF de un mes a otro. Una modificación normativa necesita otra versión/intervalo; no reescriba los períodos anteriores.

La matriz cubre AFP/comisión, salud, SIS, cesantía, accidentes, SANNA, nuevos aportes graduales y otras obligaciones, con sujetos, costo, base, tasa, tope, pago, cobertura, requisitos y fuente. Solo usa filas configuradas para la calidad individual y período, con respaldo en las fuentes verificadas del conjunto. Lo demás queda pendiente. No concluye que una cotización sea voluntaria por su tratamiento tributario.

El simulador APV suma aportes de la persona en todas las empresas del **mismo cliente** y todas las instituciones registradas, hasta el mes seleccionado. No mezcle el mismo aporte en varias fichas: registre cada operación una sola vez. Planilla: aplica el tope por mes y luego el anual. Aportes directos: se consideran en la determinación anual; no se deducen mensualmente. Las rebajas externas son las que no figuran en ese registro y consumen el límite anual; la renta de entrada debe estar neta de ellas. La salida muestra la rebaja y ahorro **adicionales** de los aportes registrados, no vuelve a deducir lo externo.

APVC y depósitos convenidos quedan separados: si existen y falta una regla de coordinación verificada, el cálculo se bloquea. La configuración solo admite declararlos excluidos de este límite de forma verificada o consumidores del límite sin calcular su propio beneficio. Su eventual rebaja no se calcula como APV. No se transfieren parámetros entre dependiente, independiente y sueldo empresarial. Un cálculo anual antes de diciembre se identifica como parcial. Las tablas tributarias y la procedencia deben verificarse por calidad y horizonte, no se presuponen.

## Informes

Los PDF se generan con ReportLab, no mediante impresión del navegador. Incluyen antecedentes, tres dimensiones de conclusión, poderes, hechos, matriz, simulación, comparación, acciones, fuentes, versión y hash. Se puede personalizar consultora, autor, revisor y logo PNG/JPEG. El resumen ejecutivo presenta una matriz compacta; el completo incorpora requisitos detallados, reglas y parámetros. Los encabezados de tablas se repiten y los textos se ajustan a página. Fuentes tipográficas: DejaVu Sans si está instalada, con alternativa Helvetica.

Excel contiene las 13 hojas solicitadas, filtros, tablas, encabezados congelados, importes numéricos, fechas, enlaces y fórmula de comprobación del ahorro. Las entradas APV se distinguen en amarillo, los resultados en verde. Un texto que exceda el límite de una celda se conserva por partes en una hoja adicional `Textos extensos`. Excel recalcula las fórmulas al abrir; los resultados monetarios también se guardan como valores calculados por el motor. PDF y Excel salen del mismo snapshot que muestra la evaluación.

Ejemplos reproducibles, con datos ficticios y pendientes claramente visibles:

```bash
DEBUG=1 .venv/bin/python scripts/generate_examples.py
```

Archivos privados locales en `artifacts/`: `ejemplo-ejecutivo.pdf`, `ejemplo-completo.pdf`, `ejemplo-consolidado.xlsx`. No se versionan ni se publican datos de casos.

## Verificación

```bash
DEBUG=1 .venv/bin/python manage.py test
DEBUG=1 .venv/bin/python manage.py makemigrations --check --dry-run
DEBUG=1 .venv/bin/python manage.py check
```

La suite cubre RUT, importación atómica, duplicados, vigencias, composiciones, condiciones desconocidas, mayoritarios/minoritarios/igualitarios, administración conjunta, participación indirecta, trabajo no efectivo, contradicciones, versiones, acumulación y límites APV, datos incompletos, aislamiento entre clientes, roles, CSRF, exportación y fórmulas importadas. Los resultados jurídicos de los fixtures son sintéticos, no pretenden verificar doctrina.

Validación opcional de interfaz con Chromium instalado y servidor local en ejecución:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/verify_browser.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

El navegador comprueba autenticación, creación de una nueva evaluación, descargas reales PDF/XLSX, navegación móvil y ausencia de desbordamiento horizontal. Guarda capturas en `artifacts/`. Para revisar PDF: `pdftoppm -png artifacts/ejemplo-completo.pdf artifacts/pagina` (Poppler). Se revisaron capturas de escritorio/móvil y páginas de portada, matriz y simulación.

## Seguridad y operación

[Operación y despliegue posterior](docs/operacion.md). Autenticación Django, CSRF, roles, aislamiento por cliente en consultas/formularios/descargas, documentos privados, no-cache para respuestas autenticadas y auditoría de cambios y exportaciones. Solo el administrador elimina registros; las evaluaciones protegen sus antecedentes básicos. Fuentes/reglas/parámetros se retiran por estado en lugar de eliminarse.

La primera versión no implementa IA/OCR, sincronización automática de fuentes, cálculo automático de control societario transitivo, presentación electrónica de declaraciones, pago de cotizaciones, firma digital, MFA ni un servicio de producción operado. Los esquemas de regla y parámetros se editan como JSON por un revisor. Las rentas y requisitos especiales de independientes o sueldo empresarial necesitan validación específica. Los retiros APV se documentan según fuente y parámetros; no se calcula su impuesto de retiro. Antes de usar resultados con clientes, complete la validación normativa y los parámetros del período. No se contrató ni desplegó ningún servicio externo.

## Abrir desde tu computador Windows

El servidor del entorno remoto no se puede abrir en tu computador usando su dirección `127.0.0.1`. Para ejecutar Nexo en Windows, descarga y extrae el paquete local, instala Python 3.12 y abre `iniciar_windows.bat`. El lanzador instala las dependencias, prepara datos locales y abre el navegador y la contraseña en tu computador. [Instrucciones completas](docs/abrir-en-windows.md).

Para generar ese paquete, sin incluir datos ni credenciales del entorno:

```bash
python scripts/package_local.py
```

Para iniciar desde una terminal en cualquier sistema compatible:

```bash
python scripts/launch_local.py
```

## URL HTTPS en PythonAnywhere

[Guía de publicación](docs/pythonanywhere.md). El paquete de código para subir a la cuenta se genera con `python scripts/package_local.py --output nexo-pythonanywhere.zip`. El instalador prepara base persistente en disco privado, clave local, estáticos y administrador con contraseña elegida mediante entrada oculta. Es necesario crear/configurar la aplicación Web en la cuenta del usuario. La preparación local no equivale a un despliegue ni a una URL verificada.
