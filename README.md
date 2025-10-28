[🇪🇸 Español](docs/README-ESP.md) | [🇬🇧 English](README.md)

## OSINTelegramBot
OSINTelegramBot is a Telegram bot focused on collecting basic information during OSINT investigations. The bot runs locally and allows controlled execution of commands such as `whois`, DNS lookups, requests to ipinfo.io, and searches using the Sherlock tool.

## ⚠️ Legal Notice
This software is provided for educational and personal purposes only. I am not responsible for how others may use this tool. Any modification, deletion, or alteration of metadata is the sole responsibility of the user.

## ✨ Features ✨
- **Access control** through a list of authorized user IDs.
- **Secure execution** of external utilities (`whois`, `dig`, `curl`, and `sherlock`) with argument validation and time limits.
- **Activity logging** in dedicated log files.
- **Automatic message splitting** to comply with Telegram’s message length restrictions.

## 🖥️ Requirements
- Python 3.9 or higher.
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) >= 20.0.
- Command-line tools: `whois`, `dig`, `curl`, and `sherlock` available in the system’s `PATH`.

You can use the `requirements.sh` script as a reference to install dependencies on Debian/Ubuntu-based systems:

```bash
sudo apt update
sudo apt install python3-python-telegram-bot whois dnsutils curl
sudo apt install sherlock
```

## 📦 Installation Guide
1. Clone the repository:
   ```bash
   git clone https://github.com/FranciscoFdez05/OSINTelegramBot.git
   cd OSINTelegramBot
   ```

## ⚙️ Configuration
The bot expects its configuration files to be located in the `config/` directory.

1. **Bot token**: create `config/botToken.txt` containing the token provided by @BotFather. Only the first line will be used.
2. **Authorized users**: create `config/usersIDs.txt` with one ID per line (optionally separated by commas). You can add comments starting with `#`.

If any of the files are missing or empty, the bot will stop with an error message.

## 🕹️ Usage
1. Install the required dependencies.
2. Run the bot:
   ```bash
   python3 main.py
   ```

The bot will start a *polling* loop and log events in `log/logfile.log`.

## 📋 Available Commands
All commands are only available to authorized users.
- `/start` / `/help`: displays the list of available commands.
- `/whois <domain>`: runs the `whois` utility on the provided domain.
- `/dns <domain>`: queries basic DNS records using `dig`.
- `/ipinfo <ip>`: retrieves information from ipinfo.io using `curl`.
- `/sherlock <username>`: launches the Sherlock tool to search for a username across multiple services.

Outputs are sent as plain text and automatically split if they exceed the configured size limit.

## 🔐 Security & Best Practices
- Limit the authorized user list to accounts that genuinely require access.
- Periodically review logs in the `log/` directory for suspicious activity.
- Keep external tools and the `python-telegram-bot` library up to date.

## 📜 License
📄 This project is licensed under the MIT License. See the `LICENSE` file for more details.

**Developed with ❤️ by [Francisco](https://github.com/FranciscoFdez05)**