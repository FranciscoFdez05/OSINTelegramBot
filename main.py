#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requisitos: python>=3.9, python-telegram-bot>=20.0

import asyncio
import io
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Optional, List, Callable, Tuple, Dict

from telegram import (BotCommand, BotCommandScopeChat, BotCommandScopeDefault, ForceReply, InlineKeyboardButton,
                      InlineKeyboardMarkup, Update, __version__ as tgVersion)
from telegram.ext import (ApplicationBuilder, ApplicationHandlerStop, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, TypeHandler, filters)

from log.logEvent import logEvent
from webpanel.audit import Audit
from webpanel.stats import Stats
from webpanel.server import arrancarPanel
from utilitis import sherlock, whois, ipinfo, dnslookup
from utilitis import nmap, gobuster, holehe, theharvester, h8mail, emailrep
from utilitis import maigret, dnsrecon, whatweb, nikto, sslscan, wafw00f, phoneinfoga, recon
from utilitis import exif
from utilitis import common

commandHandlers = {
    # Red y dominios
    "whois":     whois.run,
    "ipinfo":    ipinfo.run,
    "dns":       dnslookup.run,
    "nmap":      nmap.run,
    "gobuster":  gobuster.run,
    "harvester": theharvester.run,
    "dnsrecon":  dnsrecon.run,
    "recon":     recon.run,
    # Web
    "whatweb":   whatweb.run,
    "nikto":     nikto.run,
    "sslscan":   sslscan.run,
    "waf":       wafw00f.run,
    # Usuarios
    "sherlock":  sherlock.run,
    "maigret":   maigret.run,
    # Email
    "holehe":    holehe.run,
    "h8mail":    h8mail.run,
    "emailrep":  emailrep.run,
    # Teléfono
    "phone":     phoneinfoga.run,
}

# CONFIGURACIÓN
configDir = os.environ.get("CONFIG_DIR", "config")
botTokenFile = os.path.join(configDir, "botToken.txt")
allowedUsersFile = os.path.join(configDir, "usersIDs.txt")
adminUsersFile = os.path.join(configDir, "adminIDs.txt")

# límite de caracteres por mensaje (texto plano)
maxPlainChunk = 3800
# por encima de esto la salida se manda como fichero .txt y en el chat solo va un resumen
maxTextoChat = 6000
lineasResumen = 15

# comandos que lanzan procesos largos o pesados: comparten un número limitado de plazas
comandosPesados = {"nmap", "gobuster", "harvester", "dnsrecon", "nikto", "sherlock", "maigret", "holehe", "h8mail",
                   "recon"}
maxTrabajosPesados = max(1, int(os.environ.get("MAX_HEAVY_JOBS", "3")))
logFilePath = os.path.join("log", "logfile.log")

# progreso vivo: cada cuántos segundos se edita el «Ejecutando…»
segundosProgreso = 5
# caché de resultados: segundos que se reutiliza una misma consulta (0 la desactiva)
cacheTtl = max(0, int(os.environ.get("CACHE_TTL", "300")))
cacheMaxEntradas = 200
# /history: cuántas consultas distintas se muestran
maxHistorial = 8
# herramientas que se ofrecen como botones según el tipo de objetivo
pivotesPorTipo = {
    "dominio": ["whois", "dns", "whatweb", "sslscan", "harvester", "recon"],
    "ip":      ["whois", "ipinfo", "nmap"],
    "email":   ["holehe", "h8mail", "emailrep"],
    "phone":   ["phone"],
    "url":     ["whatweb", "waf", "sslscan", "nikto", "gobuster"],
}
etiquetasBoton = {"dns": "DNS", "whatweb": "WhatWeb", "sslscan": "SSL", "harvester": "Harvester",
                  "ipinfo": "IPinfo", "dnsrecon": "DNSrecon", "waf": "WAF", "h8mail": "h8mail"}


# CARGA DE CONFIG
def leerFicheroTexto(ruta: str) -> Optional[str]:
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception:
        return None

def cargarBotToken(ruta: str) -> Optional[str]:
    contenido = leerFicheroTexto(ruta)
    if not contenido:
        return None
    return contenido.splitlines()[0].strip()

def cargarAllowedUserIds(ruta: str) -> List[int]:
    texto = leerFicheroTexto(ruta)
    if not texto:
        return []
    texto = texto.replace(",", "\n")
    ids: List[int] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        try:
            ids.append(int(linea))
        except ValueError:
            continue
    return ids

def cargarAdminUserIds(ruta: str, porDefecto: List[int]) -> List[int]:
    """Admins del bot. Si no hay config/adminIDs.txt, el primer usuario
    autorizado es el administrador."""
    ids = cargarAllowedUserIds(ruta)
    if ids:
        return ids
    return porDefecto[:1]

botToken = cargarBotToken(botTokenFile)
allowedUserIds = cargarAllowedUserIds(allowedUsersFile)
adminUserIds = cargarAdminUserIds(adminUsersFile, allowedUserIds)
# allowedUserIds lo modifican el bot y el panel (hilos distintos)
lockUsuarios = threading.Lock()

def usuariosPermitidos() -> List[int]:
    with lockUsuarios:
        return list(allowedUserIds)

def avisarConfig() -> None:
    """Con el panel web, token y usuarios pueden configurarse después de arrancar."""
    if not botToken:
        logEvent(f"AVISO: falta token del bot. Ponlo en el panel web o en {botTokenFile}.")
    if not allowedUserIds:
        logEvent(f"AVISO: no hay usuarios autorizados. Añádelos en el panel web o en {allowedUsersFile}.")

avisarConfig()

