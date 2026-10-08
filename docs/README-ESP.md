[🇪🇸 Español](README-ESP.md) | [🇬🇧 English](../README.md)

# OSINTelegramBot

Bot de Telegram para ejecutar herramientas OSINT de forma remota. El acceso está restringido a una lista blanca de IDs de usuario autorizados. Todos los comandos se ejecutan dentro de un contenedor Docker — sin dependencias en la máquina anfitriona.

## ⚠️ Aviso legal

Este software se proporciona únicamente con **fines educativos y personales**. El autor no se hace responsable del uso que otros puedan hacer de esta herramienta. Cualquier modificación o alteración de datos es responsabilidad exclusiva del usuario. Úsalo solo sobre sistemas propios o en los que tengas permiso explícito.

---

## ✨ Características

- **Control de acceso** mediante lista blanca de IDs de usuario.
- **Ejecución segura** de herramientas externas con validación de argumentos, entorno restringido y tiempos de espera por comando.
- **Registro de actividad** en `log/logfile.log`.
- **División automática de mensajes largos** para respetar los límites de Telegram.
- **Docker-first** — un solo comando para construir y arrancar, sin instalar nada en el host.

---

## 📋 Comandos disponibles

Todos los comandos están restringidos a usuarios autorizados.

### Red y dominios
| Comando | Descripción |
|---|---|
| `/whois <dominio\|ip>` | Consulta WHOIS de un dominio o IP |
| `/dns <dominio>` | Resolución DNS |
| `/ipinfo <ip>` | Detalles de una IP desde ipinfo.io |
| `/nmap <ip\|host>` | Escaneo de puertos y servicios (top 100) |
| `/gobuster <url>` | Enumeración de rutas con wordlists comunes |
| `/harvester <dominio>` | Cosecha emails y subdominios de fuentes públicas |
| `/dnsrecon <dominio>` | Enumeración DNS avanzada (zone transfer, SRV, fuerza bruta) |

### Web
| Comando | Descripción |
|---|---|
| `/whatweb <url>` | Fingerprinting de tecnologías web (CMS, frameworks, versiones) |
| `/nikto <url>` | Escáner de vulnerabilidades web |
| `/sslscan <host>` | Análisis de configuración TLS/SSL |
| `/waf <url>` | Detección de WAF |

### Usuarios
| Comando | Descripción |
|---|---|
| `/sherlock <usuario>` | Búsqueda de usuario en redes sociales |
| `/maigret <usuario>` | Búsqueda avanzada de usuario (2500+ sitios) |

### Email
| Comando | Descripción |
|---|---|
| `/holehe <email>` | Comprueba en qué servicios está registrado el email |
| `/h8mail <email>` | Busca el email en bases de datos de brechas conocidas |
| `/emailrep <email>` | Reputación y puntuación de riesgo del email (emailrep.io) |

### Teléfono
| Comando | Descripción |
|---|---|
| `/phone <+34XXXXXXXXX>` | OSINT de número de teléfono (operadora, país, tipo de línea) |

### Administración (solo admins)
| Comando | Descripción |
|---|---|
| `/adduser <userID>` | Autoriza un nuevo ID de Telegram (se guarda en `config/usersIDs.txt`) |
| `/deluser <userID>` | Revoca un ID autorizado |
| `/users` | Lista los IDs autorizados |

Los administradores son los IDs de `config/adminIDs.txt`. Si ese fichero no existe o está
vacío, se considera administrador al **primer ID** de `config/usersIDs.txt`.
Los IDs de administrador no se pueden borrar con `/deluser`; para eso hay que editar los
ficheros a mano.

---

## 🐳 Inicio rápido (Docker)

### 1. Clona el repositorio
```bash
git clone https://github.com/FranciscoFdez05/OSINTelegramBot.git
cd OSINTelegramBot
```

### 2. Crea el directorio de configuración y añade tus credenciales
```bash
mkdir -p config
echo "TU_TOKEN_DE_BOT"    > config/botToken.txt
echo "TU_ID_DE_TELEGRAM"  > config/usersIDs.txt

# opcional: limita quién puede gestionar la whitelist
echo "TU_ID_DE_TELEGRAM"  > config/adminIDs.txt
```

Tienes plantillas en `config/*.example` por si prefieres copiarlas.

