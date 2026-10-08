# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "nikto"
usage = "/nikto <url|ip>"
defaultArgs = ["-nointeractive", "-maxtime", "90s"]

def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("nikto", ayuda="Instala con: apt install nikto")
    objetivo = common.validarUrl(args, usage)
    comando = [binario, "-h", objetivo] + defaultArgs
    return common.ejecutar(comando, nombre)
