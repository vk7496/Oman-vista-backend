# backend/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, time, random, requests, xml.etree.ElementTree as ET
from urllib.parse import quote_plus

app = FastAPI(title="OmanVista Backend")

# CORS: بعد از تست، allow_origins رو محدود کن به دامنه‌ی front-endت
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config from env
PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
UNSPLASH_SECRET = os.getenv("UNSPLASH_SECRET_KEY", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))

# Simple in-memory cache (process memory — برای دمو کافی است)
_cache = {}

def cache_get(key):
    item = _cache.get(key)
    if not item: return None
    exp, value = item
    if time.time() < exp:
        return value
    _cache.pop(key, None)
    return None

def cache_set(key, value, ttl=CACHE_TTL):
    _cache[key] = (time.time() + ttl, value)

# ---------- Images endpoint: try Pexels -> Unsplash(secret) -> Unsplash source fallback
@app.get("/images")
def images(q: str = "Oman", per: int = 6):
    key = f"images::{q}::{per}"
    cached = cache_get(key)
    if cached:
        return {"cached": True, **cached}

    imgs = []
    source = None

    # Pexels
    if PEXELS_KEY:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                             headers={"Authorization": PEXELS_KEY},
                             params={"query": q, "per_page": per}, timeout=10)
            if r.ok:
                data = r.json()
                imgs = [p["src"].get("large") or p["src"].get("medium") for p in data.get("photos", [])]
                imgs = [u for u in imgs if u]
                if imgs:
                    source = "pexels"
        except Exception:
            imgs = []

    # Unsplash (secret key) - search endpoint
    if not imgs and UNSPLASH_SECRET:
        try:
            r = requests.get("https://api.unsplash.com/search/photos",
                             headers={"Authorization": f"Client-ID {UNSPLASH_SECRET}"},
                             params={"query": q, "per_page": per}, timeout=10)
            if r.ok:
                data = r.json()
                imgs = [res["urls"]["regular"] for res in data.get("results", []) if res.get("urls")]
                if imgs:
                    source = "unsplash_secret"
        except Exception:
            imgs = []

    # Unsplash source fallback (no key)
    if not imgs:
        imgs = [f"https://source.unsplash.com/1200x800/?{quote_plus(q)},oman&sig={i}" for i in range(1, per+1)]
        source = "unsplash_source"

    payload = {"query": q, "images": imgs, "source": source, "count": len(imgs)}
    cache_set(key, payload)
    return payload

# ---------- Reddit RSS endpoint (r/oman + r/travel search)
@app.get("/reddit")
def reddit(topic: str = "Oman travel", limit: int = 6):
    key = f"reddit::{topic}::{limit}"
    cached = cache_get(key)
    if cached:
        return {"cached": True, **cached}

    endpoints = [
        f"https://www.reddit.com/r/oman/search.rss?q={quote_plus(topic)}&restrict_sr=on&sort=new",
        f"https://www.reddit.com/r/travel/search.rss?q={quote_plus(topic + ' Oman')}&restrict_sr=on&sort=new",
    ]
    posts = []
    headers = {"User-Agent": "OmanVistaBackend/1.0"}
    try:
        for url in endpoints:
            r = requests.get(url, headers=headers, timeout=10)
            if not r.ok:
                continue
            root = ET.fromstring(r.content)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for it in items:
                title = it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "(no title)"
                link = it.findtext("link") or (it.find("{http://www.w3.org/2005/Atom}link").get("href") if it.find("{http://www.w3.org/2005/Atom}link") is not None else "#")
                posts.append({"title": title, "link": link})
                if len(posts) >= limit:
                    break
            if len(posts) >= limit:
                break
    except Exception:
        posts = []

    # fallback offline posts
    if not posts:
        posts = [
            {"title": "Top things to do in Muscat", "link": "#"},
            {"title": "Salalah Khareef travel tips", "link": "#"}
        ]

    payload = {"topic": topic, "posts": posts[:limit]}
    cache_set(key, payload)
    return payload

# ---------- Health
@app.get("/health")
def health():
    return {"ok": True, "ts": int(time.time())}
