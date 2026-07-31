#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requisitos: python>=3.9, python-telegram-bot>=20.0

import os
from datetime import datetime
from typing import Optional, List, Callable, Tuple, Dict

from telegram import Update, __version__ as tgVersion
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from log.logEvent import logEvent
from utilitis import sherlock, whois, ipinfo, dnslookup
from utilitis import nmap, gobuster, holehe, theharvester, h8mail, emailrep
from utilitis import maigret, dnsrecon, whatweb, nikto, sslscan, wafw00f, phoneinfoga

commandHandlers = {
    # Red y dominios
    "whois":     whois.run,
    "ipinfo":    ipinfo.run,
    "dns":       dnslookup.run,
    "nmap":      nmap.run,
    "gobuster":  gobuster.run,
    "harvester": theharvester.run,
    "dnsrecon":  dnsrecon.run,
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
logFilePath = os.path.join("log", "logfile.log")


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

def validarConfig() -> None:
    problemas = []
    if not botToken:
        problemas.append(f"Falta token del bot. Crea {botTokenFile} con el token (una línea).")
    if not allowedUserIds:
        problemas.append(f"Falta lista de usuarios permitidos o está vacía. Crea {allowedUsersFile} con tu user_id.")
    if problemas:
        for p in problemas:
            logEvent("ERROR:"), p
            #print("ERROR:", p)          
        raise SystemExit(1)
        
validarConfig()


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
    if userId in allowedUserIds:
        return False
    allowedUserIds.append(userId)
    os.makedirs(configDir, exist_ok=True)
    contenido = leerFicheroTexto(allowedUsersFile) or ""
    sufijo = "" if (not contenido or contenido.endswith("\n")) else "\n"
    with open(allowedUsersFile, "a", encoding="utf-8") as f:
        f.write(f"{sufijo}{userId}\n")
    return True

def eliminarUsuarioPermitido(userId: int) -> bool:
    """Elimina el userId de la whitelist (memoria + fichero). False si no estaba."""
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
    return True

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

async def sendLongPlain(context: ContextTypes.DEFAULT_TYPE, chatId: int, texto: str) -> None:
    partes = chunkText(texto, maxPlainChunk)
    total = len(partes)
    for idx, parte in enumerate(partes, start=1):
        pref = f"[{idx}/{total}] " if total > 1 else ""
        await context.bot.send_message(chat_id=chatId, text=pref + parte, disable_web_page_preview=True)

def makeHandler(commandName: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        usuario = update.effective_user
        chatId = update.effective_chat.id
        userId = usuario.id if usuario else None
        userName = usuario.username if usuario and usuario.username else "(sin-username)"

        logEvent(f"Comando recibido: /{commandName} por user_id={userId} chat_id={chatId} username={userName}")
        #print(f"[DEBUG] input user: /{commandName} {' '.join(context.args) if context.args else '(sin-args)'} from user_id={userId}")

        if not usuarioPermitido(userId):
            await context.bot.send_message(chat_id=chatId, text="Acceso denegado.", disable_web_page_preview=True)
            logEvent(f"Acceso denegado a user_id={userId}")
            #print(f"[DEBUG] acceso denegado para user_id={userId}")
            return

        if commandName not in commandHandlers:
            await context.bot.send_message(chat_id=chatId, text="Comando no permitido.", disable_web_page_preview=True)
            logEvent(f"[DEBUG] comando no permitido: {commandName}")
            #print(f"[DEBUG] comando no permitido: {commandName}")
            return

        try:
            salida, exitCode = commandHandlers[commandName](context.args or [])
        except RuntimeError as e:
            await context.bot.send_message(chat_id=chatId, text=f"Error: {e}", disable_web_page_preview=True)
            logEvent(f"[DEBUG] RuntimeError en {commandName}: {e}")
            #print(f"[DEBUG] RuntimeError en {commandName}: {e}")
            return
        except Exception as e:
            await context.bot.send_message(chat_id=chatId, text=f"Error ejecutando /{commandName}: {type(e).__name__} {e}", disable_web_page_preview=True)
            logEvent(f"[DEBUG] Excepción en {commandName}: {type(e).__name__} {e}")
            #print(f"[DEBUG] Excepción en {commandName}: {type(e).__name__} {e}")
            return

        if not salida:
            salida = f"(sin salida, código de retorno {exitCode})"

        cabecera = f"Salida de {commandName} (exit {exitCode})"
        await context.bot.send_message(chat_id=chatId, text=cabecera, disable_web_page_preview=True)
        await sendLongPlain(context, chatId, salida)
        logEvent(f"[DEBUG] Salida enviada como texto plano en {chatId}")
        #print(f"[DEBUG] Salida enviada como texto plano en {chatId}")

    return handler


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
        "/dnsrecon <dominio>    Enumeracion DNS avanzada\n\n"
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
        "-- Administracion (solo admins) --\n"
        "/adduser <userID>      Autorizar a un usuario\n"
        "/deluser <userID>      Revocar a un usuario\n"
        "/users                 Listar usuarios autorizados\n"
    )
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
    if not allowedUserIds:
        return ("No hay usuarios autorizados.", f"/users consultado por admin_id={adminId}")
    lineas = [f"{uid} (admin)" if uid in adminUserIds else str(uid) for uid in allowedUserIds]
    texto = "Usuarios autorizados:\n" + "\n".join(lineas)
    return (texto, f"/users consultado por admin_id={adminId}")


# MAIN
def main() -> None:
    if not botToken:
        print("ERROR: configura config/botToken.txt con el token.")
        return

    os.makedirs(os.path.dirname(logFilePath), exist_ok=True)

    logEvent(f"Arrancando bot telegram (versión librería {tgVersion})")
    logEvent(f"Usuarios autorizados: {allowedUserIds} | admins: {adminUserIds}")
    print(f"[DEBUG] Arrancando bot telegram (versión librería {tgVersion})")
    print(f"[DEBUG] Usuarios autorizados: {allowedUserIds} | admins: {adminUserIds}")
    app = ApplicationBuilder().token(botToken).build()

    app.add_handler(CommandHandler("start", startHandler))
    app.add_handler(CommandHandler("help", startHandler))

    # comandos de administración de la whitelist
    app.add_handler(CommandHandler("adduser", makeAdminHandler("adduser", accionAddUser)))
    app.add_handler(CommandHandler("deluser", makeAdminHandler("deluser", accionDelUser)))
    app.add_handler(CommandHandler("users",   makeAdminHandler("users",   accionListUsers)))

    # registrar dinámicamente todos los comandos permitidos
    for cmd in commandHandlers.keys():
        app.add_handler(CommandHandler(cmd, makeHandler(cmd)))

    logEvent("Bot listo. Entrando al polling.")
    print("[DEBUG] Bot listo. Entrando al polling.")
    app.run_polling()

if __name__ == "__main__":
    main()
