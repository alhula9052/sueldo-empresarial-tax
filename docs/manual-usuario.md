# Manual de usuario · Nexo

Versión 1.0 · 2 de noviembre de 2026 · Guía para la aplicación actualmente implementada.

Nexo permite organizar y analizar los antecedentes de socios, accionistas y empresarios que trabajan en sus empresas. El expediente reúne hechos, poderes, documentación, reglas y parámetros, y permite emitir informes PDF y Excel.

**Estado de esta versión:** la instalación nueva no incorpora normativa ni tasas oficiales verificadas. Puede registrar casos y exportar sus antecedentes, pero las conclusiones y cálculos que requieren fuentes y parámetros pendientes permanecerán bloqueados. Cambiar un estado a “Verificado” exige una revisión profesional previa; no es un trámite para quitar advertencias.

## 1. Entender el flujo

**Empresa → personas y composición → poderes y documentos → trabajo efectivo → evaluación → APV → nueva evaluación → PDF y Excel.**

La unidad de análisis es una combinación de **empresa, persona y mes**. Una misma persona puede tener fichas en varias empresas o en varios períodos. Cada ficha permite guardar distintas versiones de evaluación.

| Elemento | Para qué sirve | Ejemplo ficticio |
| --- | --- | --- |
| Empresa | Identifica la entidad analizada y su régimen | Horizonte Consultores Ltda. |
| Persona o entidad | Identifica a quien participa o trabaja | Ana Ejemplo |
| Participación | Registra capital, utilidades, votos y vigencia | 90% de capital directo |
| Poder | Registra facultades que realmente tiene la persona | Sin administración ni representación |
| Ficha de trabajo | Describe funciones y realidad del trabajo en un mes | Funciones técnicas, noviembre de 2026 |
| Evaluación guardada | Conserva una versión de antecedentes, reglas y resultados | Evaluación previa o posterior a agregar evidencia |

La herramienta separa tres preguntas: **¿podría existir vínculo laboral?, ¿qué tratamiento tributario corresponde?, ¿qué obligaciones previsionales y coberturas deben revisarse?** Una respuesta en una dimensión no resuelve automáticamente las demás.

## 2. Ingreso y navegación

1. Abra la dirección HTTPS de la aplicación y entre en `/ingresar/`.
2. Ingrese el usuario y contraseña asignados. En la instalación de esta cuenta, el administrador inicial se llama `asesor`; utilice la contraseña que eligió en la consola.
3. Al entrar verá el **Panel de casos**, con empresas, personas, evaluaciones y pendientes.
4. Utilice el menú lateral para abrir cada módulo. En teléfonos, pulse **Menú**.
5. Termine la sesión con **Salir**, especialmente en computadores compartidos.

El usuario de Nexo es independiente de la cuenta de PythonAnywhere. No comparta credenciales entre asesores. Si olvida la contraseña, solicite al responsable técnico su restablecimiento: esta versión no incluye recuperación por correo.

### Quién puede hacer cada tarea

| Rol | Permisos principales |
| --- | --- |
| Administrador | Gestiona antecedentes, evaluaciones, normativa, parámetros, usuarios y eliminaciones permitidas |
| Analista | Registra y modifica antecedentes, documentos y simulaciones; guarda evaluaciones y exporta |
| Revisor | Además del trabajo del analista, administra fuentes, reglas y parámetros y consulta auditoría |
| Lector | Consulta los registros y evaluaciones de su cliente y descarga informes; no modifica datos |

Cada usuario pertenece a un espacio de cliente o consultora. No puede consultar los datos de otro espacio. El administrador inicial tiene facultades de configuración: puede asignar roles de menor alcance desde **Equipo y acceso**.

## 3. Preparar el primer expediente

Antes de ingresar un caso, reúna la identificación de la empresa y personas, composición societaria vigente, escrituras y poderes, descripción de funciones, evidencia de control y autonomía, respaldos de asignaciones y cotizaciones y, si corresponde, certificados APV.

Si desea obtener conclusiones o cifras tributarias, un administrador o revisor debe preparar además la **Biblioteca normativa**, las **Reglas versionadas** y los **Parámetros por período**. Puede avanzar con el registro de antecedentes mientras esa revisión está pendiente.

### Registrar la empresa

1. Abra **Empresas → Registrar** o pulse **Registrar empresa** en el panel.
2. Complete razón social, RUT y tipo jurídico.
3. Registre régimen tributario, determinación de renta, sociedad de profesionales y categoría tributaria cuando corresponda.
4. Agregue observaciones sobre antecedentes no confirmados y pulse **Guardar registro**.

