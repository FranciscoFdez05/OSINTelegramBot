# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

timeoutSeconds = 12
safeEnv = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}

def _resolverBinario() -> str:
    ruta = shutil.which("curl")
    if not ruta:
        raise RuntimeError("No se encontró 'curl' en PATH.")
    return ruta

def _validarArgs(args: List[str]) -> List[str]:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /ipinfo <ip>")
    return args

def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    argsValidados = _validarArgs(args)
    target = argsValidados[0]
    comando = [binario, "-fsSL", f"https://ipinfo.io/{target}/json"]

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