stats = Stats(os.path.join(configDir, "stats.json"))
audit = Audit(os.path.join("log", "audit.jsonl"))


# UTILIDADES
def escribirLog(mensaje: str) -> None:
    ts = datetime.utcnow().isoformat()
    try:
        os.makedirs(os.path.dirname(logFilePath), exist_ok=True)
        with open(logFilePath, "a", encoding="utf-8") as f:
            f.write(f"{ts} {mensaje}\n")
    except Exception:
        logEvent(f"{ts} (log fail) {mensaje}")
        #print(f"{ts} (log fail) {mensaje}")
        

def usuarioPermitido(userId: int) -> bool:
    with lockUsuarios:
        return userId in allowedUserIds

def usuarioAdmin(userId: int) -> bool:
    return userId in adminUserIds


# GESTIÓN DE USUARIOS AUTORIZADOS
def parsearUserId(texto: str) -> Optional[int]:
    texto = texto.strip().lstrip("@")
    try:
        valor = int(texto)
    except ValueError:
        return None
    if valor <= 0:
        return None
    return valor

def anadirUsuarioPermitido(userId: int) -> bool:
    """Añade el userId a la whitelist (memoria + fichero). False si ya existía."""
    with lockUsuarios:
        if userId in allowedUserIds:
            return False
        os.makedirs(configDir, exist_ok=True)
        contenido = leerFicheroTexto(allowedUsersFile) or ""
        sufijo = "" if (not contenido or contenido.endswith("\n")) else "\n"
        with open(allowedUsersFile, "a", encoding="utf-8") as f:
            f.write(f"{sufijo}{userId}\n")
        allowedUserIds.append(userId)
    refrescarMenu(userId)
    return True

def eliminarUsuarioPermitido(userId: int) -> bool:
    """Elimina el userId de la whitelist (memoria + fichero). False si no estaba."""
    with lockUsuarios:
        if userId not in allowedUserIds:
            return False
        allowedUserIds.remove(userId)
        os.makedirs(configDir, exist_ok=True)
        lineas = (leerFicheroTexto(allowedUsersFile) or "").splitlines()
        conservadas: List[str] = []
        for linea in lineas:
            limpia = linea.strip()
            if limpia.startswith("#"):
                conservadas.append(linea)
                continue
            # una línea puede llevar varios ids separados por comas
            restantes = [t.strip() for t in limpia.replace(",", "\n").splitlines() if t.strip()]
            restantes = [t for t in restantes if parsearUserId(t) != userId]
            conservadas.extend(restantes)
        with open(allowedUsersFile, "w", encoding="utf-8") as f:
            f.write("\n".join(conservadas).strip() + "\n")
    refrescarMenu(userId)
    return True

def guardarBotToken(token: str) -> None:
    os.makedirs(configDir, exist_ok=True)
    with open(botTokenFile, "w", encoding="utf-8") as f:
        f.write(token.strip() + "\n")

def reiniciarProceso() -> None:
    """Relanza el proceso para aplicar un nuevo token."""
    logEvent("Reiniciando proceso")
    os.execv(sys.executable, [sys.executable] + sys.argv)

def registrarContacto(update: Update, comando: str, permitido: bool) -> None:
    u = update.effective_user
    if u:
        stats.recordContact(u.id, u.username, u.full_name, comando, permitido)