El sistema valida el dígito verificador del RUT y evita duplicarlo dentro del mismo espacio. Que un RUT sea formalmente válido no confirma la identidad ni su situación ante el SII.

### Registrar personas y entidades

Abra **Personas y entidades → Registrar** e ingrese nombre, RUT y tipo **Natural** o **Jurídica**. Registre también a las entidades intermedias de una participación indirecta antes de seleccionarlas en composición.

Las fichas de trabajo se crean para personas naturales. Una entidad jurídica puede figurar como titular o intermediario societario, pero no como trabajador de una ficha.

## 4. Cargar la composición societaria

### Ingreso manual

1. Abra **Composición societaria → Registrar**.
2. Seleccione empresa y titular.
3. Complete por separado porcentajes de capital, utilidades y votos. Escriba `90` para noventa por ciento; no `0.90`.
4. Agregue clase de acciones, derechos especiales y fechas de vigencia.
5. Deje **A través de** vacío para una participación directa. Para una indirecta, seleccione al intermediario.
6. Guarde y revise la tabla y el mapa de participaciones.

Los derechos económicos y el control jurídico son conceptos distintos. El sistema no transforma una participación indirecta en calidad de socio directo ni calcula automáticamente control societario transitivo.

### Importación Excel o CSV

1. Abra **Composición societaria** y pulse **Descargar plantilla .xlsx**.
2. Complete la plantilla con los datos de una empresa. Si usa CSV, guárdelo como UTF-8.
3. Pulse **Importar Excel / CSV**, seleccione la empresa y cargue el archivo.
4. En el **mapeo**, asocie cada campo del sistema con la columna correspondiente del archivo. Las columnas opcionales pueden quedar sin mapear.
5. Pulse **Validar y previsualizar** y revise titulares, porcentajes, fechas y mensajes.
6. Si no hay errores, pulse **Confirmar participaciones**. La vista previa por sí sola no guarda la importación.

Columnas obligatorias: `nombre`, `rut`, `tipo`, `capital`, `utilidades`, `votos`, `desde`. Opcionales: `clase`, `derechos`, `hasta`, `via_rut`. En el archivo, tipo debe ser `natural` o `legal`; las fechas deben usar `AAAA-MM-DD`; los decimales, punto.

Se admiten archivos de hasta 2 MB, 1.000 filas y 40 columnas. Los porcentajes admiten hasta cuatro decimales. Excel importado no admite fórmulas: pegue valores antes de cargarlo. El intermediario indicado por `via_rut` debe existir previamente.

Un total directo superior al 100% se rechaza; uno inferior se admite como composición incompleta y genera un pendiente. Los duplicados y las fechas superpuestas se revisan al confirmar. Si una fila falla, la importación no guarda parcialmente las demás. Importar no reemplaza automáticamente una composición existente: para corregirla, edite sus registros o cierre sus vigencias según corresponda.

## 5. Registrar poderes y documentos

En **Administración y poderes → Registrar**, seleccione empresa, persona y vigencias. Registre por separado representación legal, administración general, forma de ejercicio, facultad de contratar/despedir/fijar remuneraciones, disciplina, directorio, designación de administradores y dirección efectiva.

**Individual, conjunto e indistinto** no son equivalentes. Anote las restricciones y delegaciones en **Poderes específicos, delegaciones y evidencia**, citando documento, fecha y cláusula. Si no conoce una facultad, use **No determinado**.

En **Documentos privados → Registrar**, elija la empresa, la persona si corresponde, un título descriptivo, página o cláusula pertinente, archivo y observaciones. El límite es 5 MB por archivo. Para respaldos mayores, separe el documento en partes identificables.

Ejemplo de referencia: “Poder de administración, 15-10-2026, cláusula cuarta, página 3”. Subir un archivo no completa automáticamente las respuestas ni interpreta su contenido: debe registrar los hechos y citar el respaldo en la ficha pertinente. Las descargas de documentos requieren sesión y pertenencia al mismo cliente.

## 6. Crear la ficha de trabajo efectivo

1. Abra **Trabajo efectivo → Registrar**.
2. Seleccione empresa y persona, y registre el período con el **primer día del mes**. Para noviembre de 2026, use `2026-11-01`.
3. Describa funciones, dedicación, asignación mensual CLP, forma de fijación y a quién reporta.
4. Conteste sobre trabajo efectivo, instrucciones obligatorias, control y evaluación, disciplina, permisos, disponibilidad, autonomía y trabajo comprometido como aporte societario.
5. Complete las observaciones y evidencia de cada respuesta, con documento y página cuando existan.
6. Anote discrepancias entre documentos y realidad, otras actividades o rentas, razonabilidad de la asignación y respaldos tributarios.
7. Pulse **Guardar registro**.

