# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()

# -----------------------
# CORS برای دسترسی Streamlit
# -----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # برای تست همه بازه، بعد میشه محدود کرد
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# API Keys
# -----------------------
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY", "")

# -----------------------
# API Root
# -----------------------
@app.get("/")
def root():
    return {"message": "OmanVista Backend Running 🚀"}


# -----------------------
# گرفتن عکس
# -----------------------
@app.get("/images")
def get_images(query: str = "Oman tourism"):
    images = []

    # 1) امتحان با Pexels
    if PEXELS_API_KEY:
        try:
            url = "https://api.pexels.com/v1/search"
            headers = {"Authorization": PEXELS_API_KEY}
            params = {"query": query, "per_page": 5}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for photo in data.get("photos", []):
                    images.append(photo["src"]["medium"])
        except Exception as e:
            print("Pexels error:", e)

    # 2) اگر Pexels خالی بود، امتحان با Unsplash (Secret Key)
    if not images and UNSPLASH_SECRET_KEY:
        try:
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {UNSPLASH_SECRET_KEY}"}
            params = {"query": query, "per_page": 5}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for result in data.get("results", []):
                    images.append(result["urls"]["regular"])
        except Exception as e:
            print("Unsplash error:", e)

    # 3) اگر هیچ‌کدوم جواب نداد، از Source Unsplash بدون کلید
    if not images:
        fallback = [
            f"https://source.unsplash.com/800x600/?{query},Oman,{i}"
            for i in range(1, 6)
        ]
        images.extend(fallback)

    return {"query": query, "images": images}


# -----------------------
# گرفتن پست‌ها از Reddit
# -----------------------
@app.get("/reddit")
def get_reddit(subreddit: str = "travel"):
    url = f"https://www.reddit.com/r/{subreddit}/.json?limit=5"
    headers = {"User-Agent": "OmanVistaApp/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        posts = []
        if res.status_code == 200:
            data = res.json()
            for post in data["data"]["children"]:
                p = post["data"]
                posts.append({
                    "title": p.get("title"),
                    "url": "https://reddit.com" + p.get("permalink", "")
                })
        return {"subreddit": subreddit, "posts": posts}
    except Exception as e:
        return {"error": str(e)}
