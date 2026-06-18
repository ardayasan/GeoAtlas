from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os


class NoCacheStaticFiles(StaticFiles):
    """Statik dosyalara 'no-cache' ekler: tarayıcı her istekte ETag ile
    yeniden doğrular (değişmemişse 304). Böylece güncellenen JS/CSS bayat
    cache'ten servis edilmez — 'tarayıcıda eski sürüm' hatalarını önler."""
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

from routers import boundaries, poi, demographics, groups, labels, excel_upload, regions, chat
from services.db_service import init_db

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Veritabanı hazır.")
    print("Uygulama başlatıldı → http://localhost:8000")
    yield


app = FastAPI(
    title="Türkiye GIS Uygulaması",
    description="Türkiye il/ilçe sınırları, POI ve demografik veri görselleştirme API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── API Routers — mount'tan ÖNCE kayıtlanmalı ──────────────────────
app.include_router(boundaries.router,   prefix="/api/boundaries",  tags=["Sınırlar"])
app.include_router(regions.router,      prefix="/api/regions",     tags=["Avrupa Bölgeleri"])
app.include_router(poi.router,          prefix="/api/poi",         tags=["POI"])
app.include_router(demographics.router, prefix="/api/demographics", tags=["Demografik"])
app.include_router(groups.router,       prefix="/api/groups",      tags=["Gruplar"])
app.include_router(labels.router,       prefix="/api/labels",      tags=["Etiketler"])
app.include_router(excel_upload.router, prefix="/api/excel",       tags=["Excel"])
app.include_router(chat.router,         prefix="/api/chat",        tags=["Asistan"])


@app.get("/api/health", tags=["Sistem"])
async def health_check():
    return {"status": "ok", "message": "Türkiye GIS API çalışıyor"}


# ── Frontend statik dosyalar (EN SONA — catch-all olarak) ──────────
# html=True  → / isteğinde index.html döner, bulunamayan path'lerde de.
# Mount "/" olduğu için HTML içindeki "css/style.css" gibi
# göreceli yollar doğrudan çözümlenir: GET /css/style.css → frontend/css/style.css
app.mount("/", NoCacheStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
