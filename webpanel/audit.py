# -*- coding: utf-8 -*-
"""Registro de auditoría: una línea JSON por evento (quién, qué comando, argumentos, resultado)."""

import json
import os
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

maxFileBytes = 5 * 1024 * 1024


class Audit:
    def __init__(self, ruta: str):
        self.ruta = ruta
        self.lock = threading.Lock()

    def registrar(self, userId: Optional[int], username: Optional[str], comando: str,
                  args: Optional[List[str]], resultado: str, exitCode: Optional[int] = None,
                  segundos: Optional[float] = None) -> None:
        """resultado: ok | error | ignorado (usuario no autorizado) | denegado (sin rol admin)."""
        entrada: Dict[str, Any] = {
            "t": int(time.time()), "user": userId, "username": username or "",
            "cmd": comando, "args": (args or [])[:10], "result": resultado,
        }
        if exitCode is not None:
            entrada["exit"] = exitCode
        if segundos is not None:
            entrada["seconds"] = round(segundos, 2)
        linea = json.dumps(entrada, ensure_ascii=False)[:2000]
        with self.lock:
            try:
                os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)
                if os.path.exists(self.ruta) and os.path.getsize(self.ruta) > maxFileBytes:
                    os.replace(self.ruta, self.ruta + ".1")
                with open(self.ruta, "a", encoding="utf-8") as f:
                    f.write(linea + "\n")
            except OSError:
                pass

    def ultimos(self, limite: int = 100) -> List[Dict[str, Any]]:
        with self.lock:
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    lineas = deque(f, maxlen=limite)
            except OSError:
                return []
        salida = []
        for linea in reversed(lineas):
            try:
                salida.append(json.loads(linea))
            except ValueError:
                continue
        return salida
