# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

defaultArgs = ["-nointeractive", "-maxtime", "90s"]
timeoutSeconds = 120
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    ruta = shutil.which("nikto")
    if not ruta:
        raise RuntimeError("No se encontró 'nikto' en PATH. Instala con: apt install nikto")
    return ruta


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /nikto <url|ip>")
    if args[0].startswith("-"):
        raise RuntimeError("Uso: /nikto <url|ip>")
    objetivo = args[0]
    if not objetivo.startswith("http://") and not objetivo.startswith("https://"):
        objetivo = "http://" + objetivo
    return objetivo


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    objetivo = _validarArgs(args)
    comando = [binario, "-h", objetivo] + defaultArgs

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

    maxBytes = 2 * 1024 * 1024
    if len(salida.encode("utf-8", errors="ignore")) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado]\n"
    return salida, exitCode
