#!/usr/bin/env sh
# Levanta el bot con Docker pidiendo usuario, contraseña y puerto del panel web.
# Los valores se guardan en .env (PANEL_USER, PANEL_PASSWORD, PANEL_PORT) y
# docker-compose.yml los lee de ahí. Uso: ./docker-up.sh [args para compose up]
set -e
cd "$(dirname "$0")"

if [ "$(id -u)" -eq 0 ]; then
    echo "ERROR: no ejecutes docker-up.sh con sudo (.env y los datos quedarían como root)." >&2
    exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker no está en el PATH." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "ERROR: Docker no está disponible (¿daemon parado o sin permisos?)." >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: falta Docker Compose v2." >&2; exit 1; }

[ -f .env ] || { : > .env; chmod 600 .env 2>/dev/null || true; }

env_get() { sed -n "s/^$1=//p" .env | head -n 1 | sed 's/\$\$/$/g'; }

env_set() {
    # Compose interpreta `$` en .env: se duplica para que llegue literal.
    valor=$(printf '%s' "$2" | sed 's/\$/$$/g')
    grep -v "^$1=" .env > .env.tmp || true
    printf '%s=%s\n' "$1" "$valor" >> .env.tmp
    mv .env.tmp .env
}

USER_ACTUAL=$(env_get PANEL_USER)
PASS_ACTUAL=$(env_get PANEL_PASSWORD)
PORT=$(env_get PANEL_PORT)
[ -n "$PORT" ] || PORT=6050
if [ "$PORT" = "6000" ] || [ "$PORT" = "6001" ]; then PORT=6050; fi  # 6000 lo bloquean los navegadores

if [ -t 0 ]; then
    # Usuario
    DEF_USER=${USER_ACTUAL:-admin}
    printf 'ID de usuario para acceder a la web [%s]: ' "$DEF_USER"
    read -r R || R=""
    PANEL_USER=${R:-$DEF_USER}

    # Contraseña (Enter conserva la actual, si la hay)
    while true; do
        stty -echo 2>/dev/null || true
        if [ -n "$PASS_ACTUAL" ]; then
            printf 'Contraseña (Enter para mantener la actual): '
        else
            printf 'Contraseña: '
        fi
        read -r PW || PW=""
        printf '\n'
        if [ -z "$PW" ] && [ -n "$PASS_ACTUAL" ]; then
            stty echo 2>/dev/null || true
            PW=$PASS_ACTUAL
            break
        fi
        printf 'Repite la contraseña: '
        read -r PW2 || PW2=""
        printf '\n'
        stty echo 2>/dev/null || true
        if [ -n "$PW" ] && [ "$PW" = "$PW2" ]; then break; fi
        echo "  Las contraseñas no coinciden o están vacías." >&2
    done
    PANEL_PASSWORD=$PW

    # Puerto
    while true; do
        printf 'Puerto del servidor [%s]: ' "$PORT"
        read -r R || R=""
        [ -n "$R" ] || break
        R=$(printf '%s' "$R" | sed 's/^0*//')
        case "$R" in
            ''|*[!0-9]*) ;;
            *) if [ "$R" -ge 1 ] && [ "$R" -le 65535 ]; then
                   case "$R" in
                       6000|6665|6666|6667|6668|6669|6697|5060|5061|2049|3659|4045|10080)
                           echo "  El puerto $R lo bloquean Chrome/Vivaldi/Edge (ERR_UNSAFE_PORT). Elige otro." >&2
                           continue ;;
                   esac
                   PORT=$R; break
               fi ;;
        esac
        echo "  Tiene que ser un número entre 1 y 65535." >&2
    done

    env_set PANEL_USER "$PANEL_USER"
    env_set PANEL_PASSWORD "$PANEL_PASSWORD"
    env_set PANEL_PORT "$PORT"
    unset PW PW2
else
    if [ -z "$PASS_ACTUAL" ]; then
        echo "AVISO: sin terminal y sin PANEL_PASSWORD en .env; el bot generará una" >&2
        echo "       contraseña aleatoria (config/panelPassword.txt)." >&2
    fi
fi

mkdir -p config log

# Para la actualización desde el panel (ver docker-update.sh y webpanel/updater.py)
PROJECT_DIR=$(pwd)
PUID=$(id -u)
PGID=$(id -g)
BOT_VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' version.py | head -n 1)
export PROJECT_DIR PUID PGID BOT_VERSION

docker compose up -d --build "$@"

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -n "$LAN_IP" ] || LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
[ -n "$LAN_IP" ] || LAN_IP="<IP_DEL_SERVIDOR>"

echo
echo "Panel levantado:"
echo "  Esta máquina : http://localhost:$PORT"
echo "  Red local    : http://$LAN_IP:$PORT"
echo "  Usuario      : $(env_get PANEL_USER)"
echo
echo "Aviso: sin HTTPS, la contraseña viaja en claro por la red local."
