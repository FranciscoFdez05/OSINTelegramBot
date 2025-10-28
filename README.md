## OSINTelegramBot
OSINTelegramBot es un bot de Telegram orientado a la recolección de información básica durante investigaciones OSINT. El bot se ejecuta localmente y permite lanzar, de forma controlada, comandos como `whois`, consultas DNS, peticiones a ipinfo.io y búsquedas con la herramienta Sherlock.

## Características principales
- **Control de acceso** mediante una lista de identificadores de usuario autorizados.
- **Ejecución segura** de utilidades externas (`whois`, `dig`, `curl` e `sherlock`) con validación de argumentos y límites de tiempo.
- **Registro de actividad** en ficheros de log dedicados.
- **División automática de mensajes largos** para ajustarse a las restricciones de Telegram.

## Requisitos
- Python 3.9 o superior.
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) >= 20.0.
- Herramientas de línea de comandos: `whois`, `dig`, `curl` y `sherlock` disponibles en el `PATH` del sistema.

Puedes usar el script `requirements.sh` como referencia para instalar dependencias en sistemas basados en Debian/Ubuntu:
```bash
sudo apt update
sudo apt install python3-python-telegram-bot whois dnsutils curl
sudo apt install sherlock
```

## Configuración
El bot espera encontrar sus ficheros de configuración en el directorio `config/`.
1. **Token del bot**: crea `config/botToken.txt` con el token proporcionado por @BotFather. Solo se usa la primera línea.
2. **Usuarios autorizados**: crea `config/usersIDs.txt` con un identificador por línea (opcionalmente separados por comas). Puedes añadir comentarios precedidos por `#`.

Si alguno de los ficheros no existe o está vacío, el bot se detendrá con un mensaje de error.

## Ejecución
1. Instala las dependencias necesarias.
2. Ejecuta el bot:
```bash
python3 main.py
```

El bot iniciará un bucle de *polling* y registrará eventos en `log/logfile.log`.

## Comandos disponibles
Todos los comandos sólo están disponibles para los usuarios autorizados.
- `/start` / `/help`: muestra la lista de comandos habilitados.
- `/whois <dominio>`: ejecuta la utilidad `whois` sobre el dominio proporcionado.
- `/dns <dominio>`: consulta registros DNS básicos usando `dig`.
- `/ipinfo <ip>`: recupera información de ipinfo.io mediante `curl`.
- `/sherlock <usuario>`: lanza la herramienta Sherlock para buscar un nombre de usuario en múltiples servicios.

Las salidas se envían como texto plano y se fragmentan automáticamente si superan el límite configurado.

## Seguridad y buenas prácticas
- Limita la lista de usuarios autorizados a las cuentas que realmente necesiten acceso.
- Revisa periódicamente los registros en `log/` para detectar actividad sospechosa.
- Asegúrate de mantener actualizadas las herramientas externas y la librería `python-telegram-bot`.


## Licencia
📄 Este proyecto está licenciado bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles..  

**Developed with ❤️ by [Francisco](https://github.com/FranciscoFdez05)**
