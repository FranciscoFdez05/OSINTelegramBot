# Changelog

## [0.9.0]
- Metadatos EXIF: al enviar una foto o documento el bot devuelve sus metadatos (exiftool), con enlace al mapa si lleva GPS. `/exif` explica cómo enviarlos.
- Progreso vivo: el «Ejecutando…» se edita con el tiempo transcurrido y al final se sustituye por el resultado.
- Botones inline bajo cada resultado para pivotar a otras herramientas sobre el mismo objetivo (dominio, IP, email, teléfono, URL).
- Nuevo `/recon <dominio>`: whois, dns, dnsrecon, whatweb y sslscan en un único informe.
- Detección automática: un email, IP, dominio, teléfono o URL enviado sin comando sugiere las herramientas que aplican.
- Nuevo `/history`: tus últimas consultas (de `audit.jsonl`), repetibles con un toque.
- Caché de resultados (`CACHE_TTL`, 300 s por defecto, 0 la desactiva): una misma consulta no repite el escaneo.
- Un trabajo activo por usuario y un máximo de `MAX_HEAVY_JOBS` (3) herramientas pesadas a la vez; el resto queda en cola.
- `/cancel` también detiene el comando en curso (o en cola) y mata su proceso.
- Las salidas largas (más de ~6000 caracteres) se envían como fichero `.txt` con un resumen en el chat.
- El menú de comandos se actualiza al añadir o quitar usuarios, desde `/adduser`, `/deluser` o el panel.
- Panel: bloqueo temporal de la IP tras varios logins fallidos (`PANEL_MAX_FAILS`, `PANEL_LOCKOUT`, `PANEL_TRUST_PROXY`) y cookie `Secure` detrás de HTTPS (`PANEL_COOKIE_SECURE`).
- La lista de usuarios autorizados se protege con un lock (la tocan el bot y el panel desde hilos distintos).

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
