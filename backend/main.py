"""
Gender Bias in LLM NPCs — Research Application Backend
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import scenarios, scaffolds, counterfactual, experiments, runner, responses, coding, analysis, export, ollama

app = FastAPI(
    title="Gender Bias LLM NPC Research",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules
app.include_router(scenarios.router)
app.include_router(scaffolds.router)
app.include_router(counterfactual.router)
app.include_router(experiments.router)
app.include_router(runner.router)
app.include_router(responses.router)
app.include_router(coding.router)
app.include_router(analysis.router)
app.include_router(export.router)
app.include_router(ollama.router)


@app.on_event("startup")
def on_startup():
    from database import init_db, migrate_local_json_to_db, is_db_configured
    if is_db_configured():
        init_db()
        migrate_local_json_to_db()


@app.get("/api/health")
def health():
    from database import is_db_configured
    return {
        "status": "ok",
        "database": "neon_postgresql" if is_db_configured() else "local_json"
    }
