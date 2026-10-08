# -*- coding: utf-8 -*-
"""Versión y actualización del bot desde el panel (solo librería estándar).

El contenedor del bot se recrea durante la actualización, así que no puede ejecutarla él
mismo: lanza un contenedor auxiliar (misma imagen, socket de Docker y carpeta del proyecto
montados en la misma ruta que en el host) que ejecuta docker-update.sh y sigue vivo cuando
el del bot se reemplaza. La salida queda en log/update.log.

Requiere que docker-up.sh / docker-update.sh hayan exportado PROJECT_DIR, PUID y PGID.
"""

import os
import re
import subprocess
import threading
import time
import urllib.request
from typing import Any, Dict, Optional, Tuple

from version import __version__

repo = "FranciscoFdez05/OSINTelegramBot"
rama = os.environ.get("UPDATE_BRANCH", "main")
versionRemotaUrl = f"https://raw.githubusercontent.com/{repo}/{rama}/version.py"
helperName = "osintelegrambot-updater"
dockerSock = "/var/run/docker.sock"
cacheTtl = 600

_versionRegex = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.M)
_ansiRegex = re.compile(r"\x1b\[[0-9;]*m")
_cache: Dict[str, Any] = {"t": 0.0, "version": None, "error": None}
_lock = threading.Lock()


def _projectDir() -> str:
    return os.environ.get("PROJECT_DIR", "")


def _logPath() -> str:
    return os.path.join(_projectDir(), "log", "update.log")


def _tupla(v: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def motivoNoDisponible() -> Optional[str]:
    """None si se puede actualizar desde el panel; si no, el motivo en texto."""
    p = _projectDir()
    if not p or not os.path.isabs(p):
        return "Falta PROJECT_DIR: arranca con ./docker-up.sh (o ./docker-update.sh) para habilitarlo."
    if not os.path.exists(dockerSock):
        return "El contenedor no tiene acceso al socket de Docker."
    if not os.path.isdir(os.path.join(p, ".git")):
        return "La carpeta del proyecto no es un clon de git."
    if os.environ.get("PUID", "0") in ("", "0"):
        return "PUID no válido (se ejecutó con sudo/root): vuelve a arrancar con ./docker-up.sh."
    return None


def versionRemota(forzar: bool = False) -> Tuple[Optional[str], Optional[str]]:
    with _lock:
        if not forzar and time.time() - _cache["t"] < cacheTtl:
            return _cache["version"], _cache["error"]
        try:
            with urllib.request.urlopen(versionRemotaUrl, timeout=8) as r:
                m = _versionRegex.search(r.read(4096).decode("utf-8", "replace"))
            if not m:
                raise ValueError("version.py remoto sin __version__")
            _cache.update(t=time.time(), version=m.group(1), error=None)
        except Exception as e:
            _cache.update(t=time.time(), version=None, error=f"No se pudo consultar GitHub: {e}")
        return _cache["version"], _cache["error"]


def _docker(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def actualizando() -> bool:
    try:
        r = _docker("ps", "-q", "--filter", f"name=^{helperName}$")
        return bool(r.stdout.strip())
    except Exception:
        return False


def _leerLog(maxLineas: int = 60) -> Tuple[str, Optional[str]]:
    """(cola del log sin colores, 'ok'|'fail'|None según la marca final)."""
    try:
        with open(_logPath(), "r", encoding="utf-8", errors="replace") as f:
            texto = _ansiRegex.sub("", f.read()[-20000:])
    except OSError:
        return "", None
    resultado = "ok" if "== UPDATE_OK ==" in texto else "fail" if "== UPDATE_FAIL ==" in texto else None
    return "\n".join(texto.splitlines()[-maxLineas:]), resultado


def estado(forzar: bool = False) -> Dict[str, Any]:
    remota, errorRemota = versionRemota(forzar)
    log, resultado = _leerLog()
    corriendo = actualizando()
    disponible = False
    if remota:
        try:
            disponible = _tupla(remota) > _tupla(__version__)
        except ValueError:
            disponible = remota != __version__
    motivo = motivoNoDisponible()
    return {
        "current": __version__, "latest": remota, "available": disponible, "checkError": errorRemota,
        "enabled": motivo is None, "reason": motivo,
        "running": corriendo, "log": log, "result": None if corriendo else resultado,
    }


def iniciar() -> Tuple[bool, str]:
    motivo = motivoNoDisponible()
    if motivo:
        return False, motivo
    if actualizando():
        return False, "Ya hay una actualización en curso."
    imagen = os.environ.get("BOT_IMAGE", "")
    if not imagen:
        return False, "Falta BOT_IMAGE: arranca con ./docker-up.sh."
    p = _projectDir()
    try:
        gid = os.stat(dockerSock).st_gid
        _docker("rm", "-f", helperName)
        r = _docker(
            "run", "-d", "--rm", "--name", helperName,
            "--user", f"{os.environ['PUID']}:{os.environ.get('PGID', os.environ['PUID'])}",
            "--group-add", str(gid),
            "-e", "HOME=/tmp",
            "-e", "GIT_CONFIG_COUNT=1", "-e", "GIT_CONFIG_KEY_0=safe.directory", "-e", "GIT_CONFIG_VALUE_0=*",
            "-v", f"{dockerSock}:{dockerSock}", "-v", f"{p}:{p}", "-w", p,
            imagen, "sh", "-c", "sh ./docker-update.sh > log/update.log 2>&1",
        )
    except Exception as e:
        return False, f"No se pudo lanzar la actualización: {e}"
    if r.returncode != 0:
        return False, f"docker run falló: {r.stderr.strip()[:300]}"
    return True, "Actualización iniciada. El bot se reiniciará; vuelve a entrar al panel si se cierra la sesión."
