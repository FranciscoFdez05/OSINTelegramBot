#!/usr/bin/env sh
# Actualiza la instalación Docker en marcha y comprueba que arranca.
#
#   1. Hace `git pull --ff-only` (avisa antes si hay cambios locales que chocarían).
#   2. Construye la imagen etiquetada con la versión (osintelegrambot:<versión>),
#      de modo que la anterior sigue disponible para volver atrás.
#   3. Levanta el contenedor y espera a que su healthcheck (/api/health) pase.
#   4. Si no arranca, vuelve solo a la imagen anterior.
#
# Se ejecuta igual por SSH que desde el panel web (que lo lanza en un contenedor
# auxiliar, porque el contenedor del bot se recrea durante la actualización).
#
# Uso: ./docker-update.sh [--sin-pull]
set -e

# El directorio del proyecto se fija antes que nada: la copia desde la que se
# reejecuta vive en /tmp, así que allí `dirname "$0"` ya no sirve.
PM_PROYECTO="${PM_PROYECTO:-$(cd "$(dirname "$0")" && pwd)}"
export PM_PROYECTO
cd "$PM_PROYECTO"

# Reejecutarse desde una copia: el `git pull` puede reemplazar este fichero mientras
# el intérprete lo lee, y `sh` se descolocaría. Si no se puede copiar se sigue igual.
if [ -z "$PM_UPDATE_COPIA" ]; then
    copia=$(mktemp "${TMPDIR:-/tmp}/docker-update.XXXXXX" 2>/dev/null) || copia=""
    if [ -n "$copia" ] && cp "$0" "$copia" 2>/dev/null; then
        PM_UPDATE_COPIA="$copia"
        export PM_UPDATE_COPIA
        codigo=0
        sh "$copia" "$@" || codigo=$?
        rm -f "$copia"
        exit "$codigo"
    fi
fi

SIN_PULL=0
[ "$1" = "--sin-pull" ] && SIN_PULL=1

# Con sudo, el pull deja ficheros de root y los datos montados cambiarían de dueño.
if [ "$(id -u)" -eq 0 ]; then
    echo "ERROR: no ejecutes docker-update.sh con sudo/root." >&2
    echo "       Ejecútalo como tu usuario normal: ./docker-update.sh" >&2
    exit 1
fi

SERVICIO="bot"
CONTENEDOR="osintelegrambot"
IMAGEN="osintelegrambot"
ESPERA_SALUD=90   # segundos que se le dan a la versión nueva para estar sana

if [ -t 1 ]; then
    aviso() { printf '\n\033[33m%s\033[0m\n' "$*"; }
    error() { printf '\n\033[31m%s\033[0m\n' "$*" >&2; }
    paso()  { printf '\n\033[36m── %s\033[0m\n' "$*"; }
else
    aviso() { printf '\n%s\n' "$*"; }
    error() { printf '\n%s\n' "$*" >&2; }
    paso()  { printf '\n── %s\n' "$*"; }
fi

version_del_codigo() {
    sed -n 's/^__version__ = "\(.*\)"/\1/p' version.py 2>/dev/null | head -n 1
}

# Marca final que lee el panel web para saber cómo terminó.
fallo() { echo "== UPDATE_FAIL =="; exit 1; }

# ── 1. Comprobaciones previas ─────────────────────────────────────────────────
paso "Comprobando el estado local"

command -v docker >/dev/null 2>&1 || { error "Docker no está en el PATH."; fallo; }
docker compose version >/dev/null 2>&1 || { error "Falta Docker Compose v2."; fallo; }

if [ ! -f .env ]; then
    error "No hay .env. Esto es una instalación nueva: usa ./docker-up.sh."
    fallo
fi

if [ "$SIN_PULL" -eq 0 ]; then
    if [ ! -d .git ]; then
        error "Esto no es un clon de git; no se puede actualizar con pull."
        fallo
    fi
    if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        error "Hay cambios locales en ficheros versionados y el pull podría chocar."
        git status --short --untracked-files=no
        echo
        echo "Los ajustes de producción van en .env y config/ (no se versionan)."
        echo "Para descartar los cambios locales:  git checkout -- .   y vuelve a actualizar."
        fallo
    fi
