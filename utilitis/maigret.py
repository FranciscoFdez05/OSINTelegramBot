# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "maigret"
usage = "/maigret <usuario>"
defaultArgs = ["--no-color", "--timeout", "10"]

def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("maigret", ayuda="Instala con: pip install maigret")
    usuario = common.validarUsuario(args, usage)
    comando = [binario] + defaultArgs + [usuario]
    return common.ejecutar(comando, nombre)
