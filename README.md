[🇪🇸 Español](docs/README-ESP.md) | [🇬🇧 English](README.md)

# OSINTelegramBot

A Telegram bot for running OSINT tools remotely. Access is restricted to a whitelist of authorized user IDs. All commands execute inside a Docker container — no installation required on the host machine.

## ⚠️ Legal Notice

This software is provided for **educational and personal use only**. The author is not responsible for any misuse. Any modification or alteration of data is the sole responsibility of the user. Only use it against systems you own or have explicit permission to test.

---

## ✨ Features

- **Access control** via an authorized user ID whitelist.
- **Secure execution** of external tools with argument validation, restricted environment, and per-command timeouts.
- **Activity logging** to `log/logfile.log`.
- **Automatic message splitting** to respect Telegram's message size limits.
- **Docker-first** — one command to build and run, no dependencies on the host.

---

## 📋 Available Commands

All commands are restricted to authorized users.

### Network & Domains
| Command | Description |
|---|---|
| `/whois <domain\|ip>` | WHOIS lookup for a domain or IP |
| `/dns <domain>` | DNS resolution |
| `/ipinfo <ip>` | IP details from ipinfo.io |
| `/nmap <ip\|host>` | Port and service scan (top 100 ports) |
| `/gobuster <url>` | Directory enumeration with common wordlists |
| `/harvester <domain>` | Harvest emails and subdomains from public sources |
| `/dnsrecon <domain>` | Advanced DNS enumeration (zone transfer, SRV, brute force) |
| `/recon <domain>` | One combined report: whois, dns, dnsrecon, whatweb and sslscan |
| `/history` | Your last queries, tap one to repeat it |
| *(send a photo or file)* | EXIF/metadata via exiftool. Send photos as a file: Telegram strips metadata from compressed images (`/exif` shows how) |

### Web
| Command | Description |
|---|---|
| `/whatweb <url>` | Web technology fingerprinting (CMS, frameworks, versions) |
| `/nikto <url>` | Web vulnerability scanner |
| `/sslscan <host>` | TLS/SSL configuration analysis |
| `/waf <url>` | WAF detection |

### Usernames
| Command | Description |
|---|---|
| `/sherlock <username>` | Search a username across social networks |
| `/maigret <username>` | Advanced username search across 2500+ sites |

### Email
| Command | Description |
|---|---|
| `/holehe <email>` | Check which services an email is registered on |
| `/h8mail <email>` | Search for the email in known data breaches |
| `/emailrep <email>` | Email reputation and risk score (emailrep.io) |

### Phone
| Command | Description |
|---|---|
| `/phone <+34XXXXXXXXX>` | Phone number OSINT (carrier, country, line type) |

### Administration (admins only)
| Command | Description |
|---|---|
| `/adduser <userID>` | Authorize a new Telegram user ID (persisted to `config/usersIDs.txt`) |
| `/deluser <userID>` | Revoke an authorized user ID |
| `/users` | List authorized user IDs |

Admins are the IDs listed in `config/adminIDs.txt`. If that file does not exist or is
empty, the **first ID** in `config/usersIDs.txt` is treated as the administrator.
Admin IDs cannot be removed with `/deluser` — edit the files by hand for that.

---

## 🐳 Quick Start (Docker)

### 1. Clone the repository
```bash
git clone https://github.com/FranciscoFdez05/OSINTelegramBot.git
cd OSINTelegramBot
```

### 2. Create the config directory and fill in your credentials
```bash
mkdir -p config
echo "YOUR_BOT_TOKEN"   > config/botToken.txt
echo "YOUR_TELEGRAM_ID" > config/usersIDs.txt

# optional: restrict who can manage the whitelist
echo "YOUR_TELEGRAM_ID" > config/adminIDs.txt
```

Template files are provided in `config/*.example` if you prefer to copy them.