async def filtroAcceso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Primer filtro de todo update: si el usuario no está autorizado no se procesa nada
    (ni respuesta ni handlers). Solo se anota el contacto para poder autorizarlo desde el panel."""
    u = update.effective_user
    if u and usuarioPermitido(u.id):
        return
    texto = (update.effective_message.text or "") if update.effective_message else ""
    comando = texto.split()[0].lstrip("/").split("@")[0] if texto.startswith("/") and texto.split() else "(mensaje)"
    if u:
        stats.recordContact(u.id, u.username, u.full_name, comando, False)
        audit.registrar(u.id, u.username, comando, None, "ignorado")
        logEvent(f"Ignorado user_id={u.id} (no autorizado)")
    raise ApplicationHandlerStop

def chunkText(texto: str, maxLen: int) -> List[str]:
    if len(texto) <= maxLen:
        return [texto]
    partes: List[str] = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + maxLen, len(texto))
        corte = texto.rfind("\n", inicio, fin)
        if corte == -1:
            corte = texto.rfind(" ", inicio, fin)
        if corte == -1 or corte <= inicio:
            corte = fin
        partes.append(texto[inicio:corte])
        inicio = corte
    return partes

async def sendLongPlain(context: ContextTypes.DEFAULT_TYPE, chatId: int, texto: str,
                        markup: Optional[InlineKeyboardMarkup] = None) -> None:
    partes = chunkText(texto, maxPlainChunk)
    total = len(partes)
    for idx, parte in enumerate(partes, start=1):
        pref = f"[{idx}/{total}] " if total > 1 else ""
        await context.bot.send_message(chat_id=chatId, text=pref + parte, disable_web_page_preview=True,
                                       reply_markup=markup if idx == total else None)

def nombreFichero(commandName: str, args: List[str]) -> str:
    objetivo = re.sub(r"[^A-Za-z0-9._@+-]", "_", "_".join(args))[:60] or "salida"
    return f"{commandName}_{objetivo}_{datetime.utcnow():%Y%m%d-%H%M%S}.txt"

def resumenSalida(cabecera: str, salida: str) -> str:
    lineas = salida.splitlines()
    tam = len(salida.encode("utf-8"))
    tamTxt = f"{tam / 1024:.0f} KB" if tam < 1024 * 1024 else f"{tam / (1024 * 1024):.1f} MB"
    texto = f"{cabecera}: {len(lineas)} líneas, {tamTxt}. Completa en el fichero adjunto."
    encontrados = sum(1 for l in lineas if l.lstrip().startswith("[+]"))
    if encontrados:
        texto += f"\nResultados [+]: {encontrados}"
    vista = "\n".join(lineas[:lineasResumen])[:maxPlainChunk - len(texto) - 10]
    return f"{texto}\n\n{vista}\n…"

async def responder(context: ContextTypes.DEFAULT_TYPE, chatId: int, texto: str, msg=None,
                    markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """Edita el mensaje de progreso si lo hay; si no se puede editar (o no hay), manda uno nuevo."""
    if msg is not None:
        try:
            await msg.edit_text(texto, reply_markup=markup, disable_web_page_preview=True)
            return
        except Exception as e:
            logEvent(f"[DEBUG] no se pudo editar el mensaje de progreso: {type(e).__name__} {e}")
    await context.bot.send_message(chat_id=chatId, text=texto, disable_web_page_preview=True, reply_markup=markup)

async def enviarSalida(context: ContextTypes.DEFAULT_TYPE, chatId: int, commandName: str, args: List[str],
                       cabecera: str, salida: str, msg=None,
                       markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """Salidas cortas en un único mensaje (el de progreso, ya editado); las medianas en varios;
    las largas como .txt para no inundar el chat (ni chocar con el límite de envíos de Telegram).
    Los botones van en el último mensaje enviado."""
    if len(salida) > maxTextoChat:
        await responder(context, chatId, resumenSalida(cabecera, salida), msg)
        await context.bot.send_document(chat_id=chatId, document=io.BytesIO(salida.encode("utf-8")),
                                        filename=nombreFichero(commandName, args), reply_markup=markup)
        return
    junto = f"{cabecera}\n\n{salida}"
    if len(junto) <= maxPlainChunk:
        await responder(context, chatId, junto, msg, markup)
        return
    await responder(context, chatId, cabecera, msg)
    await sendLongPlain(context, chatId, salida, markup)

def tecladoPivotes(commandName: str, args: List[str]) -> Optional[InlineKeyboardMarkup]:
    """Botones para seguir investigando el mismo objetivo con otras herramientas."""
    if len(args) != 1:
        return None
    tipo = common.detectarTipo(args[0])
    botones = [InlineKeyboardButton(etiquetasBoton.get(c, c.capitalize()), callback_data=f"r|{c}|{args[0]}")
               for c in pivotesPorTipo.get(tipo or "", []) if c != commandName]
    # callback_data admite 64 bytes como máximo
    botones = [b for b in botones if len(b.callback_data.encode("utf-8")) <= 64]
    if not botones:
        return None
    return InlineKeyboardMarkup([botones[i:i + 3] for i in range(0, len(botones), 3)])

def makeHandler(commandName: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        usuario = update.effective_user
        chatId = update.effective_chat.id
        userId = usuario.id if usuario else None
        userName = usuario.username if usuario and usuario.username else "(sin-username)"

        logEvent(f"Comando recibido: /{commandName} por user_id={userId} chat_id={chatId} username={userName}")
        #print(f"[DEBUG] input user: /{commandName} {' '.join(context.args) if context.args else '(sin-args)'} from user_id={userId}")

        if not usuarioPermitido(userId):  # defensa extra; filtroAcceso ya lo descarta
            return
        registrarContacto(update, commandName, True)

        if commandName not in commandHandlers:
            await context.bot.send_message(chat_id=chatId, text="Comando no permitido.", disable_web_page_preview=True)
            logEvent(f"[DEBUG] comando no permitido: {commandName}")
            return

        args = list(context.args or [])
        if not args:
            # pulsado desde el menú: Telegram lo envía sin argumento, así que se pide aparte
            await pedirArgumento(update, context, commandName)
            return
        await ejecutarComando(update, context, commandName, args)

    return handler

def argumentoDe(commandName: str) -> str:
    """El <argumento> que espera el comando, sacado de su descripción en el menú."""
    for c, d in menuComandos:
        if c == commandName and d.startswith("<"):
            return d.split(">", 1)[0] + ">"
    return "<argumento>"

async def pedirArgumento(update: Update, context: ContextTypes.DEFAULT_TYPE, commandName: str) -> None:
    context.user_data["pendiente"] = commandName
    arg = argumentoDe(commandName)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"/{commandName}: envía {arg} (o /cancel para cancelar)",
        reply_markup=ForceReply(selective=True, input_field_placeholder=arg.strip("<>")),
        disable_web_page_preview=True,
    )

async def argumentoHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Texto suelto: si había un comando esperando argumento, se ejecuta con él;
    si no, se detecta qué es (email, IP, dominio, teléfono, URL) y se sugieren herramientas."""
    texto = (update.effective_message.text or "").strip()
    commandName = context.user_data.pop("pendiente", None)
    if not commandName:
        await sugerirHerramientas(update, context, texto)
        return
    args = texto.split()
    if not args:
        return
    registrarContacto(update, commandName, True)
    await ejecutarComando(update, context, commandName, args)

NOMBRES_TIPO = {"dominio": "un dominio", "ip": "una IP", "email": "un email", "phone": "un teléfono", "url": "una URL"}

async def sugerirHerramientas(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str) -> None:
    tipo = common.detectarTipo(texto)
    if not tipo:
        return
    markup = tecladoPivotes("", [texto])
    if markup is None:
        return
    registrarContacto(update, "(autodetección)", True)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"Parece {NOMBRES_TIPO[tipo]}: {texto}\n¿Qué quieres hacer?",
                                   reply_markup=markup, disable_web_page_preview=True)

