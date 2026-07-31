# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
from typing import List, Tuple

timeoutSeconds = 180
safeEnv = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LC_ALL": "C"}

# primera wordlist disponible (dirb viene instalado en la imagen Docker)
wordlistCandidatas = [
    "/usr/share/dirb/wordlists/common.txt",
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/dirbuster/wordlists/directory-list-2.3-small.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
]


def _resolverBinario() -> str:
    ruta = shutil.which("gobuster")
    if not ruta:
        raise RuntimeError("No se encontró 'gobuster' en PATH. Instala con: apt install gobuster")
    return ruta


def _resolverWordlist() -> str:
    for ruta in wordlistCandidatas:
        if os.path.isfile(ruta):
            return ruta
    raise RuntimeError("No se encontró ninguna wordlist. Instala con: apt install dirb")


def _validarArgs(args: List[str]) -> str:
    if not args or len(args) != 1:
        raise RuntimeError("Uso: /gobuster <url>")
    if args[0].startswith("-"):
        raise RuntimeError("Uso: /gobuster <url>")
    objetivo = args[0]
    if not objetivo.startswith("http://") and not objetivo.startswith("https://"):
        objetivo = "http://" + objetivo
    return objetivo


def run(args: List[str]) -> Tuple[str, int]:
    binario = _resolverBinario()
    wordlist = _resolverWordlist()
    objetivo = _validarArgs(args)
    comando = [
        binario, "dir",
        "-u", objetivo,
        "-w", wordlist,
        "-q", "--no-color",
        "-t", "20",
        "--timeout", "10s",
    ]

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
