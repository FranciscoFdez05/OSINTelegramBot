# -*- coding: utf-8 -*-
"""Metadatos EXIF de un fichero que el usuario envía al bot (con exiftool).

No es un comando de texto: main.py descarga el fichero a una ruta propia y llama a analizar(ruta),
así el usuario nunca elige qué ruta del servidor se lee."""

import re
from typing import Tuple

from utilitis import common

nombre = "exif"
usage = "Envía una foto o documento (como archivo, para conservar los metadatos)"

_latRe = re.compile(r"^\S*\s*GPS Latitude\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$", re.M)
_lonRe = re.compile(r"^\S*\s*GPS Longitude\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$", re.M)


def analizar(ruta: str) -> Tuple[str, int]:
    binario = common.resolverBinario("exiftool", "exiftool.pl",
                                     ayuda="Instala con: apt install libimage-exiftool-perl")
    # -a duplicados, -u desconocidos, -G1 grupo de cada etiqueta, -c coordenadas en decimal con signo
    # "--" evita que una ruta se interprete como opción
    salida, codigo = common.ejecutar([binario, "-a", "-u", "-G1", "-c", "%+.6f", "--", ruta], nombre)
    lat, lon = _latRe.search(salida), _lonRe.search(salida)
    if lat and lon:
        salida += f"\nUbicación GPS: https://www.google.com/maps?q={lat.group(1)},{lon.group(1)}\n"
    return salida, codigo
