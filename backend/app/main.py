from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.answer_routes import router as answer_router
from app.api.document_routes import router as document_router
from app.api.extraction_routes import router as extraction_router
from app.api.form_routes import router as form_router
from app.api.matching_routes import router as matching_router
from app.api.question_routes import router as question_router
from app.api.voice_routes import router as voice_router

app = FastAPI(
    title="Formless AI Backend",
    version="1.0.0",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(document_router)
app.include_router(form_router)
app.include_router(extraction_router)
app.include_router(matching_router)
app.include_router(question_router)
app.include_router(answer_router)
app.include_router(voice_router)

STATIC_VOICE_HTML = Path(__file__).resolve().parent / "static" / "voice.html"


@app.get("/")
def read_root():
    return {
        "message": "Formless AI Backend is running",
        "version": "1.0.0",
    }


@app.get("/health")
def read_health():
    return {
        "status": "healthy",
    }


@app.get("/voice", response_class=HTMLResponse, tags=["voice"])
def get_voice_interaction_page():
    """Serves the interactive voice question-answering UI."""
    if STATIC_VOICE_HTML.exists():
        return HTMLResponse(content=STATIC_VOICE_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h3>Voice page not found</h3>", status_code=404)
