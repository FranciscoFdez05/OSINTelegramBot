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

## 🖥️ Running Without Docker

### Automatic installer (Debian / Ubuntu / Kali / WSL)

`install.sh` checks every dependency one by one and installs **only what is missing**
(apt packages, Python tools, the `phoneinfoga` Go binary and the gobuster wordlist),
then creates the empty config files.

```bash
chmod +x install.sh
./install.sh            # install whatever is missing
./install.sh --check    # only report what is missing, install nothing
./install.sh --yes      # unattended, no prompts
```

`--check` exits with code `0` if everything is present and `1` if something is missing,
so it can be used in scripts.

### Manual installation

```bash
# System tools
sudo apt install -y nmap gobuster dirb nikto whatweb sslscan dnsrecon curl whois dnsutils golang-go

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
