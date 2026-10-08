# -*- coding: utf-8 -*-
"""Piezas comunes de los módulos de utilitis: timeouts, validadores y ejecución de procesos."""

import ipaddress
import os
import re
import shutil
import signal
import subprocess
from typing import List, Optional, Tuple
from urllib.parse import urlsplit

# TIMEOUTS (segundos) por comando: único sitio donde ajustarlos
timeouts = {
    "whois": 20, "dns": 15, "ipinfo": 12, "nmap": 180, "gobuster": 180,
    "harvester": 120, "dnsrecon": 90, "whatweb": 30, "nikto": 120,
    "sslscan": 30, "waf": 30, "sherlock": 180, "maigret": 300,
    "holehe": 120, "h8mail": 60, "emailrep": 15, "phone": 30,
}
defaultTimeout = 60

# LÍMITE de salida en bytes por comando (por defecto 1 MB)
maxBytesPorComando = {"maigret": 5 * 1024 * 1024, "sherlock": 5 * 1024 * 1024}
defaultMaxBytes = 1 * 1024 * 1024

safePath = "/usr/bin:/bin:/usr/local/bin:/root/go/bin"


# VALIDADORES: devuelven el valor normalizado o lanzan RuntimeError(usage)
_label = r"[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?"
_domainRe = re.compile(rf"^{_label}(?:\.{_label})*$")
_emailRe = re.compile(rf"^[A-Za-z0-9._%+-]{{1,64}}@{_label}(?:\.{_label})+$")
_userRe = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_phoneRe = re.compile(r"^\+[0-9]{6,15}$")


def _esDominio(valor: str) -> bool:
    return len(valor) <= 253 and bool(_domainRe.match(valor))


def _esIp(valor: str) -> bool:
    try:
        ipaddress.ip_address(valor)
        return True
    except ValueError:
        return False


def _unico(args: List[str], usage: str) -> str:
    if not args or len(args) != 1:
        raise RuntimeError(usage)
    valor = args[0].strip()
    if not valor or valor.startswith("-"):
        raise RuntimeError(usage)
    return valor


def validarDominio(args: List[str], usage: str) -> str:
    valor = _unico(args, usage)
    if not _esDominio(valor):
        raise RuntimeError(usage)
    return valor.lower()


def validarIp(args: List[str], usage: str) -> str:
    valor = _unico(args, usage)
    if not _esIp(valor):
        raise RuntimeError(usage)
    return valor


def validarHost(args: List[str], usage: str) -> str:
    """Dominio o IP, sin rangos ni comodines."""
    valor = _unico(args, usage)
    if not (_esIp(valor) or _esDominio(valor)):
        raise RuntimeError(usage)
    return valor.lower()


def validarHostOUrl(args: List[str], usage: str) -> str:
    """Para sslscan: acepta host o URL y devuelve solo el host (opcionalmente host:puerto)."""
    valor = _unico(args, usage)
    if "://" in valor:
        valor = validarUrl([valor], usage)
        partes = urlsplit(valor)
        return partes.hostname + (f":{partes.port}" if partes.port else "")
    return validarHost([valor], usage)


def validarUrl(args: List[str], usage: str) -> str:
    valor = _unico(args, usage)
    if "://" not in valor:
        valor = "http://" + valor
    if len(valor) > 2048 or re.search(r"[\s\x00-\x1f\x7f]", valor):
        raise RuntimeError(usage)
    try:
        partes = urlsplit(valor)
        host = partes.hostname
        partes.port  # valida el puerto
    except ValueError:
        raise RuntimeError(usage)
    if partes.scheme not in ("http", "https") or partes.username or not host:
        raise RuntimeError(usage)
    if not (_esIp(host) or _esDominio(host)):
        raise RuntimeError(usage)
    return valor


def validarEmail(args: List[str], usage: str) -> str:
    valor = _unico(args, usage)
    if not _emailRe.match(valor):
        raise RuntimeError(usage)
    return valor


def validarUsuario(args: List[str], usage: str) -> str:
    valor = _unico(args, usage)
    if not _userRe.match(valor):
        raise RuntimeError(usage)
    return valor


def validarTelefono(args: List[str], usage: str) -> str:
    valor = _unico(args, usage)
    if not _phoneRe.match(valor):
        raise RuntimeError(usage + "  (formato internacional, ej: +34612345678)")
    return valor


# EJECUCIÓN
def resolverBinario(*nombres: str, ayuda: str = "") -> str:
    for nombre in nombres:
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    raise RuntimeError(f"No se encontró '{nombres[0]}' en PATH." + (f" {ayuda}" if ayuda else ""))


def _matar(proc: subprocess.Popen) -> None:
    """Mata el proceso y sus hijos (las herramientas suelen lanzar subprocesos)."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError, OSError):
        pass


def ejecutar(comando: List[str], nombre: str, path: Optional[str] = None) -> Tuple[str, int]:
    """Ejecuta el comando con el timeout de `nombre`. Al expirar mata todo el árbol de procesos
    y devuelve lo que hubiera salido, con código 124."""
    timeout = timeouts.get(nombre, defaultTimeout)
    maxBytes = maxBytesPorComando.get(nombre, defaultMaxBytes)
    env = {"PATH": path or safePath, "LC_ALL": "C"}

    proc = subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        env=env,
        start_new_session=hasattr(os, "killpg"),
    )
    try:
        salida, _ = proc.communicate(timeout=timeout)
        codigo = proc.returncode
    except subprocess.TimeoutExpired:
        _matar(proc)
        try:
            salida, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            salida = ""
        salida = (salida or "") + f"\n[tiempo agotado tras {timeout}s: proceso terminado]\n"
        codigo = 124

    salida = salida or ""
    if len(salida) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado]\n"
    return salida, codigo
