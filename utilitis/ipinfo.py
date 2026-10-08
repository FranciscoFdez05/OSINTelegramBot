# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "ipinfo"
usage = "/ipinfo <ip>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("curl")
    ip = common.validarIp(args, usage)
    comando = [binario, "-fsSL", f"https://ipinfo.io/{ip}/json"]
    return common.ejecutar(comando, nombre)
