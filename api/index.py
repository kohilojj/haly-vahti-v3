from flask import Flask, jsonify
from flask_cors import CORS
import feedparser

app = Flask(__name__)
CORS(app)

@app.route('/api/full_feed')
def get_feed():
    sources = {
        "VAARA": "https://112.fi/vaaratiedotteet-rss",
        "POLIISI": "https://poliisi.fi/ajankohtaista/uutiset/-/asset_publisher/vK9pUnk5iI9i/rss",
        "PELASTUS": "https://www.tilannehuone.fi/haelytykset-rss.php"
    }
    all_events = []
    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                all_events.append({
                    "id": entry.link, 
                    "source": name, 
                    "title": entry.title, 
                    "summary": entry.summary if hasattr(entry, 'summary') else ""
                })
        except:
            pass
    return jsonify(all_events)

app = app
