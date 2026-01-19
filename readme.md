ADS-B Telegram Bot 🚁
🇮🇹 Italiano
Che fa?
Invia notifiche Telegram con foto quando vede aerei speciali (militari, governativi, VIP) dalla tua stazione ADS-B.

Legge aircraft.json da readsb → Controlla le tue liste → Invia foto + info su Telegram.

🚀 Come installarlo
Passo 1: Scarica

bash
git clone https://github.com/djrexishere91/telegramadsbbot
cd telegramadsbbot
Passo 2: Telegram Bot

@BotFather → /newbot → TG_TOKEN

@userinfobot → TG_CHAT_IDS

Passo 3: Configura

bash
cp config.example .env
nano .env
text
TG_TOKEN="tuo_token_qua"
TG_CHAT_IDS="-1001234567890"
Passo 4: Le tue liste

bash
nano telegram_adsb_bot.py
python
REMOTE_LISTS = [
    ("militari", "https://raw.githubusercontent.com/tuo-user/liste/main/militari.csv"),
]
Passo 5: Testa

bash
python3 telegram_adsb_bot.py
text
[21:36] sent=2 db=156 live=23  ✅ OK!
📱 Cosa ricevi
text
🚁 ADSB Alert
Matricola: MM62201  ICAO: 39C4AF  Tipo: F35
F-35 Lightning II - Aeronautica Militare

📍 Dist: 45km   ⚡ Vel: 780km/h   ⬆️ Alt: 8500m
👁️ Oggi: 2h45m   📡 ADS-B
Tar1090  #adsb [Foto]
🇺🇸 English
What does it do?
Sends Telegram notifications with photos when spotting special aircraft (military, government, VIP) from your ADS-B station.

Reads aircraft.json from readsb → Checks your lists → Sends photo + info to Telegram.

🚀 How to install
Step 1: Clone

bash
git clone https://github.com/djrexishere91/telegramadsbbot
cd telegramadsbbot
Step 2: Telegram Bot

@BotFather → /newbot → TG_TOKEN

@userinfobot → TG_CHAT_IDS

Step 3: Configure

bash
cp config.example .env
nano .env
text
TG_TOKEN="your_token_here"
TG_CHAT_IDS="-1001234567890"
Step 4: Your lists

bash
nano telegram_adsb_bot.py
python
REMOTE_LISTS = [
    ("military", "https://raw.githubusercontent.com/your-user/lists/main/military.csv"),
]
Step 5: Test

bash
python3 telegram_adsb_bot.py
text
[21:36] sent=2 db=156 live=23  ✅ OK!
📱 What you get
text
🚁 ADSB Alert
Reg: MM62201  ICAO: 39C4AF  Type: F35
F-35 Lightning II - Italian Air Force

📍 Dist: 45km   ⚡ Speed: 780km/h   ⬆️ Alt: 8500m
👁️ Today: 2h45m   📡 ADS-B
Tar1090  #adsb [Photo]
📝 CSV Lists (GitHub RAW)
🇮🇹 militari.csv 🇺🇸 military.csv

text
hex,reg,type,icao,img1,img2
39C4AF,MM62201,F-35,F35,https://i.imgur.com/f35.jpg,
3C6445,I-TIMU,G650,G650,https://i.imgur.com/g650.jpg,
⚙️ Auto-start (Entrambi / Both)
bash
sudo cp adsb-telegram.* /etc/systemd/system/
sudo systemctl enable --now adsb-telegram.timer  # ogni 30s
❓ Troubleshooting (Entrambi / Both)
🇮🇹 Problema	🇺🇸 Issue	✅ Fix
"No aircraft"	No planes	Add CSV to REMOTE_LISTS
Telegram error	Telegram fail	Check .env
No distance	No dist	STATION_LAT/LON
Not starting	Won't start	Check /run/readsb/aircraft.json
🇮🇹 Semplice. Funziona. ADS-B + Telegram = ❤️
🇺🇸 Simple. Works. ADS-B + Telegram = ❤️

MIT License