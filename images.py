import os
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

@router.get("/images")
def get_images(query: str = "Oman tourism", per_page: int = 5):
    headers = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else None
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={per_page}"

    if headers:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            photos = [
                {"url": photo["src"]["medium"], "photographer": photo["photographer"]}
                for photo in data.get("photos", [])
            ]
            if photos:
                return {"source": "pexels", "results": photos}

    # fallback → unsplash بدون API
    unsplash_urls = [
        f"https://source.unsplash.com/800x600/?{query.replace(' ', ',')}&sig={i}"
        for i in range(per_page)
    ]
    photos = [{"url": u, "photographer": "Unsplash"} for u in unsplash_urls]

    return {"source": "unsplash", "results": photos}