async def pivoteHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pulsación de un botón inline (pivotar desde un resultado, autodetección o /history)."""
    query = update.callback_query
    partes = (query.data or "").split("|", 2)
    if len(partes) != 3 or partes[0] != "r" or partes[1] not in commandHandlers:
        await query.answer()
        return
    _, commandName, objetivo = partes
    await query.answer(f"/{commandName} {objetivo}"[:200])
    registrarContacto(update, commandName, True)
    await ejecutarComando(update, context, commandName, [objetivo])

# HISTORIAL
def haceCuanto(segundos: float) -> str:
    segundos = int(max(0, segundos))
    if segundos < 90:
        return f"{segundos}s"
    if segundos < 5400:
        return f"{round(segundos / 60)} min"
    if segundos < 129600:
        return f"{round(segundos / 3600)} h"
    return f"{round(segundos / 86400)} d"

def consultasRecientes(userId: int) -> List[dict]:
    """Últimas consultas del usuario sin repetir (más recientes primero), leídas de audit.jsonl."""
    vistas = set()
    recientes = []
    for e in audit.ultimos(1000):
        if e.get("user") != userId or e.get("cmd") not in commandHandlers or e.get("result") not in ("ok", "error"):
            continue
        clave = (e["cmd"], tuple(e.get("args") or []))
        if clave in vistas or not e.get("args"):
            continue
        vistas.add(clave)
        recientes.append(e)
        if len(recientes) >= maxHistorial:
            break
    return recientes

async def historyHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    usuario = update.effective_user
    chatId = update.effective_chat.id
    registrarContacto(update, "history", True)
    recientes = consultasRecientes(usuario.id) if usuario else []
    if not recientes:
        await context.bot.send_message(chat_id=chatId, text="Aún no hay consultas en tu historial.",
                                       disable_web_page_preview=True)
        return
    ahora = time.time()
    lineas = []
    filas = []
    for i, e in enumerate(recientes, start=1):
        objetivo = " ".join(e["args"])
        lineas.append(f"{i}. /{e['cmd']} {objetivo}  ·  hace {haceCuanto(ahora - e.get('t', ahora))}")
        datos = f"r|{e['cmd']}|{e['args'][0]}"
        if len(e["args"]) == 1 and len(datos.encode("utf-8")) <= 64:
            filas.append([InlineKeyboardButton(f"{i}. /{e['cmd']} {objetivo}"[:60], callback_data=datos)])
    await context.bot.send_message(chat_id=chatId, text="Tus últimas consultas (toca una para repetirla):\n\n" + "\n".join(lineas),
                                   reply_markup=InlineKeyboardMarkup(filas) if filas else None,
                                   disable_web_page_preview=True)

# CACHÉ DE RESULTADOS: se toca solo desde el bucle de eventos
cacheResultados: Dict[Tuple[str, Tuple[str, ...]], Tuple[float, str, int]] = {}

def cacheObtener(commandName: str, args: List[str]) -> Optional[Tuple[float, str, int]]:
    if not cacheTtl:
        return None
    entrada = cacheResultados.get((commandName, tuple(args)))
    if entrada and time.monotonic() - entrada[0] <= cacheTtl:
        return entrada
    return None

def cacheGuardar(commandName: str, args: List[str], salida: str, exitCode: int) -> None:
    if not cacheTtl or exitCode != 0:
        return
    ahora = time.monotonic()
    if len(cacheResultados) >= cacheMaxEntradas:
        for k in [k for k, v in cacheResultados.items() if ahora - v[0] > cacheTtl]:
            del cacheResultados[k]
        while len(cacheResultados) >= cacheMaxEntradas:
            del cacheResultados[next(iter(cacheResultados))]
    cacheResultados[(commandName, tuple(args))] = (ahora, salida, exitCode)

# TRABAJOS EN CURSO: uno por usuario y plazas limitadas para los pesados.
# Solo se tocan desde el bucle de eventos, así que no necesitan lock.
class TrabajoUsuario:
    def __init__(self, commandName: str) -> None:
        self.commandName = commandName
        self.trabajo = common.Trabajo()
        self.eventoCancelado = asyncio.Event()

    def cancelar(self) -> None:
        self.eventoCancelado.set()
        self.trabajo.cancelar()  # mata el proceso si ya estaba corriendo

trabajosActivos: Dict[int, TrabajoUsuario] = {}
semaforoPesados: Optional[asyncio.Semaphore] = None

async def esperarPlaza(t: TrabajoUsuario) -> bool:
    """Espera una plaza libre para un comando pesado. False si se cancela mientras espera."""
    adquirir = asyncio.ensure_future(semaforoPesados.acquire())
    cancelado = asyncio.ensure_future(t.eventoCancelado.wait())
    await asyncio.wait({adquirir, cancelado}, return_when=asyncio.FIRST_COMPLETED)
    cancelado.cancel()
    if not adquirir.done():
        adquirir.cancel()
        return False
    if t.eventoCancelado.is_set():
        semaforoPesados.release()
        return False
    return True

async def cancelHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pendiente = context.user_data.pop("pendiente", None)
    t = trabajosActivos.get(update.effective_user.id) if update.effective_user else None
    if t:
        t.cancelar()
        texto = f"Cancelando /{t.commandName}…"
    elif pendiente:
        texto = f"/{pendiente} cancelado."
    else:
        texto = "No había nada pendiente."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=texto, disable_web_page_preview=True)

async def ejecutarComando(update: Update, context: ContextTypes.DEFAULT_TYPE, commandName: str, args: List[str]) -> None:
    usuario = update.effective_user
    chatId = update.effective_chat.id
    userId = usuario.id if usuario else None
    context.user_data.pop("pendiente", None)

    enCurso = trabajosActivos.get(userId)
    if enCurso:
        await context.bot.send_message(chat_id=chatId, text=f"Ya tienes /{enCurso.commandName} en curso. "
                                       "Espera a que termine o usa /cancel.", disable_web_page_preview=True)
        return
    t = trabajosActivos[userId] = TrabajoUsuario(commandName)
    pesado = commandName in comandosPesados
    try:
        if pesado and not semaforoPesados.locked():
            await semaforoPesados.acquire()  # hay plaza: se toma sin esperar
        elif pesado:
            await context.bot.send_message(chat_id=chatId, text=f"🕒 /{commandName} en cola: hay "
                                           f"{maxTrabajosPesados} trabajos pesados en curso.", disable_web_page_preview=True)
            if not await esperarPlaza(t):
                audit.registrar(userId, usuario.username, commandName, args, "cancelado")
                await context.bot.send_message(chat_id=chatId, text=f"/{commandName} cancelado.", disable_web_page_preview=True)
                return
        try:
            await ejecutarTrabajo(update, context, commandName, args, t)
        finally:
            if pesado:
                semaforoPesados.release()
    finally:
        trabajosActivos.pop(userId, None)

async def mantenerProgreso(msg, commandName: str) -> None:
    """Edita el «Ejecutando…» con el tiempo transcurrido hasta que se cancele la tarea."""
    inicio = time.monotonic()
    while True:
        await asyncio.sleep(segundosProgreso)
        try:
            await msg.edit_text(f"⏳ Ejecutando /{commandName}… {int(time.monotonic() - inicio)}s "
                                "(/cancel para detenerlo)", disable_web_page_preview=True)
        except Exception:
            pass  # límite de Telegram o mensaje borrado: se sigue sin actualizar

async def ejecutarTrabajo(update: Update, context: ContextTypes.DEFAULT_TYPE, commandName: str, args: List[str],
                          t: TrabajoUsuario) -> None:
    usuario = update.effective_user
    chatId = update.effective_chat.id
    userId = usuario.id if usuario else None

    enCache = cacheObtener(commandName, args)
    if enCache:
        antiguedad = time.monotonic() - enCache[0]
        audit.registrar(userId, usuario.username, commandName, args, "ok", enCache[2], 0)
        cabecera = f"Salida de {commandName} (exit {enCache[2]}) · en caché, de hace {haceCuanto(antiguedad)}"
        await enviarSalida(context, chatId, commandName, args, cabecera, enCache[1],
                           markup=tecladoPivotes(commandName, args))
        logEvent(f"[DEBUG] /{commandName} servido desde caché a user_id={userId}")
        return

    msg = await context.bot.send_message(chat_id=chatId, text=f"⏳ Ejecutando /{commandName}…", disable_web_page_preview=True)
    tareaProgreso = asyncio.ensure_future(mantenerProgreso(msg, commandName))
    inicio = time.monotonic()
    # to_thread copia el contexto: así common.ejecutar sabe a qué trabajo pertenece el proceso
    common.trabajoActual.set(t.trabajo)
    try:
        try:
            # en un hilo para no bloquear el bucle de eventos mientras corre la herramienta
            salida, exitCode = await asyncio.to_thread(commandHandlers[commandName], args)
        finally:
            tareaProgreso.cancel()
            await asyncio.gather(tareaProgreso, return_exceptions=True)
    except RuntimeError as e:
        dur = time.monotonic() - inicio
        stats.recordExecution(commandName, dur, False)
        audit.registrar(userId, usuario.username, commandName, args, "error", None, dur)
        await responder(context, chatId, f"Error: {e}", msg)
        logEvent(f"[DEBUG] RuntimeError en {commandName}: {e}")
        return
    except Exception as e:
        dur = time.monotonic() - inicio
        stats.recordExecution(commandName, dur, False)
        audit.registrar(userId, usuario.username, commandName, args, "error", None, dur)
        await responder(context, chatId, f"Error ejecutando /{commandName}: {type(e).__name__} {e}", msg)
        logEvent(f"[DEBUG] Excepción en {commandName}: {type(e).__name__} {e}")
        return

    dur = time.monotonic() - inicio
    if t.trabajo.cancelado:
        audit.registrar(userId, usuario.username, commandName, args, "cancelado", exitCode, dur)
        await responder(context, chatId, f"/{commandName} cancelado.", msg)
        logEvent(f"/{commandName} cancelado por user_id={userId}")
        return
    stats.recordExecution(commandName, dur, exitCode == 0)
    audit.registrar(userId, usuario.username, commandName, args, "ok" if exitCode == 0 else "error", exitCode, dur)

    if not salida:
        salida = f"(sin salida, código de retorno {exitCode})"
    cacheGuardar(commandName, args, salida, exitCode)

    cabecera = f"Salida de {commandName} (exit {exitCode}) · {dur:.0f}s"
    await enviarSalida(context, chatId, commandName, args, cabecera, salida, msg, tecladoPivotes(commandName, args))
    logEvent(f"[DEBUG] Salida de {commandName} enviada en {chatId} ({len(salida)} caracteres)")


# METADATOS EXIF: el usuario envía una foto o documento
# límite de descarga de la API de bots de Telegram
maxBytesArchivo = 20 * 1024 * 1024

async def archivoHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensaje = update.effective_message
    usuario = update.effective_user
    chatId = update.effective_chat.id
    userId = usuario.id if usuario else None
    esFoto = bool(mensaje.photo)
    adjunto = mensaje.photo[-1] if esFoto else mensaje.document
    if adjunto is None:
        return
    nombreOrig = "foto" if esFoto else (adjunto.file_name or "documento")
    registrarContacto(update, "exif", True)

    if userId in trabajosActivos:
        await context.bot.send_message(chat_id=chatId, text=f"Ya tienes /{trabajosActivos[userId].commandName} en curso. "
                                       "Espera a que termine o usa /cancel.", disable_web_page_preview=True)
        return
    if (adjunto.file_size or 0) > maxBytesArchivo:
        await context.bot.send_message(chat_id=chatId, text="El archivo supera los 20 MB, el máximo que permite "
                                       "Telegram a los bots.", disable_web_page_preview=True)
        return

    t = trabajosActivos[userId] = TrabajoUsuario("exif")
    directorio = tempfile.mkdtemp(prefix="exif_")
    inicio = time.monotonic()
    msg = await context.bot.send_message(chat_id=chatId, text="⏳ Analizando metadatos…", disable_web_page_preview=True)
    try:
        ext = re.sub(r"[^A-Za-z0-9]", "", os.path.splitext(nombreOrig)[1])[:8]
        ruta = os.path.join(directorio, "archivo" + (f".{ext}" if ext else ""))
        fichero = await context.bot.get_file(adjunto.file_id)
        await fichero.download_to_drive(ruta)
        common.trabajoActual.set(t.trabajo)
        salida, exitCode = await asyncio.to_thread(exif.analizar, ruta)
    except RuntimeError as e:
        audit.registrar(userId, usuario.username, "exif", [nombreOrig], "error", None, time.monotonic() - inicio)
        await responder(context, chatId, f"Error: {e}", msg)
        return
    except Exception as e:
        stats.recordExecution("exif", time.monotonic() - inicio, False)
        audit.registrar(userId, usuario.username, "exif", [nombreOrig], "error", None, time.monotonic() - inicio)
        await responder(context, chatId, f"Error analizando el archivo: {type(e).__name__} {e}", msg)
        logEvent(f"[DEBUG] Excepción en exif: {type(e).__name__} {e}")
        return
    finally:
        shutil.rmtree(directorio, ignore_errors=True)
        trabajosActivos.pop(userId, None)

    dur = time.monotonic() - inicio
    if t.trabajo.cancelado:
        audit.registrar(userId, usuario.username, "exif", [nombreOrig], "cancelado", exitCode, dur)
        await responder(context, chatId, "/exif cancelado.", msg)
        return
    stats.recordExecution("exif", dur, exitCode == 0)
    audit.registrar(userId, usuario.username, "exif", [nombreOrig], "ok" if exitCode == 0 else "error", exitCode, dur)

    # el grupo [System] es del fichero temporal descargado (ruta, fechas, permisos): no es del original
    salida = "\n".join(l for l in salida.splitlines() if not l.startswith("[System]")).strip()
    if not salida:
        salida = f"(sin metadatos, código de retorno {exitCode})"
    if esFoto:
        salida += ("\n\nAviso: Telegram elimina casi todos los metadatos de las fotos enviadas como imagen. "
                   "Para conservarlos, envíala como archivo (adjuntar → Archivo).")
    tam = adjunto.file_size or 0
    cabecera = f"Metadatos de {nombreOrig} ({tam / 1024:.0f} KB) · {dur:.0f}s"
    await enviarSalida(context, chatId, "exif", [nombreOrig], cabecera, salida, msg)
    logEvent(f"[DEBUG] Metadatos de {nombreOrig} enviados en {chatId} ({len(salida)} caracteres)")

async def exifAyudaHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    registrarContacto(update, "exif", True)
    await context.bot.send_message(chat_id=update.effective_chat.id, disable_web_page_preview=True,
                                   text="Envíame una foto o un documento y te devuelvo sus metadatos (EXIF).\n"
                                        "Para conservar los metadatos de una foto, envíala como archivo "
                                        "(adjuntar → Archivo): si la mandas como imagen Telegram los elimina.")


# HANDLERS BÁSICOS
async def startHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto = (
        "Bot OSINT. Uso restringido.\n\n"
        "-- Red y dominios --\n"
        "/whois <dominio|ip>    Propietario WHOIS\n"
        "/dns <dominio>         Resolucion DNS\n"
        "/ipinfo <ip>           Detalles de IP\n"
        "/nmap <ip|host>        Escaneo de puertos\n"
        "/gobuster <url>        Enumeracion de rutas\n"
        "/harvester <dominio>   Emails/subdominios publicos\n"
        "/dnsrecon <dominio>    Enumeracion DNS avanzada\n"
        "/recon <dominio>      Informe: whois+dns+dnsrecon+whatweb+sslscan\n\n"
        "-- Web --\n"
        "/whatweb <url>         Fingerprinting de tecnologias\n"
        "/nikto <url>           Escaner de vulnerabilidades web\n"
        "/sslscan <host>        Analisis TLS/SSL\n"
        "/waf <url>             Deteccion de WAF\n\n"
        "-- Usuarios --\n"
        "/sherlock <usuario>    Busqueda en redes sociales\n"
        "/maigret <usuario>     Busqueda avanzada (2500+ sitios)\n\n"
        "-- Email --\n"
        "/holehe <email>        Servicios donde esta registrado\n"
        "/h8mail <email>        Brechas de datos\n"
        "/emailrep <email>      Reputacion y riesgo\n\n"
        "-- Telefono --\n"
        "/phone <+34XXXXXXXXX>  Info del numero de telefono\n\n"
        "/cancel                Cancelar el comando en curso\n"
        "/history               Tus ultimas consultas (repetir con un toque)\n"
        "(foto/archivo)         Envia una foto o documento: metadatos EXIF\n\n"
        "Tambien puedes enviar un email, IP, dominio o telefono suelto y te sugiero herramientas.\n\n"
        "-- Administracion (solo admins) --\n"
        "/adduser <userID>      Autorizar a un usuario\n"
        "/deluser <userID>      Revocar a un usuario\n"
        "/users                 Listar usuarios autorizados\n"
    )
    registrarContacto(update, "start", usuarioPermitido(update.effective_user.id) if update.effective_user else False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=texto, disable_web_page_preview=True)
    userId = update.effective_user.id if update.effective_user else None
    userName = update.effective_user.username if update.effective_user else "(sin-username)"
    logEvent(f"/start por user_id={userId} username={userName}")
    #print(f"[DEBUG] /start pedido por user_id={userId} username={userName}")


# HANDLERS DE ADMINISTRACIÓN
def makeAdminHandler(commandName: str, accion: Callable[[Update, ContextTypes.DEFAULT_TYPE, int], Tuple[str, str]]):
    """Envuelve un comando de administración: valida permisos y responde."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        usuario = update.effective_user
        chatId = update.effective_chat.id
        userId = usuario.id if usuario else None

        logEvent(f"Comando recibido: /{commandName} por user_id={userId} chat_id={chatId}")

        registrarContacto(update, commandName, usuarioAdmin(userId))
        audit.registrar(userId, usuario.username if usuario else None, commandName, list(context.args or []),
                        "ok" if usuarioAdmin(userId) else "denegado")
        if not usuarioAdmin(userId):
            await context.bot.send_message(chat_id=chatId, text="Acceso denegado.", disable_web_page_preview=True)
            logEvent(f"Acceso denegado (admin) a user_id={userId} en /{commandName}")
            return

        respuesta, logMsg = accion(update, context, userId)
        await context.bot.send_message(chat_id=chatId, text=respuesta, disable_web_page_preview=True)
        logEvent(logMsg)

    return handler

