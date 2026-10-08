# -*- coding: utf-8 -*-
from typing import List, Tuple

from utilitis import common

nombre = "harvester"
usage = "/harvester <dominio>"
defaultArgs = ["-b", "bing,google,baidu,hackertarget,crtsh", "-l", "200"]

def run(args: List[str]) -> Tuple[str, int]:
    binario = common.resolverBinario("theHarvester", "theharvester", ayuda="Instala con: pip install theHarvester")
    dominio = common.validarDominio(args, usage)
    comando = [binario, "-d", dominio] + defaultArgs
    return common.ejecutar(comando, nombre)
