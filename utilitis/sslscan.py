# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

defaultArgs = ["--no-colour"]
timeoutSeconds = 30
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    ruta = shutil.which("sslscan")
    if not ruta:
        raise RuntimeError("No se encontró 'sslscan' en PATH. Instala con: apt install sslscan")
    return ruta


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /sslscan <host|url>")
    host = args[0]
    if host.startswith("-"):
        raise RuntimeError("Uso: /sslscan <host|url>")
    # sslscan no necesita protocolo, lo quita si viene con https://
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    return host


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    host = _validarArgs(args)
    comando = [binario] + defaultArgs + [host]

    resultado = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeoutSeconds,
        text=True,
        env=safeEnv,
    )
    salida = resultado.stdout or ""
    exitCode = resultado.returncode

    maxBytes = 1 * 1024 * 1024
    if len(salida.encode("utf-8", errors="ignore")) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado]\n"
    return salida, exitCode
