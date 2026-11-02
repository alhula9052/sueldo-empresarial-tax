# Abrir Nexo en tu navegador de Windows

`127.0.0.1` siempre se refiere al computador donde está abierto el navegador. Un proceso iniciado en el entorno remoto de esta conversación no es accesible desde el navegador de tu computador mediante esa dirección.

Este paquete inicia una copia de Nexo **en tu propio computador**. No publica información en Internet ni requiere contratar alojamiento.

1. Descarga `nexo-windows.zip` y extrae **toda** la carpeta; no ejecutes los archivos dentro del ZIP.
2. Necesitas Python 3.12 o posterior. Si falta, instálalo desde https://www.python.org/downloads/windows/ y activa “Add python.exe to PATH”.
3. En la carpeta extraída, abre `iniciar_windows.bat` con doble clic.
4. La primera ejecución descarga dependencias, crea la base local y el ejemplo ficticio. Después abre el navegador y el archivo de contraseña en Bloc de notas.
5. Ingresa con el usuario `demo` y la contraseña de `.demo-password`. Mantén abierta la ventana de Nexo mientras utilizas la aplicación. Ctrl+C detiene el servidor.

La URL exacta aparece en esa ventana. Se prefiere el puerto 8000; si está ocupado, se utiliza uno de los nueve siguientes. Desde otro equipo esa URL no funciona. La base y los documentos se guardan en la carpeta extraída; conserva esa carpeta para no perder tu trabajo. Al actualizar, respalda `db.sqlite3` y `private-media`; no sobrescribas los datos con los de otra instalación.

El paquete no incluye bases, sesiones, contraseñas, documentos ni entornos virtuales del servidor. Cada instalación genera sus propios datos de demostración y su contraseña. Las limitaciones normativas descritas en README siguen aplicándose.

Si buscas una dirección HTTPS accesible desde varios computadores, necesitas un alojamiento o servidor. Este lanzador es exclusivamente para desarrollo y uso local; no convierte el servidor de desarrollo en un servicio público. El entorno de esta conversación no ofrece publicación de puertos ni una URL pública integrada.
