from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.v1.router import api_router
from app.core.config import settings

from contextlib import asynccontextmanager
import subprocess
import time

ngrok_process = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ngrok_process
    import urllib.request
    
    # Check if ngrok is already running on port 4040
    is_running = False
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=0.2) as response:
            is_running = True
    except Exception:
        pass
        
    if not is_running:
        try:
            ngrok_bin = "ngrok"
            if os.path.exists("/opt/homebrew/bin/ngrok"):
                ngrok_bin = "/opt/homebrew/bin/ngrok"

            ngrok_cmd = [ngrok_bin, "http", "8000", "--log=stdout"]
            ngrok_token = os.getenv("NGROK_AUTHTOKEN")
            if ngrok_token:
                ngrok_cmd.extend(["--authtoken", ngrok_token])

            ngrok_process = subprocess.Popen(
                ngrok_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("Started ngrok tunnel process in background.")
            time.sleep(1.0)
        except Exception as e:
            import logging
            logging.warning(f"Failed to start ngrok automatically: {e}")
            
    yield
    
    if ngrok_process:
        print("Stopping ngrok tunnel process...")
        ngrok_process.terminate()
        ngrok_process.wait()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
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
from dotenv import load_dotenv

load_dotenv()

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