from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import engine, Base
from routers import auth, public, baotri, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 PCCC API starting...")
    yield
    # Shutdown
    print("👋 PCCC API shutting down...")


app = FastAPI(
    title="PCCC System API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,   prefix="/api/auth",   tags=["Auth"])
app.include_router(public.router, prefix="/api/public", tags=["Public"])
app.include_router(baotri.router, prefix="/api/baotri", tags=["Bảo trì"])
app.include_router(admin.router,  prefix="/api/admin",  tags=["Admin"])

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}