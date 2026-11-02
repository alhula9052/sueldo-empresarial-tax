# Publicar Nexo en PythonAnywhere

Este procedimiento prepara una URL HTTPS con autenticación. Requiere una cuenta del usuario en PythonAnywhere y acceso a su panel. No se ha publicado esta instancia ni se ha comprobado una URL remota. La disponibilidad y límites actuales del plan gratuito deben confirmarse en la cuenta; no acepte un cambio a un plan de pago si no lo desea.

## 1. Cuenta y paquete

Cree su cuenta en https://www.pythonanywhere.com/ y elija el plan gratuito si está disponible. El dominio lo proporciona PythonAnywhere; no use el ejemplo como si ya existiera.

Descargue `nexo-pythonanywhere.zip`. En la pestaña **Files**, suba el ZIP a su directorio personal. Abra una consola **Bash** desde el panel y ejecute:

```bash
unzip -n nexo-pythonanywhere.zip
cd ~/nexo
python3.12 scripts/setup_pythonanywhere.py --host SU_DOMINIO_ASIGNADO --username asesor --consultora "Mi consultora"
```

Reemplace `SU_DOMINIO_ASIGNADO` por el dominio exacto de su cuenta, sin `https://` ni `/`. El script admite los subdominios estándar y europeos de PythonAnywhere. Si Python 3.12 no está disponible, seleccione una versión posterior compatible, tanto para el comando como para la aplicación Web.

El instalador crea el entorno virtual, instala dependencias, genera una clave aleatoria privada, aplica migraciones, recopila estáticos y crea un primer administrador de la aplicación. Solicita una contraseña mediante entrada oculta en esa consola; no la envíe por el chat. El usuario de Nexo es distinto de su cuenta de alojamiento.

Los datos se guardan en `~/nexo/.runtime`, con base SQLite, documentos privados y clave local. El instalador no carga datos de demostración. Su repetición conserva la clave y no restablece la contraseña del usuario existente. No copie ni publique esa carpeta. La importación de documentos oficiales, las reglas y los parámetros se gestionan luego desde la aplicación.

## 2. Aplicación Web

En la pestaña **Web**:

1. Elija **Add a new web app**, el dominio asignado y **Manual configuration**, con la misma versión Python utilizada por el instalador. No cree otro proyecto Django que sobrescriba los archivos.
2. En **Virtualenv**, indique `/home/SU_USUARIO/nexo/.venv`.
3. Abra el archivo **WSGI configuration file** que muestra el panel. Sustituya el ejemplo por el contenido de `~/nexo/deploy/pythonanywhere_wsgi.py`. Si extrajo el proyecto en otra carpeta, ajuste `ROOT` al directorio real.
4. En **Static files**, agregue únicamente la URL `/static/` con directorio `/home/SU_USUARIO/nexo/staticfiles`.
5. No agregue rutas para `/media/`, `.runtime`, documentos o el directorio completo del proyecto. Los documentos se descargan a través de vistas autenticadas.
6. Active **Force HTTPS** si está disponible y pulse **Reload**.

El perfil de alojamiento desactiva DEBUG, restringe ALLOWED_HOSTS al dominio asignado, activa cookies seguras y redirección HTTPS, y reconoce la cabecera de esquema del proxy de PythonAnywhere. No reutilice ese ajuste de confianza detrás de un proxy que permita cabeceras arbitrarias del cliente. Se habilita HSTS por una hora; confirme HTTPS antes de aumentar su duración.

## 3. Comprobar antes de compartir el enlace

Abra la URL HTTPS proporcionada por la pestaña Web y agregue `/ingresar/`. Verifique:

- La pantalla de ingreso carga con estilos y sin advertencias TLS.
- Puede ingresar con el usuario `asesor` y la contraseña elegida.
- Sin sesión no puede ver casos ni descargar documentos privados.
- Puede registrar una empresa, una persona y su ficha; guardar una evaluación; descargar PDF y Excel.
- Los datos siguen disponibles después de **Reload**.

No entregue como operativo un enlace que aún no haya superado estas comprobaciones. Si el servicio responde 500, consulte el **error log** del panel y comparta únicamente el error sin contraseñas, claves, cookies ni datos de clientes. El chequeo local de WSGI y archivos no verifica el acceso real al alojamiento.

## Operación

El servidor no incluye datos de esta conversación, contraseñas de demostración ni documentos privados. Las limitaciones de validación normativa del README siguen vigentes. Antes de usar información real, confirme cuotas y condiciones del plan, configure copias consistentes de SQLite y documentos privados y defina la retención. Un alojamiento gratuito puede exigir renovación periódica o limitar recursos; ese comportamiento depende del plan actual y no se ha validado desde este entorno.

Para preparar de nuevo el ZIP de código:

```bash
python scripts/package_local.py --output nexo-pythonanywhere.zip
```

El paquete usa una lista explícita de directorios y no contiene `.runtime`, bases de datos, sesiones ni secretos.
