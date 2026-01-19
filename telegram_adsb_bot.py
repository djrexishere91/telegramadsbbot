#!/usr/bin/env python3
"""
ADS-B Aircraft Alert Telegram Bot

Monitors aircraft.json from readsb/tar1090 and sends Telegram notifications
for interesting aircraft from curated lists. Includes cooldown, state tracking,
distance calculation, and photo support.

Usage:
  systemd timer/service reading aircraft.json every 30-60s
  Configure via environment variables (TG_TOKEN, TG_CHAT_IDS, etc.)
"""

import os
import time
import json
import csv
import sqlite3
import html
import math
import random
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------- CONFIGURATION ----------------
# Paths (customize for your setup)
READSB_AIRCRAFT_JSON = "/run/readsb/aircraft.json"
RECEIVER_JSON = "/run/readsb/receiver.json"
STATE_DB = "/var/lib/adsb-telegram/state.sqlite"
LIST_CACHE_DIR = "/var/lib/adsb-telegram/lists"

# Timing
LIST_TTL_SEC = 900  # Cache refresh every 15 minutes
COOLDOWN_SEC = 15 * 60  # Renotify after 15 minutes
MAX_SEEN_SEC = 60.0  # "live" if seen <= 60s

# Telegram
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_IDS = os.environ.get("TG_CHAT_IDS", "")  # "chat1,chat2"
TG_CAPTION_MAX = 1024

# Stations (fallback to env vars)
TAR1090_BASE = os.environ.get("TAR1090_BASE", "")
AIRPLANESLIVE_BASE = os.environ.get("AIRPLANESLIVE_BASE", "")

# Customize these
BOT_TITLE = "ADSB Alert Bot"
FOOTER = "#adsb #alert"

# Conversion factors
KNOTS_TO_KMH = 1.852
FT_TO_M = 0.3048


# ---------------- UTILITY FUNCTIONS ----------------
def safe(s: str) -> str:
    """Safely clean string input."""
    return (s or "").strip()


def h(s: str) -> str:
    """HTML escape string."""
    return html.escape(safe(s), quote=False)


def as_float(x) -> Optional[float]:
    """Safely convert to float."""
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def fmt_duration(sec: int) -> str:
    """Format seconds as human-readable duration."""
    if sec < 0:
        sec = 0
    m, s = divmod(int(sec), 60)
    hh, mm = divmod(m, 60)
    if hh > 0:
        return f"{hh}h{mm:02d}m"
    if mm > 0:
        return f"{mm}m{s:02d}s"
    return f"{s}s"


def fmt_kmh(gs) -> str:
    """Format ground speed in km/h."""
    v = as_float(gs)
    if v is None:
        return ""
    return f"{v * KNOTS_TO_KMH:.0f}"


def fmt_alt_m_ft(alt) -> Tuple[str, str]:
    """Format altitude in meters and feet."""
    if alt is None:
        return "", ""
    if isinstance(alt, str) and alt.lower() == "ground":
        return "0", "0"
    
    ft = as_float(alt)
    if ft is None:
        return "", ""
    m = ft * FT_TO_M
    return f"{m:.0f}", f"{ft:.0f}"


def src_label(live: dict) -> str:
    """Determine data source label."""
    if live.get("mlat"):
        return "MLAT"
    if live.get("tisb"):
        return "TIS-B"
    return "ADS-B"


def today_key(now: int) -> str:
    """Get current date key."""
    return time.strftime("%Y-%m-%d", time.localtime(now))


def load_station_latlon() -> Tuple[Optional[float], Optional[float]]:
    """Load station coordinates from receiver.json or env vars."""
    try:
        p = Path(RECEIVER_JSON)
        if p.is_file():
            rj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            lat = rj.get("lat")
            lon = rj.get("lon")
            if lat is not None and lon is not None:
                return float(lat), float(lon)
    except Exception:
        pass

    elat = os.environ.get("STATION_LAT")
    elon = os.environ.get("STATION_LON")
    if elat and elon:
        return float(elat), float(elon)
    
    return None, None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two lat/lon points in km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 + 
         math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return r * c


