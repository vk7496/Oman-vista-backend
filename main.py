# main.py
import os
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from fastapi import FastAPI

app = FastAPI(title="OmanVista Backend")

# Config (from env)
PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
UNSPLASH_SECRET = os.getenv("UNSPLASH_SECRET_KEY", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))

# Simple in-memory cache
_cache = {}
def cache_get(key):
    v = _cache.get(key)
    if not v:
        return None
    exp, value = v
    if time.time() < exp:
        return value
    _cache.pop(key, None)
    return None

def cache_set(key, value, ttl=CACHE_TTL):
    _cache[key] = (time.time() + ttl, value)

# Root health
@app.get("/")
def root():
    return {"status": "ok", "service": "omanvista-backend"}

# Images endpoint: try Pexels -> Unsplash(secret) -> Unsplash source
@app.get("/images")
def images(q: str = "Oman", per: int = 6):
    cache_key = f"images::{q}::{per}"
    cached = cache_get(cache_key)
    if cached:
        return {"cached": True, **cached}

    imgs = []
    source = None

    # 1) Pexels
    if PEXELS_KEY:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": q, "per_page": per},
                timeout=10,
            )
            if r.ok:
                data = r.json()
                imgs = [p.get("src", {}).get("large") or p.get("src", {}).get("original")
                        for p in data.get("photos", [])]
                imgs = [u for u in imgs if u]
                if imgs:
                    source = "pexels"
        except Exception:
            imgs = []

    # 2) Unsplash (secret key)
    if not imgs and UNSPLASH_SECRET:
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_SECRET}"},
                params={"query": q, "per_page": per},
                timeout=10,
            )
            if r.ok:
                data = r.json()
                imgs = [it["urls"]["regular"] for it in data.get("results", []) if it.get("urls")]
                if imgs:
                    source = "unsplash_secret"
        except Exception:
            imgs = []

    # 3) Unsplash Source fallback (no key, always returns an image url)
    if not imgs:
        imgs = [f"https://source.unsplash.com/1200x800/?{quote_plus(q)},oman&sig={i}" for i in range(1, per+1)]
        source = "unsplash_source"

    payload = {"query": q, "images": imgs, "source": source, "count": len(imgs)}
    cache_set(cache_key, payload)
    return payload

# Reddit (RSS) endpoint
@app.get("/reddit")
def reddit(topic: str = "Oman travel", limit: int = 6):
    cache_key = f"reddit::{topic}::{limit}"
    cached = cache_get(cache_key)
    if cached:
        return {"cached": True, **cached}

    headers = {"User-Agent": "OmanVistaBackend/1.0"}
    endpoints = [
        f"https://www.reddit.com/r/oman/search.rss?q={quote_plus(topic)}&restrict_sr=on&sort=new",
        f"https://www.reddit.com/r/travel/search.rss?q={quote_plus(topic + ' Oman')}&restrict_sr=on&sort=new",
    ]

    posts = []
    try:
        for url in endpoints:
            r = requests.get(url, headers=headers, timeout=10)
            if not r.ok:
                continue
            root = ET.fromstring(r.content)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for it in items:
                title = it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "(no title)"
                link = it.findtext("link")
                if not link:
                    link_el = it.find("{http://www.w3.org/2005/Atom}link")
                    link = link_el.get("href") if link_el is not None else "#"
                posts.append({"title": title, "link": link})
                if len(posts) >= limit:
                    break
            if len(posts) >= limit:
                break
    except Exception:
        posts = []

    if not posts:
        posts = [
            {"title": "Top things to do in Muscat", "link": "#"},
            {"title": "Salalah Khareef travel tips", "link": "#"},
        ]

    payload = {"topic": topic, "posts": posts[:limit]}
    cache_set(cache_key, payload)
    return payload