def accionAddUser(update: Update, context: ContextTypes.DEFAULT_TYPE, adminId: int) -> Tuple[str, str]:
    args = context.args or []
    if len(args) != 1:
        return ("Uso: /adduser <userID>", f"/adduser sin argumentos válidos por admin_id={adminId}")

    nuevoId = parsearUserId(args[0])
    if nuevoId is None:
        return (f"userID no válido: {args[0]}", f"/adduser userID inválido '{args[0]}' por admin_id={adminId}")

    try:
        anadido = anadirUsuarioPermitido(nuevoId)
    except Exception as e:
        return (f"Error guardando el usuario: {type(e).__name__} {e}",
                f"/adduser error guardando {nuevoId}: {type(e).__name__} {e}")

    if not anadido:
        return (f"El usuario {nuevoId} ya estaba autorizado.", f"/adduser {nuevoId} ya autorizado (admin_id={adminId})")
    return (f"Usuario {nuevoId} autorizado.", f"Usuario {nuevoId} añadido a la whitelist por admin_id={adminId}")

def accionDelUser(update: Update, context: ContextTypes.DEFAULT_TYPE, adminId: int) -> Tuple[str, str]:
    args = context.args or []
    if len(args) != 1:
        return ("Uso: /deluser <userID>", f"/deluser sin argumentos válidos por admin_id={adminId}")

    objetivoId = parsearUserId(args[0])
    if objetivoId is None:
        return (f"userID no válido: {args[0]}", f"/deluser userID inválido '{args[0]}' por admin_id={adminId}")

    if objetivoId in adminUserIds:
        return (f"El usuario {objetivoId} es administrador y no puede eliminarse aquí.",
                f"/deluser bloqueado sobre admin {objetivoId} (admin_id={adminId})")

    try:
        eliminado = eliminarUsuarioPermitido(objetivoId)
    except Exception as e:
        return (f"Error eliminando el usuario: {type(e).__name__} {e}",
                f"/deluser error eliminando {objetivoId}: {type(e).__name__} {e}")

    if not eliminado:
        return (f"El usuario {objetivoId} no estaba autorizado.", f"/deluser {objetivoId} no estaba en la whitelist (admin_id={adminId})")
    return (f"Usuario {objetivoId} eliminado.", f"Usuario {objetivoId} eliminado de la whitelist por admin_id={adminId}")

