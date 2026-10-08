# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "sslscan"
usage = "/sslscan <host|url>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("sslscan", ayuda="Instala con: apt install sslscan")
    host = common.validarHostOUrl(args, usage)
    comando = [binario, "--no-colour", host]
    return common.ejecutar(comando, nombre)
