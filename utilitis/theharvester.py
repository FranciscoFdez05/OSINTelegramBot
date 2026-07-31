# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

# -b all usa todas las fuentes públicas, -l limita resultados para no colgar el bot
defaultArgs = ["-b", "bing,google,baidu,hackertarget,crtsh", "-l", "200"]
timeoutSeconds = 120
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    for nombre in ("theHarvester", "theharvester"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    raise RuntimeError(
        "No se encontró 'theHarvester' en PATH. Instala con: pip install theHarvester"
    )


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /harvester <dominio>")
    dominio = args[0]
    if dominio.startswith("-"):
        raise RuntimeError("Uso: /harvester <dominio>")
    return dominio


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    dominio = _validarArgs(args)
    comando = [binario, "-d", dominio] + defaultArgs

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
