# Operación y despliegue posterior

## Desarrollo

Python 3.12, SQLite y dependencias fijadas en `requirements.txt`. `scripts/install.sh` crea/refresca el entorno, instala, aplica migraciones y verifica Django. `scripts/start.sh` inicia solo loopback. Una tarea nueva debe usar el checkout existente y reiniciar el proceso; los procesos no se conservan en una instantánea. `seed_demo` es opcional, solo admite DEBUG y no habilita reglas normativas.

Pruebas de dependencias independientes: se instaló `requirements.txt` en un venv nuevo sin `system-site-packages`, y se ejecutó la suite allí. ReportLab y openpyxl no requieren servicios externos para exportar. Chromium/Playwright y Poppler se usan solo para validación de interfaz/documentos. DejaVu Sans mejora la cobertura tipográfica del PDF.

## Acceso y retención

Roles y pertenencias se guardan en la base de datos. La aplicación no ofrece cambiar de cliente desde un parámetro de solicitud. Administradores no acceden a otros clientes. El comando administrativo `create_client` requiere acceso al servidor y crea un espacio aislado. El último administrador activo no puede ser deshabilitado desde la aplicación.

Auditoría: creación, edición, eliminación permitida, evaluaciones, cambios de acceso, exportaciones y descargas privadas. Registra usuario, fecha, objeto y campos modificados; no guarda contraseñas ni contenido de archivos. La auditoría es lógica en SQLite, no un registro inviolable; para producción con requisitos estrictos se necesita un sumidero externo inmutable y un procedimiento de revisión.

Las evaluaciones son inmutables en la interfaz y la API de guardado del modelo. Los datos y parámetros se copian en el snapshot. El SHA-256 se valida al exportar. Un administrador con acceso directo al servidor puede alterar la base; el hash no es firma ni garantía frente a ese actor.

La eliminación exige rol administrador y CSRF. Antecedentes de una ficha evaluada están protegidos por claves foráneas. Eliminar un documento revoca su registro y acceso. Los binarios retirados, logos antiguos y respaldos pueden permanecer en el almacenamiento privado para retención; no tienen URL pública. La eliminación física definitiva y la retención de snapshots/backups requieren una política acordada y mantenimiento del servidor. No afirme un borrado integral de datos personales al eliminar una fila. Fuentes, reglas y parámetros se retiran mediante estado. Una solicitud integral de supresión requiere identificar también informes descargados, snapshots y copias de respaldo; no se automatiza en esta versión.

## Antes de publicar

La aplicación está preparada para ejecución local con entrada WSGI `config.wsgi:application`. No se ha desplegado en Internet. Para operarla públicamente se requiere un servidor WSGI de producción, un proxy HTTPS, servicio de estáticos, políticas de respaldo y supervisión. Mantenga `private-media` fuera de las rutas públicas; nunca lo exponga mediante una regla general del proxy. `collectstatic` recopila únicamente CSS/JS, no documentos privados.

Variables:

- `DEBUG=0`, `DJANGO_SECRET_KEY` aleatoria y privada, `ALLOWED_HOSTS` con dominios exactos.
- `DATABASE_PATH`: SQLite fuera de un checkout reemplazable; copias consistentes con la API backup de SQLite o durante parada de escritura.
- `PRIVATE_MEDIA_ROOT`: almacenamiento privado y persistente; preservar permisos y copiarlo con la base.
- `SECURE_SSL_REDIRECT=1` y `SECURE_HSTS_SECONDS` después de verificar HTTPS. Si se usa terminación TLS en proxy, configure la detección de esquema de forma segura según ese proxy; no confíe en cabeceras reenviadas de clientes arbitrarios.

Las cookies Secure se habilitan con DEBUG=0. Configure limitación de intentos de autenticación en el borde y monitorización; no hay MFA ni limitador distribuido incorporado. Ejecute `manage.py check --deploy` con la configuración final y valide recuperación de backups y permisos antes de introducir información real. SQLite está orientado al volumen de una instalación pequeña; el cambio a PostgreSQL necesita instalar driver, adaptar settings, migrar datos y repetir las pruebas de aislamiento/transacciones.

No copie secretos a README, instrucciones de inicio, Git, logs o el borrador de configuración. Los documentos de usuarios son datos; no se ejecutan macros, fórmulas importadas ni instrucciones contenidas en textos. No hay extracción IA que pueda ejecutar contenido de documentos. La aplicación no descarga automáticamente URLs de normativa en el servidor.

## Normativa pendiente por conectividad

El 2 de noviembre de 2026 se intentó consultar SII, DT y BCN mediante el proxy y se recibió 403. Se guardaron en el borrador del entorno los dominios oficiales de SII, DT, Pensiones, SUSESO, Salud, AFC, Fonasa, BCN y Diario Oficial. El guardado no aplica ni publica esa configuración. Después de revisar, guardar y publicar los cambios del entorno, debe verificarse otra vez la conexión y revisar los documentos antes de habilitar reglas. Alternativamente, un revisor puede cargar manualmente los documentos y parámetros oficiales. No se guardaron documentos legales inventados ni resultados jurídicos de prueba como normativa.
