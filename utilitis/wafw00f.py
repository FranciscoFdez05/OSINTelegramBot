# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "waf"
usage = "/waf <url|dominio>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("wafw00f", ayuda="Instala con: pip install wafw00f")
    objetivo = common.validarUrl(args, usage)
    comando = [binario, objetivo]
    return common.ejecutar(comando, nombre)
