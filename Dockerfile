FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOPATH=/root/go \
    PATH="/root/go/bin:/usr/local/go/bin:${PATH}"

# Herramientas del sistema.
# Cada paquete se instala por separado: si uno no existe en la distro no se cae el build.
# Lo que falte lo instala docker-entrypoint.sh al arrancar el contenedor.
RUN apt-get update \
    && for p in nmap gobuster dirb whatweb sslscan dnsrecon curl whois dnsutils golang-go perl libnet-ssleay-perl ca-certificates; do \
         apt-get install -y --no-install-recommends "$p" || echo "AVISO: no se pudo instalar $p"; \
       done \
    && rm -rf /var/lib/apt/lists/*

# nikto: ya no está en los repos de Debian (trixie); se instala desde GitHub
RUN curl -fsSL https://github.com/sullo/nikto/archive/refs/heads/master.tar.gz \
    | tar -xz -C /opt \
    && mv /opt/nikto-master /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && chmod +x /opt/nikto/program/nikto.pl

# phoneinfoga (binario Go)
RUN go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest

# CLI de Docker + Compose: el panel web los usa para lanzar docker-update.sh
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:27-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose

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

# Comprueba al arrancar que las herramientas están instaladas y repone las que falten
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "main.py"]
