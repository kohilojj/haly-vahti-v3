from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import feedparser
import os
import re

app = Flask(__name__, static_folder='../')
CORS(app)

# SANAT JOTKA ESTETÄÄN (Blacklist)
# Jos uutinen sisältää jonkun näistä, se jätetään väliin
BLACKLIST = [
    "oikeus", "käräjillä", "syyte", "tuomio", "päätoimittaja", 
    "muutosneuvottelut", "irtisanoo", "ennätyslukemiin", "tutkimus", 
    "analyysi", "kolumni", "mielipide", "kuollut", "historia",
    "vuosipäivä", "tilasto", "prosenttia", "palkinto", "arkisto"
]

# SANAT JOTKA HYVÄKSYTÄÄN (Priority)
# Nämä pääsevät aina läpi
PRIORITY = ["kadonnut", "etsitään", "kolar", "tulipalo", "onnettomuus", "vaara", "hälytys", "suljettu"]

@app.route('/')
def serve_index():
    return send_from_directory(os.path.join(app.root_path, '../'), 'index.html')

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
                
                # 1. Tarkista onko uutinen blacklistalla
                is_blacklisted = any(word in title_lc for word in BLACKLIST)
                
                # 2. Tarkista onko uutisessa prioriteettisana (kuten "kolari")
                is_priority = any(word in title_lc for word in PRIORITY)
                
                # Suodatus: Jos on blacklistalla EIKÄ ole prioriteetti, skipataan
                if is_blacklisted and not is_priority:
                    continue

                # 3. Kaksoiskappaleiden esto
                norm_title = re.sub(r'[^\w\s]', '', title_lc)
                if norm_title not in seen_titles:
                    all_events.append({
                        "id": entry.get('link', title), 
                        "source": name, 
                        "title": title, 
                        "summary": entry.get('summary', ""),
                        "is_priority": is_priority
                    })
                    seen_titles.add(norm_title)
        except:
            continue
            
    return jsonify(all_events)
