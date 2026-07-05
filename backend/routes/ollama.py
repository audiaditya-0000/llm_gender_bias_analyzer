"""
Ollama proxy routes.
Provides the frontend with access to Ollama model information.
"""

from fastapi import APIRouter, HTTPException
from services.ollama import list_models, check_health

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/models")
async def get_models():
    """Return the list of locally available Ollama models."""
    try:
        models = await list_models()
        # Simplify the response for the frontend
        return [
            {
                "name": m.get("name", ""),
                "size": m.get("size", 0),
                "modified_at": m.get("modified_at", ""),
                "digest": m.get("digest", ""),
            }
            for m in models
        ]
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to Ollama: {str(e)}",
        )


@router.get("/health")
async def health_check():
    """Check if Ollama server is reachable."""
    healthy = await check_health()
    return {"healthy": healthy}
