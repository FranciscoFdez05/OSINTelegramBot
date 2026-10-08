FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1


# Herramientas del sistema.
# Cada paquete se instala por separado: si uno no existe en la distro no se cae el build.
# Lo que falte lo instala docker-entrypoint.sh al arrancar el contenedor.
RUN apt-get update \
    && for p in nmap gobuster dirb whatweb sslscan dnsrecon curl whois dnsutils perl libnet-ssleay-perl ca-certificates; do \
         apt-get install -y --no-install-recommends "$p" || echo "AVISO: no se pudo instalar $p"; \
       done \
    && rm -rf /var/lib/apt/lists/*

# nikto: ya no está en los repos de Debian (trixie); se instala desde GitHub
RUN mkdir -p /opt/nikto \
    && ( curl -fsSL https://github.com/sullo/nikto/archive/HEAD.tar.gz \
         | tar -xz --strip-components=1 -C /opt/nikto \
         && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
         && chmod +x /opt/nikto/program/nikto.pl ) \
    || echo "AVISO: no se pudo instalar nikto (se reintentará al arrancar)"

# phoneinfoga (binario precompilado de las releases)
RUN ( case "$(uname -m)" in aarch64) a=arm64;; armv7l) a=armv7;; i686|i386) a=i386;; *) a=x86_64;; esac \
      && curl -fsSL "https://github.com/sundowndev/phoneinfoga/releases/latest/download/phoneinfoga_Linux_$a.tar.gz" \
         | tar -xz -C /usr/local/bin phoneinfoga ) \
    || echo "AVISO: no se pudo instalar phoneinfoga (se reintentará al arrancar)"

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
