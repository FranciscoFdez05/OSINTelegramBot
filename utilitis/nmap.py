# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "nmap"
usage = "/nmap <ip|host>"
defaultArgs = ["-Pn", "-T4", "--top-ports", "100", "-sV", "--version-light"]

def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("nmap", ayuda="Instala con: apt install nmap")
    objetivo = common.validarHost(args, usage)
    comando = [binario] + defaultArgs + [objetivo]
    return common.ejecutar(comando, nombre)
