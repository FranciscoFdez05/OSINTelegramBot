# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

timeoutSeconds = 120
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    ruta = shutil.which("holehe")
    if not ruta:
        raise RuntimeError("No se encontró 'holehe' en PATH. Instala con: pip install holehe")
    return ruta


def _validarArgs(args: List[str]) -> List[str]:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /holehe <email>")
    if args[0].startswith("-"):
        raise RuntimeError("Uso: /holehe <email>")
    if "@" not in args[0]:
        raise RuntimeError("Uso: /holehe <email>  (debe contener @)")
    return args


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    argsValidados = _validarArgs(args)
    comando = [binario] + argsValidados

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
