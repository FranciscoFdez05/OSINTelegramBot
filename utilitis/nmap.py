# -*- coding: utf-8 -*-
import re
import shutil
import subprocess
from typing import List, Tuple

defaultArgs = ["-Pn", "-T4", "--top-ports", "100", "-sV", "--version-light"]
timeoutSeconds = 180
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}

# dominio, IPv4 o IPv6 simple; sin comodines ni rangos para evitar barridos masivos
objetivoValido = re.compile(r"^[A-Za-z0-9._:-]+$")


def _resolverBinario() -> str:
    ruta = shutil.which("nmap")
    if not ruta:
        raise RuntimeError("No se encontró 'nmap' en PATH. Instala con: apt install nmap")
    return ruta


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /nmap <ip|host>")
    objetivo = args[0]
    if objetivo.startswith("-"):
        raise RuntimeError("Uso: /nmap <ip|host>")
    if "/" in objetivo or "*" in objetivo:
        raise RuntimeError("Solo se permite un host, no rangos ni redes.")
    if not objetivoValido.match(objetivo):
        raise RuntimeError("Objetivo no válido. Uso: /nmap <ip|host>")
    return objetivo


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    objetivo = _validarArgs(args)
    comando = [binario] + defaultArgs + [objetivo]

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
