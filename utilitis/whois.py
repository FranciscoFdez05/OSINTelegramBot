# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "whois"
usage = "/whois <dominio|ip>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("whois")
    objetivo = common.validarHost(args, usage)
    comando = [binario, objetivo]
    return common.ejecutar(comando, nombre)
