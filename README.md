# Oman-vista-backend
AI assistant Tourism in Oman
# OmanVista Backend 🌴

This is the backend service for **OmanVista – AI Tourism Explorer**.  
It provides an API to fetch photos and other tourism-related data.

## Endpoints
- `/` → health check
- `/photos?query=Salalah` → fetch tourism photos

## Run locally
```bash
uvicorn main:app --reload --port 8000
