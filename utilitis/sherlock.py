# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "sherlock"
usage = "/sherlock <usuario>"
defaultArgs = ["--timeout", "10", "--print-found"]

def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("sherlock")
    usuario = common.validarUsuario(args, usage)
    comando = [binario] + defaultArgs + [usuario]
    return common.ejecutar(comando, nombre)
