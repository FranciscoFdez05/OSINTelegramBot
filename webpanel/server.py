# -*- coding: utf-8 -*-
"""Panel de control web del bot (solo librería estándar).

Se arranca en un hilo desde main.py. Recibe un diccionario de callbacks (`api`) para
no depender de main.py:
  getUsers() -> (allowed, admins)   addUser(id) -> bool   delUser(id) -> bool
  getToken() -> str|None            setToken(token)       restart()
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from log.logEvent import logEvent
from version import __version__
from webpanel import updater
from webpanel.audit import Audit
from webpanel.stats import Stats

pageFile = Path(__file__).resolve().parent / "index.html"
tokenRegex = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{30,}$")
sessionTtl = 8 * 3600


pbkdfIter = 600_000


def hashPassword(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, pbkdfIter)
    return f"pbkdf2${pbkdfIter}${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"


def verificarPassword(password: str, almacenado: str) -> bool:
    try:
        _, iters, salt, esperado = almacenado.split("$")
        h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt), int(iters))
        return hmac.compare_digest(h, base64.b64decode(esperado))
    except Exception:
        return False


def cargarPasswordHash(configDir: str) -> str:
    """Devuelve el hash de la contraseña del panel. Orden de origen:
    PANEL_PASSWORD (env) > config/panelPassword.txt > se genera una aleatoria.
    El fichero solo guarda el hash; si contiene texto plano (puesto a mano para cambiar la
    contraseña) se convierte a hash y se reescribe."""
    env = os.environ.get("PANEL_PASSWORD")
    if env:
        return hashPassword(env)
    ruta = os.path.join(configDir, "panelPassword.txt")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            valor = f.read().strip()
    except OSError:
        valor = ""
    if valor.startswith("pbkdf2$"):
        return valor
    nuevo = valor or secrets.token_urlsafe(12)
    almacenado = hashPassword(nuevo)
    try:
        os.makedirs(configDir, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(almacenado + "\n")
    except OSError:
        pass
    if valor:
        print(f"[PANEL] La contraseña de {ruta} estaba en texto plano; ahora se guarda hasheada.")
    else:
        print(f"[PANEL] Contraseña generada (solo se muestra ahora, se guarda hasheada): {nuevo}")
    return almacenado


def enmascarar(token: Optional[str]) -> str:
    if not token:
        return ""
    return token.split(":")[0] + ":" + "*" * 8 + token[-4:]


def crearServidor(host: str, port: int, passwordHash: str, stats: Stats, audit: Audit, api: Dict[str, Callable]):
    usuario = os.environ.get("PANEL_USER", "").strip()  # vacío = solo contraseña
    sesiones: Dict[str, float] = {}
    lockSesiones = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "OsintPanel"

        def log_message(self, fmt, *args):  # silenciar el log por stderr
            pass

        # --- utilidades ---
        def _enviar(self, codigo: int, cuerpo: bytes, tipo: str, extra: Optional[Dict[str, str]] = None):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(cuerpo)

        def _json(self, codigo: int, datos: Any, extra: Optional[Dict[str, str]] = None):
            self._enviar(codigo, json.dumps(datos).encode("utf-8"), "application/json", extra)

        def _sesion(self) -> Optional[str]:
            c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            sid = c["sid"].value if "sid" in c else None
            if not sid:
                return None
            with lockSesiones:
                caduca = sesiones.get(sid)
                if caduca and caduca > time.time():
                    return sid
                sesiones.pop(sid, None)
            return None

        def _body(self) -> Dict[str, Any]:
            try:
                n = min(int(self.headers.get("Content-Length", "0")), 4096)
                datos = json.loads(self.rfile.read(n) or b"{}")
                return datos if isinstance(datos, dict) else {}
            except Exception:
                return {}

        # --- rutas ---
        def do_GET(self):
            if self.path == "/":
                self._enviar(200, pageFile.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/health":
                # Sin sesión: lo usa el healthcheck de Docker. No expone nada sensible.
                self._json(200, {"ok": True, "version": __version__})
            elif self.path.split("?")[0] == "/api/update":
                if not self._sesion():
                    return self._json(401, {"error": "no autenticado"})
                self._json(200, updater.estado(forzar="force=1" in self.path))
            elif self.path == "/api/state":
                if not self._sesion():
                    return self._json(401, {"error": "no autenticado"})
                self._json(200, self._estado())
            else:
                self._json(404, {"error": "no encontrado"})

        def do_POST(self):
            # Cabecera personalizada: un formulario de otro sitio no puede enviarla (anti-CSRF)
            if self.headers.get("X-Panel") != "1":
                return self._json(403, {"error": "petición no válida"})
            datos = self._body()

            if self.path == "/api/login":
                okPass = verificarPassword(str(datos.get("password", "")), passwordHash)
                okUser = hmac.compare_digest(str(datos.get("user", "")).encode(), usuario.encode()) if usuario else True
                if not (okPass and okUser):
                    time.sleep(1)
                    logEvent(f"Panel: login fallido desde {self.client_address[0]}")
                    return self._json(401, {"error": "usuario o contraseña incorrectos" if usuario else "contraseña incorrecta"})
                sid = secrets.token_urlsafe(32)
                with lockSesiones:
                    sesiones[sid] = time.time() + sessionTtl
                logEvent(f"Panel: login correcto desde {self.client_address[0]}")
                return self._json(200, {"ok": True},
                                  {"Set-Cookie": f"sid={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age={sessionTtl}"})

            sid = self._sesion()
            if not sid:
                return self._json(401, {"error": "no autenticado"})

            if self.path == "/api/logout":
                with lockSesiones:
                    sesiones.pop(sid, None)
                return self._json(200, {"ok": True}, {"Set-Cookie": "sid=; Max-Age=0; Path=/"})

            if self.path in ("/api/users/add", "/api/users/del"):
                try:
                    uid = int(str(datos.get("id", "")).strip())
                    if uid <= 0:
                        raise ValueError
                except ValueError:
                    return self._json(400, {"error": "ID de Telegram no válido"})
                if self.path.endswith("add"):
                    ok = api["addUser"](uid)
                    logEvent(f"Panel: add usuario {uid} ({'nuevo' if ok else 'ya existía'})")
                    return self._json(200, {"ok": True, "msg": f"Usuario {uid} autorizado" if ok else f"{uid} ya estaba autorizado"})
                if uid in api["getUsers"]()[1]:
                    return self._json(400, {"error": "No se puede eliminar a un administrador"})
                ok = api["delUser"](uid)
                logEvent(f"Panel: del usuario {uid} ({'eliminado' if ok else 'no estaba'})")
                return self._json(200, {"ok": True, "msg": f"Usuario {uid} eliminado" if ok else f"{uid} no estaba autorizado"})

            if self.path == "/api/token":
                token = str(datos.get("token", "")).strip()
                if not tokenRegex.match(token):
                    return self._json(400, {"error": "Formato de token no válido (123456:ABC...)"})
                api["setToken"](token)
                logEvent("Panel: token del bot actualizado")
                return self._json(200, {"ok": True, "msg": "Token guardado. Reinicia el bot para aplicarlo."})

            if self.path == "/api/update/start":
                ok, msg = updater.iniciar()
                logEvent(f"Panel: actualización {'iniciada' if ok else 'rechazada'}: {msg}")
                return self._json(200, {"ok": True, "msg": msg}) if ok else self._json(409, {"error": msg})

            if self.path == "/api/restart":
                logEvent("Panel: reinicio solicitado")
                self._json(200, {"ok": True, "msg": "Reiniciando..."})
                threading.Timer(0.5, api["restart"]).start()
                return

            self._json(404, {"error": "no encontrado"})

        def _estado(self) -> Dict[str, Any]:
            snap = stats.snapshot()
            allowed, admins = api["getUsers"]()
            ids = set(map(str, allowed)) | set(snap["users"].keys())
            filas = []
            for uid in ids:
                s = snap["users"].get(uid, {})
                filas.append({"id": int(uid), "username": s.get("username", ""), "name": s.get("name", ""),
                              "allowed": int(uid) in allowed, "admin": int(uid) in admins,
                              "commands": s.get("commands", 0), "denied": s.get("denied", 0),
                              "last": s.get("last")})
            filas.sort(key=lambda r: r["last"] or 0, reverse=True)
            return {"version": __version__, "users": filas, "token": enmascarar(api["getToken"]()),
                    "audit": audit.ultimos(100),
                    "perf": {k: snap[k] for k in ("uptime", "totalCommands", "totalErrors", "avgSeconds", "commands", "recent")}}

    return ThreadingHTTPServer((host, port), Handler)


def arrancarPanel(configDir: str, stats: Stats, audit: Audit, api: Dict[str, Callable]) -> Optional[threading.Thread]:
    if os.environ.get("PANEL_ENABLED", "1") == "0":
        return None
    host = os.environ.get("PANEL_HOST", "0.0.0.0")
    port = int(os.environ.get("PANEL_PORT", "6050"))
    passwordHash = cargarPasswordHash(configDir)
    try:
        servidor = crearServidor(host, port, passwordHash, stats, audit, api)
    except OSError as e:
        logEvent(f"Panel: no se pudo abrir {host}:{port}: {e}")
        print(f"[PANEL] No se pudo abrir {host}:{port}: {e}")
        return None
    hilo = threading.Thread(target=servidor.serve_forever, name="panel", daemon=True)
    hilo.start()
    logEvent(f"Panel web escuchando en http://{host}:{port}")
    print(f"[PANEL] http://{host}:{port}")
    return hilo
