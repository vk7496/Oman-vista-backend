import os
import time
import random
import requests
from collections import defaultdict, deque
from urllib.parse import quote_plus

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ---------- Config ----------
PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
CACHE_TTL = 600          # seconds (10 minutes)
RATE_LIMIT = 60          # requests per 60s per IP per endpoint
WINDOW_SECS = 60
USER_AGENT = "OmanVistaBackend/1.0 (+contact: hello@goldenbird.example)"

# ---------- App ----------
app = FastAPI(title="OmanVista Backend", version="1.0.0")

# CORS: برای تست بازه، بعداً دامنه Streamlit خودت رو جایگزین کن
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <--- در پروDUCTION محدود کن به دامنه خودت
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

# ---------- Simple Cache ----------
CACHE: dict[str, tuple[float, dict]] = {}

def cache_get(key: str):
    item = CACHE.get(key)
    if not item:
        return None
    exp, data = item
    if time.time() < exp:
        return data
    CACHE.pop(key, None)
    return None

def cache_set(key: str, data: dict, ttl: int = CACHE_TTL):
    CACHE[key] = (time.time() + ttl, data)

# ---------- Simple Rate Limit ----------
WINDOWS: dict[str, deque] = defaultdict(deque)

def check_rate(key: str):
    now = time.time()
    dq = WINDOWS[key]
    # prune old
    while dq and dq[0] <= now - WINDOW_SECS:
        dq.popleft()
    if len(dq) >= RATE_LIMIT:
        return False
    dq.append(now)
    return True

def client_key(request: Request, endpoint: str):
    ip = request.client.host if request.client else "unknown"
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        ip = fwd.split(",")[0].strip()
    return f"{endpoint}:{ip}"

# ---------- Providers ----------
def pexels_images(query: str, per: int = 6) -> list[str]:
    if not PEXELS_KEY:
        return []
    try:
        r = session.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": per},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        photos = data.get("photos", [])
        return [p["src"]["large"] for p in photos if p.get("src", {}).get("large")]
    except Exception:
        return []

def unsplash_images(query: str, per: int = 6) -> list[str]:
    # بدون کلید: از source.unsplash.com استفاده می‌کنیم و URL نهایی را برمی‌گردانیم
    urls = set()
    for _ in range(per * 2):  # کمی بیشتر سعی کن تا تکراری نشه
        try:
            url = f"https://source.unsplash.com/1600x900/?{quote_plus(query)}&sig={random.randint(1,10_000_000)}"
            resp = session.get(url, timeout=12, allow_redirects=True)
            if resp.status_code == 200 and resp.url:
                urls.add(resp.url)
            if len(urls) >= per:
                break
        except Exception:
            continue
    return list(urls)[:per]

WIKIMEDIA_FALLBACKS = [
    # مسیرهای امنی که قبلاً تست کرده‌ایم
    "https://upload.wikimedia.org/wikipedia/commons/5/5d/Muscat_Oman_sunset.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/f/f4/Muscat_City.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/6/6d/Salalah_beach.jpg",
]

def fallback_images(per: int = 6) -> list[str]:
    if not WIKIMEDIA_FALLBACKS:
        return [f"https://placehold.co/1200x800?text=OmanVista"] * per
    out = []
    i = 0
    while len(out) < per:
        out.append(WIKIMEDIA_FALLBACKS[i % len(WIKIMEDIA_FALLBACKS)])
        i += 1
    return out

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"ok": True, "ts": int(time.time())}

@app.get("/images")
def images(request: Request, q: str = "Oman", per: int = 6):
    key = client_key(request, "images")
    if not check_rate(key):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    cache_key = f"images::{q}::{per}"
    cached = cache_get(cache_key)
    if cached:
        return dict(cached, cached=True)

    # 1) Try Pexels
    imgs = pexels_images(q, per=per)
    source = "pexels" if imgs else None

    # 2) Fallback to Unsplash
    if not imgs:
        imgs = unsplash_images(q, per=per)
        source = "unsplash" if imgs else None

    # 3) Final Fallback to Wikimedia/Placeholder
    if not imgs:
        imgs = fallback_images(per=per)
        source = "fallback"

    payload = {"query": q, "images": imgs, "source": source, "cached": False}
    cache_set(cache_key, payload)
    return payload

@app.get("/reddit")
def reddit(request: Request, topic: str = "Oman travel", limit: int = 8):
    key = client_key(request, "reddit")
    if not check_rate(key):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    cache_key = f"reddit::{topic}::{limit}"
    cached = cache_get(cache_key)
    if cached:
        return dict(cached, cached=True)

    # دو فید: r/oman و r/travel
    endpoints = [
        f"https://www.reddit.com/r/oman/search.rss?q={quote_plus(topic)}&restrict_sr=on&sort=new",
        f"https://www.reddit.com/r/travel/search.rss?q={quote_plus(topic+' Oman')}&restrict_sr=on&sort=new",
    ]
    posts = []
    try:
        for url in endpoints:
            r = session.get(url, timeout=12)
            r.raise_for_status()
            # پارس ساده با xml
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            for it in items[:limit]:
                title = it.findtext("title") or "(no title)"
                link = it.findtext("link") or "#"
                posts.append({"title": title, "link": link})
        # یکتا و محدودسازی
        uniq = []
        seen = set()
        for p in posts:
            if p["link"] in seen:
                continue
            seen.add(p["link"])
            uniq.append(p)
            if len(uniq) >= limit:
                break
        payload = {"topic": topic, "posts": uniq, "cached": False}
        cache_set(cache_key, payload)
        return payload
    except Exception as e:
        # fallback آفلاین
        payload = {
            "topic": topic,
            "posts": [
                {"title": "Top things to do in Muscat", "link": "#"},
                {"title": "Salalah in Khareef season tips", "link": "#"},
            ],
            "cached": False,
            "note": "fallback",
        }
        cache_set(cache_key, payload, ttl=120)
        return payload
