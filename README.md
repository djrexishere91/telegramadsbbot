ADS-B Telegram Bot 🚁
🇮🇹 Che fa?
Invia notifiche Telegram con foto quando vede aerei speciali (militari, governativi, VIP) dalla tua stazione ADS-B.

Legge aircraft.json da readsb → Controlla le tue liste → Invia foto + info su Telegram.

🇺🇸 What does it do?
Sends Telegram notifications with photos when it spots special aircraft (military, government, VIP) from your ADS-B station.

Reads aircraft.json from readsb → Checks your lists → Sends photo + info to Telegram.

🚀 Come installarlo / How to install
Passo 1: Scarica
bash
git clone https://github.com/djrexishere91/adsb-telegram-bot
cd adsb-telegram-bot
Passo 2: Telegram Bot
Vai su @BotFather

/newbot → Nome bot → Copia TG_TOKEN

Trova chat ID con @userinfobot

Passo 3: Configura
bash
cp config.example .env
nano .env
text
TG_TOKEN="tuo_token_qua"
TG_CHAT_IDS="-1001234567890"
Passo 4: Le tue liste
bash
nano adsb-telegram.py
python
# Cambia con i TUOI CSV su GitHub
REMOTE_LISTS = [
    ("militari", "https://raw.githubusercontent.com/tuo-user/liste-adsb/main/militari.csv"),
]
Passo 5: Testa
bash
python3 adsb-telegram.py
text
[21:36] sent=2 db=156 live=23  ✅ OK!
📱 Cosa ricevi su Telegram
text
🚁 ADSB Alert
Matricola: MM62201  ICAO: 39C4AF  Tipo: F35
F-35 Lightning II - Aeronautica Militare

📍 Dist: 45km   ⚡ Vel: 780km/h   ⬆️ Alt: 8500m
👁️ Oggi: 2h45m   📡 ADS-B

Tar1090 #adsb
[Foto aereo]
📝 Crea le tue liste CSV (su GitHub)
File: militari.csv

text
hex,matricola,tipo,icao,foto1,foto2
39C4AF,MM62201,F-35,F35,https://i.imgur.com/f35-1.jpg,https://i.imgur.com/f35-2.jpg
3C6445,I-TIMU,Gulfstream G650,G650,https://i.imgur.com/g650.jpg,
Salva come RAW → Copia URL → Inserisci in REMOTE_LISTS.

⚙️ Opzionale: Avvio automatico
bash
# Copia service
sudo cp adsb-telegram.* /etc/systemd/system/

# Avvia ogni 30 secondi
sudo systemctl enable --now adsb-telegram.timer
❓ Problemi comuni
Problema	Soluzione
"No aircraft"	Aggiungi CSV in REMOTE_LISTS
"Telegram error"	Controlla .env token
Nessuna distanza	Aggiungi STATION_LAT=44.8 STATION_LON=11.6
Non parte	ls /run/readsb/aircraft.json
Semplice. Funziona. ADS-B + Telegram = ❤️

MIT License

text

---

## 🎯 **File per GitHub**:

adsb-telegram.py ✅
README.md ✅ (copia sopra)
config.example ✅
adsb-telegram.service ✅
adsb-telegram.timer ✅
LICENSE ✅

text

## **Description GitHub**:
Bot Telegram notifiche ADS-B con foto da readsb. Liste CSV GitHub, cooldown 15min, distanza, HTML ricco.
