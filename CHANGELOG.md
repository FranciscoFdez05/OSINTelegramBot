# Changelog

## [0.8.1]
- Menú de comandos de Telegram: al escribir `/` se listan los comandos disponibles (los de administración solo para admins).
- Nuevo `/info` (igual que `/start` y `/help`).
- Las herramientas ya no devuelven códigos de terminal ni anuncios (p. ej. el de OSINTSearch en sherlock).
- El bot avisa con «Ejecutando /comando…» antes de lanzar la herramienta.

## [0.8.0]
- Panel web de control (usuarios, token, rendimiento), con usuario y contraseña opcionales (`PANEL_USER`, `PANEL_PASSWORD`).
- Puerto del panel por defecto: 6050 (`PANEL_PORT`).
- `docker-up.sh`: pide usuario, contraseña y puerto, los guarda en `.env` y levanta el stack.
- Actualización desde el panel con `docker-update.sh`, con vuelta atrás automática.
- Eliminado `install.sh`; la instalación con Docker se hace con `docker-up.sh`.