| Respuesta | Cuándo usarla |
| --- | --- |
| Sí | El hecho está afirmado en los antecedentes; explique cómo lo respalda |
| No | Los antecedentes permiten negar el hecho; explique el fundamento |
| No determinado | Falta evidencia o no se ha podido aclarar el hecho |

Una ausencia de documentos no equivale a una respuesta negativa. La ausencia de órdenes diarias o de horario fijo no prueba, por sí sola, autonomía. Tampoco el porcentaje de propiedad o ser representante legal decide automáticamente la clasificación laboral.

Solo puede existir una ficha por empresa, persona y mes. Para corregir el mismo período, use **Editar**; para analizar otro mes, cree una ficha nueva. Esa nueva ficha requiere ingresar sus antecedentes: esta versión no los copia automáticamente del mes anterior.

## 7. Abrir y guardar una evaluación

Desde el **Panel de casos**, busque la empresa o persona y pulse **Abrir caso**. También puede hacerlo desde la lista de **Trabajo efectivo**.

La página del caso muestra un análisis con los datos actuales. Revise las tres dimensiones, hechos e inferencias, sueldo empresarial, matriz previsional, APV, comparación de escenarios y acciones pendientes.

Pulse **Guardar evaluación** para conservar una versión. El botón no aprueba ni certifica el análisis: guarda los datos disponibles, incluso si hay pendientes. Una evaluación guardada tiene identificador, fecha, autor, versión del motor y huella de integridad.

### Qué significa cada estado

| Mensaje o situación | Qué hacer |
| --- | --- |
| Sin evaluar | Abrir el caso, revisar la ficha y guardar su primera evaluación |
| Información insuficiente / pendiente de validación | Revisar hechos desconocidos y fuentes, reglas o parámetros faltantes |
| Regla candidata pendiente | El patrón de antecedentes coincide, pero falta validación suficiente; no usarlo como conclusión definitiva |
| Antecedentes contradictorios o reglas concurrentes | Identificar la contradicción y solicitar revisión; no elegir el resultado más conveniente |
| Resultado respaldado por una regla aplicada | Leer fundamento, fuente, vigencia, excepciones y pendientes; no extenderlo automáticamente a otras dimensiones |
| Simulación parcial | Revisar integridad de datos, calidad individual y parámetros; puede no existir una cifra calculada |

El nombre de un resultado favorable no elimina la necesidad de revisar su fundamento. Las reglas pueden producir resultados como indicios de dependencia, autonomía o impedimento conforme a doctrina aplicable, pero solo después de la validación requerida.

### Corregir sin perder el historial

Abra la ficha correspondiente y use **Editar**. Guarde la corrección, vuelva al caso y pulse otra vez **Guardar evaluación**. Obtendrá una versión nueva; los informes y evaluaciones anteriores conservan sus datos originales.

No espere que una evaluación ya guardada cambie al agregar un documento, corregir una respuesta o actualizar la normativa. Para reflejar esos cambios debe generar y seleccionar una evaluación nueva.

## 8. Leer sueldo empresarial y cotizaciones

El apartado de sueldo empresarial reúne asignación, trabajo efectivo, razonabilidad, pago/devengo, contabilidad y antecedentes de IUSC, LRE, DJ 1887 y F22. No presenta por sí mismo declaraciones ni verifica su envío al SII.

Revise los comparables y respaldos de la asignación. La aplicación no usa automáticamente el tope previsional como límite tributario del gasto. Que una cotización no sea requisito de aceptación tributaria tampoco permite concluir que sea voluntaria.

La matriz previsional muestra AFP y comisión, salud, SIS, cesantía, accidentes del trabajo, SANNA, nuevos aportes graduales y otras obligaciones. Por concepto, revise estado, sujeto obligado, costo, base, tasa, tope, pago, cobertura, requisitos, fuente y vigencia.

**Pendiente no significa “no corresponde” ni “cero a pagar”.** La matriz depende de la calidad individual, el período y los parámetros verificados. No sustituye una liquidación de remuneraciones ni efectúa pagos de cotizaciones.

## 9. Registrar aportes y simular APV B

### Ingresar los aportes

En **Aportes APV / APVC / depósitos → Registrar**, seleccione la ficha y registre instrumento, institución, modalidad **Planilla** o **Directo**, fecha e importe CLP. Mantenga separados APV B, APVC y depósitos convenidos.

Registre cada aporte una sola vez. El cálculo considera los aportes de la misma persona en todas las empresas e instituciones registradas dentro de su espacio de cliente, para el año y hasta el mes analizado. No vuelva a copiar en cada ficha los aportes que ya registró para esa persona. La aplicación no elimina automáticamente operaciones duplicadas.

