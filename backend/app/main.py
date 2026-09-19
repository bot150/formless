from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.answer_routes import router as answer_router
from app.api.auth_routes import router as auth_router
from app.api.document_routes import router as document_router
from app.api.extraction_routes import router as extraction_router
from app.api.form_routes import router as form_router
from app.api.matching_routes import router as matching_router
from app.api.question_routes import router as question_router
from app.api.voice_routes import router as voice_router
from app.core.config import settings
from app.core.database import Base, engine
import app.models  # Ensures all models are registered before create_all

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Formless AI Backend",
    description="Backend for AI-powered form filling",
    version="1.0.0",
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware — required by Authlib for Google OAuth 2.0 state/nonce management
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key,
)

# ── Register all API routers ────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(document_router)
app.include_router(form_router)
app.include_router(extraction_router)
app.include_router(matching_router)
app.include_router(question_router)
app.include_router(answer_router)
app.include_router(voice_router)

# ── Static HTML pages ───────────────────────────────────────────────────────
_STATIC = Path(__file__).resolve().parent / "static"


@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Formless AI Backend is running", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def read_health():
    return {"status": "healthy"}


@app.get("/auth", response_class=HTMLResponse, tags=["Authentication & Profile"])
def get_auth_page():
    """Serves the authentication UI (Register, Login, Google OAuth)."""
    html = _STATIC / "auth.html"
    if html.exists():
        return HTMLResponse(content=html.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h3>Auth page not found</h3>", status_code=404)


@app.get("/profile/setup", response_class=HTMLResponse, tags=["Authentication & Profile"])
def get_profile_setup_page():
    """Serves the Aadhaar card upload and profile verification UI."""
    html = _STATIC / "profile_setup.html"
    if html.exists():
        return HTMLResponse(content=html.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h3>Profile setup page not found</h3>", status_code=404)


@app.get("/voice", response_class=HTMLResponse, tags=["Voice"])
def get_voice_interaction_page():
    """Serves the interactive voice question-answering UI."""
    html = _STATIC / "voice.html"
    if html.exists():
        return HTMLResponse(content=html.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h3>Voice page not found</h3>", status_code=404)