> Get your bot token from [@BotFather](https://t.me/BotFather).  
> Get your user ID from [@userinfobot](https://t.me/userinfobot).  
> Multiple user IDs can be added one per line or comma-separated.  
> Once running, further users can be added from Telegram with `/adduser <userID>`.

### 3. Build and run
```bash
docker compose up -d --build
```

### 4. View logs
```bash
docker compose logs -f
```

### Stop the bot
```bash
docker compose down
```

---

## ⚙️ Configuration

| File | Purpose |
|---|---|
| `config/botToken.txt` | Bot token from @BotFather (first line only) |
| `config/usersIDs.txt` | Authorized Telegram user IDs (one per line or comma-separated, `#` for comments) |
| `config/adminIDs.txt` | *(optional)* Admin user IDs allowed to run `/adduser`, `/deluser` and `/users` |

These files are mounted as a volume — they are never baked into the Docker image.
`/adduser` and `/deluser` write to `config/usersIDs.txt` inside that volume, so changes
survive container restarts and rebuilds.

---

## 🌐 Web Control Panel

A small dashboard starts together with the bot (standard library only, no extra dependencies):
user list (authorized users and anyone who has contacted the bot, with a one-click *Authorize*),
add/remove users, change the bot token, and performance data (uptime, commands run, success rate,
average time per command, recent activity).

- URL: `http://<server-LAN-IP>:6050` (listens on `0.0.0.0` by default).
- Password: `PANEL_PASSWORD` env var, or `config/panelPassword.txt`. The file only stores a PBKDF2 hash. If it does not exist, a random password is generated, printed once in the console and saved hashed. To change it, write the new password in plain text in that file and restart: it is hashed automatically.
- Audit: every command is logged in `log/audit.jsonl` (who, command, arguments, result, exit code, duration) and shown in the panel. Messages from users who are not authorized are ignored without any reply (only recorded as *ignorado*, so you can authorize them from the panel).
- Settings (env vars): `PANEL_HOST` (default `0.0.0.0`), `PANEL_PORT` (default `6050`), `PANEL_USER` (optional username), `PANEL_ENABLED=0` to disable.
- Login protection: after `PANEL_MAX_FAILS` failed logins (default 5) within 15 minutes, the IP is blocked for `PANEL_LOCKOUT` seconds (default 900). Behind a reverse proxy, set `PANEL_TRUST_PROXY=1` so the client IP is taken from `X-Forwarded-For`. The session cookie gets `Secure` when the proxy sends `X-Forwarded-Proto: https` (`PANEL_COOKIE_SECURE=auto`, the default); force it with `1` or disable it with `0`.
- Bot jobs: each user can run one command at a time (`/cancel` stops it and kills the process). Heavy tools (nmap, gobuster, harvester, dnsrecon, nikto, sherlock, maigret, holehe, h8mail, recon) share `MAX_HEAVY_JOBS` slots (default 3); the rest wait in a queue. While a tool runs, the "Running…" message shows the elapsed time and is replaced by the result when it finishes. Results include inline buttons to pivot to other tools on the same target, and a loose email, IP, domain or phone number sent without a command gets tool suggestions. Identical queries are served from a cache for `CACHE_TTL` seconds (default 300, 0 disables it). Outputs longer than ~6000 characters are sent as a `.txt` file with a summary in the chat.
- A new token is applied with the **Reiniciar bot** button. The bot can start without a token and wait for it from the panel.
- **Updates**: the panel shows the installed version and the latest one on GitHub, and an **Actualizar** button runs `docker-update.sh` (git pull, rebuild, health check, automatic rollback) without SSH. The same script works from the shell: `./docker-update.sh`. It needs the stack started with `./docker-up.sh` (it mounts the project folder and `/var/run/docker.sock` into the bot container, which is root-equivalent on the host, so keep the panel password strong). The version lives in `version.py`; bump it when you publish a release.
- The panel is plain HTTP: keep it on your LAN (do not forward the port to the internet) and use a strong password.

---

## 🖥️ Running Without Docker

### Manual installation

```bash
# System tools
sudo apt install -y nmap gobuster dirb whatweb sslscan dnsrecon curl whois dnsutils libimage-exiftool-perl
# nikto is no longer in Debian trixie: git clone https://github.com/sullo/nikto and link program/nikto.pl

# phoneinfoga
go install github.com/sundowndev/phoneinfoga/v2/cmd/phoneinfoga@latest

# Python dependencies
pip install -r requirements.txt

# Run
python3 main.py
```

Requires Python 3.9+. On Windows or macOS use Docker — most of these tools are Linux-only.

---

## 🔐 Security & Best Practices

- Keep the authorized user list to the minimum necessary.
- Review `log/logfile.log` periodically for unexpected activity.
- Keep the Docker image up to date: `docker compose build --pull`.
- The bot token and user IDs are never stored inside the image — they live only in the mounted `config/` volume.

---

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

**Developed with ❤️ by [Francisco](https://github.com/FranciscoFdez05)**
