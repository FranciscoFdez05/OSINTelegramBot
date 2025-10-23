# -*- coding: utf-8 -*-
# run(args: List[str]) -> (salida, exitCode)
import shutil
import subprocess
from typing import List, Tuple

defaultArgs = []
timeoutSeconds = 20
safeEnv = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}

def _resolverBinario() -> str:
    ruta = shutil.which("whois")
    if not ruta:
        raise RuntimeError("No se encontró 'whois' en PATH.")
    return ruta

def _validarArgs(args: List[str]) -> List[str]:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /whois <dominio>")
    return args

def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    argsValidados = _validarArgs(args)
    comando = [binario] + defaultArgs + argsValidados

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

    maxBytes = 1 * 1024 * 1024  # 1 MB
    if len(salida.encode("utf-8", errors="ignore")) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado]\n"
    return salida, exitCode