# ---------------- LIST CACHE MANAGEMENT ----------------
def _cache_path(name: str) -> Path:
    """Get local cache path for remote list."""
    Path(LIST_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    return Path(LIST_CACHE_DIR) / f"{name}.csv"


def fetch_remote_list(name: str, url: str) -> Path:
    """
    Download remote CSV list with intelligent caching:
    - Use fresh cache if < TTL
    - Download if stale/missing
    - Fallback to cache on download failure
    """
    dst = _cache_path(name)
    now = time.time()

    try:
        if dst.is_file():
            age = now - dst.stat().st_mtime
            if age < LIST_TTL_SEC:
                return dst

        req = urllib.request.Request(url, headers={"User-Agent": "adsb-telegram/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()

        tmp = dst.with_suffix(".csv.tmp")
        tmp.write_bytes(data)
        tmp.replace(dst)
        return dst

    except Exception:
        if dst.is_file():
            return dst
        raise


# ---------------- STATE DATABASE ----------------
def ensure_db() -> sqlite3.Connection:
    """Initialize SQLite state database."""
    Path(STATE_DB).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(STATE_DB)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            hex         TEXT PRIMARY KEY,
            last_notify INTEGER NOT NULL,
            first_seen  INTEGER NOT NULL,
            day         TEXT NOT NULL,
            today_seen  INTEGER NOT NULL
        )
    """)
    con.commit()
    return con


def get_state(con: sqlite3.Connection, hx: str) -> Optional[Tuple[int, int, str, int]]:
    """Get aircraft state from DB."""
    cur = con.cursor()
    cur.execute("SELECT last_notify, first_seen, day, today_seen FROM seen WHERE hex=?", (hx,))
    row = cur.fetchone()
    if not row:
        return None
    return int(row[0]), int(row[1]), str(row[2]), int(row[3])


def ensure_state_row(con: sqlite3.Connection, hx: str, now: int) -> Tuple[int, int, str, int]:
    """Ensure aircraft has state row, reset daily stats."""
    tkey = today_key(now)
    st = get_state(con, hx)
    cur = con.cursor()

    if not st:
        cur.execute(
            "INSERT INTO seen(hex,last_notify,first_seen,day,today_seen) VALUES(?,?,?,?,?)",
            (hx, 0, now, tkey, 0),
        )
        con.commit()
        return 0, now, tkey, 0

    last_notify, first_seen, day, today_seen = st

    if day != tkey:
        cur.execute(
            "UPDATE seen SET day=?, today_seen=?, first_seen=? WHERE hex=?",
            (tkey, 0, now, hx),
        )
        con.commit()
        return last_notify, now, tkey, 0

    return last_notify, first_seen, day, today_seen


def should_notify(last_notify: int, now: int) -> bool:
    """Check if aircraft cooldown expired."""
    if last_notify <= 0:
        return True
    return (now - last_notify) >= COOLDOWN_SEC


def set_last_notify(con: sqlite3.Connection, hx: str, now: int):
    """Mark aircraft as notified."""
    cur = con.cursor()
    cur.execute("UPDATE seen SET last_notify=? WHERE hex=?", (now, hx))
    con.commit()


def close_session_add_today(con: sqlite3.Connection, hx: str, now: int, first_seen: int):
    """Close tracking session and add duration to daily total."""
    add = max(0, now - first_seen)
    cur = con.cursor()
    cur.execute(
        "UPDATE seen SET today_seen=today_seen+?, first_seen=? WHERE hex=?",
        (add, now, hx),
    )
    con.commit()


# ---------------- TELEGRAM API ----------------
def _tg_destinations() -> List[str]:
    """Get list of Telegram chat IDs."""
    return [x.strip() for x in (TG_CHAT_IDS or "").split(",") if x.strip()]


def _require_tg():
    """Ensure Telegram credentials configured."""
    if not TG_TOKEN or not _tg_destinations():
        raise SystemExit("Missing TG_TOKEN or TG_CHAT_IDS environment variables")


def tg_send_message(text: str) -> str:
    """Send HTML-formatted message to all chats."""
    _require_tg()
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    last = None

    for chat_id in _tg_destinations():
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                last = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Telegram sendMessage failed: HTTP {e.code} {body}")

    return last


def tg_send_photo(photo_url: str, caption: str) -> str:
    """Send photo with HTML caption to all chats."""
    _require_tg()
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    last = None

    for chat_id in _tg_destinations():
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                last = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Telegram sendPhoto failed: HTTP {e.code} {body}")

    return last


def send_photo_or_text(photo_url: str, caption: str):
    """Send photo if caption fits, otherwise text message."""
    try:
        if len(caption) <= TG_CAPTION_MAX:
            return tg_send_photo(photo_url, caption)

        short = caption[:1000] + "…"
        tg_send_photo(photo_url, short)
        return tg_send_message(caption)
    except SystemExit:
        return tg_send_message(caption)


# ---------------- AIRCRAFT LISTS ----------------
def load_db_lists(remote_lists: List[Tuple[str, str]]) -> Dict[str, dict]:
    """
    Load curated aircraft lists from remote CSV files with caching.
    
    Expected CSV format:
    hex,reg,operator,type,icao_type,cmpg,tag1,tag2,tag3,category,link,img1,img2,img3,img4
    """
    db = {}
    local_files = []

    for name, url in remote_lists:
        try:
            local_files.append(fetch_remote_list(name, url))
        except Exception as e:
            raise SystemExit(f"Failed to fetch list {name}: {e}")

    for p in local_files:
        if not p.is_file():
            continue
            
        with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.reader(f)
            next(r, None)  # Skip header
            for row in r:
                if not row:
                    continue
                hx = safe(row[0]).upper()
                if len(hx) != 6:
                    continue

                def get(i): 
                    return safe(row[i]) if i < len(row) else ""
                    
                db[hx] = {
                    "hex": hx,
                    "reg": get(1),
                    "operator": get(2),
                    "type": get(3),
                    "icao_type": get(4),
                    "cmpg": get(5),
                    "tag1": get(6),
                    "tag2": get(7),
                    "tag3": get(8),
                    "category": get(9),
                    "link": get(10),
                    "img1": get(11),
                    "img2": get(12),
                    "img3": get(13),
                    "img4": get(14),
                }
    return db


def pick_photo_urls(info: dict) -> List[str]:
    """Extract and clean photo URLs from aircraft info."""
    urls = []
    for k in ("img1", "img2", "img3", "img4"):
        u = safe(info.get(k, ""))
        if 'https://' in u:
            start = u.find('https://')
            # Clean URL by finding first ] ) or space after start
            for end in [u.find(c, start) for c in ']) ']:
                if end > start:
                    clean_u = u[start:end].rstrip(')')
                    break
            else:
                clean_u = u[start:]
            if len(clean_u) > 20:
                urls.append(clean_u)
    
    random.shuffle(urls)
    return urls


def build_tags(info: dict) -> str:
    """Build pipe-separated tags string."""
    tags = [safe(info.get(k, "")) for k in ("tag1", "tag2", "tag3") if safe(info.get(k, ""))]
    return " | ".join(tags) if tags else ""


# ---------------- CAPTION BUILDER ----------------
def fmt_caption(
    info: dict, 
    live: dict, 
    now: int, 
    first_seen: int, 
    today_seen: int, 
    st_lat: Optional[float], 
    st_lon: Optional[float]
) -> str:
    """Build rich HTML caption for Telegram."""
    hx = safe(info.get("hex", "")).upper()
    
    # Basic info
    tail = safe(info.get("reg", "")) or safe(live.get("r", ""))
    flt = safe(live.get("flight", "")) or safe(info.get("tag3", ""))
    operator_ = safe(info.get("operator", ""))
    typdesc = safe(info.get("type", ""))
    icao_type = safe(info.get("icao_type", "")) or safe(live.get("t", ""))
    link_ref = safe(info.get("link", ""))
    
    # Live data
    alt = live.get("alt_baro") or live.get("alt_geom")
    gs = live.get("gs")
    seen_s = as_float(live.get("seen"))
    
    # Timing
    in_session = fmt_duration(now - first_seen)
    today_total = fmt_duration(today_seen + (now - first_seen))
    last_txt = f"{seen_s:.0f}s" if seen_s is not None else ""
    
    # Format live data
    alt_m, alt_ft = fmt_alt_m_ft(alt)
    kmh = fmt_kmh(gs)
    src = src_label(live)
    
    # Distance
    dist_txt = ""
    rdst = as_float(live.get("r_dst"))
    if rdst is not None:
        dist_txt = f"{rdst:.1f}"
    else:
        alat = live.get("lat")
        alon = live.get("lon")
        try:
            if (st_lat and st_lon and alat is not None and alon is not None and 
                isinstance(alat, (int, float)) and isinstance(alon, (int, float))):
                dkm = haversine_km(float(st_lat), float(st_lon), float(alat), float(alon))
                dist_txt = f"{dkm:.1f}"
        except Exception:
            pass
    
    # Direction
    dir_txt = ""
    rdir = as_float(live.get("r_dir"))
    if rdir is not None:
        dir_txt = f"{rdir:.0f}"
    
    # Timestamps
    ts_local = time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(now))
    ts_utc = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))
    ts = f"{ts_local} ({ts_utc} UTC)"
    
    # Build links
    links = []
    if TAR1090_BASE:
        links.append(f'<a href="{TAR1090_BASE}/?icao={urllib.parse.quote(hx)}">Tar1090</a>')
    if AIRPLANESLIVE_BASE:
        links.append(f'<a href="{AIRPLANESLIVE_BASE}/?icao={urllib.parse.quote(hx)}">Airplanes.live</a>')
    if link_ref.startswith("http"):
        links.append(f'<a href="{h(link_ref)}">Info</a>')
    
    # Tags
    tags = build_tags(info)
    
    # Assemble caption lines
    lines = [f"<b>{h(BOT_TITLE)}</b>"]
    
    top = f"<b>{h(tail) if tail else '-'}</b> • <b>ICAO:</b> <code>{h(hx)}</code>"
    if icao_type:
        top += f" • <code>{h(icao_type)}</code>"
    lines.append(top)
    
    if flt:
        lines.append(f"<b>Volo:</b> <code>{h(flt)}</code>")
    if operator_:
        lines.append(f"<b>Gestore:</b> {h(operator_)}")
    if typdesc:
        lines.append(f"<b>Aeromobile:</b> {h(typdesc)}")
    
    # Live status
    live_parts = []
    if alt_m and alt_ft:
        live_parts.append(f"<b>Alt:</b> <code>{h(alt_m)}</code> m (<code>{h(alt_ft)}</code> ft)")
    if kmh:
        live_parts.append(f"<b>Vel:</b> <code>{h(kmh)}</code> km/h")
    if dist_txt:
        if dir_txt:
            live_parts.append(f"<b>Dist:</b> <code>{h(dist_txt)}</code> km @ <code>{h(dir_txt)}</code>°")
        else:
            live_parts.append(f"<b>Dist:</b> <code>{h(dist_txt)}</code> km")
    
    live_parts.extend([
        f"<b>Vista oggi:</b> <code>{h(today_total)}</code>",
        f"<b>In vista:</b> <code>{h(in_session)}</code>"
    ])
    
    if last_txt:
        live_parts.append(f"<b>Ultimo msg:</b> <code>{h(last_txt)}</code>")
    live_parts.append(f"<b>Sorgente:</b> <code>{h(src)}</code>")
    
    lines.append(" • ".join(live_parts))
    lines.extend([ts, FOOTER])
    
    if tags:
        lines.append(h(tags))
    if links:
        lines.append(" | ".join(links))
    
    return "\n".join(lines)


def is_recent(live: dict) -> bool:
    """Check if aircraft data is recent enough."""
    seen = live.get("seen")
    if seen is None:
        return True
    try:
        return float(seen) <= MAX_SEEN_SEC
    except (ValueError, TypeError):
        return True


# ---------------- MAIN LOOP ----------------
def main():
    """Main monitoring loop."""
    # Load interesting aircraft lists (customize REMOTE_LISTS)
    REMOTE_LISTS = [
        # ("category", "https://raw.githubusercontent.com/user/repo/main/list.csv"),
        # Add your lists here following the CSV format
    ]
    
    db = load_db_lists(REMOTE_LISTS)
    if not db:
        print("No aircraft loaded from lists", file=sys.stderr)
        sys.exit(1)

    con = ensure_db()
    p = Path(READSB_AIRCRAFT_JSON)
    if not p.is_file():
        raise SystemExit(f"Aircraft data not found: {READSB_AIRCRAFT_JSON}")

    st_lat, st_lon = load_station_latlon()
    j = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    aircraft = j.get("aircraft", [])

    now = int(time.time())
    sent = 0

    for a in aircraft:
        hx = safe(a.get("hex", "")).upper()
        if len(hx) != 6:
            continue

        info = db.get(hx)
        if not info:
            continue

        last_notify, first_seen, _day, today_seen = ensure_state_row(con, hx, now)

        # Skip if too old
        seen_s = as_float(a.get("seen"))
        if seen_s is not None and seen_s > MAX_SEEN_SEC:
            close_session_add_today(con, hx, now, first_seen)
            continue

        if not is_recent(a):
            close_session_add_today(con, hx, now, first_seen)
            continue

        # Send notification if cooldown expired
        if should_notify(last_notify, now):
            caption = fmt_caption(info, a, now, first_seen, today_seen, st_lat, st_lon)
            photo_urls = pick_photo_urls(info)
            sent_photo = False

            # Try photos first
            for photo in photo_urls:
                try:
                    send_photo_or_text(photo, caption)
                    sent_photo = True
                    break
                except Exception:
                    continue  # Try next photo

            # Fallback to text
            if not sent_photo:
                try:
                    tg_send_message(caption)
                    sent_photo = True
                except Exception:
                    pass

            if sent_photo:
                set_last_notify(con, hx, now)
                sent += 1

    con.close()
    print(f"[{time.strftime('%H:%M:%S')}] sent={sent} db={len(db)} live={len(aircraft)}", 
          file=sys.stderr)


if __name__ == "__main__":
    main()
