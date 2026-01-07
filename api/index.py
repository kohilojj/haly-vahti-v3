from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import feedparser
import os
import re

app = Flask(__name__, static_folder='../')
CORS(app)

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
    seen_titles = set() # Estetään samat otsikot jo tässä vaiheessa

    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title.strip()
                
                # Yksinkertainen normalisointi: poistetaan välimerkit vertailun ajaksi
                norm_title = re.sub(r'[^\w\s]', '', title.lower())
                
                if norm_title not in seen_titles:
                    all_events.append({
                        "id": entry.get('link', title), 
                        "source": name, 
                        "title": title, 
                        "summary": entry.get('summary', ""),
                        "published": entry.get('published', "")
                    })
                    seen_titles.add(norm_title)
        except:
            continue
            
    return jsonify(all_events)
