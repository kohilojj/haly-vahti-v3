from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import feedparser
import os
import re
import requests
from datetime import datetime

# Flask-sovelluksen alustus
app = Flask(__name__, static_folder='../')
CORS(app)

# --- ÄLYKKÄÄT SUODATTIMET ---
# Poistetaan uutiset, jotka eivät ole akuutteja hälytyksiä
BLACKLIST = [
    "oikeus", "käräjillä", "syyte", "tuomio", "irtisanoo", "ennätys", 
    "päätoimittaja", "analyysi", "kolumni", "mielipide", "historia",
    "palkinto", "arkisto", "digi", "urheilu", "viihde", "pörssi"
]

# Nämä sanat varmistavat, että tärkeät asiat tulevat läpi
PRIORITY = [
    "kadonnut", "etsitään", "kaivataan", "tuntomerkit", "kolari", 
    "onnettomuus", "tulipalo", "vaara", "suljettu", "tie", "räjähdys"
]

@app.route('/api/full_feed')
def get_feed():
    sources = {
        "POLIISI": "https://poliisi.fi/ajankohtaista/uutiset/-/asset_publisher/vK9pUnk5iI9i/rss",
        "POLIISI_HAKU": "https://poliisi.fi/haku/-/asset_publisher/vK9pUnk5iI9i/rss?_101_INSTANCE_vK9pUnk5iI9i_keywords=kadonnut",
        "TILANNEHUONE": "https://www.tilannehuone.fi/haelytykset-rss.php",
        "YLE": "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34837",
        "VAARA": "https://112.fi/vaaratiedotteet-rss"
    }
    
    all_events = []
    seen_titles = set()

    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title.strip()
                title_lc = title.lower()
                
                is_blacklisted = any(word in title_lc for word in BLACKLIST)
                is_priority = any(word in title_lc for word in PRIORITY)
                
                if is_blacklisted and not is_priority:
                    continue

                norm_title = re.sub(r'[^\w\s]', '', title_lc)
                if norm_title not in seen_titles:
                    all_events.append({
                        "id": entry.get('link', title), 
                        "source": name, 
                        "title": title,
                        "is_priority": is_priority,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    seen_titles.add(norm_title)
        except:
            continue
            
    return jsonify(all_events)

@app.route('/api/weather_analysis')
def weather_analysis():
    lat = request.args.get('lat', default=60.17, type=float)
    lon = request.args.get('lon', default=24.94, type=float)
    
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code,visibility,wind_speed_10m&forecast_days=1"
        r = requests.get(w_url).json()
        curr = r['current']
        
        temp = curr['temperature_2m']
        prec = curr['precipitation']
        vis = curr['visibility']
        wind = curr['wind_speed_10m']
        
        analysis = ["✅ Ajokeli on tällä hetkellä vakaa."]
        risk = "Normaali"
        brake = "Normaali"

        if temp < 1 and prec > 0:
            analysis = ["⚠️ MUSTAN JÄÄN VAARA: Tie on erittäin liukas!"]
            risk = "KORKEA"
            brake = "4x Pitempi"
        elif vis < 1000:
            analysis = ["🌫️ HUONO NÄKYVYYS: Sumua tai rankkaa sadetta."]
            risk = "KOHONNUT"
            brake = "Varovasti"

        return jsonify({
            "temp": temp, "analysis": analysis, "risk_level": risk, "braking": brake, "wind": wind
        })
    except:
        return jsonify({"temp": "--", "analysis": ["Sää-AI yhteysvirhe"], "risk_level": "Normaali"})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory(app.static_folder, 'index.html')
