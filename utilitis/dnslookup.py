# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "dns"
usage = "/dns <dominio>   (ej: /dns example.com)"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("dig")
    dominio = common.validarDominio(args, usage)
    comando = [binario, "+nocmd", "+noall", "+answer", dominio]
    return common.ejecutar(comando, nombre)
