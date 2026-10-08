# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "h8mail"
usage = "/h8mail <email>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("h8mail", ayuda="Instala con: pip install h8mail")
    email = common.validarEmail(args, usage)
    comando = [binario, "-t", email]
    return common.ejecutar(comando, nombre)
