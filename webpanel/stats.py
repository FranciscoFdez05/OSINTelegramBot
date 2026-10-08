# -*- coding: utf-8 -*-
"""Estadísticas de uso del bot (contactos, comandos, tiempos). Persisten en config/stats.json."""

import json
import os
import threading
import time
from collections import deque
from typing import Any, Dict, Optional

maxRecent = 50


class Stats:
    def __init__(self, ruta: str):
        self.ruta = ruta
        self.lock = threading.Lock()
        self.startTime = time.time()
        self.users: Dict[str, Dict[str, Any]] = {}
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.recent: deque = deque(maxlen=maxRecent)
        self._cargar()

    def _cargar(self) -> None:
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self.users = datos.get("users", {})
            self.commands = datos.get("commands", {})
            self.recent.extend(datos.get("recent", []))
        except Exception:
            pass

    def _guardar(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"users": self.users, "commands": self.commands,
                           "recent": list(self.recent)}, f)
            os.replace(tmp, self.ruta)
        except Exception:
            pass

    def recordContact(self, userId: Optional[int], username: Optional[str], name: Optional[str],
                      command: str, allowed: bool) -> None:
        if userId is None:
            return
        ahora = int(time.time())
        with self.lock:
            u = self.users.setdefault(str(userId), {"first": ahora, "commands": 0, "denied": 0})
            u["username"] = username or u.get("username") or ""
            u["name"] = name or u.get("name") or ""
            u["last"] = ahora
            u["commands" if allowed else "denied"] += 1
            self.recent.appendleft({"t": ahora, "user": userId, "cmd": command,
                                    "status": "ok" if allowed else "denegado"})
            self._guardar()

    def recordExecution(self, command: str, seconds: float, ok: bool) -> None:
        with self.lock:
            c = self.commands.setdefault(command, {"count": 0, "errors": 0, "seconds": 0.0})
            c["count"] += 1
            c["seconds"] += seconds
            if not ok:
                c["errors"] += 1
                if self.recent and self.recent[0].get("cmd") == command:
                    self.recent[0]["status"] = "error"
            self._guardar()

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            total = sum(c["count"] for c in self.commands.values())
            errores = sum(c["errors"] for c in self.commands.values())
            segundos = sum(c["seconds"] for c in self.commands.values())
            return {
                "uptime": int(time.time() - self.startTime),
                "totalCommands": total,
                "totalErrors": errores,
                "avgSeconds": round(segundos / total, 2) if total else 0,
                "commands": {k: {"count": v["count"], "errors": v["errors"],
                                 "avgSeconds": round(v["seconds"] / v["count"], 2) if v["count"] else 0}
                             for k, v in self.commands.items()},
                "users": json.loads(json.dumps(self.users)),
                "recent": list(self.recent),
            }
