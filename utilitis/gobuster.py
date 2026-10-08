# -*- coding: utf-8 -*-
import os
from typing import List, Tuple

from utilitis import common

nombre = "gobuster"
usage = "/gobuster <url>"
# primera wordlist disponible (dirb viene instalado en la imagen Docker)
wordlistCandidatas = [
    "/usr/share/dirb/wordlists/common.txt",
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/dirbuster/wordlists/directory-list-2.3-small.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
]


def _resolverWordlist() -> str:
    for ruta in wordlistCandidatas:
        if os.path.isfile(ruta):
            return ruta
    raise RuntimeError("No se encontró ninguna wordlist. Instala con: apt install dirb")


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("gobuster", ayuda="Instala con: apt install gobuster")
    objetivo = common.validarUrl(args, usage)
    wordlist = _resolverWordlist()
    comando = [binario, "dir", "-u", objetivo, "-w", wordlist, "-q", "--no-color", "-t", "20", "--timeout", "10s"]
    return common.ejecutar(comando, nombre)
