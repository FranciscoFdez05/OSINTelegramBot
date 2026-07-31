# -*- coding: utf-8 -*-
import shutil
import subprocess
from typing import List, Tuple

# emailrep.io API pública (sin key, límite 10 req/día por IP; con key más)
timeoutSeconds = 15
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}


def _resolverBinario() -> str:
    ruta = shutil.which("curl")
    if not ruta:
        raise RuntimeError("No se encontró 'curl' en PATH.")
    return ruta


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /emailrep <email>")
    email = args[0]
    if email.startswith("-"):
        raise RuntimeError("Uso: /emailrep <email>")
    if "@" not in email:
        raise RuntimeError("Uso: /emailrep <email>  (debe contener @)")
    return email


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    email = _validarArgs(args)
    url = f"https://emailrep.io/{email}"
    comando = [binario, "-fsSL", "-H", "User-Agent: osint-bot/1.0", url]

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