def accionListUsers(update: Update, context: ContextTypes.DEFAULT_TYPE, adminId: int) -> Tuple[str, str]:
    usuarios = usuariosPermitidos()
    if not usuarios:
        return ("No hay usuarios autorizados.", f"/users consultado por admin_id={adminId}")
    lineas = [f"{uid} (admin)" if uid in adminUserIds else str(uid) for uid in usuarios]
    texto = "Usuarios autorizados:\n" + "\n".join(lineas)
    return (texto, f"/users consultado por admin_id={adminId}")


# MENÚ DE COMANDOS (lo que Telegram sugiere al escribir "/")
menuComandos = [
    ("start", "Ayuda y lista de comandos"),
    ("info", "Ayuda y lista de comandos"),
    ("whois", "<dominio|ip> Propietario WHOIS"),
    ("dns", "<dominio> Resolución DNS"),
    ("ipinfo", "<ip> Detalles de una IP"),
    ("nmap", "<ip|host> Escaneo de puertos"),
    ("gobuster", "<url> Enumeración de rutas"),
    ("harvester", "<dominio> Emails y subdominios"),
    ("dnsrecon", "<dominio> Enumeración DNS"),
    ("recon", "<dominio> Informe completo del dominio"),
    ("whatweb", "<url> Tecnologías web"),
    ("nikto", "<url> Vulnerabilidades web"),
    ("sslscan", "<host> Análisis TLS/SSL"),
    ("waf", "<url> Detección de WAF"),
    ("sherlock", "<usuario> Búsqueda en redes"),
    ("maigret", "<usuario> Búsqueda avanzada"),
    ("holehe", "<email> Servicios registrados"),
    ("h8mail", "<email> Brechas de datos"),
    ("emailrep", "<email> Reputación del email"),
    ("phone", "<+34XXXXXXXXX> Info de teléfono"),
    ("exif", "Metadatos EXIF de una foto o documento"),
    ("history", "Tus últimas consultas"),
    ("cancel", "Cancelar el comando en curso"),
]
menuAdmin = [
    ("adduser", "<userID> Autorizar usuario"),
    ("deluser", "<userID> Revocar usuario"),
    ("users", "Listar usuarios autorizados"),
]

