# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

timeoutSeconds = 30
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin:/root/go/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    ruta = shutil.which("phoneinfoga")
    if not ruta:
        raise RuntimeError(
            "No se encontró 'phoneinfoga' en PATH. "
            "Instala con: go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest"
        )
    return ruta


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /phone <numero>  (formato internacional, ej: +34612345678)")
    numero = args[0]
    if numero.startswith("-"):
        raise RuntimeError("Uso: /phone <numero>  (formato internacional, ej: +34612345678)")
    if not numero.startswith("+"):
        raise RuntimeError("El numero debe incluir el prefijo internacional (ej: +34612345678)")
    return numero


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    numero = _validarArgs(args)
    comando = [binario, "scan", "-n", numero]

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
