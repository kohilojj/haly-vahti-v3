from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import feedparser
import requests
import re
from datetime import datetime

app = Flask(__name__, static_folder='../')
CORS(app)

# --- GLOBAL INTELLIGENCE SOURCES ---
SOURCES = {
    "FI": {
        "Poliisi": "https://poliisi.fi/ajankohtaista/uutiset/-/asset_publisher/vK9pUnk5iI9i/rss",
        "Hätätiedotteet": "https://112.fi/vaaratiedotteet-rss",
        "Sähköverkko": "https://www.fingrid.fi/sharepoint/syotteet/hairiotiedotteet-rss",
        "Infra": "https://www.hsy.fi/vesi-ja-viemarit/tiedotteet/rss/"
    },
    "SE": {
        "Polisen": "https://polisen.se/aktuellt/rss/hela-landet/handelser-rss/",
        "Krisinfo": "https://api.krisinformation.se/v1/feed?format=rss"
    },
    "US": {
        "Safety": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom",
        "Weather": "https://alerts.weather.gov/cap/us.php?x=1"
    }
}

@app.route('/api/full_feed')
def get_feed():
    country = request.args.get('country', default='FI')
    sources = SOURCES.get(country, SOURCES["FI"])
    all_events = []
    seen = set()

    # AI-AVAINSONAT ERI KATEGORIOILLE
    CRIME_WORDS = ["ryöstö", "väkivalta", "puukotus", "robbery", "assault", "stabbing", "rån", "misshandel", "ase", "weapon"]
    POWER_WORDS = ["sähkökatko", "power outage", "blackout", "strömavbrott", "elavbrott"]
    WATER_WORDS = ["vesikatko", "water outage", "vattentiedote"]

    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.title not in seen:
                    t_lc = entry.title.lower()
                    category = "INFO"
                    reason = ""
                    
                    if any(x in t_lc for x in CRIME_WORDS):
                        category = "STREET_CRIME"
                        reason = "Katurikollisuuden riski: Alueella raportoitu väkivaltaa tai ryöstö."
                    elif any(x in t_lc for x in POWER_WORDS):
                        category = "POWER"
                        reason = "Sähköverkon häiriö alueella."
                    elif any(x in t_lc for x in WATER_WORDS):
                        category = "WATER"
                        reason = "Vesikatko tai vesihuollon häiriö."
                    elif "vaara" in t_lc or "danger" in t_lc or "fara" in t_lc:
                        category = "DANGER"
                        reason = "Yleinen vaaratiedote."

                    all_events.append({
                        "source": name,
                        "title": entry.title,
                        "category": category,
                        "reason": reason,
                        "time": datetime.now().strftime("%H:%M"),
                        "urgent": category in ["STREET_CRIME", "DANGER", "POWER"]
                    })
                    seen.add(entry.title)
        except: continue
    return jsonify(all_events)

@app.route('/api/weather_analysis')
def weather_analysis():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    lang = request.args.get('lang', default='fi')
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,visibility&forecast_days=1"
        r = requests.get(w_url).json()
        curr = r['current']
        
        msgs = {
            "fi": ["✅ Kaikki kunnossa", "⚠️ Liukas tie", "🌫️ Huono näkyvyys"],
            "en": ["✅ All clear", "⚠️ Slippery road", "🌫️ Low visibility"],
            "sv": ["✅ Allt lugnt", "⚠️ Hal väg", "🌫️ Dålig sikt"]
        }
        m_list = msgs.get(lang, msgs["en"])
        msg = m_list[0]
        if curr['temperature_2m'] < 1 and curr['precipitation'] > 0: msg = m_list[1]
        elif curr['visibility'] < 1000: msg = m_list[2]
        return jsonify({"temp": curr['temperature_2m'], "analysis": msg})
    except: return jsonify({"temp": "--", "analysis": "N/A"})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory(app.static_folder, 'index.html')
