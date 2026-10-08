# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "whatweb"
usage = "/whatweb <url|dominio>"
defaultArgs = ["--color=never", "-a", "3"]

def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("whatweb", ayuda="Instala con: apt install whatweb")
    objetivo = common.validarUrl(args, usage)
    comando = [binario] + defaultArgs + [objetivo]
    return common.ejecutar(comando, nombre)
