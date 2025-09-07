# Oman-vista-backend
AI assistant Tourism in Oman
# OmanVista Backend (minimal)

Endpoints:
- GET `/`          -> health
- GET `/images?q=Muscat&per=6` -> images (Pexels -> Unsplash fallback)
- GET `/reddit?topic=Oman travel&limit=6` -> reddit posts via RSS

Deploy (Railway):
1. Push repo to GitHub.
2. In Railway create New Project -> Deploy from GitHub -> select this repo.
3. In Railway Service -> Variables add:
   - PEXELS_API_KEY
   - UNSPLASH_SECRET_KEY
4. Deploy. Use the generated domain (e.g. https://your-app.up.railway.app).

