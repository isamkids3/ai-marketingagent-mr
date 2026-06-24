from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure shares directory exists
shares_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "shares"))
os.makedirs(shares_dir, exist_ok=True)

# Mount shares static folder
app.mount("/shares", StaticFiles(directory=shares_dir), name="shares")

# Sandbox Environment Setup (Additive)
from pathlib import Path
BASE_WORKSPACE = Path(os.getenv("SHARED_WORKSPACE_ROOT", str(Path(__file__).parent.parent / "gen-content"))).resolve()
try:
    os.makedirs(BASE_WORKSPACE, exist_ok=True)
except Exception as e:
    import logging
    logging.warning(f"Could not create BASE_WORKSPACE: {e}")

# Mount the sandbox static folder
app.mount("/sandbox", StaticFiles(directory=str(BASE_WORKSPACE)), name="sandbox")

# Include the API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": "/docs",
    }