fi

VERSION_ANTERIOR=$(version_del_codigo)
[ -n "$VERSION_ANTERIOR" ] || VERSION_ANTERIOR="desconocida"
COMMIT_ANTERIOR=$(git rev-parse --short HEAD 2>/dev/null || echo "")
echo "Versión instalada: $VERSION_ANTERIOR"

# ── 2. Traer los cambios ──────────────────────────────────────────────────────
if [ "$SIN_PULL" -eq 0 ]; then
    paso "Descargando la versión nueva"
    git pull --ff-only || { error "git pull falló."; fallo; }
fi

VERSION_NUEVA=$(version_del_codigo)
[ -n "$VERSION_NUEVA" ] || VERSION_NUEVA="desconocida"

if [ "$VERSION_NUEVA" = "$VERSION_ANTERIOR" ]; then
    aviso "Ya estabas en la $VERSION_NUEVA. Se reconstruye igualmente."
else
    echo "Actualizando: $VERSION_ANTERIOR → $VERSION_NUEVA"
    if [ -f CHANGELOG.md ]; then
        paso "Novedades de la $VERSION_NUEVA"
        awk '/^## \[/{n++} n==1{print} n==2{exit}' CHANGELOG.md
    fi
fi

# ── 3. Entorno de compose ─────────────────────────────────────────────────────
PROJECT_DIR="$PM_PROYECTO"
PUID=$(id -u)
PGID=$(id -g)
BOT_VERSION="$VERSION_NUEVA"
export PROJECT_DIR PUID PGID BOT_VERSION
mkdir -p config log

# ── 4. Construir y levantar ───────────────────────────────────────────────────
paso "Construyendo la imagen $IMAGEN:$VERSION_NUEVA"
docker compose build || { error "La construcción falló; no se ha tocado el contenedor en marcha."; fallo; }

paso "Levantando"
docker compose up -d || true

# ── 5. Comprobar que arranca de verdad ────────────────────────────────────────
# El healthcheck del compose consulta /api/health, así que «sano» significa que
# la aplicación responde, no solo que el contenedor esté arriba.
paso "Esperando a que esté sano (hasta ${ESPERA_SALUD}s)"

salud() {
    docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTENEDOR" 2>/dev/null || echo "ausente"
}

sano=0
i=0
while [ "$i" -lt "$ESPERA_SALUD" ]; do
    if [ "$(salud)" = "healthy" ]; then
        sano=1
        break
    fi
    i=$((i + 1))
    sleep 1
done

if [ "$sano" -eq 1 ]; then
    paso "Actualización correcta"
    echo "Versión $VERSION_NUEVA en marcha."
    # Las imágenes de versiones antiguas se conservan; se limpia lo huérfano.
    docker image prune -f >/dev/null 2>&1 || true
    echo "== UPDATE_OK =="
    exit 0
fi

# ── 6. Vuelta atrás ───────────────────────────────────────────────────────────
error "La versión $VERSION_NUEVA no está sana tras ${ESPERA_SALUD}s. Volviendo atrás."

echo "Últimas líneas del log:"
docker compose logs --tail 40 "$SERVICIO" 2>&1 || true

if [ "$VERSION_ANTERIOR" != "desconocida" ] \
   && docker image inspect "$IMAGEN:${VERSION_ANTERIOR}" >/dev/null 2>&1; then
    paso "Levantando de nuevo la $VERSION_ANTERIOR"
    BOT_VERSION="$VERSION_ANTERIOR" docker compose up -d --no-build || true
    aviso "Se ha vuelto a la $VERSION_ANTERIOR. El código del repositorio SÍ está actualizado.
Para dejarlo también como estaba:  git reset --hard ${COMMIT_ANTERIOR:-<commit anterior>}"
else
    error "No hay imagen etiquetada de la $VERSION_ANTERIOR; no se puede volver sola."
fi
fallo