### Completar la simulación

1. Abra **Simulación de APV B → Registrar** y seleccione la ficha.
2. Indique la calidad aplicable a APV: no determinada, dependiente, independiente o sueldo empresarial. No la asuma a partir de la conclusión laboral.
3. Elija horizonte mensual o anual e ingrese renta relevante, cotizaciones deducibles y rebajas APV externas ya utilizadas.
4. En renta, use la base del horizonte elegido y siga la indicación de que esté neta de las rebajas externas ya utilizadas. No registre el mismo beneficio como aporte y como rebaja externa.
5. Confirme integridad de rentas, aportes y todas las instituciones solo después de revisarlas; anote supuestos y respaldos.
6. Guarde, vuelva al caso y genere una **nueva evaluación** para conservar y exportar la simulación actualizada.

Si hay parámetros verificados y antecedentes suficientes, verá base antes/después, rebaja admisible, exceso, impuesto antes/después y ahorro estimado. Se coordinan topes mensuales de planilla y límite anual; no se deducen automáticamente aportes directos en un cálculo mensual.

Si existen APVC o depósitos convenidos sin coordinación verificada, o falta la procedencia específica de la calidad seleccionada, el cálculo se bloquea. No se reutilizan reglas de dependientes para independientes o sueldo empresarial. Un cálculo anual antes de diciembre se identifica como parcial.

La simulación no equivale a una declaración de impuestos ni garantiza devolución. El tratamiento de retiros se documenta cuando está verificado; esta versión no calcula el impuesto del retiro anticipado.

## 10. Preparar los informes PDF y Excel

### Personalizar

Antes de guardar la evaluación destinada al cliente, entre en **Personalizar informes** y registre nombre de consultora, autor, revisor y logo opcional. El logo debe ser PNG/JPEG, hasta 5 MB y 2048 × 2048 píxeles.

Si ya existe la configuración, use **Editar** sobre ese registro. La personalización queda conservada en cada evaluación: modificarla después no cambia informes históricos. El nombre escrito en “Revisor” es un dato del informe, no una firma ni un proceso electrónico de aprobación.

### Descargar

Desde una evaluación guardada, elija **Informe ejecutivo** o **Completo con anexos** y pulse **Descargar PDF** o **Descargar Excel**.

Para varias personas o empresas, abra **Informes y expedientes**, filtre por empresa, persona o período, seleccione las evaluaciones y descargue. El límite es 50 versiones por archivo. Seleccionar dos versiones del mismo caso incluye ambas, no las reemplaza por la más reciente automáticamente.

El PDF ejecutivo resume el expediente; el completo agrega detalle de reglas y parámetros. Ambos conservan los pendientes. Excel incluye resumen, empresas, socios, poderes, antecedentes laborales, evaluación, sueldo empresarial, cotizaciones, APV, escenarios, parámetros, normativa y pendientes. Las entradas APV se distinguen en amarillo y los resultados en verde.

PDF, Excel y pantalla de la evaluación usan la misma versión guardada. Antes de entregar, compruebe persona, empresa, período, versión, montos y pendientes. Descargar un archivo lo deja fuera del control de acceso de Nexo: compártalo por un canal adecuado.

## 11. Biblioteca, reglas y parámetros: tarea del revisor

En **Biblioteca normativa**, registre institución, documento, fecha, materias, resumen, extracto, URL oficial, archivo de respaldo, verificación, vigencias y documentos relacionados. Use búsqueda y filtros para separar fuentes oficiales de artículos complementarios.

Un enlace al sitio de una institución no acredita por sí mismo un documento ni su vigencia. Los artículos profesionales, incluidos los que se incorporen de Círculo Verde, son complementarios y no habilitan por sí solos reglas verificadas.

En **Reglas versionadas**, el administrador o revisor registra identificador, versión, ámbito, condiciones, excepciones, resultado, fundamento, fuentes y vigencias. En **Parámetros por período**, prepara UF, UTM, topes, tasas, límites y tramos pertinentes. Estos formularios usan JSON y requieren apoyo técnico; el esquema se explica en [Parámetros auditables](parametros.md).

Una regla no emite conclusión definitiva sin fuentes y validación suficientes. Un conjunto de parámetros ambiguo o superpuesto se bloquea. Para cambios normativos, prepare versiones e intervalos adecuados y conserve las evaluaciones ya emitidas. No altere cifras ni estados solo para conseguir un resultado esperado.

Esta versión no descarga ni actualiza automáticamente normativa, UF, UTM o tasas. La disponibilidad de datos correctos depende de la carga y revisión profesional.

