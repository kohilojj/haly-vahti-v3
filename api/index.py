from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import feedparser
import os
import re
import requests
from datetime import datetime

app = Flask(__name__, static_folder='../')
CORS(app)

# --- ASETUKSET JA SUODATTIMET ---

# Estetään turhat uutiset, jotka eivät ole hälytyksiä
BLACKLIST = [
    "oikeus", "käräjillä", "syyte", "tuomio", "päätoimittaja", 
    "muutosneuvottelut", "irtisanoo", "ennätyslukemiin", "tutkimus", 
    "analyysi", "kolumni", "mielipide", "historia", "palkinto", 
    "arkisto", "digi", "urheilu", "viihde", "pörssi"
]

# Nämä sanat ohittavat suodattimen (Priority)
PRIORITY = [
    "kadonnut", "etsitään", "kaivataan", "tuntomerkit", "kolari", 
    "onnettomuus", "tulipalo", "vaara", "suljettu", "tie", "räjähdys"
]

# --- REIPPAASTI LAAJENNETTU TIEDONHAKU ---

@app.route('/api/full_feed')
def get_feed():
    sources = {
        "POLIISI": "https://poliisi.fi/ajankohtaista/uutiset/-/asset_publisher/vK9pUnk5iI9i/rss",
        "POLIISI_HAKU": "https://poliisi.fi/haku/-/asset_publisher/vK9pUnk5iI9i/rss?_101_INSTANCE_vK9pUnk5iI9i_keywords=kadonnut",
        "TILANNEHUONE": "https://www.tilannehuone.fi/haelytykset-rss.php",
        "YLE_KOTIMAA": "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34837",
        "VAARA_112": "https://112.fi/vaaratiedotteet-rss"
    }
    
    all_events = []
    seen_titles = set()

    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title.strip()
                title_lc = title.lower()
                
                # 1. Älykäs suodatus (Gettomasat ja talousuutiset pois)
                is_blacklisted = any(word in title_lc for word in BLACKLIST)
                is_priority = any(word in title_lc for word in PRIORITY)
                
                if is_blacklisted and not is_priority:
                    continue

                # 2. Kaksoiskappaleiden esto (Deduplication)
                # Puhdistetaan otsikko vertailua varten
                norm_title = re.sub(r'[^\w\s]', '', title_lc)
                if norm_title not in seen_titles:
                    all_events.append({
                        "id": entry.get('link', title), 
                        "source": name, 
                        "title": title, 
                        "summary": entry.get('summary', ""),
                        "is_priority": is_priority,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    seen_titles.add(norm_title)
        except Exception as e:
            print(f"Virhe lähteessä {name}: {e}")
            
    return jsonify(all_events)

# --- SÄÄ-AI JA TURVALLISUUSANALYYSY ---

@app.route('/api/weather_analysis')
def weather_analysis():
    # Haetaan koordinaatit selaimelta (oletus Helsinki)
    lat = request.args.get('lat', default=60.17, type=float)
    lon = request.args.get('lon', default=24.94, type=float)
    
    try:
        # Open-Meteo API haku
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,snowfall,weather_code,visibility,wind_speed_10m&forecast_days=1"
        res = requests.get(weather_url).json()
        current = res['current']
        
        temp = current['temperature_2m']
        precip = current['precipitation']
        snow = current['snowfall']
        vis = current['visibility']
        wind = current['wind_speed_10m']
        code = current['weather_code']
        
        analysis = []
        risk_level = "Normaali"
        braking_dist = "Normaali"

        # 1. Liukkaustutka
        if temp > -1 and temp < 1.5 and precip > 0:
            analysis.append("⚠️ MUSTAN JÄÄN VAARA: Lämpötila nollassa ja sataa vettä!")
            risk_level = "KORKEA"
            braking_dist = "Erittäin pitkä (liukasta)"
        elif temp < 0 and snow > 0:
            analysis.append("❄️ LUMISADE: Tie on liukas ja sohjoutuu.")
            risk_level = "KOHONNUT"
            braking_dist = "Pidentynyt (lumi)"
        
        # 2. Sumu ja näkyvyys
        if vis < 400:
            analysis.append("🌫️ VAARALLINEN SUMU: Näkyvyys lähes nolla!")
            risk_level = "VAARALLINEN"
        elif vis < 1500:
            analysis.append("🌫️ HEIKKO NÄKYVYYS: Sumua tai rankkasadetta.")

        # 3. Myrsky ja ukkonen
        if code in [95, 96, 99]:
            analysis.append("⚡ UKKOSMYRSKY: Voimakas salamointi mahdollista.")
            risk_level = "KORKEA"

        if not analysis:
            analysis.append("✅ Ajokeli on tällä hetkellä vakaa.")

        return jsonify({
            "temp": temp,
            "analysis": analysis,
            "risk_level": risk_level,
            "braking": braking_dist,
            "wind": wind
        })
    except Exception as e:
        return jsonify({"analysis": ["Sääpalveluun ei saada yhteyttä"], "risk_level": "Normaali", "temp": "--"})

# --- STAATTISET TIEDOSTOT ---

@app.route('/')
def serve_index():
    return send_from_directory(os.path.join(app.root_path, '../'), 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
