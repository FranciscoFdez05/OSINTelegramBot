# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "phone"
usage = "/phone <+34XXXXXXXXX>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("phoneinfoga", ayuda="Instala con: go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest")
    numero = common.validarTelefono(args, usage)
    comando = [binario, "scan", "-n", numero]
    return common.ejecutar(comando, nombre)
