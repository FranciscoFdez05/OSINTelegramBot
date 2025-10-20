# -*- coding: utf-8 -*-
# Módulo de ejecución para el comando /sherlock

import shutil
import subprocess
from typing import List, Tuple

# configuración específica de sherlock
defaultArgs = ["--timeout", "10", "--print-found"]
timeoutSeconds = 180

# entorno mínimo y seguro
safeEnv = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
}

def _resolverBinario() -> str:
    ruta = shutil.which("sherlock")
    if not ruta:
        raise RuntimeError("No se encontró el binario de sherlock en PATH.")
    return ruta

def _validarArgs(args: List[str]) -> List[str]:
    # solo permite un argumento y que no empiece por '-'
    if not args or len(args) != 1 or args[0].startswith("-"):
        raise RuntimeError("Uso: /sherlock <usuario_sin_flags>")
    return args

def run(args: List[str]) -> Tuple[str, int]:

    # Ejecuta sherlock de forma segura.
    # Devuelve (salida_texto, exit_code).
    # Lanza RuntimeError si hay problemas de validación o binario ausente.

    binario = _resolverBinario()
    argsValidados = _validarArgs(args)
    comando = [binario] + defaultArgs + argsValidados

    resultado = subprocess.run(
        comando,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeoutSeconds,
        text=True,
        env=safeEnv,
    )

    salida = resultado.stdout or ""
    exitCode = resultado.returncode

    # limitar salida para no reventar memoria en escenarios tóxicos
    maxBytes = 5 * 1024 * 1024  # 5 MB
    if len(salida.encode("utf-8", errors="ignore")) > maxBytes:
        salida = salida[:maxBytes] + "\n[output truncado por límite de tamaño]\n"

    return salida, exitCode