> Obtén el token del bot en [@BotFather](https://t.me/BotFather).  
> Obtén tu ID de usuario en [@userinfobot](https://t.me/userinfobot).  
> Puedes añadir varios IDs, uno por línea o separados por comas.  
> Con el bot ya en marcha, puedes añadir más usuarios desde Telegram con `/adduser <userID>`.

### 3. Construir y arrancar
```bash
docker compose up -d --build
```

### 4. Ver los logs
```bash
docker compose logs -f
```

### Detener el bot
```bash
docker compose down
```

---

## ⚙️ Configuración

| Fichero | Uso |
|---|---|
| `config/botToken.txt` | Token del bot de @BotFather (solo se usa la primera línea) |
| `config/usersIDs.txt` | IDs de Telegram autorizados (uno por línea o separados por comas, `#` para comentarios) |
| `config/adminIDs.txt` | *(opcional)* IDs con permiso para usar `/adduser`, `/deluser` y `/users` |

Estos ficheros se montan como volumen — nunca quedan dentro de la imagen Docker.
`/adduser` y `/deluser` escriben en `config/usersIDs.txt` dentro de ese volumen, así que
los cambios sobreviven a reinicios y reconstrucciones del contenedor.

---

## 🌐 Panel de control web

Junto al bot arranca un pequeño panel (solo librería estándar, sin dependencias extra): lista de
usuarios (autorizados y cualquiera que haya contactado con el bot, con botón *Autorizar*),
alta/baja de usuarios, cambio del token del bot y datos de rendimiento (tiempo activo, comandos
ejecutados, tasa de éxito, tiempo medio por comando y actividad reciente).

- URL: `http://<IP-LAN-del-servidor>:6000` (escucha en `0.0.0.0` por defecto).
- Contraseña: variable `PANEL_PASSWORD` o `config/panelPassword.txt`. El fichero solo guarda un hash PBKDF2. Si no existe, se genera una aleatoria, se muestra una sola vez en consola y se guarda hasheada. Para cambiarla, escribe la nueva en texto plano en ese fichero y reinicia: se convierte a hash sola.
- Auditoría: cada comando queda en `log/audit.jsonl` (quién, comando, argumentos, resultado, código de salida, duración) y se ve en el panel. Los mensajes de usuarios no autorizados se ignoran sin responder (solo se anotan como *ignorado*, para que puedas autorizarlos desde el panel).
- Ajustes (variables de entorno): `PANEL_HOST` (por defecto `0.0.0.0`), `PANEL_PORT` (por defecto `6000`), `PANEL_USER` (usuario opcional), `PANEL_ENABLED=0` para desactivarlo.
- El nuevo token se aplica con el botón **Reiniciar bot**. El bot puede arrancar sin token y esperarlo desde el panel.
- El panel va en HTTP plano: mantenlo en la LAN (no redirijas el puerto a internet) y usa una contraseña fuerte.

- **Actualizaciones**: el panel muestra la versión instalada y la última en GitHub, y el botón **Actualizar** ejecuta `docker-update.sh` (git pull, reconstruir, comprobación de salud y vuelta atrás automática) sin entrar por SSH. El mismo script sirve desde consola: `./docker-update.sh`. Requiere haber arrancado con `./docker-up.sh` (monta la carpeta del proyecto y `/var/run/docker.sock` en el contenedor, lo que equivale a root en el host: usa una contraseña de panel fuerte). La versión está en `version.py`; súbela al publicar una release.
---

## 🖥️ Ejecución sin Docker

### Instalación manual

```bash
# Herramientas del sistema
sudo apt install -y nmap gobuster dirb whatweb sslscan dnsrecon curl whois dnsutils golang-go
# nikto ya no está en Debian trixie: git clone https://github.com/sullo/nikto y enlaza program/nikto.pl

# phoneinfoga
go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest

# Dependencias Python
pip install -r requirements.txt

# Arrancar
python3 main.py
```

Requiere Python 3.9+. En Windows o macOS usa Docker: casi todas estas herramientas son
solo para Linux.

---

## 🔐 Seguridad y buenas prácticas

- Mantén la lista de usuarios autorizados al mínimo necesario.
- Revisa `log/logfile.log` periódicamente para detectar actividad inesperada.
- Mantén la imagen Docker actualizada: `docker compose build --pull`.
- El token y los IDs nunca se almacenan dentro de la imagen — viven únicamente en el volumen `config/` montado.

---

## 📜 Licencia

Este proyecto está licenciado bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

**Developed with ❤️ by [Francisco](https://github.com/FranciscoFdez05)**
