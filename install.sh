#!/usr/bin/env bash
# Instalador de dependencias de OSINTelegramBot.
# Comprueba cada herramienta y solo instala las que faltan.
#
#   ./install.sh            instala lo que falte
#   ./install.sh --check    solo comprueba, no instala nada
#   ./install.sh --yes      no pregunta nada (modo desatendido)
#
# Pensado para Debian/Ubuntu/Kali (o WSL). En Windows/macOS usa Docker:
#   docker compose up -d --build

set -u

soloComprobar=0
sinPreguntar=0
for arg in "$@"; do
    case "$arg" in
        --check) soloComprobar=1 ;;
        --yes|-y) sinPreguntar=1 ;;
        --help|-h)
            sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "Opción desconocida: $arg (usa --help)"; exit 1 ;;
    esac
done

# COLORES
if [ -t 1 ]; then
    verde=$'\033[0;32m'; rojo=$'\033[0;31m'; amarillo=$'\033[0;33m'; azul=$'\033[0;34m'; reset=$'\033[0m'
else
    verde=""; rojo=""; amarillo=""; azul=""; reset=""
fi

ok()    { echo "  ${verde}[OK]${reset}    $*"; }
falta() { echo "  ${amarillo}[FALTA]${reset} $*"; }
error() { echo "  ${rojo}[ERROR]${reset} $*"; }
info()  { echo "${azul}==>${reset} $*"; }

# DEPENDENCIAS  ->  "binario:paquete:comando_del_bot"
paquetesApt=(
    "nmap:nmap:/nmap"
    "gobuster:gobuster:/gobuster"
    "nikto:nikto:/nikto"
    "whatweb:whatweb:/whatweb"
    "sslscan:sslscan:/sslscan"
    "dnsrecon:dnsrecon:/dnsrecon"
    "whois:whois:/whois"
    "dig:dnsutils:/dns"
    "curl:curl:/ipinfo y /emailrep"
)

paquetesPip=(
    "sherlock:sherlock-project:/sherlock"
    "maigret:maigret:/maigret"
    "holehe:holehe:/holehe"
    "h8mail:h8mail:/h8mail"
    "theHarvester:theHarvester:/harvester"
    "wafw00f:wafw00f:/waf"
)

# wordlists para gobuster (las trae el paquete dirb)
wordlists=(
    "/usr/share/dirb/wordlists/common.txt"
    "/usr/share/wordlists/dirb/common.txt"
    "/usr/share/dirbuster/wordlists/directory-list-2.3-small.txt"
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt"
)

faltantesApt=()
faltantesPip=()
faltaPhoneinfoga=0
faltaWordlist=0
faltaTelegramLib=0

tieneBinario() { command -v "$1" >/dev/null 2>&1; }

# SUDO
sudoCmd=""
if [ "$(id -u)" -ne 0 ]; then
    if tieneBinario sudo; then
        sudoCmd="sudo"
    fi
fi

# PIP: Debian moderno bloquea instalar fuera de un venv (PEP 668)
flagsPip=()
detectarFlagsPip() {
    flagsPip=("--no-input")
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        return
    fi
    flagsPip+=("--user")
    local marca
    marca="$(python3 -c 'import sysconfig,os;print(os.path.join(sysconfig.get_path("stdlib"),"EXTERNALLY-MANAGED"))' 2>/dev/null)"
    if [ -n "$marca" ] && [ -f "$marca" ]; then
        flagsPip+=("--break-system-packages")
    fi
}

# 1. COMPROBACIÓN
echo
info "Comprobando dependencias del sistema"
if ! tieneBinario apt-get; then
    error "Este instalador necesita apt (Debian/Ubuntu/Kali)."
    echo "      En Windows o macOS usa Docker:  docker compose up -d --build"
    exit 1
fi

for entrada in "${paquetesApt[@]}"; do
    binario="${entrada%%:*}"; resto="${entrada#*:}"
    paquete="${resto%%:*}"; comando="${resto#*:}"
    if tieneBinario "$binario"; then
        ok "$binario  ($comando)"
    else
        falta "$binario  ($comando)  -> apt: $paquete"
        faltantesApt+=("$paquete")
    fi
done

echo
info "Comprobando herramientas Python"
if ! tieneBinario python3; then
    error "python3 no está instalado. Instálalo antes de continuar."
    exit 1
fi
if python3 -c "import telegram" >/dev/null 2>&1; then
    ok "python-telegram-bot"
else
    falta "python-telegram-bot  -> pip: python-telegram-bot"
    faltaTelegramLib=1
fi
for entrada in "${paquetesPip[@]}"; do
    binario="${entrada%%:*}"; resto="${entrada#*:}"
    paquete="${resto%%:*}"; comando="${resto#*:}"
    if tieneBinario "$binario"; then
        ok "$binario  ($comando)"
    else
        falta "$binario  ($comando)  -> pip: $paquete"
        faltantesPip+=("$paquete")
    fi
done

echo
info "Comprobando extras"
if tieneBinario phoneinfoga; then
    ok "phoneinfoga  (/phone)"
else
    falta "phoneinfoga  (/phone)  -> go install"
    faltaPhoneinfoga=1
fi

