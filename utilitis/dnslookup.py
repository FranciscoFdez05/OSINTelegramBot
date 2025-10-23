# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

defaultArgs = ["+nocmd", "+noall", "+answer"]
timeoutSeconds = 15
safeEnv = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}

def _resolverBinario() -> str:
    ruta = shutil.which("dig")
    if not ruta:
        raise RuntimeError("No se encontró 'dig' en PATH.")
    return ruta

def _validarArgs(args: List[str]) -> List[str]:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /dns <dominio>   (ej: /dns example.com)")
    return args

def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    argsValidados = _validarArgs(args)
    # consultamos registros A, MX, TXT con dig +short si quieres más añade opciones
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

    maxBytes = 512 * 1024
    if len(salida.encode("utf-8", errors="ignore")) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado]\n"
    return salida, exitCode