# el bot y su bucle, para poder actualizar el menú desde el panel (otro hilo)
appBot = None
bucleBot: Optional[asyncio.AbstractEventLoop] = None

async def menuDeUsuario(bot, uid: int) -> None:
    """Publica el menú de un usuario autorizado o se lo quita si ya no lo está."""
    scope = BotCommandScopeChat(chat_id=uid)
    try:
        if usuarioPermitido(uid):
            cmds = menuComandos + (menuAdmin if usuarioAdmin(uid) else [])
            await bot.set_my_commands([BotCommand(c, d[:256]) for c, d in cmds], scope=scope)
        else:
            await bot.delete_my_commands(scope=scope)
    except Exception as e:
        logEvent(f"No se pudo actualizar el menú de user_id={uid}: {type(e).__name__} {e}")

def refrescarMenu(uid: int) -> None:
    """Actualiza el menú de un usuario. Vale desde cualquier hilo (bot o panel); si el bot
    aún no ha arrancado no hace nada: publicarMenu lo cubre al arrancar."""
    if appBot is None or bucleBot is None or bucleBot.is_closed():
        return
    asyncio.run_coroutine_threadsafe(menuDeUsuario(appBot.bot, uid), bucleBot)

async def publicarMenu(app) -> None:
    """Registra los comandos en Telegram: los usuarios autorizados ven el menú completo
    y los admins además los de administración. El resto no ve ninguno."""
    global appBot, bucleBot, semaforoPesados
    appBot, bucleBot = app, asyncio.get_running_loop()
    semaforoPesados = asyncio.Semaphore(maxTrabajosPesados)
    try:
        await app.bot.set_my_commands([], scope=BotCommandScopeDefault())
    except Exception as e:
        logEvent(f"No se pudo publicar el menú de comandos: {type(e).__name__} {e}")
    for uid in usuariosPermitidos():
        await menuDeUsuario(app.bot, uid)