encontrada=""
for w in "${wordlists[@]}"; do
    if [ -f "$w" ]; then encontrada="$w"; break; fi
done
if [ -n "$encontrada" ]; then
    ok "wordlist para gobuster ($encontrada)"
else
    falta "wordlist para gobuster  -> apt: dirb"
    faltaWordlist=1
fi

totalFaltantes=$(( ${#faltantesApt[@]} + ${#faltantesPip[@]} + faltaPhoneinfoga + faltaWordlist + faltaTelegramLib ))

echo
if [ "$totalFaltantes" -eq 0 ]; then
    info "${verde}Todas las dependencias están instaladas.${reset}"
else
    info "Faltan $totalFaltantes dependencia(s)."
fi

if [ "$soloComprobar" -eq 1 ]; then
    echo
    info "Modo --check: no se instala nada."
    [ "$totalFaltantes" -eq 0 ] && exit 0 || exit 1
fi

# 2. INSTALACIÓN
if [ "$totalFaltantes" -gt 0 ]; then
    if [ "$sinPreguntar" -eq 0 ]; then
        echo
        read -r -p "¿Instalar las dependencias que faltan? [s/N] " respuesta
        case "$respuesta" in
            s|S|y|Y) ;;
            *) echo "Cancelado."; exit 1 ;;
        esac
    fi

    if [ -z "$sudoCmd" ] && [ "$(id -u)" -ne 0 ]; then
        error "Se necesitan permisos de root (instala sudo o ejecuta como root)."
        exit 1
    fi

    # apt
    if [ "$faltaWordlist" -eq 1 ]; then
        faltantesApt+=("dirb")
    fi
    if [ "$faltaPhoneinfoga" -eq 1 ] && ! tieneBinario go; then
        faltantesApt+=("golang-go")
    fi
    if [ ${#faltantesApt[@]} -gt 0 ]; then
        echo
        info "Instalando con apt: ${faltantesApt[*]}"
        $sudoCmd apt-get update -qq || { error "apt-get update falló."; exit 1; }
        $sudoCmd apt-get install -y --no-install-recommends "${faltantesApt[@]}" \
            || { error "apt-get install falló."; exit 1; }
    fi

    # pip
    if [ "$faltaTelegramLib" -eq 1 ]; then
        faltantesPip+=("python-telegram-bot>=20.0")
    fi
    if [ ${#faltantesPip[@]} -gt 0 ]; then
        echo
        if ! tieneBinario pip3; then
            info "Instalando pip3"
            $sudoCmd apt-get install -y --no-install-recommends python3-pip \
                || { error "No se pudo instalar python3-pip."; exit 1; }
        fi
        detectarFlagsPip
        info "Instalando con pip: ${faltantesPip[*]}"
        pip3 install "${flagsPip[@]}" "${faltantesPip[@]}" || {
            error "pip install falló. Prueba dentro de un virtualenv:"
            echo "      python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
            exit 1
        }
    fi

    # phoneinfoga (binario Go)
    if [ "$faltaPhoneinfoga" -eq 1 ]; then
        echo
        info "Instalando phoneinfoga (go install)"
        if tieneBinario go; then
            go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest \
                || error "go install falló; /phone no estará disponible."
        else
            error "Go no está disponible; /phone no estará disponible."
        fi
    fi
fi

# 3. CONFIGURACIÓN
echo
info "Preparando config/"
mkdir -p config log
creados=0
for fichero in config/botToken.txt config/usersIDs.txt; do
    if [ ! -f "$fichero" ]; then
        : > "$fichero"
        chmod 600 "$fichero"
        falta "creado $fichero (vacío, hay que rellenarlo)"
        creados=1
    else
        ok "$fichero ya existe"
    fi
done
if [ ! -f config/adminIDs.txt ]; then
    ok "config/adminIDs.txt no existe (opcional: el primer ID de usersIDs.txt será admin)"
fi

# 4. RESUMEN
echo
info "Comprobación final"
pendientes=0
for entrada in "${paquetesApt[@]}" "${paquetesPip[@]}"; do
    binario="${entrada%%:*}"
    if ! tieneBinario "$binario"; then
        falta "$binario sigue sin estar disponible"
        pendientes=$(( pendientes + 1 ))
    fi
done
if ! tieneBinario phoneinfoga; then
    falta "phoneinfoga sigue sin estar disponible (/phone no funcionará)"
    echo "        Si acabas de instalarlo, añade Go al PATH:"
    echo "        export PATH=\"\$PATH:\$(go env GOPATH)/bin\""
    pendientes=$(( pendientes + 1 ))
fi

echo
if [ "$pendientes" -eq 0 ]; then
    info "${verde}Todo listo.${reset}"
else
    info "${amarillo}Quedan $pendientes herramienta(s) sin instalar.${reset} El resto de comandos sí funcionarán."
fi

if [ "$creados" -eq 1 ]; then
    echo
    echo "Antes de arrancar, rellena la configuración:"
    echo "  echo \"TU_TOKEN\"          > config/botToken.txt"
    echo "  echo \"TU_ID_DE_TELEGRAM\" > config/usersIDs.txt"
fi
echo
echo "Arrancar el bot:  python3 main.py"
echo
