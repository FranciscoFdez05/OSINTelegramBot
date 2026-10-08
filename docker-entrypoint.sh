#!/bin/sh
# Al arrancar el contenedor comprueba que cada herramienta externa está instalada
# y, si falta alguna, intenta instalarla. Nunca bloquea el arranque: lo que no se
# pueda instalar se avisa y el bot arranca igualmente (ese comando dará error).

faltan=""

tiene() { command -v "$1" >/dev/null 2>&1; }

apt_ok=0
apt_instalar() {
    if [ "$apt_ok" -eq 0 ]; then
        apt-get update >/dev/null 2>&1 && apt_ok=1
    fi
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$1" >/dev/null 2>&1
}

# binario  método  paquete/origen
asegurar() {
    bin="$1"; metodo="$2"; origen="$3"
    tiene "$bin" && return 0
    echo "[tools] Falta '$bin', instalando ($metodo: $origen)..."
    case "$metodo" in
        apt) apt_instalar "$origen" ;;
        pip) pip install --no-cache-dir "$origen" >/dev/null 2>&1 ;;
        phoneinfoga)
            case "$(uname -m)" in aarch64) a=arm64;; armv7l) a=armv7;; i686|i386) a=i386;; *) a=x86_64;; esac
            curl -fsSL "https://github.com/sundowndev/phoneinfoga/releases/latest/download/phoneinfoga_Linux_$a.tar.gz" \
                | tar -xz -C /usr/local/bin phoneinfoga
            ;;
        nikto)
            apt_instalar perl; apt_instalar libnet-ssleay-perl
            mkdir -p /opt/nikto \
                && curl -fsSL https://github.com/sullo/nikto/archive/HEAD.tar.gz \
                    | tar -xz --strip-components=1 -C /opt/nikto \
                && ln -sf /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
                && chmod +x /opt/nikto/program/nikto.pl
            ;;
    esac
    if tiene "$bin"; then
        echo "[tools] '$bin' instalado."
    else
        echo "[tools] AVISO: no se pudo instalar '$bin'." >&2
        faltan="$faltan $bin"
    fi
}

asegurar nmap         apt  nmap
asegurar gobuster     apt  gobuster
asegurar dirb         apt  dirb
asegurar nikto        nikto -
asegurar whatweb      apt  whatweb
asegurar sslscan      apt  sslscan
asegurar dnsrecon     apt  dnsrecon
asegurar curl         apt  curl
asegurar whois        apt  whois
asegurar dig          apt  dnsutils
asegurar phoneinfoga  phoneinfoga -
asegurar holehe       pip  holehe
asegurar h8mail       pip  h8mail
asegurar theHarvester pip  theHarvester
asegurar sherlock     pip  sherlock-project
asegurar maigret      pip  maigret
asegurar wafw00f      pip  wafw00f

if [ -n "$faltan" ]; then
    echo "[tools] Herramientas no disponibles:$faltan" >&2
else
    echo "[tools] Todas las herramientas están instaladas."
fi

exec "$@"