# MAIN
def main() -> None:
    os.makedirs(os.path.dirname(logFilePath), exist_ok=True)

    hiloPanel = arrancarPanel(configDir, stats, audit, {
        "getUsers": lambda: (usuariosPermitidos(), list(adminUserIds)),
        "addUser": anadirUsuarioPermitido,
        "delUser": eliminarUsuarioPermitido,
        "getToken": lambda: botToken,
        "setToken": guardarBotToken,
        "restart": reiniciarProceso,
    })

    if not botToken:
        print(f"AVISO: falta el token del bot. Configúralo en el panel web o en {botTokenFile}.")
        if hiloPanel is None:
            raise SystemExit(1)
        hiloPanel.join()  # esperar a que el panel guarde el token y reinicie
        return

    logEvent(f"Arrancando bot telegram (versión librería {tgVersion})")
    logEvent(f"Usuarios autorizados: {usuariosPermitidos()} | admins: {adminUserIds}")
    logEvent(f"Trabajos pesados simultáneos: {maxTrabajosPesados} | caché: {cacheTtl}s")
    print(f"[DEBUG] Arrancando bot telegram (versión librería {tgVersion})")
    print(f"[DEBUG] Usuarios autorizados: {allowedUserIds} | admins: {adminUserIds}")
    # concurrent_updates: varias consultas largas a la vez sin bloquear al resto de usuarios
    app = ApplicationBuilder().token(botToken).concurrent_updates(True).post_init(publicarMenu).build()

    # grupo -1: se ejecuta antes que cualquier otro handler y descarta a los no autorizados
    app.add_handler(TypeHandler(Update, filtroAcceso), group=-1)

    app.add_handler(CommandHandler("start", startHandler))
    app.add_handler(CommandHandler("help", startHandler))
    app.add_handler(CommandHandler("info", startHandler))
    app.add_handler(CommandHandler("cancel", cancelHandler))
    app.add_handler(CommandHandler("history", historyHandler))
    app.add_handler(CommandHandler("exif", exifAyudaHandler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, archivoHandler))
    app.add_handler(CallbackQueryHandler(pivoteHandler, pattern=r"^r\|"))

    # comandos de administración de la whitelist
    app.add_handler(CommandHandler("adduser", makeAdminHandler("adduser", accionAddUser)))
    app.add_handler(CommandHandler("deluser", makeAdminHandler("deluser", accionDelUser)))
    app.add_handler(CommandHandler("users",   makeAdminHandler("users",   accionListUsers)))

    # registrar dinámicamente todos los comandos permitidos
    for cmd in commandHandlers.keys():
        app.add_handler(CommandHandler(cmd, makeHandler(cmd)))

    # argumento enviado tras pulsar un comando del menú
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, argumentoHandler))

    logEvent("Bot listo. Entrando al polling.")
    print("[DEBUG] Bot listo. Entrando al polling.")
    app.run_polling()

if __name__ == "__main__":
    main()