## 12. Equipo, auditoría y eliminación

El administrador usa **Equipo y acceso** para crear usuarios, asignar roles, actualizar permisos o desactivar accesos. La aplicación impide deshabilitar al último administrador activo. Entregue las contraseñas iniciales por un canal seguro.

Administradores y revisores pueden abrir **Auditoría** para consultar los últimos 300 eventos del espacio: cambios, evaluaciones, accesos modificados, exportaciones y descargas registradas. Es una bitácora lógica; no representa una firma digital ni registra automáticamente la aprobación profesional de un informe.

Solo el administrador puede ejecutar las eliminaciones permitidas. Los antecedentes protegidos por una evaluación pueden impedir su eliminación. Fuentes, reglas y parámetros se retiran por su estado en vez de borrarse desde la interfaz.

Eliminar una fila no garantiza borrar toda copia de información personal: pueden existir snapshots, archivos retirados, respaldos e informes descargados. Una solicitud integral de supresión debe coordinarse con el responsable técnico y la política de retención.

## 13. Ejercicio guiado ficticio

Use una empresa y personas claramente identificadas como ficticias, sin presentarlas como clientes reales. No mezcle el ejercicio con expedientes de producción.

1. Registre una Ltda. ficticia, dos personas y participaciones directas 90% y 10%, usando identificaciones de prueba apropiadas.
2. Registre que la socia del 90% no tiene administración ni representación y que el socio del 10% administra. Cite que estos datos son simulados.
3. Cree una ficha mensual para la socia del 90%, describa funciones y conteste afirmativamente a instrucciones, control y disciplina en un primer escenario hipotético.
4. Guarde una evaluación. Luego describa un escenario alternativo con autonomía real y respuestas negativas sustentadas como supuestos; guarde otra versión o use otro período claramente identificado.
5. Compare los antecedentes de ambas versiones, no solo su porcentaje de propiedad. Las conclusiones pueden seguir pendientes si no hay reglas verificadas.
6. Seleccione las dos evaluaciones en **Informes y expedientes** y descargue el comparativo consolidado.

La sección de escenarios del caso expone supuestos cualitativos. No crea automáticamente otra ficha ni recalcula una evaluación alternativa al pulsar un escenario. La demostración automática del entorno local no se instala por defecto en PythonAnywhere.

## 14. Resolver problemas frecuentes

| Situación | Acción |
| --- | --- |
| No aparece una persona en la ficha | Confirme que esté registrada como persona natural en el mismo espacio |
| El sistema rechaza el período | Use el primer día del mes, por ejemplo 2026-11-01 |
| RUT inválido | Revise cuerpo y dígito verificador; no invente uno para forzar el guardado |
| Participación duplicada o total mayor a 100% | Revise clase, titular, porcentajes y vigencias; no importe otra vez los mismos registros |
| No puedo editar normativa | Necesita rol administrador o revisor |
| Todo aparece pendiente | Complete hechos y solicite revisar fuentes, reglas y parámetros vigentes; no es una aprobación negativa del caso |
| No aparece ahorro APV | Revise calidad, horizonte, aportes, integridad, límites y tramos verificados; pendiente no equivale a ahorro cero |
| El PDF no refleja una corrección | Guarde una nueva evaluación después de la corrección y exporte esa versión |
| No hay evaluaciones para exportar | Cree la ficha, abra el caso y pulse Guardar evaluación |
| No puedo eliminar un registro | Compruebe rol administrador y protección por evaluaciones existentes |
| El sitio muestra un error de servidor | Avise al responsable técnico con pantalla y hora; no envíe contraseñas, cookies ni documentos privados |

## 15. Lista de revisión antes de entregar al cliente

- Empresa, persona y período correctos.
- Composición y poderes vigentes, con respaldo identificable.
- Trabajo efectivo y respuestas desconocidas o contradictorias explicados.
- Conclusiones laboral, tributaria y previsional revisadas por separado.
- Normativa, reglas, fuentes y parámetros suficientes para los resultados emitidos.
- APV sin duplicación de aportes ni rebajas y con supuestos visibles.
- Evaluación nueva guardada después de las últimas correcciones y personalización.
- PDF y Excel de esa misma versión; pendientes comunicados al cliente.
- Identificación de autor y revisor revisada; sin confundirla con firma digital.
- Archivos entregados por un canal seguro y copias conservadas según la política de la consultora.

El objetivo es que cada conclusión se pueda explicar desde sus antecedentes y fuentes. Cuando falta respaldo, el producto útil es un expediente claro de pendientes y acciones, no una conclusión automática sin fundamento.
