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

commandHandlers = {
    "whois": whois.run,
    "ipinfo": ipinfo.run,
    "sherlock": sherlock.run,
    "dns": dnslookup.run,
}

# CONFIGURACIÓN
configDir = "config"
botTokenFile = os.path.join(configDir, "botToken.txt")
allowedUsersFile = os.path.join(configDir, "usersIDs.txt")

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

botToken = cargarBotToken(botTokenFile)
allowedUserIds = cargarAllowedUserIds(allowedUsersFile)

def validarConfig() -> None:
    problemas = []
    if not botToken:
        problemas.append(f"Falta token del bot. Crea {botTokenFile} con el token (una línea).")
    if not allowedUserIds:
        problemas.append(f"Falta lista de usuarios permitidos o está vacía. Crea {allowedUsersFile} con tu user_id.")
    if problemas:
        for p in problemas:
            print("ERROR:", p)
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
        print(f"{ts} (log fail) {mensaje}")

def usuarioPermitido(userId: int) -> bool:
    return userId in allowedUserIds

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
        print(f"[DEBUG] input user: /{commandName} {' '.join(context.args) if context.args else '(sin-args)'} from user_id={userId}")

        if not usuarioPermitido(userId):
            await context.bot.send_message(chat_id=chatId, text="Acceso denegado.", disable_web_page_preview=True)
            logEvent(f"Acceso denegado a user_id={userId}")
            print(f"[DEBUG] acceso denegado para user_id={userId}")
            return

        if commandName not in commandHandlers:
            await context.bot.send_message(chat_id=chatId, text="Comando no permitido.", disable_web_page_preview=True)
            print(f"[DEBUG] comando no permitido: {commandName}")
            return

        try:
            salida, exitCode = commandHandlers[commandName](context.args or [])
        except RuntimeError as e:
            await context.bot.send_message(chat_id=chatId, text=f"Error: {e}", disable_web_page_preview=True)
            print(f"[DEBUG] RuntimeError en {commandName}: {e}")
            return
        except Exception as e:
            await context.bot.send_message(chat_id=chatId, text=f"Error ejecutando /{commandName}: {type(e).__name__} {e}", disable_web_page_preview=True)
            print(f"[DEBUG] Excepción en {commandName}: {type(e).__name__} {e}")
            return

        if not salida:
            salida = f"(sin salida, código de retorno {exitCode})"

        cabecera = f"Salida de {commandName} (exit {exitCode})"
        await context.bot.send_message(chat_id=chatId, text=cabecera, disable_web_page_preview=True)
        await sendLongPlain(context, chatId, salida)
        print(f"[DEBUG] Salida enviada como texto plano en {chatId}")

    return handler


# HANDLERS BÁSICOS
async def startHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto = (
        "Bot de ejecución remota. Uso restringido.\n"
        "Comandos disponibles:\n"
        "/whois dominio o ip --> Consultar el propietario de un dominio o ip\n"
        "/dns dominio --> Resuelve el dominio y muestra la ip\n"
        "/ipinfo ip --> Muestra los detalles de una direccion ip\n"
        "/serlock nombre --> Rastrear nombres de usuario\n"
        
        #+ "".join([f"/{c}\n" for c in sorted(commandHandlers.keys())])
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=texto, disable_web_page_preview=True)
    userId = update.effective_user.id if update.effective_user else None
    userName = update.effective_user.username if update.effective_user else "(sin-username)"
    logEvent(f"/start por user_id={userId} username={userName}")
    print(f"[DEBUG] /start pedido por user_id={userId} username={userName}")


# MAIN
def main() -> None:
    if not botToken:
        print("ERROR: configura config/botToken.txt con el token.")
        return

    os.makedirs(os.path.dirname(logFilePath), exist_ok=True)

    logEvent(f"Arrancando bot telegram (versión librería {tgVersion})")
    print(f"[DEBUG] Arrancando bot telegram (versión librería {tgVersion})")
    app = ApplicationBuilder().token(botToken).build()

    app.add_handler(CommandHandler("start", startHandler))
    app.add_handler(CommandHandler("help", startHandler))

    # registrar dinámicamente todos los comandos permitidos
    for cmd in commandHandlers.keys():
        app.add_handler(CommandHandler(cmd, makeHandler(cmd)))

    logEvent("Bot listo. Entrando al polling.")
    print("[DEBUG] Bot listo. Entrando al polling.")
    app.run_polling()

if __name__ == "__main__":
    main()
