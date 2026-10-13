# -*- coding: utf-8 -*-
"""/recon <dominio>: lanza varias herramientas sobre el mismo dominio y junta todo en un único informe."""

from typing import List, Tuple

from utilitis import common, whois, dnslookup, dnsrecon, whatweb, sslscan

nombre = "recon"
usage = "/recon <dominio>"

# (etiqueta en el informe, función que ejecuta). Se corren en este orden.
pasos = [
    ("whois", whois.run),
    ("dns", dnslookup.run),
    ("dnsrecon", dnsrecon.run),
    ("whatweb", whatweb.run),
    ("sslscan", sslscan.run),
]


def run(args: List[str]) -> Tuple[str, int]:
    dominio = common.validarDominio(args, usage)
    partes: List[str] = []
    peorCodigo = 0
    for etiqueta, fn in pasos:
        trabajo = common.trabajoActual.get()
        if trabajo is not None and trabajo.cancelado:
            break
        try:
            salida, codigo = fn([dominio])
        except RuntimeError as e:
            salida, codigo = f"[no disponible: {e}]\n", 1
        except Exception as e:  # una herramienta que falla no debe tumbar el informe entero
            salida, codigo = f"[error: {type(e).__name__} {e}]\n", 1
        if codigo != 0:
            peorCodigo = codigo
        partes.append(f"===== {etiqueta} =====\n{salida.strip()}\n")
    informe = f"Informe recon de {dominio}\n\n" + "\n".join(partes)
    return informe, peorCodigo
