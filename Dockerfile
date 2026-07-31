FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOPATH=/root/go \
    PATH="/root/go/bin:/usr/local/go/bin:${PATH}"

# Herramientas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    gobuster \
    dirb \
    nikto \
    whatweb \
    sslscan \
    dnsrecon \
    curl \
    whois \
    dnsutils \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

# phoneinfoga (binario Go)
RUN go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest

WORKDIR /app

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY . .

# Directorios y ficheros de config vacíos (se rellenan via volumen)
RUN mkdir -p config log \
    && touch config/botToken.txt config/usersIDs.txt config/adminIDs.txt

ENV CONFIG_DIR=/app/config

CMD ["python", "main.py"]
