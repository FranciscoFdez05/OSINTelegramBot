# config/logEvent.py

from pathlib import Path
from datetime import datetime

# Archivo de log por defecto: config/monitorLog.txt
defaultLogFile = Path(__file__).resolve().parent / "logsFile.txt"
currentLogFile = defaultLogFile

def setLogFileName(fileName: str):
    global currentLogFile
    currentLogFile = Path(__file__).resolve().parent / fileName

def logEvent(eventMsg: str):
    try:
        currentLogFile.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="seconds")
        with open(currentLogFile, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {eventMsg}\n")
    except Exception:
        pass
