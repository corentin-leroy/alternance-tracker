"""Point d'entrée de l'API FastAPI.

Lancer en local avec :

    uvicorn alternance_tracker.api.main:app --reload

Puis ouvrir http://localhost:8000/docs pour la doc interactive (tu peux y
tester chaque endpoint sans frontend).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import fetch, offers, stats

app = FastAPI(
    title="Alternance Tracker API",
    description="API REST locale par-dessus l'agrégateur d'offres d'alternance.",
    version="0.1.0",
)

# Le frontend React (Vite) tourne sur localhost:5173. En dev on utilise un proxy
# Vite, mais on autorise aussi l'origine directement par sécurité.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Toutes les routes sont préfixées par /api pour les distinguer (et matcher le
# proxy Vite).
app.include_router(offers.router, prefix="/api")
app.include_router(fetch.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}
