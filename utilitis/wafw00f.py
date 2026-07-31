# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

timeoutSeconds = 30
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    ruta = shutil.which("wafw00f")
    if not ruta:
        raise RuntimeError("No se encontró 'wafw00f' en PATH. Instala con: pip install wafw00f")
    return ruta


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /waf <url|dominio>")
    if args[0].startswith("-"):
        raise RuntimeError("Uso: /waf <url|dominio>")
    objetivo = args[0]
    if not objetivo.startswith("http://") and not objetivo.startswith("https://"):
        objetivo = "http://" + objetivo
    return objetivo


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    objetivo = _validarArgs(args)
    comando = [binario, objetivo]

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

    maxBytes = 512 * 1024
    if len(salida.encode("utf-8", errors="ignore")) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado]\n"
    return salida, exitCode
