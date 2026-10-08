# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "dnsrecon"
usage = "/dnsrecon <dominio>"


def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("dnsrecon", ayuda="Instala con: apt install dnsrecon")
    dominio = common.validarDominio(args, usage)
    comando = [binario, "-d", dominio, "-t", "std,brt,srv,axfr"]
    return common.ejecutar(comando, nombre)
