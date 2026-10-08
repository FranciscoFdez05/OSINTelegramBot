# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "emailrep"
usage = "/emailrep <email>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("curl")
    email = common.validarEmail(args, usage)
    comando = [binario, "-fsSL", "-H", "User-Agent: osint-bot/1.0", f"https://emailrep.io/{email}"]
    return common.ejecutar(comando, nombre)
