# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "holehe"
usage = "/holehe <email>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("holehe", ayuda="Instala con: pip install holehe")
    email = common.validarEmail(args, usage)
    comando = [binario, email]
    return common.ejecutar(comando, nombre)
