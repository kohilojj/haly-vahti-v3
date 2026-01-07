from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import feedparser
import requests
import re
import os
from datetime import datetime

# Vercel-ympäristössä static_folder pitää osoittaa juureen, jotta index.html löytyy
app = Flask(__name__, static_folder='../')
CORS(app)

# --- GLOBAALIT LÄHTEET ---
# Nämä agentit vahtivat eri maita erikseen
SOURCES = {
    "FI": {
        "Poliisi": "https://poliisi.fi/ajankohtaista/uutiset/-/asset_publisher/vK9pUnk5iI9i/rss",
        "112_Vaara": "https://112.fi/vaaratiedotteet-rss",
        "Sähkökatkot": "https://www.fingrid.fi/sharepoint/syotteet/hairiotiedotteet-rss"
    },
    "SE": {
        "Polisen": "https://polisen.se/aktuellt/rss/hela-landet/handelser-rss/",
        "Krisinfo": "https://api.krisinformation.se/v1/feed?format=rss"
    },
    "US": {
        "USGS_Quakes": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom",
        "Weather_Alerts": "https://alerts.weather.gov/cap/us.php?x=1"
    }
}

@app.route('/api/full_feed')
def get_feed():
    country = request.args.get('country', default='FI')
    sources = SOURCES.get(country, SOURCES["FI"])
    all_events = []
    seen = set()

    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                if title not in seen:
                    # AI-tunnistus sähkökatkoille (Suomi, Ruotsi, Englanti)
                    outage_words = ["sähkökatko", "power outage", "blackout", "strömavbrott", "elavbrott"]
                    is_outage = any(word in title.lower() for word in outage_words)
                    
                    all_events.append({
                        "id": entry.get('link', title),
                        "source": name,
                        "title": title,
                        "is_outage": is_outage,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    seen.add(title)
        except Exception as e:
            continue
            
    # Palautetaan vain tuoreimmat uutiset
    return jsonify(all_events[:40])

@app.route('/api/weather_analysis')
def weather_analysis():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    lang = request.args.get('lang', default='fi')
    
    try:
        # Haetaan sää Open-Meteo API:sta
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code,visibility&forecast_days=1"
        r = requests.get(w_url).json()
        curr = r['current']
        
        # Monikieliset AI-viestit
        translations = {
            "fi": ["✅ Kaikki kunnossa", "⚠️ Liukas tie", "🌫️ Huono näkyvyys"],
            "en": ["✅ All clear", "⚠️ Slippery roads", "🌫️ Low visibility"],
            "sv": ["✅ Allt lugnt", "⚠️ Hal väg", "🌫️ Dålig sikt"]
        }
        
        m = translations.get(lang, translations["en"])
        msg = m[0]
        if curr['temperature_2m'] < 1 and curr['precipitation'] > 0:
            msg = m[1]
        elif curr['visibility'] < 1000:
            msg = m[2]

        return jsonify({
            "temp": curr['temperature_2m'],
            "analysis": msg,
            "precip": curr['precipitation']
        })
    except:
        return jsonify({"temp": "--", "analysis": "N/A"})

# Tärkeä reitti: Jos osoite ei ole /api, lähetetään index.html
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    app.run()
