ADS-B Telegram Alert Bot 🚁
🇮🇹 Italiano
Bot Telegram per notifiche ADS-B da readsb/tar1090.

Monitora aircraft.json → Foto + alert per aerei dalle tue liste CSV GitHub (mil/gov/VIP).

🚀 Setup 3 Minuti
bash
git clone https://github.com/djrexishere91/adsb-telegram-bot
cd adsb-telegram-bot

# 1. Telegram
cp env.example .env
nano .env  # TG_TOKEN=@BotFather
          # TG_CHAT_IDS=@userinfobot

# 2. Personalizza
nano adsb-telegram.py
# BOT_TITLE="🚁 TuoStazione"
# REMOTE_LISTS=[("mil","https://raw...")]

# 3. Test
python3 adsb-telegram.py
📁 Configurazione
.env (solo Telegram!)

text
TG_TOKEN="1234567890:ABC..."
TG_CHAT_IDS="-100xxxxxxxxxx"
adsb-telegram.py

python
BOT_TITLE = "🚁 ADSB Alert"
REMOTE_LISTS = [
    ("mil", "https://raw.githubusercontent.com/user/repo/main/mil.csv"),
]
✨ Funzionalità
Foto auto (4 URL random)

Cooldow 15min

Distanza haversine

HTML ricco m/ft km/h

SQLite tracking

Multi-chat

📊 Esempio
text
🚁 ADSB Alert
MM62201 • 39C4AF • F35
F-35A | Vel: 780km/h | Dist: 45km
#adsb
🛠 Systemd
bash
sudo systemctl enable --now adsb-telegram.timer  # 30s
🇺🇸 English
Real-time ADS-B Telegram alerts from readsb/tar1090.

Monitors aircraft.json → Photos + alerts for aircraft from your GitHub CSV lists (mil/gov/VIP).

🚀 3 Minute Setup
bash
git clone https://github.com/djrexishere91/adsb-telegram-bot
cd adsb-telegram-bot

# 1. Telegram
cp env.example .env
nano .env  # TG_TOKEN=@BotFather
          # TG_CHAT_IDS=@userinfobot

# 2. Customize
nano adsb-telegram.py
# BOT_TITLE="🚁 YourStation"
# REMOTE_LISTS=[("mil","https://raw...")]

# 3. Test
python3 adsb-telegram.py
📁 Configuration
.env (Telegram only!)

text
TG_TOKEN="1234567890:ABC..."
TG_CHAT_IDS="-100xxxxxxxxxx"
adsb-telegram.py

python
BOT_TITLE = "🚁 ADSB Alert"
REMOTE_LISTS = [
    ("mil", "https://raw.githubusercontent.com/user/repo/main/mil.csv"),
]
✨ Features
Auto photos (4 random URLs)

15min cooldown

Haversine distance

Rich HTML m/ft km/h

SQLite tracking

Multi-chat

📊 Example
text
🚁 ADSB Alert
MM62201 • 39C4AF • F35
F-35A | Speed: 780km/h | Dist: 45km
#adsb
🛠 Systemd
bash
sudo systemctl enable --now adsb-telegram.timer  # 30s
📋 CSV Format
text
hex,reg,type,icao,img1,img2
39C4AF,MM62201,F-35A,F35,https://foto1.jpg,https://foto2.jpg
🔧 Troubleshooting
text
No aircraft → Fill REMOTE_LISTS
Telegram error → Check .env
No distance → STATION_LAT/LON env
Log: [21:36] sent=2 db=156 live=23
MIT License | Powered by ADS-B 🛫
