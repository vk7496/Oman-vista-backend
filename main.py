import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

# Example route: Unsplash images
@app.route("/unsplash")
def get_unsplash_images():
    UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
    if not UNSPLASH_KEY:
        return jsonify({"error": "Missing Unsplash API key"}), 400

    url = "https://api.unsplash.com/photos/random"
    params = {"query": "Oman tourism", "count": 5}
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Example route: Reddit via RSS
@app.route("/reddit")
def get_reddit_feed():
    import feedparser
    feed_url = "https://www.reddit.com/r/travel/.rss"
    feed = feedparser.parse(feed_url)

    posts = []
    for entry in feed.entries[:5]:
        posts.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return jsonify(posts)


# Health check (Railway needs this sometimes)
@app.route("/")
def home():
    return "OmanVista Backend is running ✅"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT automatically
    app.run(host="0.0.0.0", port=port)
