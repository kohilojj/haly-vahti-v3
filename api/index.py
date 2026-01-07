from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import feedparser
import requests
import re
import os
from datetime import datetime

app = Flask(__name__, static_folder='../')
CORS(app)

# MAAKOHTAISET LÄHTEET (Pidetään erillään)
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
        "Safety": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.atom",
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
                    # Sähkökatko-analyysi
                    is_power_outage = any(x in title.lower() for x in ["sähkökatko", "strömavbrott", "power outage", "blackout"])
                    
                    all_events.append({
                        "source": name,
                        "title": title,
                        "is_outage": is_power_outage,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    seen.add(title)
        except: continue
    return jsonify(all_events)

@app.route('/api/weather_analysis')
def weather_analysis():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    lang = request.args.get('lang', default='fi')
    
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code,visibility&forecast_days=1"
        r = requests.get(w_url).json()
        curr = r['current']
        
        # Kansainvälinen AI-viesti
        messages = {
            "fi": ["✅ Kaikki kunnossa", "⚠️ Liukas tie", "🌫️ Huono näkyvyys"],
            "en": ["✅ All clear", "⚠️ Slippery road", "🌫️ Low visibility"],
            "sv": ["✅ Allt lugnt", "⚠️ Hal väg", "🌫️ Dålig sikt"]
        }
        
        m_list = messages.get(lang, messages["en"])
        msg = m_list[0]
        if curr['temperature_2m'] < 1 and curr['precipitation'] > 0: msg = m_list[1]
        elif curr['visibility'] < 1000: msg = m_list[2]

        return jsonify({"temp": curr['temperature_2m'], "analysis": msg})
    except:
        return jsonify({"temp": "--", "analysis": "Error"})
